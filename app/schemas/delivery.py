"""
Pydantic schemas for email delivery management.

Provides structured recipient handling and delivery status tracking
for Phase 5 automated email delivery.
"""
from enum import Enum
from pydantic import BaseModel


class DeliveryStatus(str, Enum):
    """Status of email delivery attempt."""
    PENDING = "pending"      # Delivery not yet attempted
    SENT = "sent"            # Email submitted to Graph API (202 accepted)
    FAILED = "failed"        # Email send failed
    SKIPPED = "skipped"      # No recipients configured


class EmailRecipients(BaseModel):
    """
    Structured email recipient lists with TO/CC/BCC support.

    Used by Settings.get_email_recipients() to return parsed
    recipient configuration for each role.
    """
    to: list[str]
    cc: list[str] = []
    bcc: list[str] = []

    @property
    def total_recipients(self) -> int:
        """Total count of all recipients."""
        return len(self.to) + len(self.cc) + len(self.bcc)

    @property
    def has_recipients(self) -> bool:
        """Check if there's at least one recipient configured."""
        return len(self.to) > 0
