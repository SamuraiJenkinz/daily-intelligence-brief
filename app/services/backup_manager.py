"""
Database backup service with Azure Blob Storage integration.

Uses sqlite3 .backup() API for safe online backups (no exclusive lock).
Verifies backup integrity before upload and manages retention.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

logger = structlog.get_logger()


class DatabaseBackupManager:
    """Manages SQLite database backups with Azure Blob Storage integration."""

    def __init__(
        self,
        connection_string: str,
        container: str,
        retention_days: int
    ):
        """
        Initialize backup manager.

        Args:
            connection_string: Azure Storage connection string (empty string for local-only)
            container: Azure Blob container name
            retention_days: Number of days to retain backups in Azure
        """
        self.logger = logger.bind(service="backup")
        self.container_name = container
        self.retention_days = retention_days

        # Handle empty connection string gracefully
        if not connection_string:
            self.logger.warning("azure_not_configured",
                               message="Azure Storage connection string not set - backups will be local only")
            self.blob_service = None
        else:
            try:
                self.blob_service = BlobServiceClient.from_connection_string(connection_string)
                self.logger.info("azure_storage_initialized", container=container)
            except Exception as e:
                self.logger.error("azure_init_failed", error=str(e))
                self.blob_service = None

    def backup_database(self, db_path: str) -> dict:
        """
        Create a verified backup of the SQLite database.

        Args:
            db_path: Path to the SQLite database file

        Returns:
            dict with status, local_path, azure_uploaded, backup_name

        Raises:
            ValueError: If backup verification fails
            Exception: For other backup errors
        """
        try:
            # Create backup directory
            backup_dir = Path("data/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"mdinsights_{timestamp}.db"
            local_backup_path = backup_dir / backup_filename

            self.logger.info("backup_started",
                           source=db_path,
                           destination=str(local_backup_path))

            # Use sqlite3 .backup() API for safe online backup
            src_conn = sqlite3.connect(db_path)
            dst_conn = sqlite3.connect(str(local_backup_path))

            try:
                # Perform backup (safe with concurrent readers)
                src_conn.backup(dst_conn)
                self.logger.info("backup_completed", path=str(local_backup_path))
            finally:
                src_conn.close()
                dst_conn.close()

            # Verify backup integrity
            self._verify_backup(str(local_backup_path))

            # Upload to Azure if configured
            azure_uploaded = False
            if self.blob_service:
                self._upload_to_azure(str(local_backup_path), backup_filename)
                azure_uploaded = True

            # Cleanup old backups
            self._cleanup_local_backups()
            if self.blob_service:
                self._cleanup_azure_backups()

            result = {
                "status": "ok",
                "local_path": str(local_backup_path),
                "azure_uploaded": azure_uploaded,
                "backup_name": backup_filename
            }

            self.logger.info("backup_successful", **result)
            return result

        except Exception as e:
            self.logger.error("backup_failed", error=str(e), db_path=db_path)
            raise

    def _verify_backup(self, backup_path: str) -> None:
        """
        Verify backup integrity.

        Args:
            backup_path: Path to backup file

        Raises:
            ValueError: If integrity check fails or backup is empty
        """
        conn = sqlite3.connect(backup_path)

        try:
            # Run integrity check
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]

            if result != "ok":
                raise ValueError(f"Integrity check failed: {result}")

            # Check for empty backup
            cursor = conn.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table'"
            )
            table_count = cursor.fetchone()[0]

            if table_count == 0:
                raise ValueError("Backup is empty (no tables)")

            self.logger.info("backup_verified",
                           path=backup_path,
                           tables=table_count)

        finally:
            conn.close()

    def _upload_to_azure(self, local_path: str, blob_name: str) -> None:
        """
        Upload backup to Azure Blob Storage.

        Args:
            local_path: Path to local backup file
            blob_name: Name for blob in Azure

        Raises:
            Exception: If upload fails
        """
        try:
            # Ensure container exists
            container_client = self.blob_service.get_container_client(self.container_name)
            try:
                container_client.get_container_properties()
            except ResourceNotFoundError:
                self.logger.info("creating_container", container=self.container_name)
                container_client.create_container()

            # Upload blob
            blob_client = self.blob_service.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            with open(local_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=False)

            self.logger.info("azure_upload_complete",
                           blob=blob_name,
                           container=self.container_name)

        except Exception as e:
            self.logger.error("azure_upload_failed",
                            blob=blob_name,
                            error=str(e))
            raise

    def _cleanup_local_backups(self, max_age_days: int = 7) -> None:
        """
        Remove local backups older than max_age_days.

        Args:
            max_age_days: Maximum age in days for local backups
        """
        backup_dir = Path("data/backups")
        if not backup_dir.exists():
            return

        cutoff_time = datetime.now().timestamp() - (max_age_days * 86400)
        deleted_count = 0

        for backup_file in backup_dir.glob("mdinsights_*.db"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                deleted_count += 1

        if deleted_count > 0:
            self.logger.info("local_cleanup_complete",
                           deleted=deleted_count,
                           max_age_days=max_age_days)

    def _cleanup_azure_backups(self) -> None:
        """
        Remove Azure backups older than retention period.

        Raises:
            Exception: If cleanup fails
        """
        try:
            container_client = self.blob_service.get_container_client(self.container_name)

            # Ensure container exists
            try:
                container_client.get_container_properties()
            except ResourceNotFoundError:
                self.logger.info("container_not_found_skip_cleanup",
                               container=self.container_name)
                return

            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            deleted_count = 0

            # List and delete old blobs
            for blob in container_client.list_blobs():
                if blob.last_modified < cutoff_date:
                    container_client.delete_blob(blob.name)
                    deleted_count += 1

            if deleted_count > 0:
                self.logger.info("azure_cleanup_complete",
                               deleted=deleted_count,
                               retention_days=self.retention_days)

        except Exception as e:
            self.logger.error("azure_cleanup_failed", error=str(e))
            raise
