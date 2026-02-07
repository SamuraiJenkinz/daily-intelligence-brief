#!/usr/bin/env python3
"""
Database migration: Add Phase 3 classification fields to news_articles table.

Adds 5 new columns:
- entities: JSON array of extracted entities (companies, people, organizations)
- impact_level: Market impact level (Critical/High/Medium/Low)
- category: Article category (M&A/Regulatory/Loss Event/etc.)
- region: Geographic region (North America/Europe/etc.)
- business_line: Insurance business line (Property/Casualty/etc.)

All columns are nullable for backward compatibility with existing articles.

Usage:
    python scripts/migrate_003_classification_fields.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import engine
from sqlalchemy import text


def migrate():
    """Add Phase 3 classification fields to news_articles table."""

    columns = [
        ("entities", "TEXT", "JSON array of extracted entities"),
        ("impact_level", "VARCHAR(20)", "Market impact level"),
        ("category", "VARCHAR(50)", "Article category"),
        ("region", "VARCHAR(50)", "Geographic region"),
        ("business_line", "VARCHAR(50)", "Insurance business line"),
    ]

    print("Starting migration 003: Add classification fields")
    print("=" * 60)

    for col_name, col_type, description in columns:
        try:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE news_articles ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"[OK] Added column: {col_name} ({description})")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print(f"  Column '{col_name}' already exists - skipping")
            else:
                print(f"[ERROR] Error adding column '{col_name}': {e}")
                raise

    print("=" * 60)
    print("Migration 003 complete!")


if __name__ == "__main__":
    migrate()
