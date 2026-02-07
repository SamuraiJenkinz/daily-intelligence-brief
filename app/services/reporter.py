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
from openai import AzureOpenAI
import structlog

from app.models.news_article import NewsArticle
from app.schemas.report import ExecutiveSummary, WhatToWatch
from app.config import get_settings
from app.services.aggregator import ReportAggregator


# Priority ranking order for article sorting
PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Monitor": 3}

logger = structlog.get_logger(__name__)


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

        # Azure OpenAI client (same pattern as classifier.py)
        if settings.is_azure_openai_configured():
            self.client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version
            )
            self.deployment = settings.azure_openai_deployment
        else:
            self.client = None
            self.deployment = None

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

    def _generate_executive_summary(
        self,
        role: str,
        prepared_articles: List[dict],
        report_date: datetime
    ) -> ExecutiveSummary:
        """
        Generate AI-powered executive summary for a specific role.

        Args:
            role: Role name (e.g., "Brokers", "Leadership")
            prepared_articles: List of prepared article dictionaries
            report_date: Date of the report

        Returns:
            ExecutiveSummary object with structured summary content
        """
        # Filter articles for this role
        role_articles = [a for a in prepared_articles if role in a.get('roles', [])]

        # If no articles for role, return fallback
        if not role_articles:
            logger.info("no_articles_for_role", role=role)
            return ExecutiveSummary(
                summary_paragraphs=[f"No significant developments for {role} today."],
                key_numbers=[],
                role_context=f"No {role}-relevant intelligence in today's edition."
            )

        # If Azure OpenAI not configured, return fallback
        if self.client is None:
            logger.warning("azure_openai_not_configured", role=role)
            return ExecutiveSummary(
                summary_paragraphs=[
                    f"Executive summary generation requires Azure OpenAI configuration.",
                    f"Found {len(role_articles)} articles for {role} in today's edition."
                ],
                key_numbers=[f"{len(role_articles)} total articles"],
                role_context=f"Azure OpenAI configuration needed for AI-generated summaries."
            )

        try:
            # Sort by priority
            role_articles.sort(key=lambda a: PRIORITY_ORDER.get(a.get('priority'), 4))

            # Build article context from top 20 articles
            article_context = []
            for a in role_articles[:20]:
                context_str = (
                    f"[{a.get('priority', 'N/A')}] {a.get('title', 'No title')}\n"
                    f"{a.get('summary', a.get('description', 'No summary'))}\n"
                    f"(Category: {a.get('category', 'N/A')}, Impact: {a.get('impact_level', 'N/A')}, "
                    f"Region: {a.get('region', 'N/A')})"
                )
                article_context.append(context_str)

            article_context_str = "\n\n".join(article_context)

            # Build prompt
            system_message = {
                "role": "system",
                "content": "You are an insurance industry intelligence analyst writing executive summaries for senior professionals. Be concise, fact-based, and actionable."
            }

            date_str = report_date.strftime("%B %d, %Y") if report_date else "today"
            user_message = {
                "role": "user",
                "content": f"""Generate an executive summary for {role} based on {len(role_articles)} articles from {date_str}.

Articles (priority-sorted):
{article_context_str}

Generate:
1. 2-3 paragraphs summarizing key developments relevant to {role}
2. 3-5 key numbers/statistics from the articles (with context)
3. One sentence explaining why this matters to {role}

Focus on actionable insights and business implications."""
            }

            # Call Azure OpenAI with structured outputs
            completion = self.client.beta.chat.completions.parse(
                model=self.deployment,
                messages=[system_message, user_message],
                response_format=ExecutiveSummary,
                temperature=0.4
            )

            summary = completion.choices[0].message.parsed

            logger.info(
                "executive_summary_generated",
                role=role,
                article_count=len(role_articles),
                paragraph_count=len(summary.summary_paragraphs),
                key_numbers_count=len(summary.key_numbers)
            )

            return summary

        except Exception as e:
            logger.warning(
                "executive_summary_generation_failed",
                role=role,
                error=str(e)
            )
            # Return fallback on error
            return ExecutiveSummary(
                summary_paragraphs=[
                    f"Unable to generate AI summary for {role}.",
                    f"Found {len(role_articles)} articles in today's edition."
                ],
                key_numbers=[f"{len(role_articles)} total articles"],
                role_context=f"Summary generation encountered an error: {str(e)[:100]}"
            )

    def _generate_what_to_watch(
        self,
        prepared_articles: List[dict],
        report_date: datetime
    ) -> WhatToWatch:
        """
        Generate forward-looking "What to Watch" items based on high-priority
        and market trend articles.

        Args:
            prepared_articles: List of prepared article dictionaries
            report_date: Date of the report

        Returns:
            WhatToWatch object with 4-6 forward-looking items
        """
        # Filter to relevant articles: Critical/High priority OR Market Trends
        relevant_articles = [
            a for a in prepared_articles
            if a.get('priority') in ["Critical", "High"] or a.get('category') == "Market Trends"
        ]

        # If no relevant articles or Azure OpenAI not configured, return empty fallback
        if not relevant_articles or self.client is None:
            if self.client is None:
                logger.warning("azure_openai_not_configured_for_what_to_watch")
            else:
                logger.info("no_relevant_articles_for_what_to_watch", count=len(prepared_articles))
            return WhatToWatch(items=[])

        try:
            # Sort by priority
            relevant_articles.sort(key=lambda a: PRIORITY_ORDER.get(a.get('priority'), 4))

            # Build article context from top 15 relevant articles
            article_context = []
            for a in relevant_articles[:15]:
                context_str = (
                    f"{a.get('title', 'No title')}\n"
                    f"{a.get('summary', a.get('description', 'No summary'))}\n"
                    f"(Category: {a.get('category', 'N/A')}, Region: {a.get('region', 'N/A')})"
                )
                article_context.append(context_str)

            article_context_str = "\n\n".join(article_context)

            # Build prompt
            system_message = {
                "role": "system",
                "content": "You are a strategic intelligence analyst identifying forward-looking market signals for insurance professionals."
            }

            date_str = report_date.strftime("%B %d, %Y") if report_date else "today"
            user_message = {
                "role": "user",
                "content": f"""Based on {len(relevant_articles)} high-priority and market trend articles from {date_str}, identify 4-6 forward-looking items to watch.

Articles:
{article_context_str}

For each item, provide:
1. A concise headline (5-8 words)
2. 1-2 sentence explanation of what to watch and why
3. WHEN this matters (specific timeframe like "Next 30-60 days", "Q2 2026", "Renewal season 2026")
4. WHO should monitor this (which roles: Brokers, Leadership, Compliance, Underwriting)

Focus areas:
- M&A activity and due diligence timelines
- Regulatory changes and implementation deadlines
- Renewal cycle trends and pricing dynamics
- Emerging risks and market shifts

Generate 4-6 actionable forward-looking items."""
            }

            # Call Azure OpenAI with structured outputs
            completion = self.client.beta.chat.completions.parse(
                model=self.deployment,
                messages=[system_message, user_message],
                response_format=WhatToWatch,
                temperature=0.5
            )

            what_to_watch = completion.choices[0].message.parsed

            logger.info(
                "what_to_watch_generated",
                article_count=len(relevant_articles),
                item_count=len(what_to_watch.items)
            )

            return what_to_watch

        except Exception as e:
            logger.warning(
                "what_to_watch_generation_failed",
                error=str(e)
            )
            # Return empty fallback on error
            return WhatToWatch(items=[])

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

        # Generate executive summaries for all roles
        executive_summaries = {}
        for role in ["Brokers", "Leadership", "Compliance", "Underwriting"]:
            executive_summaries[role] = self._generate_executive_summary(
                role, prepared_articles, report_date
            )

        # Convert ExecutiveSummary objects to dicts for template
        executive_summaries_dict = {
            role: summary.model_dump() for role, summary in executive_summaries.items()
        }

        # Generate what to watch items
        what_to_watch = self._generate_what_to_watch(prepared_articles, report_date)
        what_to_watch_dict = what_to_watch.model_dump()

        # Aggregate data for visualizations (pure Python, fast)
        sector_heatmap = ReportAggregator.aggregate_sector_heatmap(prepared_articles)
        entity_tracker = ReportAggregator.aggregate_entity_tracker(prepared_articles, top_n=15)
        market_pulse = ReportAggregator.aggregate_market_pulse(prepared_articles)

        # Compute edition stats (now with entity and signal counts)
        source_count = len(set(a.source_name for a in articles if a.source_name))
        article_count = len(articles)

        edition_stats = {
            'source_count': source_count,
            'article_count': article_count,
            'entity_count': len(entity_tracker),
            'signal_count': len(what_to_watch_dict.get("items", [])),
        }

        # Load template
        template = self.env.get_template('role_brief.html')

        # Render template with complete context
        context = {
            'articles': prepared_articles,
            'report_date': report_date,
            'company_name': company_name,
            'edition_stats': edition_stats,
            'executive_summaries': executive_summaries_dict,
            'what_to_watch': what_to_watch_dict,
            'sector_heatmap': sector_heatmap,
            'entity_tracker': entity_tracker,
            'market_pulse': market_pulse,
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
