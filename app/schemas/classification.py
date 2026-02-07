"""
Pydantic schemas for article classification.

Used for Azure OpenAI structured output guidance.
"""
from typing import List, Literal
from pydantic import BaseModel, Field


# Define role and priority types as literals for validation
RoleType = Literal["Brokers", "Leadership", "Compliance", "Underwriting"]
PriorityType = Literal["Critical", "High", "Medium", "Monitor"]
SentimentType = Literal["positive", "negative", "neutral"]

# Phase 3: Advanced classification types
ImpactLevelType = Literal["Critical", "High", "Medium", "Low"]
CategoryType = Literal["M&A", "Regulatory", "Loss Event", "Financial Results", "Market Trends", "Product Launch", "Executive Change", "Other"]
RegionType = Literal["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa", "Global"]
BusinessLineType = Literal["Property", "Casualty", "Life & Health", "Reinsurance", "Specialty", "Multiple Lines", "Other"]


class ExtractedEntity(BaseModel):
    """
    Entity extracted from article (company, person, or organization).

    Used to identify key actors and stakeholders mentioned in news articles.
    """
    name: str = Field(
        description="Entity name normalized to official form (e.g., 'Marsh McLennan' not 'Marsh')"
    )
    type: Literal["company", "person", "organization"] = Field(
        description="Entity type: company (insurers/brokers/vendors), person (executives/analysts), organization (regulators/associations)"
    )
    context: str = Field(
        description="Brief context of entity's role in the article (1 sentence)"
    )


class ArticleClassification(BaseModel):
    """
    Article classification schema for Azure OpenAI structured output.

    Guides the AI to classify articles by relevance to multiple roles,
    priority level, and sentiment.
    """

    roles: List[RoleType] = Field(
        description="List of roles this article is relevant to. Can be multiple roles per article."
    )
    priority: PriorityType = Field(
        description="Priority level: Critical (immediate action), High (urgent attention), "
                    "Medium (important but not urgent), Monitor (awareness only)"
    )
    summary: str = Field(
        description="Concise summary of the article highlighting key points relevant to the target roles"
    )
    sentiment: SentimentType = Field(
        description="Overall sentiment: positive (favorable news), negative (concerns/risks), "
                    "neutral (informational)"
    )

    # Phase 3: Advanced classification fields
    entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="3-10 most relevant companies, people, and organizations mentioned in article"
    )
    impact_level: ImpactLevelType = Field(
        description="Market impact: Critical ($1B+/systemic), High ($100M-$1B), Medium ($10M-$100M), Low (<$10M/routine)"
    )
    category: CategoryType = Field(
        description="Primary article category based on content theme"
    )
    region: RegionType = Field(
        description="Primary geographic region. Use Global for multi-region stories."
    )
    business_line: BusinessLineType = Field(
        description="Primary insurance business line affected. Use Multiple Lines for cross-segment."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "roles": ["Brokers", "Leadership"],
                "priority": "High",
                "summary": "Major regulatory change affecting sales process and compliance requirements",
                "sentiment": "negative",
                "entities": [
                    {"name": "Marsh McLennan", "type": "company", "context": "Major broker adapting to new compliance rules"},
                    {"name": "SEC", "type": "organization", "context": "Regulatory body issuing new guidance"}
                ],
                "impact_level": "High",
                "category": "Regulatory",
                "region": "North America",
                "business_line": "Multiple Lines"
            }
        }
