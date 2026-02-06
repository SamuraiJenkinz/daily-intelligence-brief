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

    class Config:
        json_schema_extra = {
            "example": {
                "roles": ["Brokers", "Leadership"],
                "priority": "High",
                "summary": "Major regulatory change affecting sales process and compliance requirements",
                "sentiment": "negative"
            }
        }
