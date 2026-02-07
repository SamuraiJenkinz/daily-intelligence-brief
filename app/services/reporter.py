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


# Priority ranking order for article sorting
PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Monitor": 3}


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

    @staticmethod
    def filter_articles_by_role(articles: List[dict], role: str) -> List[dict]:
        """
        Filter articles by role membership and sort by priority.

        Args:
            articles: List of prepared article dictionaries
            role: Role to filter by (e.g., "Brokers", "Leadership")

        Returns:
            List of articles where role is in article['roles'], sorted by priority
            (Critical first, Monitor last)
        """
        # Filter articles that include this role
        role_articles = [a for a in articles if role in a.get('roles', [])]

        # Sort by priority using PRIORITY_ORDER
        # Unknown priorities get value 4 (sorted after Monitor)
        role_articles.sort(key=lambda a: PRIORITY_ORDER.get(a.get('priority'), 4))

        return role_articles

    def _prepare_articles(self, articles: List[NewsArticle]) -> List[dict]:
        """
        Prepare articles for template by parsing JSON fields.

        Args:
            articles: List of NewsArticle ORM objects

        Returns:
            List of article dictionaries with parsed JSON fields (roles, entities)
        """
        prepared = []
        for article in articles:
            # Parse entities field (JSON string -> list of dicts)
            entities = []
            if article.entities:
                if isinstance(article.entities, str):
                    entities = json.loads(article.entities)
                else:
                    entities = article.entities

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
                'entities': entities,
                'impact_level': article.impact_level,
                'category': article.category,
                'region': article.region,
                'business_line': article.business_line,
            }
            prepared.append(article_dict)
        return prepared

    def generate_role_brief(
        self,
        articles: List[NewsArticle],
        report_date: datetime,
        company_name: str = None
    ) -> str:
        """
        Generate unified HTML brief for all roles.

        The brief contains all roles in a single HTML document with tabs for
        each role. Articles are filtered and sorted by role/priority within
        the template via filter_articles_by_role.

        Args:
            articles: List of classified NewsArticle objects
            report_date: Date for the report
            company_name: Company name (defaults to settings)

        Returns:
            HTML string with inlined CSS
        """
        if company_name is None:
            company_name = self.company_name

        # Prepare articles (parse JSON fields)
        prepared_articles = self._prepare_articles(articles)

        # Compute edition stats
        source_count = len(set(a.source_name for a in articles if a.source_name))
        article_count = len(articles)

        edition_stats = {
            'source_count': source_count,
            'article_count': article_count,
            'entity_count': 0,  # Filled later by aggregator (Plan 04)
            'signal_count': 0   # Filled later by what-to-watch (Plan 05)
        }

        # Load template
        template = self.env.get_template('role_brief.html')

        # Render template
        context = {
            'articles': prepared_articles,
            'report_date': report_date,
            'company_name': company_name,
            'edition_stats': edition_stats,
        }
        html = template.render(**context)

        # Inline CSS for email compatibility
        html_inlined = transform(html)

        return html_inlined

    def generate_all_role_briefs(
        self,
        articles: List[NewsArticle],
        report_date: datetime
    ) -> str:
        """
        Generate unified HTML brief for all roles.

        Since the brief is now unified (all roles in one HTML with tabs),
        this method simply calls generate_role_brief once.

        Args:
            articles: List of classified NewsArticle objects
            report_date: Date for the report

        Returns:
            HTML string (single unified brief)
        """
        return self.generate_role_brief(
            articles=articles,
            report_date=report_date
        )
