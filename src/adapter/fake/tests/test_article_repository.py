"""Unit tests for FakeArticleRepository — verifies Port contract compliance."""

import unittest
from datetime import datetime, timedelta, timezone

from adapter.fake.article_repository import FakeArticleRepository
from domain.model.article import Article, ArticleInputs, ArticleStatus


class TestFakeArticleRepository(unittest.TestCase):
    """Tests that FakeArticleRepository correctly implements ArticleRepository Protocol."""

    def setUp(self):
        self.repo = FakeArticleRepository()
        self.inputs = ArticleInputs(language='German', level='B2', length='500', topic='AI')

    # ── save_metadata + get_by_id (round-trip) ────────────────

    def test_save_metadata_and_get_by_id(self):
        """save_metadata → get_by_id returns the same Article."""
        result = self.repo.save_metadata(
            article_id='art-1',
            inputs=self.inputs,
            user_id='user-1',
            job_id='job-1',
        )

        self.assertTrue(result)
        article = self.repo.get_by_id('art-1')
        self.assertIsNotNone(article)
        self.assertIsInstance(article, Article)
        self.assertEqual(article.id, 'art-1')
        self.assertEqual(article.inputs, self.inputs)
        self.assertEqual(article.status, ArticleStatus.RUNNING)
        self.assertEqual(article.user_id, 'user-1')
        self.assertEqual(article.job_id, 'job-1')
        self.assertIsNone(article.content)

    def test_get_by_id_returns_none_for_missing(self):
        self.assertIsNone(self.repo.get_by_id('nonexistent'))

    # ── save_content ──────────────────────────────────────────

    def test_save_content_updates_article(self):
        """save_content sets content and status to COMPLETED."""
        self.repo.save_metadata(article_id='art-1', inputs=self.inputs)
        result = self.repo.save_content('art-1', '# Hello World')

        self.assertTrue(result)
        article = self.repo.get_by_id('art-1')
        self.assertEqual(article.content, '# Hello World')
        self.assertEqual(article.status, ArticleStatus.COMPLETED)

    def test_save_content_returns_false_for_missing(self):
        self.assertFalse(self.repo.save_content('nonexistent', 'content'))

    def test_save_content_with_started_at(self):
        self.repo.save_metadata(article_id='art-1', inputs=self.inputs)
        started = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.repo.save_content('art-1', 'content', started_at=started)

        article = self.repo.get_by_id('art-1')
        self.assertEqual(article.started_at, started)

    # ── update_status ─────────────────────────────────────────

    def test_update_status(self):
        self.repo.save_metadata(article_id='art-1', inputs=self.inputs)
        result = self.repo.update_status('art-1', ArticleStatus.FAILED)

        self.assertTrue(result)
        self.assertEqual(self.repo.get_by_id('art-1').status, ArticleStatus.FAILED)

    def test_update_status_returns_false_for_missing(self):
        self.assertFalse(self.repo.update_status('nonexistent', ArticleStatus.FAILED))

    # ── delete (soft delete) ──────────────────────────────────

    def test_delete_sets_status_deleted(self):
        self.repo.save_metadata(article_id='art-1', inputs=self.inputs)
        result = self.repo.delete('art-1')

        self.assertTrue(result)
        self.assertEqual(self.repo.get_by_id('art-1').status, ArticleStatus.DELETED)

    def test_delete_returns_false_for_missing(self):
        self.assertFalse(self.repo.delete('nonexistent'))

    # ── find_many ─────────────────────────────────────────────

    def test_find_many_returns_all_non_deleted(self):
        self.repo.save_metadata(article_id='art-1', inputs=self.inputs)
        self.repo.save_metadata(article_id='art-2', inputs=self.inputs)
        self.repo.delete('art-2')

        articles, total = self.repo.find_many()
        self.assertEqual(total, 1)
        self.assertEqual(articles[0].id, 'art-1')

    def test_find_many_filters_by_status(self):
        self.repo.save_metadata(article_id='art-1', inputs=self.inputs)
        self.repo.save_content('art-1', 'content')
        self.repo.save_metadata(article_id='art-2', inputs=self.inputs)

        articles, total = self.repo.find_many(status=ArticleStatus.COMPLETED)
        self.assertEqual(total, 1)
        self.assertEqual(articles[0].id, 'art-1')

    def test_find_many_filters_by_language(self):
        self.repo.save_metadata(article_id='art-1', inputs=self.inputs)
        self.repo.save_metadata(
            article_id='art-2',
            inputs=ArticleInputs(language='English', level='B2', length='500', topic='AI'),
        )

        articles, total = self.repo.find_many(language='English')
        self.assertEqual(total, 1)
        self.assertEqual(articles[0].id, 'art-2')

    def test_find_many_pagination(self):
        for i in range(5):
            self.repo.save_metadata(
                article_id=f'art-{i}',
                inputs=self.inputs,
                created_at=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
            )

        articles, total = self.repo.find_many(skip=1, limit=2)
        self.assertEqual(total, 5)
        self.assertEqual(len(articles), 2)

    def test_find_many_sorted_newest_first(self):
        self.repo.save_metadata(
            article_id='old', inputs=self.inputs,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.repo.save_metadata(
            article_id='new', inputs=self.inputs,
            created_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        )

        articles, _ = self.repo.find_many()
        self.assertEqual(articles[0].id, 'new')
        self.assertEqual(articles[1].id, 'old')

    # ── find_duplicate ────────────────────────────────────────

    def test_find_duplicate(self):
        self.repo.save_metadata(
            article_id='art-1', inputs=self.inputs,
            created_at=datetime.now(timezone.utc)-timedelta(hours=12), user_id='user-1'
        )
        self.repo.save_metadata(
            article_id='art-2', inputs=self.inputs,
            created_at=datetime.now(timezone.utc)-timedelta(hours=36), user_id='user-2'
        )

        self.assertTrue(self.repo.find_duplicate(self.inputs, user_id='user-1', hours=24))
        self.assertFalse(self.repo.find_duplicate(self.inputs, user_id='user-2', hours=24))


if __name__ == '__main__':
    unittest.main()
