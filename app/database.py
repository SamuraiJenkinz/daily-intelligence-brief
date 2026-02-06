"""
Database configuration for MDInsights API.

Provides SQLAlchemy engine, session factory, and declarative base for ORM models.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database URL from environment with default SQLite path
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/mdinsights.db")

# SQLite requires check_same_thread=False for FastAPI's async context
# This is safe because SQLAlchemy handles connection pooling properly
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=os.getenv("DEBUG", "false").lower() == "true"
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
