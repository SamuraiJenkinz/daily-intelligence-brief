"""
Reporter service for generating HTML role-based intelligence briefs.

Uses Jinja2 templates to generate tabbed HTML reports with inlined CSS
for email compatibility (via premailer).
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from jinja2 import Environment, FileSystemLoader
from premailer import transform

from app.models.news_article import NewsArticle
from app.config import get_settings


class RoleReportService:
    """
    Service for generating role-based intelligence briefs.

    Renders Jinja2 templates with classified articles, then inlines CSS
    using premailer for email compatibility.
    """

    def __init__(self):
        """Initialize Jinja2 environment with templates directory."""
        settings = get_settings()

        # Get templates directory path relative to app directory
        app_dir = Path(__file__).parent.parent
        templates_dir = app_dir / "templates"

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True
        )

        self.company_name = settings.company_name

    def _prepare_articles(self, articles: List[NewsArticle]) -> List[dict]:
        """
        Prepare articles for template by parsing JSON roles field.

        Args:
            articles: List of NewsArticle ORM objects

        Returns:
            List of article dictionaries with parsed roles
        """
        prepared = []
        for article in articles:
            article_dict = {
                'id': article.id,
                'title': article.title,
                'description': article.description,
                'source_url': article.source_url,
                'source_name': article.source_name,
                'published_at': article.published_at,
                'roles': json.loads(article.roles) if article.roles else [],
                'priority': article.priority,
                'summary': article.summary,
                'sentiment': article.sentiment,
            }
            prepared.append(article_dict)
        return prepared

    def generate_role_brief(
        self,
        target_role: str,
        articles: List[NewsArticle],
        report_date: datetime,
        company_name: str = None
    ) -> str:
        """
        Generate HTML brief for a specific role.

        Note: For Phase 1, the template shows all roles with tabs.
        The target_role parameter is retained for potential future use
        (e.g., separate emails per role in Phase 5).

        Args:
            target_role: Role to generate brief for (Brokers, Leadership, etc.)
            articles: List of classified NewsArticle objects
            report_date: Date for the report
            company_name: Company name (defaults to settings)

        Returns:
            HTML string with inlined CSS
        """
        if company_name is None:
            company_name = self.company_name

        # Prepare articles (parse JSON roles)
        prepared_articles = self._prepare_articles(articles)

        # Load template
        template = self.env.get_template('role_brief.html')

        # Render template
        context = {
            'target_role': target_role,
            'articles': prepared_articles,
            'report_date': report_date,
            'company_name': company_name,
        }
        html = template.render(**context)

        # Inline CSS for email compatibility
        html_inlined = transform(html)

        return html_inlined

    def generate_all_role_briefs(
        self,
        articles: List[NewsArticle],
        report_date: datetime
    ) -> Dict[str, str]:
        """
        Generate separate HTML briefs for all roles.

        Args:
            articles: List of classified NewsArticle objects
            report_date: Date for the report

        Returns:
            Dictionary mapping role name to HTML string
        """
        roles = ["Brokers", "Leadership", "Compliance", "Underwriting"]
        briefs = {}

        for role in roles:
            briefs[role] = self.generate_role_brief(
                target_role=role,
                articles=articles,
                report_date=report_date
            )

        return briefs
