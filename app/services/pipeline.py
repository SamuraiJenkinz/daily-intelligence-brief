"""
Pipeline orchestration service for MDInsights.

Coordinates collection → classification → reporting workflow with
comprehensive error handling and progress tracking.
"""
from datetime import datetime
from typing import Dict, Optional
import asyncio
import json
import os
import structlog
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import NewsArticle, Run, RunStatus
from app.services.classifier import RoleClassificationService
from app.services.reporter import RoleReportService
from app.services.emailer import GraphEmailService
from app.services.enterprise_emailer import EnterpriseEmailClient
from app.services.health_monitor import SourceHealthMonitor
from app.config import get_settings
from app.auth.token_manager import TokenManager
from app.collectors.factiva import FactivaCollector
from app.collectors.equity import EquityPriceClient
from app.models.factiva_config import FactivaConfig
from app.models.api_event import ApiEvent, ApiEventType
from app.models.equity_ticker import EquityTicker

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
        classifier: RoleClassificationService,
        reporter: RoleReportService,
        token_manager: Optional[TokenManager] = None
    ):
        """
        Initialize pipeline orchestrator with service dependencies.

        Args:
            classifier: RoleClassificationService for article classification
            reporter: RoleReportService for HTML report generation
            token_manager: Optional TokenManager for MMC Core API JWT auth.
                           When None (default), pipeline runs without enterprise
                           auth (degraded_auth=True, Graph API fallback for email).
        """
        self.classifier = classifier
        self.reporter = reporter
        self.token_manager = token_manager
        self.logger = logger.bind(service="pipeline")

    def _store_articles(self, db: Session, run_id: int, articles: list) -> None:
        """Store collected articles in database.

        Args:
            db: Database session
            run_id: ID of current pipeline run
            articles: List of normalized article dicts from FactivaCollector
        """
        for article_data in articles:
            article = NewsArticle(
                run_id=run_id,
                title=article_data["title"],
                description=article_data.get("description"),
                source_url=article_data.get("url"),
                source_name=article_data["source_name"],
                published_at=article_data.get("published_at"),
                collector_source=article_data.get("collector_source", "Factiva"),
                roles=None,
                priority=None,
                summary=None,
                sentiment=None,
            )
            db.add(article)
        db.commit()

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
            "collection_source": "Factiva",
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

            # Step 1: Collect articles from Factiva (sole source)
            self.logger.info("step_1_collection_started")

            factiva_collector = FactivaCollector()

            # Verify Factiva is configured
            if not factiva_collector.is_configured():
                error_msg = "Factiva not configured (missing MMC_API_BASE_URL or MMC_API_KEY)"
                self.logger.error("factiva_not_configured", error=error_msg)
                result["error"] = error_msg
                return result

            # Load query params from database config
            factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
            if not factiva_config or not factiva_config.enabled:
                error_msg = "Factiva disabled in admin dashboard"
                self.logger.warning("factiva_disabled", error=error_msg)
                result["error"] = error_msg
                return result

            query_params = {
                "industry_codes": factiva_config.industry_codes or "",
                "company_codes": factiva_config.company_codes or "",
                "keywords": factiva_config.keywords or "",
                "page_size": factiva_config.page_size or 25,
                "date_range_hours": factiva_config.date_range_hours or 48,
            }

            # Create Run record at start of Step 1
            run = Run(status=RunStatus.RUNNING)
            db.add(run)
            db.commit()
            db.refresh(run)
            result["run_id"] = run.id

            self.logger.info("factiva_collection_starting", run_id=run.id, **query_params)

            # Collect articles (raises exception on failure after retries)
            try:
                factiva_articles = factiva_collector.collect(query_params)
            except Exception as e:
                error_msg = f"Factiva collection failed after retries: {str(e)}"
                self.logger.error("factiva_collection_failed", error=error_msg, exc_info=True)
                result["error"] = error_msg
                run.status = RunStatus.FAILED
                run.error_message = error_msg
                db.commit()
                return result

            # Handle zero articles (not an error — system working, just no results)
            if not factiva_articles:
                self.logger.info("factiva_returned_zero_articles", message="Continuing with empty brief")

            # URL-dedup against today's existing articles
            from datetime import date as date_type
            from sqlalchemy import func as sqla_func
            today = date_type.today()
            existing_urls = set(
                url for (url,) in db.query(NewsArticle.source_url).filter(
                    sqla_func.date(NewsArticle.created_at) == today,
                    NewsArticle.source_url.isnot(None)
                ).all()
            )
            pre_url_dedup = len(factiva_articles)
            factiva_articles = [a for a in factiva_articles if a.get("url") not in existing_urls]
            self.logger.info("url_dedup_complete", before=pre_url_dedup, after=len(factiva_articles))

            # Semantic dedup (handles wire service near-duplicates)
            if len(factiva_articles) > 1:
                from app.services.deduplicator import ArticleDeduplicator
                deduplicator = ArticleDeduplicator()
                pre_semantic_dedup = len(factiva_articles)
                factiva_articles = deduplicator.deduplicate(factiva_articles)
                self.logger.info("semantic_dedup_complete",
                               before=pre_semantic_dedup,
                               after=len(factiva_articles))

            # Store articles
            self._store_articles(db, run.id, factiva_articles)
            articles_collected = len(factiva_articles)

            # Update Run record with article count
            run.articles_collected = articles_collected
            db.commit()

            result["articles_collected"] = articles_collected
            result["collection_source"] = "Factiva"

            self.logger.info(
                "step_1_collection_completed",
                articles_collected=articles_collected,
                collection_source="Factiva"
            )

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
            self.logger.info("step_2_querying_articles", run_id=run.id)
            articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == run.id
            ).all()

            if not articles:
                self.logger.warning(
                    "no_articles_to_classify",
                    run_id=run.id
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

            # Step 3b: Equity price enrichment
            # Fetch current prices for articles mentioning tracked public companies.
            # Failures are per-entity and never block the pipeline or report generation.
            self.logger.info("step_3b_equity_enrichment_started")

            equity_client = EquityPriceClient()
            if equity_client.is_configured():
                # Load all enabled ticker mappings into dict for O(1) lookup
                ticker_mappings = db.query(EquityTicker).filter(EquityTicker.enabled == True).all()
                ticker_map = {
                    mapping.entity_name.lower(): mapping
                    for mapping in ticker_mappings
                }

                if ticker_map:
                    # Cache fetched prices to avoid duplicate API calls for same ticker
                    fetched_prices = {}  # ticker -> price_dict or None

                    for article in articles:
                        equity_hits = []
                        # Parse entities from article (JSON string or list)
                        entities_raw = article.entities
                        if isinstance(entities_raw, str):
                            try:
                                entities_list = json.loads(entities_raw)
                            except (json.JSONDecodeError, TypeError):
                                entities_list = []
                        elif isinstance(entities_raw, list):
                            entities_list = entities_raw
                        else:
                            entities_list = []

                        for entity in entities_list:
                            entity_name = entity.get("name", "") if isinstance(entity, dict) else str(entity)
                            mapping = ticker_map.get(entity_name.lower())
                            if mapping:
                                ticker_key = f"{mapping.exchange}:{mapping.ticker}"
                                if ticker_key not in fetched_prices:
                                    fetched_prices[ticker_key] = equity_client.get_price(
                                        ticker=mapping.ticker,
                                        exchange=mapping.exchange,
                                        run_id=run.id,
                                    )
                                price_data = fetched_prices[ticker_key]
                                if price_data:
                                    equity_hits.append(price_data)

                        # Attach as transient attribute — NOT persisted to DB
                        article._equity_data = equity_hits

                    self.logger.info(
                        "step_3b_equity_enrichment_completed",
                        tickers_mapped=len(ticker_map),
                        tickers_fetched=len(fetched_prices),
                        tickers_with_price=len([v for v in fetched_prices.values() if v]),
                    )
                else:
                    self.logger.info("step_3b_equity_no_mappings")
                    for article in articles:
                        article._equity_data = []
            else:
                self.logger.info("step_3b_equity_not_configured")
                for article in articles:
                    article._equity_data = []

            # Step 4: Re-query classified articles
            self.logger.info("step_4_querying_classified_articles")
            classified_articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == run.id,
                NewsArticle.roles.isnot(None)
            ).all()

            # Transfer equity data from Step 3b to re-queried articles
            equity_data_map = {a.id: getattr(a, '_equity_data', []) for a in articles}
            for article in classified_articles:
                article._equity_data = equity_data_map.get(article.id, [])

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
            run.articles_classified = articles_classified
            run.status = RunStatus.COMPLETED
            db.commit()

            self.logger.info("step_6_run_updated", run_id=run.id)

            # Calculate duration
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result["status"] = "completed"

            self.logger.info(
                "pipeline_completed",
                run_id=run.id,
                articles_collected=articles_collected,
                articles_classified=articles_classified,
                degraded_auth=degraded_auth,
                collection_source="Factiva",
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
            "collection_source": "Factiva",
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

            # Step 1: Collect articles from Factiva (sole source)
            step_start = datetime.utcnow()
            self.logger.info("step_1_collection_started")

            factiva_collector = FactivaCollector()

            # Verify Factiva is configured
            if not factiva_collector.is_configured():
                error_msg = "Factiva not configured (missing MMC_API_BASE_URL or MMC_API_KEY)"
                self.logger.error("factiva_not_configured", error=error_msg)
                result["error"] = error_msg
                await self._send_admin_alert(error_msg, result)
                return result

            # Load query params from database config
            factiva_config = db.query(FactivaConfig).filter(FactivaConfig.id == 1).first()
            if not factiva_config or not factiva_config.enabled:
                error_msg = "Factiva disabled in admin dashboard"
                self.logger.warning("factiva_disabled", error=error_msg)
                result["error"] = error_msg
                return result

            query_params = {
                "industry_codes": factiva_config.industry_codes or "",
                "company_codes": factiva_config.company_codes or "",
                "keywords": factiva_config.keywords or "",
                "page_size": factiva_config.page_size or 25,
                "date_range_hours": factiva_config.date_range_hours or 48,
            }

            # Create Run record at start of Step 1
            run = Run(status=RunStatus.RUNNING)
            db.add(run)
            db.commit()
            db.refresh(run)
            result["run_id"] = run.id

            # Bind run_id to all subsequent log entries
            import structlog
            structlog.contextvars.bind_contextvars(run_id=run.id)

            self.logger.info("factiva_collection_starting", run_id=run.id, **query_params)

            # Collect articles (raises exception on failure after retries)
            try:
                factiva_articles = factiva_collector.collect(query_params)
            except Exception as e:
                error_msg = f"Factiva collection failed after retries: {str(e)}"
                self.logger.error("factiva_collection_failed", error=error_msg, exc_info=True)
                result["error"] = error_msg
                run.status = RunStatus.FAILED
                run.error_message = error_msg
                db.commit()
                await self._send_admin_alert(error_msg, result)
                return result

            # Handle zero articles (not an error — system working, just no results)
            if not factiva_articles:
                self.logger.info("factiva_returned_zero_articles", message="Continuing with empty brief")

            # URL-dedup against today's existing articles
            from datetime import date as date_type
            from sqlalchemy import func as sqla_func
            today = date_type.today()
            existing_urls = set(
                url for (url,) in db.query(NewsArticle.source_url).filter(
                    sqla_func.date(NewsArticle.created_at) == today,
                    NewsArticle.source_url.isnot(None)
                ).all()
            )
            pre_url_dedup = len(factiva_articles)
            factiva_articles = [a for a in factiva_articles if a.get("url") not in existing_urls]
            self.logger.info("url_dedup_complete", before=pre_url_dedup, after=len(factiva_articles))

            # Semantic dedup (handles wire service near-duplicates)
            if len(factiva_articles) > 1:
                from app.services.deduplicator import ArticleDeduplicator
                deduplicator = ArticleDeduplicator()
                pre_semantic_dedup = len(factiva_articles)
                factiva_articles = deduplicator.deduplicate(factiva_articles)
                self.logger.info("semantic_dedup_complete",
                               before=pre_semantic_dedup,
                               after=len(factiva_articles))

            # Store articles
            self._store_articles(db, run.id, factiva_articles)
            articles_collected = len(factiva_articles)

            # Update Run record with article count
            run.articles_collected = articles_collected
            db.commit()

            result["articles_collected"] = articles_collected
            result["collection_source"] = "Factiva"

            step_duration = (datetime.utcnow() - step_start).total_seconds()
            self.logger.info(
                "step_1_collection_completed",
                articles_collected=articles_collected,
                collection_source="Factiva",
                duration_seconds=round(step_duration, 2)
            )

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
                NewsArticle.run_id == run.id
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

            # Step 3b: Equity price enrichment
            # Fetch current prices for articles mentioning tracked public companies.
            # Failures are per-entity and never block the pipeline or report generation.
            step_start = datetime.utcnow()
            self.logger.info("step_3b_equity_enrichment_started")

            equity_client = EquityPriceClient()
            if equity_client.is_configured():
                # Load all enabled ticker mappings into dict for O(1) lookup
                ticker_mappings = db.query(EquityTicker).filter(EquityTicker.enabled == True).all()
                ticker_map = {
                    mapping.entity_name.lower(): mapping
                    for mapping in ticker_mappings
                }

                if ticker_map:
                    # Cache fetched prices to avoid duplicate API calls for same ticker
                    fetched_prices = {}  # ticker -> price_dict or None

                    for article in articles:
                        equity_hits = []
                        # Parse entities from article (JSON string or list)
                        entities_raw = article.entities
                        if isinstance(entities_raw, str):
                            try:
                                entities_list = json.loads(entities_raw)
                            except (json.JSONDecodeError, TypeError):
                                entities_list = []
                        elif isinstance(entities_raw, list):
                            entities_list = entities_raw
                        else:
                            entities_list = []

                        for entity in entities_list:
                            entity_name = entity.get("name", "") if isinstance(entity, dict) else str(entity)
                            mapping = ticker_map.get(entity_name.lower())
                            if mapping:
                                ticker_key = f"{mapping.exchange}:{mapping.ticker}"
                                if ticker_key not in fetched_prices:
                                    fetched_prices[ticker_key] = equity_client.get_price(
                                        ticker=mapping.ticker,
                                        exchange=mapping.exchange,
                                        run_id=run.id,
                                    )
                                price_data = fetched_prices[ticker_key]
                                if price_data:
                                    equity_hits.append(price_data)

                        # Attach as transient attribute — NOT persisted to DB
                        article._equity_data = equity_hits

                    self.logger.info(
                        "step_3b_equity_enrichment_completed",
                        tickers_mapped=len(ticker_map),
                        tickers_fetched=len(fetched_prices),
                        tickers_with_price=len([v for v in fetched_prices.values() if v]),
                    )
                else:
                    self.logger.info("step_3b_equity_no_mappings")
                    for article in articles:
                        article._equity_data = []
            else:
                self.logger.info("step_3b_equity_not_configured")
                for article in articles:
                    article._equity_data = []

            step_duration = (datetime.utcnow() - step_start).total_seconds()
            self.logger.info("step_3b_duration", duration_seconds=round(step_duration, 2))

            # Step 4: Re-query classified articles
            step_start = datetime.utcnow()
            self.logger.info("step_4_querying_classified_articles")
            classified_articles = db.query(NewsArticle).filter(
                NewsArticle.run_id == run.id,
                NewsArticle.roles.isnot(None)
            ).all()

            # Transfer equity data from Step 3b to re-queried articles
            equity_data_map = {a.id: getattr(a, '_equity_data', []) for a in articles}
            for article in classified_articles:
                article._equity_data = equity_data_map.get(article.id, [])

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

            # Step 8: Send emails per role (enterprise primary, Graph API fallback)
            step_start = datetime.utcnow()
            self.logger.info("step_8_email_delivery_started")

            enterprise_client = EnterpriseEmailClient()
            graph_service = GraphEmailService()
            settings = get_settings()

            # Log enterprise email configuration status
            if settings.is_mmc_email_configured():
                self.logger.info("enterprise_email_configured", sender=settings.mmc_sender_email)
            elif settings.mmc_sender_email:
                self.logger.info("enterprise_email_partial_config", hint="MMC auth or API key missing")
            else:
                self.logger.info("enterprise_email_not_configured", hint="MMC_SENDER_EMAIL not set, using Graph API")

            # Fetch JWT token ONCE before per-role loop (avoid 4 separate token calls)
            # token is None if degraded_auth=True or token acquisition fails
            token = None
            if not degraded_auth and enterprise_client.is_configured():
                token = await self.token_manager.get_token()
                if not token:
                    self.logger.warning("step_8_token_fetch_failed", hint="Will use Graph API for all roles")

            delivery_failure_count = 0

            for role, html in role_emails.items():
                # Get recipients for this role
                recipients = settings.get_email_recipients(role)

                # Skip if no recipients configured
                if not recipients.has_recipients:
                    self.logger.info("skipping_email_no_recipients", role=role)
                    result["emails_sent"][role] = {"status": "skipped", "path": "skipped", "message": "No recipients configured"}
                    continue

                # Build subject ONCE — same for both delivery paths
                subject = f"[{settings.company_name}] {role} Intelligence Brief - {report_date.strftime('%d %B %Y')}"

                # Deliver with fallback
                delivery_result = await self._send_with_fallback(
                    role=role,
                    subject=subject,
                    html=html,
                    recipients=recipients,
                    degraded_auth=degraded_auth,
                    enterprise_client=enterprise_client,
                    graph_service=graph_service,
                    token=token,
                    run_id=run.id,
                )

                result["emails_sent"][role] = delivery_result

                # Track failures for status reporting
                if delivery_result.get("path") == "both_failed":
                    delivery_failure_count += 1

                self.logger.info(
                    "email_delivery_outcome",
                    role=role,
                    status=delivery_result.get("status"),
                    path=delivery_result.get("path"),
                    recipients=recipients.total_recipients,
                )

            step_duration = (datetime.utcnow() - step_start).total_seconds()

            # Log delivery summary
            enterprise_count = len([r for r in result["emails_sent"].values() if r.get("path") == "enterprise"])
            graph_fallback_count = len([r for r in result["emails_sent"].values() if r.get("path") == "graph_fallback"])
            graph_primary_count = len([r for r in result["emails_sent"].values() if r.get("path") == "graph_primary"])
            skipped_count = len([r for r in result["emails_sent"].values() if r.get("path") == "skipped"])

            self.logger.info(
                "step_8_email_delivery_completed",
                enterprise_sent=enterprise_count,
                graph_fallback_sent=graph_fallback_count,
                graph_primary_sent=graph_primary_count,
                skipped=skipped_count,
                delivery_failures=delivery_failure_count,
                duration_seconds=round(step_duration, 2),
            )

            # Step 9: Update Run record
            step_start = datetime.utcnow()
            run.articles_classified = articles_classified
            run.status = RunStatus.COMPLETED
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

            # Downgrade status if any role had both delivery paths fail
            if delivery_failure_count > 0:
                result["status"] = "completed_with_delivery_failure"
                self.logger.warning(
                    "pipeline_delivery_failures",
                    failed_roles=delivery_failure_count,
                    hint="Reports archived but email delivery failed for some roles",
                )

            # Summary log with all metrics
            self.logger.info(
                "pipeline_summary",
                total_duration=round(duration, 2),
                articles_collected=articles_collected,
                articles_classified=articles_classified,
                degraded_auth=degraded_auth,
                collection_source="Factiva",
                emails_sent_count=len([r for r in result["emails_sent"].values() if r.get("status") == "ok"]),
                enterprise_sent=enterprise_count,
                graph_fallback_sent=graph_fallback_count,
                graph_primary_sent=graph_primary_count,
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

    async def _send_with_fallback(
        self,
        role: str,
        subject: str,
        html: str,
        recipients,  # EmailRecipients
        degraded_auth: bool,
        enterprise_client: EnterpriseEmailClient,
        graph_service: GraphEmailService,
        token: Optional[str],
        run_id: int,
    ) -> dict:
        """
        Attempt enterprise email delivery, fall back to Graph API on failure.

        Decision tree:
        1. degraded_auth=True OR enterprise not configured OR no token:
           -> Skip enterprise, use Graph API as primary (path="graph_primary")
        2. Enterprise attempt succeeds:
           -> Return success (path="enterprise")
        3. Enterprise attempt fails (auth_error, client_error, network_error):
           -> Fall back to Graph API (path="graph_fallback")
        4. Both enterprise and Graph fail:
           -> Return error (path="both_failed"), pipeline continues

        Args:
            role: Role name (Brokers, Leadership, etc.)
            subject: Email subject line (same for both paths)
            html: HTML brief body
            recipients: EmailRecipients with .to, .cc, .bcc
            degraded_auth: True when JWT acquisition failed at Step 0
            enterprise_client: EnterpriseEmailClient instance
            graph_service: GraphEmailService instance (fallback)
            token: JWT token string (may be None if degraded_auth)
            run_id: Pipeline run ID for ApiEvent attribution

        Returns:
            Dict with keys: status, path, and optionally recipients, message
        """
        # Determine whether enterprise delivery should be attempted
        enterprise_attempted = not degraded_auth and enterprise_client.is_configured() and token

        if enterprise_attempted:
            enterprise_result = await enterprise_client.send_email(
                token=token,
                to_addresses=recipients.to,
                subject=subject,
                html_body=html,
                cc_addresses=recipients.cc or None,
                run_id=run_id,
            )
            if enterprise_result.get("status") == "ok":
                return {**enterprise_result, "path": "enterprise"}

            # Enterprise failed — log and fall through to Graph API
            self.logger.warning(
                "enterprise_email_failed_falling_back",
                role=role,
                enterprise_status=enterprise_result.get("status"),
                error=enterprise_result.get("message", "unknown"),
            )
        else:
            # Log why enterprise was skipped (useful for debugging)
            skip_reason = (
                "degraded_auth" if degraded_auth
                else "enterprise_not_configured" if not enterprise_client.is_configured()
                else "no_token"
            )
            self.logger.info("enterprise_email_skipped", role=role, reason=skip_reason)

        # Graph API fallback (or primary when enterprise skipped)
        try:
            graph_result = await graph_service.send_email(
                to_addresses=recipients.to,
                subject=subject,
                html_body=html,
                cc_addresses=recipients.cc or None,
                bcc_addresses=recipients.bcc or None,
            )

            path = "graph_fallback" if enterprise_attempted else "graph_primary"

            if graph_result.get("status") == "ok":
                return {**graph_result, "path": path}
            else:
                return {**graph_result, "path": "both_failed"}

        except Exception as graph_exc:
            self.logger.error(
                "graph_email_also_failed",
                role=role,
                error=str(graph_exc)[:200],
            )
            return {
                "status": "error",
                "message": f"Both enterprise and Graph failed: {str(graph_exc)[:200]}",
                "path": "both_failed",
            }
