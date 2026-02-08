"""
MDInsights Database Backup Script

Creates a verified SQLite backup and uploads to Azure Blob Storage.
Run by Windows Task Scheduler daily or on-demand for disaster recovery.

Usage: python scripts/backup_db.py
Exit codes: 0 = success, 1 = failure
"""
import sys
import os
from pathlib import Path

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.services.backup_manager import DatabaseBackupManager


def main():
    """Run database backup with human-readable output."""
    try:
        settings = get_settings()

        print("MDInsights Database Backup")
        print("=" * 50)

        # Parse database path from settings
        db_url = settings.database_url
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            # Resolve relative paths from project root
            if not os.path.isabs(db_path):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                db_path = os.path.join(project_root, db_path)
        else:
            print(f"ERROR: Unsupported database URL format: {db_url}")
            return 1

        print(f"Database: {db_path}")

        # Check if database exists
        if not os.path.exists(db_path):
            print(f"ERROR: Database file not found: {db_path}")
            return 1

        # Initialize backup manager
        backup_manager = DatabaseBackupManager(
            connection_string=settings.azure_storage_connection_string,
            container=settings.azure_storage_container,
            retention_days=settings.backup_retention_days
        )

        # Run backup
        result = backup_manager.backup_database(db_path)

        # Print results
        print(f"Backup: {result['local_path']}")
        print(f"Integrity: OK")

        if result['azure_uploaded']:
            print(f"Azure upload: OK")
            print(f"Container: {settings.azure_storage_container}")
            print(f"Retention: {settings.backup_retention_days} days")
        else:
            print("Azure upload: SKIPPED (not configured)")
            print("Note: Backup saved locally only")

        print("\nBackup completed successfully!")
        return 0

    except Exception as e:
        print(f"\nERROR: Backup failed")
        print(f"Details: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
