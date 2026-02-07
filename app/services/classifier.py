"""
Azure OpenAI role classification service using structured outputs.

Uses GPT-4o with structured output parsing to classify articles by role,
priority, summary, and sentiment with guaranteed schema compliance.
"""
import json
from typing import List
import structlog
from openai import AzureOpenAI
from sqlalchemy.orm import Session

from app.schemas.classification import ArticleClassification
from app.models.news_article import NewsArticle


logger = structlog.get_logger(__name__)


# Classification prompt with role definitions and multi-role guidance
CLASSIFICATION_PROMPT = """You are an intelligence analyst for Marsh, a global insurance broker. Your job is to classify news articles by their relevance to different roles within the organization.

**CRITICAL INSTRUCTION**: Most significant articles apply to multiple roles. Be generous with role assignment — better to over-include than miss an audience.

**Role Definitions with Examples:**

**Brokers**: Articles relevant to sales, client relationships, market positioning
- Examples: Competitor intelligence, market positioning, pricing trends, capacity shifts, broker M&A, new product launches, client advisory topics

**Leadership**: Articles relevant to strategic decision-making and executive awareness
- Examples: Major M&A, financial results, strategic market shifts, industry forecasts, executive changes, economic trends, regulatory impacts

**Compliance**: Articles relevant to legal, regulatory, and policy matters
- Examples: Regulatory changes, legal developments, coverage gaps, policy reforms, sanctions, compliance requirements, litigation

**Underwriting**: Articles relevant to risk assessment, pricing, and technical insurance matters
- Examples: Catastrophe losses, combined ratios, reserve adequacy, rate movements, risk trends, claims patterns, reinsurance capacity

**Multi-Role Examples:**
- M&A article → Brokers (competitor intel) + Leadership (strategic implications)
- Regulatory change → Compliance (legal requirements) + Leadership (strategic impact) + Underwriting (technical implications)
- Catastrophic loss → Underwriting (loss assessment) + Leadership (market impact) + Brokers (client advisory)
- Financial results → Leadership (strategic) + Brokers (market positioning)

**Priority Guidance:**
- Critical: Immediate action required (major regulatory changes, catastrophic events, market disruptions)
- High: Monitor closely and prepare responses (significant M&A, financial changes, emerging risks)
- Medium: Informational and important for context (industry trends, smaller developments)
- Monitor: Background awareness only (general news, minor updates)

**Sentiment Guidance:**
- positive: Growth opportunities, favorable developments, competitive advantages
- negative: Losses, threats, regulatory burdens, competitive challenges
- neutral: Factual reporting without clear positive/negative implications

**Entity Extraction Guidelines:**

Extract 3-10 of the MOST RELEVANT entities (companies, people, organizations) mentioned in the article:
- **Companies**: Insurance carriers, brokers, reinsurers, vendors (e.g., "Marsh McLennan", "AIG", "Lloyd's of London"). Normalize to official full names.
- **People**: Named executives, analysts, regulators with their title/role if mentioned (e.g., "John Smith" with context "CEO of Zurich Insurance").
- **Organizations**: Regulators, trade associations, rating agencies (e.g., "NAIC", "AM Best", "European Commission").

Prioritize entities with significant context or market impact. Skip generic mentions without meaningful context.

**Impact Level Assessment:**

Assess market impact independently from priority (priority = urgency for Marsh, impact = market magnitude):
- **Critical**: Market-moving events ($1B+ losses, major regulatory overhauls, systemic risk indicators)
- **High**: Significant market impact ($100M-$1B range, important M&A, notable regulatory shifts)
- **Medium**: Notable but contained ($10M-$100M, smaller M&A, local regulations, regional events)
- **Low**: Minor industry news (<$10M impact, routine updates, individual appointments, editorial commentary)

**Category Assignment:**

Assign the PRIMARY category that best describes the article's main theme:
- **M&A**: Mergers, acquisitions, divestitures, strategic partnerships, joint ventures
- **Regulatory**: New regulations, compliance requirements, legal rulings, policy reforms
- **Loss Event**: Natural catastrophes, claims developments, reserve adjustments, insured losses
- **Financial Results**: Earnings reports, rate changes, combined ratios, premium growth
- **Market Trends**: Industry analysis, forecasts, emerging risks, market outlook
- **Product Launch**: New products, coverage innovations, technology deployments
- **Executive Change**: C-suite appointments, leadership transitions, board changes
- **Other**: Articles not fitting above categories

**Region Assignment:**

Assign the PRIMARY geographic focus of the article:
- **North America**: US, Canada, Bermuda
- **Europe**: UK, EU, Switzerland, Nordic
- **Asia Pacific**: Australia, Japan, China, India, Southeast Asia
- **Latin America**: Central and South America, Caribbean
- **Middle East & Africa**: MENA region, Sub-Saharan Africa
- **Global**: Multi-region stories, worldwide market impacts, international organizations

**Business Line Assignment:**

Assign the PRIMARY insurance business line affected:
- **Property**: Property insurance, homeowners, commercial property, fire
- **Casualty**: Auto, general liability, workers compensation, professional liability
- **Life & Health**: Life insurance, health insurance, accident, disability
- **Reinsurance**: Reinsurance treaties, retrocession, ILS, catastrophe bonds
- **Specialty**: Cyber, D&O, marine, aviation, political risk, niche coverages
- **Multiple Lines**: Cross-segment stories affecting 3+ business lines, multi-line carriers
- **Other**: Not clearly aligned with a specific business line
"""


class RoleClassificationService:
    """
    Service for classifying news articles using Azure OpenAI structured outputs.

    Uses GPT-4o with structured output parsing to ensure schema compliance
    and consistent classification results.
    """

    def __init__(self, endpoint: str, api_key: str, deployment: str, api_version: str = "2024-08-01-preview"):
        """
        Initialize classification service with Azure OpenAI credentials.

        Args:
            endpoint: Azure OpenAI endpoint URL
            api_key: Azure OpenAI API key
            deployment: Deployment name (e.g., "gpt-4o")
            api_version: API version supporting structured outputs (default: 2024-08-01-preview)
        """
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.deployment = deployment
        self.logger = structlog.get_logger(__name__)

    def classify_article(self, title: str, description: str, source: str) -> ArticleClassification:
        """
        Classify a single article using Azure OpenAI structured outputs.

        Args:
            title: Article title
            description: Article description/summary
            source: Source name

        Returns:
            ArticleClassification object with guaranteed schema compliance

        Raises:
            Exception: If classification fails (for retry logic)
        """
        try:
            # Build user message with article context
            user_message = f"""Title: {title}

Description: {description or "No description available"}

Source: {source}

Classify this article according to the role definitions provided."""

            # Use structured output parsing with guaranteed schema compliance
            completion = self.client.beta.chat.completions.parse(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                response_format=ArticleClassification,
                temperature=0.3  # Lower temperature for consistent classification
            )

            # Extract parsed classification from response
            classification = completion.choices[0].message.parsed

            self.logger.info(
                "article_classified",
                title=title[:50],
                roles=classification.roles,
                priority=classification.priority,
                sentiment=classification.sentiment
            )

            return classification

        except Exception as e:
            self.logger.error(
                "classification_failed",
                title=title[:50],
                error=str(e)
            )
            raise

    def classify_articles(self, db: Session, articles: List[NewsArticle]) -> int:
        """
        Classify a batch of articles and update database with results.

        Processes articles in batches, committing every 10 articles for
        progress tracking and error recovery. Skips articles that fail
        classification to avoid blocking the entire batch.

        Args:
            db: SQLAlchemy database session
            articles: List of NewsArticle objects to classify

        Returns:
            Number of articles successfully classified
        """
        classified_count = 0
        total_articles = len(articles)

        self.logger.info(
            "classification_batch_started",
            total_articles=total_articles
        )

        for idx, article in enumerate(articles, 1):
            try:
                # Skip if already classified
                if article.roles is not None:
                    self.logger.debug(
                        "article_already_classified",
                        article_id=article.id,
                        title=article.title[:50]
                    )
                    continue

                # Classify article
                classification = self.classify_article(
                    title=article.title,
                    description=article.description or "",
                    source=article.source_name or "Unknown"
                )

                # Update article with classification results
                article.roles = json.dumps(classification.roles)
                article.priority = classification.priority
                article.summary = classification.summary
                article.sentiment = classification.sentiment

                classified_count += 1

                # Commit in batches of 10 for progress tracking
                if classified_count % 10 == 0:
                    db.commit()
                    self.logger.info(
                        "classification_progress",
                        classified=classified_count,
                        total=total_articles,
                        progress_pct=round((classified_count / total_articles) * 100, 1)
                    )

            except Exception as e:
                # Log error but continue with remaining articles
                self.logger.error(
                    "article_classification_failed",
                    article_id=article.id,
                    title=article.title[:50],
                    error=str(e)
                )
                # Don't fail entire batch on single article error
                continue

        # Final commit for remaining articles
        db.commit()

        self.logger.info(
            "classification_batch_completed",
            classified=classified_count,
            total=total_articles,
            success_rate=round((classified_count / total_articles) * 100, 1) if total_articles > 0 else 0
        )

        return classified_count
