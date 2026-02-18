"""
Pipeline orchestration service for MDInsights.

Coordinates collection → classification → reporting workflow with
comprehensive error handling and progress tracking.
"""
from datetime import datetime
from typing import Dict, Optional
import asyncio
import os
import structlog
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import NewsArticle, Run, RunStatus
from app.services.collector import ApifyCollector
from app.services.classifier import RoleClassificationService
from app.services.reporter import RoleReportService
from app.services.emailer import GraphEmailService
from app.services.health_monitor import SourceHealthMonitor
from app.config import get_settings
from app.auth.token_manager import TokenManager

# Project root directory (absolute path for reliable file operations)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = structlog.get_logger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates complete MDInsights pipeline.

    Coordinates collection → classification → reporting workflow with
    transaction management and structured logging.
    """

    def __init__(
        self,
        collector: ApifyCollector,
        classifier: RoleClassificationService,
        reporter: RoleReportService,
        token_manager: Optional[TokenManager] = None
    ):
        """
        Initialize pipeline orchestrator with service dependencies.

        Args:
            collector: ApifyCollector for news collection
            classifier: RoleClassificationService for article classification
            reporter: RoleReportService for HTML report generation
            token_manager: Optional TokenManager for MMC Core API JWT auth.
                           When None (default), pipeline runs without enterprise
                           auth (degraded_auth=True, Graph API fallback for email).
        """
        self.collector = collector
        self.classifier = classifier
        self.reporter = reporter
        self.token_manager = token_manager
        self.logger = logger.bind(service="pipeline")

    def run_full_pipeline(self) -> Dict:
        """
        Execute complete pipeline from collection to report generation.

        Steps:
        0. Authenticate to MMC Core API (optional — degrades gracefully if not configured)
        1. Collect articles from enabled sources (creates Run internally)
        2. Query collected articles for classification
        3. Classify articles with Azure OpenAI
        4. Generate unified HTML report for all roles
        5. Update Run record with final status

        Returns:
            Dictionary with pipeline results:
                - run_id: Run record ID
                - articles_collected: Number of articles collected
                - articles_classified: Number of articles classified
                - html_output: Generated HTML report
                - degraded_auth: True if JWT unavailable (Graph API fallback for email)
                - status: Pipeline status (completed/failed)
                - error: Error message if failed
        """
        db = SessionLocal()
        result = {
            "run_id": None,
            "articles_collected": 0,
            "articles_classified": 0,
            "html_output": None,
            "degraded_auth": True,
            "status": "failed",
            "error": None
        }

        try:
            self.logger.info("pipeline_started")
            start_time = datetime.utcnow()

            # Step 0: Authenticate to MMC Core API
            # degraded_auth defaults to True (safe: Graph API fallback)
            # Auth failure NEVER blocks the pipeline — logs warning and continues
            degraded_auth = True
            if self.token_manager and self.token_manager.is_configured():
                self.logger.info("step_0_auth_started")
                import asyncio as _asyncio
                try:
                    loop = _asyncio.get_event_loop()
                    if loop.is_running():
                        # If already in async context, create a task
                        token = None  # run_full_pipeline is sync; token_manager is async
                    else:
                        token = loop.run_until_complete(self.token_manager.get_token())
                except RuntimeError:
                    token = _asyncio.run(self.token_manager.get_token())
                if token:
                    degraded_auth = False
                    self.logger.info("step_0_auth_completed", degraded_auth=False)
                else:
                    self.logger.warning(
                        "step_0_auth_failed",
                        degraded_auth=True,
                        message="JWT acquisition failed, email will use Graph API fallback"
                    )
            else:
                self.logger.info(
                    "step_0_auth_skipped",
                    reason="MMC auth not configured" if not self.token_manager else "TokenManager not configured"
                )
            result["degraded_auth"] = degraded_auth

            # Step 1: Collect articles (collector creates Run internally)
            self.logger.info("step_1_collection_started")
            articles_collected = self.collector.collect_from_sources()
            result["articles_collected"] = articles_collected

            self.logger.info(
                "step_1_collection_completed",
                articles_collected=articles_collected
            )

            # Query latest Run to get run_id
            latest_run = db.query(Run).order_by(Run.id.desc()).first()

            if not latest_run:
                error_msg = "No Run record found after collection"
                self.logger.error("pipeline_failed", error=error_msg)
                result["error"] = error_msg
                return result

            result["run_id"] = latest_run.id
            self.logger.info("run_identified", run_id=latest_run.id)

            # Step 1b: Source health check
            self.logger.info("step_1b_health_check_started")
            health_monitor = SourceHealthMonitor()
            health_results = health_monitor.check_all_sources(db)
            alerts = [r for r in health_results if r["alert"]]

            if alerts:
                # Log alert summary
                alert_summary = health_monitor.format_alert_summary(alerts)
                self.logger.warning("source_health_alerts", alert_count=len(alerts), summary=alert_summary)
                result["health_alerts"] = len(alerts)
            else:
                self.logger.info("step_1b_health_check_passed", sources_checked=len(health_results))
                result["health_alerts"] = 0

            # Step 2: Query collected articles for this run
            self.logger.info("step_2_querying_articles", run_id=latest_run.id)
            articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == latest_run.id
            ).all()

            if not articles:
                self.logger.warning(
                    "no_articles_to_classify",
                    run_id=latest_run.id
                )
                result["status"] = "completed"
                result["html_output"] = "<html><body><h1>No articles collected</h1></body></html>"
                return result

            self.logger.info(
                "step_2_articles_queried",
                article_count=len(articles)
            )

            # Step 3: Classify articles
            self.logger.info("step_3_classification_started")
            articles_classified = self.classifier.classify_articles(db, articles)
            result["articles_classified"] = articles_classified

            self.logger.info(
                "step_3_classification_completed",
                articles_classified=articles_classified
            )

            # Step 4: Re-query classified articles
            self.logger.info("step_4_querying_classified_articles")
            classified_articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == latest_run.id,
                NewsArticle.roles.isnot(None)
            ).all()

            self.logger.info(
                "step_4_classified_articles_queried",
                classified_count=len(classified_articles)
            )

            # Step 5: Generate report
            self.logger.info("step_5_report_generation_started")
            report_date = datetime.utcnow()
            html_output = self.reporter.generate_role_brief(
                articles=classified_articles,
                report_date=report_date
            )
            result["html_output"] = html_output

            self.logger.info(
                "step_5_report_generation_completed",
                html_length=len(html_output)
            )

            # Step 5b: Generate per-role reports and archive to disk
            self.logger.info("step_5b_archiving_reports")
            role_emails = self.reporter.generate_role_emails(
                articles=classified_articles,
                report_date=report_date
            )
            date_str = report_date.strftime("%Y-%m-%d")
            reports_archived = []
            for role, html in role_emails.items():
                role_dir = os.path.join(PROJECT_ROOT, "data", "reports", role.lower())
                os.makedirs(role_dir, exist_ok=True)
                report_path = os.path.join(role_dir, f"{date_str}.html")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(html)
                reports_archived.append(report_path)
            self.logger.info(
                "step_5b_archiving_completed",
                files_archived=len(reports_archived)
            )

            # Step 6: Update Run record
            latest_run.articles_classified = articles_classified
            latest_run.status = RunStatus.COMPLETED
            db.commit()

            self.logger.info("step_6_run_updated", run_id=latest_run.id)

            # Calculate duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result["status"] = "completed"

            self.logger.info(
                "pipeline_completed",
                run_id=latest_run.id,
                articles_collected=articles_collected,
                articles_classified=articles_classified,
                degraded_auth=degraded_auth,
                duration_seconds=round(duration, 2)
            )

            return result

        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg

            self.logger.error(
                "pipeline_failed",
                error=error_msg,
                exc_info=True
            )

            # Update Run record if we have it
            if result["run_id"]:
                try:
                    run = db.query(Run).filter(Run.id == result["run_id"]).first()
                    if run:
                        run.status = RunStatus.FAILED
                        run.error_message = error_msg
                        db.commit()
                except Exception as update_error:
                    self.logger.error(
                        "run_update_failed",
                        error=str(update_error)
                    )

            return result

        finally:
            db.close()

    async def run_full_pipeline_with_email(self) -> Dict:
        """
        Execute complete pipeline from collection to email delivery.

        Steps:
        0. Authenticate to MMC Core API (optional — degrades gracefully if not configured)
        1. Collect articles from enabled sources (creates Run internally)
        2. Query collected articles for classification
        3. Classify articles with Azure OpenAI
        4. Re-query classified articles
        5. Generate unified HTML report for browser
        6. Generate per-role emails
        7. Archive reports to disk
        8. Send emails per role (uses Graph API; Phase 12 will check degraded_auth flag)
        9. Update Run record with final status

        Returns:
            Dictionary with pipeline results including email delivery status
        """
        db = SessionLocal()
        result = {
            "run_id": None,
            "articles_collected": 0,
            "articles_classified": 0,
            "role_emails_generated": 0,
            "emails_sent": {},
            "reports_archived": [],
            "html_output": None,
            "degraded_auth": True,
            "status": "failed",
            "error": None
        }

        try:
            self.logger.info("pipeline_with_email_started")
            start_time = datetime.utcnow()

            # Step 0: Authenticate to MMC Core API
            # degraded_auth defaults to True (safe: Graph API fallback)
            # Auth failure NEVER blocks the pipeline — logs warning and continues
            # Phase 12 will check degraded_auth to choose between enterprise email
            # and Graph API fallback.
            degraded_auth = True
            if self.token_manager and self.token_manager.is_configured():
                step_start = datetime.utcnow()
                self.logger.info("step_0_auth_started")
                token = await self.token_manager.get_token()
                if token:
                    degraded_auth = False
                    self.logger.info("step_0_auth_completed", degraded_auth=False)
                else:
                    self.logger.warning(
                        "step_0_auth_failed",
                        degraded_auth=True,
                        message="JWT acquisition failed, email will use Graph API fallback"
                    )
                step_duration = (datetime.utcnow() - step_start).total_seconds()
                self.logger.info("step_0_auth_duration", duration_seconds=round(step_duration, 2))
            else:
                self.logger.info(
                    "step_0_auth_skipped",
                    reason="MMC auth not configured" if not self.token_manager else "TokenManager not configured"
                )
            result["degraded_auth"] = degraded_auth

            # Step 1: Collect articles (collector creates Run internally)
            step_start = datetime.utcnow()
            self.logger.info("step_1_collection_started")
            articles_collected = self.collector.collect_from_sources()
            result["articles_collected"] = articles_collected
            step_duration = (datetime.utcnow() - step_start).total_seconds()

            self.logger.info(
                "step_1_collection_completed",
                articles_collected=articles_collected,
                duration_seconds=round(step_duration, 2)
            )

            # Query latest Run to get run_id
            latest_run = db.query(Run).order_by(Run.id.desc()).first()

            if not latest_run:
                error_msg = "No Run record found after collection"
                self.logger.error("pipeline_failed", error=error_msg)
                result["error"] = error_msg
                return result

            result["run_id"] = latest_run.id

            # Bind run_id to all subsequent log entries
            import structlog
            structlog.contextvars.bind_contextvars(run_id=latest_run.id)

            self.logger.info("run_identified", run_id=latest_run.id)

            # Step 1b: Source health check
            step_start = datetime.utcnow()
            self.logger.info("step_1b_health_check_started")
            health_monitor = SourceHealthMonitor()
            health_results = health_monitor.check_all_sources(db)
            alerts = [r for r in health_results if r["alert"]]

            if alerts:
                # Log alert summary
                alert_summary = health_monitor.format_alert_summary(alerts)
                self.logger.warning("source_health_alerts", alert_count=len(alerts), summary=alert_summary)

                # Send health alert email to admin
                try:
                    settings = get_settings()
                    if settings.admin_email:
                        alert_html = health_monitor.format_alert_email(alerts)
                        email_service = GraphEmailService()
                        await email_service.send_email(
                            to_addresses=[settings.admin_email],
                            subject=f"[MDInsights] Source Health Alert - {datetime.utcnow().strftime('%d %B %Y')}",
                            html_body=alert_html
                        )
                        self.logger.info("health_alert_email_sent")
                except Exception as alert_err:
                    self.logger.error("health_alert_email_failed", error=str(alert_err))
                    # Don't fail pipeline on alert failure

                result["health_alerts"] = len(alerts)
            else:
                self.logger.info("step_1b_health_check_passed", sources_checked=len(health_results))
                result["health_alerts"] = 0

            step_duration = (datetime.utcnow() - step_start).total_seconds()
            self.logger.info(
                "step_1b_health_check_completed",
                duration_seconds=round(step_duration, 2)
            )

            # Step 2: Query collected articles for this run
            step_start = datetime.utcnow()
            self.logger.info("step_2_querying_articles")
            articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == latest_run.id
            ).all()

            if not articles:
                self.logger.warning("no_articles_to_classify")
                result["status"] = "completed"
                result["html_output"] = "<html><body><h1>No articles collected</h1></body></html>"
                return result

            step_duration = (datetime.utcnow() - step_start).total_seconds()
            self.logger.info(
                "step_2_articles_queried",
                article_count=len(articles),
                duration_seconds=round(step_duration, 2)
            )

            # Step 3: Classify articles
            step_start = datetime.utcnow()
            self.logger.info("step_3_classification_started")
            articles_classified = self.classifier.classify_articles(db, articles)
            result["articles_classified"] = articles_classified
            step_duration = (datetime.utcnow() - step_start).total_seconds()

            self.logger.info(
                "step_3_classification_completed",
                articles_classified=articles_classified,
                duration_seconds=round(step_duration, 2)
            )

            # Step 4: Re-query classified articles
            step_start = datetime.utcnow()
            self.logger.info("step_4_querying_classified_articles")
            classified_articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == latest_run.id,
                NewsArticle.roles.isnot(None)
            ).all()
            step_duration = (datetime.utcnow() - step_start).total_seconds()

            self.logger.info(
                "step_4_classified_articles_queried",
                classified_count=len(classified_articles),
                duration_seconds=round(step_duration, 2)
            )

            # Step 5: Generate unified browser report
            step_start = datetime.utcnow()
            self.logger.info("step_5_report_generation_started")
            report_date = datetime.utcnow()
            html_output = self.reporter.generate_role_brief(
                articles=classified_articles,
                report_date=report_date
            )
            result["html_output"] = html_output
            step_duration = (datetime.utcnow() - step_start).total_seconds()

            self.logger.info(
                "step_5_report_generation_completed",
                html_length=len(html_output),
                duration_seconds=round(step_duration, 2)
            )

            # Step 6: Generate per-role emails
            step_start = datetime.utcnow()
            self.logger.info("step_6_email_generation_started")
            role_emails = self.reporter.generate_role_emails(
                articles=classified_articles,
                report_date=report_date
            )
            result["role_emails_generated"] = len(role_emails)
            step_duration = (datetime.utcnow() - step_start).total_seconds()

            self.logger.info(
                "step_6_email_generation_completed",
                role_count=len(role_emails),
                duration_seconds=round(step_duration, 2)
            )

            # Step 7: Archive reports to disk
            step_start = datetime.utcnow()
            self.logger.info("step_7_archiving_reports")
            date_str = report_date.strftime("%Y-%m-%d")
            for role, html in role_emails.items():
                role_dir = os.path.join(PROJECT_ROOT, "data", "reports", role.lower())
                os.makedirs(role_dir, exist_ok=True)
                report_path = os.path.join(role_dir, f"{date_str}.html")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(html)
                result["reports_archived"].append(report_path)
            step_duration = (datetime.utcnow() - step_start).total_seconds()

            self.logger.info(
                "step_7_archiving_completed",
                files_archived=len(result["reports_archived"]),
                duration_seconds=round(step_duration, 2)
            )

            # Step 8: Send emails per role
            step_start = datetime.utcnow()
            self.logger.info("step_8_email_delivery_started")
            email_service = GraphEmailService()
            settings = get_settings()

            for role, html in role_emails.items():
                # Get recipients for this role
                recipients = settings.get_email_recipients(role)

                # Skip if no recipients configured
                if not recipients.has_recipients:
                    self.logger.info(
                        "skipping_email_no_recipients",
                        role=role
                    )
                    result["emails_sent"][role] = {
                        "status": "skipped",
                        "message": "No recipients configured"
                    }
                    continue

                # Build subject
                subject = f"[{settings.company_name}] {role} Intelligence Brief - {report_date.strftime('%d %B %Y')}"

                # Send email
                send_result = await email_service.send_email(
                    to_addresses=recipients.to,
                    subject=subject,
                    html_body=html,
                    cc_addresses=recipients.cc or None,
                    bcc_addresses=recipients.bcc or None
                )

                result["emails_sent"][role] = send_result

                self.logger.info(
                    "email_sent",
                    role=role,
                    status=send_result.get("status"),
                    recipients=recipients.total_recipients
                )

            step_duration = (datetime.utcnow() - step_start).total_seconds()
            self.logger.info(
                "step_8_email_delivery_completed",
                emails_sent=len([r for r in result["emails_sent"].values() if r.get("status") == "ok"]),
                duration_seconds=round(step_duration, 2)
            )

            # Step 9: Update Run record
            step_start = datetime.utcnow()
            latest_run.articles_classified = articles_classified
            latest_run.status = RunStatus.COMPLETED
            db.commit()
            step_duration = (datetime.utcnow() - step_start).total_seconds()

            self.logger.info(
                "step_9_run_updated",
                duration_seconds=round(step_duration, 2)
            )

            # Calculate duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result["status"] = "completed"

            # Summary log with all metrics
            self.logger.info(
                "pipeline_summary",
                total_duration=round(duration, 2),
                articles_collected=articles_collected,
                articles_classified=articles_classified,
                degraded_auth=degraded_auth,
                emails_sent_count=len([r for r in result["emails_sent"].values() if r.get("status") == "ok"]),
                reports_archived_count=len(result["reports_archived"])
            )

            return result

        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg

            self.logger.error(
                "pipeline_with_email_failed",
                error=error_msg,
                exc_info=True
            )

            # Send admin alert on failure
            try:
                await self._send_admin_alert(error_msg, result)
            except Exception as alert_error:
                self.logger.error(
                    "admin_alert_failed",
                    error=str(alert_error)
                )

            # Update Run record if we have it
            if result["run_id"]:
                try:
                    run = db.query(Run).filter(Run.id == result["run_id"]).first()
                    if run:
                        run.status = RunStatus.FAILED
                        run.error_message = error_msg
                        db.commit()
                except Exception as update_error:
                    self.logger.error(
                        "run_update_failed",
                        error=str(update_error)
                    )

            return result

        finally:
            # Unbind context variables
            import structlog
            structlog.contextvars.unbind_contextvars("run_id")
            db.close()

    async def _send_admin_alert(self, error_msg: str, result: dict):
        """
        Send admin alert email when pipeline fails.

        Args:
            error_msg: Error message from exception
            result: Pipeline result dict with run details
        """
        settings = get_settings()

        # Skip if no admin email configured
        if not settings.admin_email:
            self.logger.info("admin_alert_skipped_no_email")
            return

        try:
            email_service = GraphEmailService()

            # Build subject
            subject = f"[MDInsights] Pipeline Failed - {datetime.utcnow().strftime('%d %B %Y')}"

            # Build simple HTML body
            html_body = f"""
            <html>
            <body style="font-family: sans-serif; padding: 20px;">
                <h2 style="color: #dc3545;">MDInsights Pipeline Failure</h2>
                <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Run ID:</strong> {result.get('run_id', 'N/A')}</p>
                <p><strong>Articles Collected:</strong> {result.get('articles_collected', 0)}</p>
                <p><strong>Articles Classified:</strong> {result.get('articles_classified', 0)}</p>
                <h3>Error Details</h3>
                <pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">{error_msg}</pre>
                <p style="color: #6c757d; font-size: 12px; margin-top: 30px;">
                    This is an automated alert from MDInsights. Check application logs for full details.
                </p>
            </body>
            </html>
            """

            # Send alert
            await email_service.send_email(
                to_addresses=[settings.admin_email],
                subject=subject,
                html_body=html_body
            )

            self.logger.info("admin_alert_sent", admin_email=settings.admin_email)

        except Exception as e:
            # Never let alert failure crash the pipeline
            self.logger.error(
                "admin_alert_send_failed",
                error=str(e)
            )
