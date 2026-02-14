"""Unit tests for Article domain model — ArticleStatus, ArticleInputs, Article.

Tests focus on business-logic behavior used by other components:
- ArticleStatus string↔enum conversion (used by _to_domain adapter)
- ArticleInputs equality/hash (used by find_duplicate)
"""

import unittest

from domain.model.article import ArticleInputs, ArticleStatus


class TestArticleStatus(unittest.TestCase):
    """Tests for ArticleStatus string-enum behavior used by _to_domain adapter."""

    def test_article_status_is_string_enum(self):
        """ArticleStatus compares equal to its string value (used in adapter layer)."""
        self.assertEqual(ArticleStatus.RUNNING, 'running')
        self.assertEqual(ArticleStatus.COMPLETED, 'completed')
        self.assertEqual(ArticleStatus.FAILED, 'failed')
        self.assertEqual(ArticleStatus.DELETED, 'deleted')

    def test_article_status_from_string_value(self):
        """ArticleStatus can be constructed from string values stored in MongoDB."""
        self.assertEqual(ArticleStatus('running'), ArticleStatus.RUNNING)
        self.assertEqual(ArticleStatus('completed'), ArticleStatus.COMPLETED)
        self.assertEqual(ArticleStatus('failed'), ArticleStatus.FAILED)
        self.assertEqual(ArticleStatus('deleted'), ArticleStatus.DELETED)


class TestArticleInputs(unittest.TestCase):
    """Tests for ArticleInputs equality and hashing used by find_duplicate."""

    def test_article_inputs_equality(self):
        """ArticleInputs instances with identical fields are equal (find_duplicate relies on this)."""
        inputs1 = ArticleInputs(
            language='German',
            level='B2',
            length='500',
            topic='Technology'
        )
        inputs2 = ArticleInputs(
            language='German',
            level='B2',
            length='500',
            topic='Technology'
        )
        self.assertEqual(inputs1, inputs2)

    def test_article_inputs_inequality(self):
        """ArticleInputs instances with different fields are not equal."""
        inputs1 = ArticleInputs(
            language='German',
            level='B2',
            length='500',
            topic='Technology'
        )
        inputs2 = ArticleInputs(
            language='English',
            level='B2',
            length='500',
            topic='Technology'
        )
        self.assertNotEqual(inputs1, inputs2)

    def test_article_inputs_hash_consistency(self):
        """Equal ArticleInputs produce same hash, enabling set/dict deduplication."""
        inputs1 = ArticleInputs(
            language='German',
            level='B2',
            length='500',
            topic='Technology'
        )
        inputs2 = ArticleInputs(
            language='German',
            level='B2',
            length='500',
            topic='Technology'
        )
        # Same hash → collapses in set
        input_set = {inputs1, inputs2}
        self.assertEqual(len(input_set), 1)

        # Dict lookup by equal key
        input_dict = {inputs1: 'value1'}
        self.assertEqual(input_dict[inputs2], 'value1')


if __name__ == '__main__':
    unittest.main()
