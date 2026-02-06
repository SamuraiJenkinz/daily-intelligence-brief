"""
Services module for MDInsights.

Contains business logic for collection, classification, and reporting.
"""
from app.services.collector import ApifyCollector

__all__ = ["ApifyCollector"]
