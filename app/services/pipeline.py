"""
Pipeline orchestration service for MDInsights.

Coordinates collection → classification → reporting workflow with
comprehensive error handling and progress tracking.
"""
from datetime import datetime
from typing import Dict, Optional
import structlog
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import NewsArticle, Run, RunStatus
from app.services.collector import ApifyCollector
from app.services.classifier import RoleClassificationService
from app.services.reporter import RoleReportService


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
        reporter: RoleReportService
    ):
        """
        Initialize pipeline orchestrator with service dependencies.

        Args:
            collector: ApifyCollector for news collection
            classifier: RoleClassificationService for article classification
            reporter: RoleReportService for HTML report generation
        """
        self.collector = collector
        self.classifier = classifier
        self.reporter = reporter
        self.logger = logger.bind(service="pipeline")

    def run_full_pipeline(self) -> Dict:
        """
        Execute complete pipeline from collection to report generation.

        Steps:
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
                - status: Pipeline status (completed/failed)
                - error: Error message if failed
        """
        db = SessionLocal()
        result = {
            "run_id": None,
            "articles_collected": 0,
            "articles_classified": 0,
            "html_output": None,
            "status": "failed",
            "error": None
        }

        try:
            self.logger.info("pipeline_started")
            start_time = datetime.utcnow()

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
