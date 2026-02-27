"""
Pydantic schemas for admin interface forms and validation.

Provides validation models for source management operations.
"""
from pydantic import BaseModel, field_validator


class SourceCreate(BaseModel):
    """Schema for creating a new source."""
    name: str
    url: str
    enabled: bool = True

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is not empty and within length limits."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        if len(v) > 255:
            raise ValueError('Name must be 255 characters or less')
        return v.strip()

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL is not empty."""
        if not v or len(v.strip()) == 0:
            raise ValueError('URL cannot be empty')
        return v.strip()


class SourceUpdate(BaseModel):
    """Schema for updating an existing source."""
    name: str
    url: str
    enabled: bool = True

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is not empty and within length limits."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        if len(v) > 255:
            raise ValueError('Name must be 255 characters or less')
        return v.strip()

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL is not empty."""
        if not v or len(v.strip()) == 0:
            raise ValueError('URL cannot be empty')
        return v.strip()
