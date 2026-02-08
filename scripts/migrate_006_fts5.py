#!/usr/bin/env python3
"""
Database migration: Add SQLite FTS5 full-text search support for articles.

Creates articles_fts virtual table with triggers to keep it synchronized
with news_articles table. Enables fast full-text search with BM25 ranking.

Usage:
    python scripts/migrate_006_fts5.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import engine
from sqlalchemy import text


def migrate():
    """Create FTS5 virtual table and sync triggers for news_articles."""

    print("Starting migration 006: Add FTS5 full-text search")
    print("=" * 60)

    with engine.connect() as conn:
        # 1. Create FTS5 virtual table
        try:
            conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                    title,
                    description,
                    summary,
                    content=news_articles,
                    content_rowid=id,
                    tokenize='porter unicode61'
                )
            """))
            conn.commit()
            print("[OK] Created FTS5 virtual table: articles_fts")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  FTS5 table 'articles_fts' already exists - skipping")
            else:
                print(f"[ERROR] Error creating FTS5 table: {e}")
                raise

        # 2. Create INSERT trigger
        try:
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS articles_fts_insert
                AFTER INSERT ON news_articles
                BEGIN
                    INSERT INTO articles_fts(rowid, title, description, summary)
                    VALUES (new.id, new.title, new.description, new.summary);
                END
            """))
            conn.commit()
            print("[OK] Created INSERT trigger: articles_fts_insert")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  INSERT trigger already exists - skipping")
            else:
                print(f"[ERROR] Error creating INSERT trigger: {e}")
                raise

        # 3. Create UPDATE trigger
        try:
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS articles_fts_update
                AFTER UPDATE ON news_articles
                BEGIN
                    UPDATE articles_fts
                    SET title = new.title,
                        description = new.description,
                        summary = new.summary
                    WHERE rowid = new.id;
                END
            """))
            conn.commit()
            print("[OK] Created UPDATE trigger: articles_fts_update")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  UPDATE trigger already exists - skipping")
            else:
                print(f"[ERROR] Error creating UPDATE trigger: {e}")
                raise

        # 4. Create DELETE trigger
        try:
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS articles_fts_delete
                AFTER DELETE ON news_articles
                BEGIN
                    DELETE FROM articles_fts WHERE rowid = old.id;
                END
            """))
            conn.commit()
            print("[OK] Created DELETE trigger: articles_fts_delete")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  DELETE trigger already exists - skipping")
            else:
                print(f"[ERROR] Error creating DELETE trigger: {e}")
                raise

        # 5. Backfill existing data
        try:
            # Check if FTS5 table is empty
            result = conn.execute(text("SELECT COUNT(*) FROM articles_fts")).fetchone()
            fts_count = result[0] if result else 0

            # Get article count
            result = conn.execute(text("SELECT COUNT(*) FROM news_articles")).fetchone()
            articles_count = result[0] if result else 0

            if fts_count == 0 and articles_count > 0:
                # Backfill data
                conn.execute(text("""
                    INSERT INTO articles_fts(rowid, title, description, summary)
                    SELECT id, title, description, summary FROM news_articles
                """))
                conn.commit()
                print(f"[OK] Backfilled {articles_count} existing articles into FTS5 table")
            elif fts_count > 0:
                print(f"  FTS5 table already contains {fts_count} entries - skipping backfill")
            else:
                print("  No existing articles to backfill")

        except Exception as e:
            print(f"[WARNING] Error during backfill: {e}")
            # Non-fatal - triggers will sync new data

    print("=" * 60)
    print("Migration 006 complete!")


if __name__ == "__main__":
    migrate()
