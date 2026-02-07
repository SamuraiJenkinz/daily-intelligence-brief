"""
News source scrapers module.

Contains abstract base class and concrete implementations for each
supported news source.
"""
from app.services.sources.base import NewsSource
from app.services.sources.reinsurance_news import ReinsuranceNewsSource
from app.services.sources.insurance_journal import InsuranceJournalSource
from app.services.sources.business_insurance import BusinessInsuranceSource
from app.services.sources.artemis import ArtemisSource
from app.services.sources.lloyds_list import LloydsListSource
from app.services.sources.rss_source import RSSSource

__all__ = [
    "NewsSource",
    "ReinsuranceNewsSource",
    "InsuranceJournalSource",
    "BusinessInsuranceSource",
    "ArtemisSource",
    "LloydsListSource",
    "RSSSource"
]
