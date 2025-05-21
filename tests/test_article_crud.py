"""
Unit tests for article CRUD operations.

This module tests the CRUD operations for articles, with a focus on the upsert
and deduplication functionality.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app import crud, models, schemas


class TestArticleCrud(unittest.TestCase):
    """Test case for article CRUD operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=Session)
        self.test_uuid = uuid4()
        self.test_url = "https://example.com/article/123"
        self.test_datetime = datetime.utcnow()

    def test_get_article(self):
        """Test retrieving an article by ID."""
        # Configure mock
        mock_article = MagicMock(spec=models.Article)
        mock_article.id = self.test_uuid
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_article

        # Call the function
        result = crud.get_article(self.mock_db, self.test_uuid)

        # Verify results
        self.assertEqual(result, mock_article)
        self.mock_db.query.assert_called_once_with(models.Article)
        self.mock_db.query.return_value.filter.assert_called_once()

    def test_get_article_by_url(self):
        """Test retrieving an article by URL."""
        # Configure mock
        mock_article = MagicMock(spec=models.Article)
        mock_article.url = self.test_url
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_article

        # Call the function
        result = crud.get_article_by_url(self.mock_db, self.test_url)

        # Verify results
        self.assertEqual(result, mock_article)
        self.mock_db.query.assert_called_once_with(models.Article)
        self.mock_db.query.return_value.filter.assert_called_once()

    def test_create_article(self):
        """Test creating a new article."""
        # Create test data
        article_data = schemas.ArticleCreate(
            source="Test Source",
            title="Test Title",
            content="Test Content",
            url=self.test_url,
            published_at=self.test_datetime,
            authors="Test Author",
            image_url="https://example.com/image.jpg",
            summary="Test Summary"
        )

        # Call the function
        crud.create_article(self.mock_db, article_data)

        # Verify database operations
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()

        # Get the Article object that was created
        created_article = self.mock_db.add.call_args[0][0]
        self.assertEqual(created_article.source, "Test Source")
        self.assertEqual(created_article.title, "Test Title")
        self.assertEqual(created_article.content, "Test Content")
        self.assertEqual(created_article.url, self.test_url)
        self.assertEqual(created_article.published_at, self.test_datetime)
        self.assertEqual(created_article.authors, "Test Author")
        self.assertEqual(created_article.image_url, "https://example.com/image.jpg")
        self.assertEqual(created_article.summary, "Test Summary")

    def test_upsert_article_new(self):
        """Test upserting a new article (create case)."""
        # Configure mock to return None for get_article_by_url (article doesn't exist)
        with patch('app.crud.get_article_by_url') as mock_get:
            mock_get.return_value = None

            # Create test data
            article_data = schemas.ArticleCreate(
                source="Test Source",
                title="Test Title",
                content="Test Content",
                url=self.test_url,
                published_at=self.test_datetime,
                authors="Test Author",
                image_url="https://example.com/image.jpg",
                summary="Test Summary"
            )

            # Call the function
            with patch('app.crud.create_article') as mock_create:
                mock_created_article = MagicMock(spec=models.Article)
                mock_create.return_value = mock_created_article
                
                result, created = crud.upsert_article(self.mock_db, article_data)

                # Verify results
                self.assertEqual(result, mock_created_article)
                self.assertTrue(created)
                mock_get.assert_called_once_with(self.mock_db, self.test_url)
                mock_create.assert_called_once_with(self.mock_db, article_data)

    def test_upsert_article_existing(self):
        """Test upserting an existing article (update case)."""
        # Create mock existing article
        mock_existing = MagicMock(spec=models.Article)
        mock_existing.url = self.test_url
        mock_existing.title = "Old Title"
        mock_existing.content = "Old Content"
        mock_existing.source = "Old Source"
        mock_existing.published_at = self.test_datetime + timedelta(days=1)  # Newer date
        mock_existing.authors = "Old Author"
        mock_existing.image_url = "https://example.com/old_image.jpg"
        mock_existing.summary = "Old Summary"

        # Configure mock to return the existing article
        with patch('app.crud.get_article_by_url') as mock_get:
            mock_get.return_value = mock_existing

            # Create test data with an earlier date
            earlier_date = self.test_datetime - timedelta(days=1)
            article_data = schemas.ArticleCreate(
                source="New Source",
                title="New Title",
                content="New Content",
                url=self.test_url,
                published_at=earlier_date,  # Earlier date should be used
                authors="New Author",
                image_url="https://example.com/new_image.jpg",
                summary="New Summary"
            )

            # Call the function
            result, created = crud.upsert_article(self.mock_db, article_data)

            # Verify results
            self.assertEqual(result, mock_existing)
            self.assertFalse(created)
            
            # Verify that fields were updated
            self.assertEqual(mock_existing.title, "New Title")
            self.assertEqual(mock_existing.content, "New Content")
            self.assertEqual(mock_existing.source, "New Source")
            # Date should be updated to the earlier date
            self.assertEqual(mock_existing.published_at, earlier_date)
            self.assertEqual(mock_existing.authors, "New Author")
            self.assertEqual(mock_existing.image_url, "https://example.com/new_image.jpg")
            self.assertEqual(mock_existing.summary, "New Summary")
            
            mock_get.assert_called_once_with(self.mock_db, self.test_url)
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(mock_existing)

    def test_get_articles_by_date_range(self):
        """Test retrieving articles within a date range."""
        # Configure mock
        mock_articles = [MagicMock(spec=models.Article) for _ in range(3)]
        self.mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_articles

        # Define date range
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Call the function
        result = crud.get_articles_by_date_range(self.mock_db, start_date, end_date)

        # Verify results
        self.assertEqual(result, mock_articles)
        self.mock_db.query.assert_called_once_with(models.Article)
        self.mock_db.query.return_value.filter.assert_called()
        self.mock_db.query.return_value.filter.return_value.filter.assert_called()
        self.mock_db.query.return_value.filter.return_value.filter.return_value.order_by.assert_called_once()


if __name__ == "__main__":
    unittest.main() 