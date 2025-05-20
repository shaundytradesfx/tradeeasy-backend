#!/usr/bin/env python
"""
Database Migration Script.

This script performs the necessary database migrations to update
the schema for the TradeEasy backend application.
"""

import logging
import sqlite3
import sys
from pathlib import Path

# Add the project root to the path so we can import our app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app import models
from app.database import SessionLocal, engine, get_db

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def migrate_articles_table():
    """
    Add the new columns to the articles table if they don't exist.
    """
    logger.info("Checking if the articles table needs migration...")

    # For SQLite, we need to use raw SQL to add columns
    try:
        # Connect to the database
        conn = sqlite3.connect("./tradeeasy.db")
        cursor = conn.cursor()

        # Check if the authors column exists
        cursor.execute("PRAGMA table_info(articles)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Add the missing columns if they don't exist
        if "authors" not in column_names:
            logger.info("Adding 'authors' column to articles table")
            cursor.execute("ALTER TABLE articles ADD COLUMN authors TEXT")

        if "image_url" not in column_names:
            logger.info("Adding 'image_url' column to articles table")
            cursor.execute("ALTER TABLE articles ADD COLUMN image_url TEXT")

        if "summary" not in column_names:
            logger.info("Adding 'summary' column to articles table")
            cursor.execute("ALTER TABLE articles ADD COLUMN summary TEXT")

        # Commit the changes
        conn.commit()
        logger.info("Database migration completed successfully.")

    except Exception as e:
        logger.error(f"Error during migration: {e}")

    finally:
        # Close the connection
        if conn:
            conn.close()


def update_tables_with_sqlalchemy():
    """
    Use SQLAlchemy to update/create all tables based on the models.
    """
    try:
        logger.info("Creating/updating tables with SQLAlchemy...")
        models.Base.metadata.create_all(bind=engine)
        logger.info("SQLAlchemy tables updated successfully.")
    except Exception as e:
        logger.error(f"Error updating tables with SQLAlchemy: {e}")


if __name__ == "__main__":
    logger.info("Starting database migration...")

    # Perform SQLite-specific migration for existing tables
    migrate_articles_table()

    # Use SQLAlchemy to create/update all tables
    update_tables_with_sqlalchemy()

    logger.info("Database migration completed.")
