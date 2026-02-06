"""
Pydantic schemas for report generation.

Used for structuring report context and data.
"""
from typing import List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ReportContext(BaseModel):
    """
    Context data for generating role-specific reports.

    Provides all necessary information for template rendering.
    """

    target_role: str = Field(
        description="Role this report is targeted for (e.g., 'Brokers', 'Leadership')"
    )
    articles: List[Any] = Field(
        description="List of classified articles relevant to this role"
    )
    report_date: datetime = Field(
        description="Date this report is generated for"
    )
    company_name: str = Field(
        description="Company name for report header (e.g., 'Marsh')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "target_role": "Brokers",
                "articles": [],
                "report_date": "2026-02-06T00:00:00Z",
                "company_name": "Marsh"
            }
        }
