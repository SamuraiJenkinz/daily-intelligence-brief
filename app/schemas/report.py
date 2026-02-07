"""
Pydantic schemas for report generation.

Used for structuring report context and data.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EditionStats(BaseModel):
    """
    Statistics for a single edition of the intelligence brief.

    Tracks metadata about articles included in this report edition.
    """

    source_count: int = Field(
        description="Number of unique sources in this edition"
    )
    article_count: int = Field(
        description="Total number of articles in this edition"
    )
    entity_count: int = Field(
        default=0,
        description="Number of tracked entities (filled by aggregator in Plan 04)"
    )
    signal_count: int = Field(
        default=0,
        description="Number of watch signals (filled by what-to-watch in Plan 05)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source_count": 12,
                "article_count": 47,
                "entity_count": 23,
                "signal_count": 5
            }
        }


class ExecutiveSummary(BaseModel):
    """Schema for role-specific executive summary (Azure OpenAI structured output)."""
    summary_paragraphs: List[str] = Field(
        description="2-3 paragraphs of executive summary for this role"
    )
    key_numbers: List[str] = Field(
        description="3-5 highlighted numbers/statistics from articles (with context)",
        default_factory=list
    )
    role_context: str = Field(
        description="One-sentence context about why this matters to this role"
    )


class ReportContext(BaseModel):
    """
    Context data for generating unified role-based intelligence brief.

    Provides all necessary information for template rendering.
    The brief is now unified (all roles in one HTML with tabs) rather than
    per-role briefs.
    """

    articles: List[dict] = Field(
        description="List of prepared article dictionaries (not ORM objects)"
    )
    report_date: datetime = Field(
        description="Date this report is generated for"
    )
    company_name: str = Field(
        description="Company name for report header (e.g., 'Marsh')"
    )
    edition_stats: Optional[EditionStats] = Field(
        default=None,
        description="Edition statistics (source count, article count, etc.)"
    )
    executive_summaries: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Role-specific executive summaries (added in Plan 02)"
    )
    sector_heatmap: Optional[List[Any]] = Field(
        default=None,
        description="Sector activity heatmap data (added in Plan 03)"
    )
    entity_tracker: Optional[List[Any]] = Field(
        default=None,
        description="Entity activity tracker data (added in Plan 04)"
    )
    what_to_watch: Optional[Any] = Field(
        default=None,
        description="What to watch signals (added in Plan 05)"
    )
    market_pulse: Optional[List[Any]] = Field(
        default=None,
        description="Market pulse indicators (added in Plan 06)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "articles": [],
                "report_date": "2026-02-07T00:00:00Z",
                "company_name": "Marsh",
                "edition_stats": {
                    "source_count": 12,
                    "article_count": 47
                }
            }
        }
