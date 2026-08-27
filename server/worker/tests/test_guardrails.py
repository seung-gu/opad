"""Tests for CrewAI task guardrails."""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adapter.crew.guardrails import repair_json_output, require_articles


class FakeTaskOutput:
    """Minimal stand-in for crewai.TaskOutput — the guardrails only read .raw."""

    def __init__(self, raw: str):
        self.raw = raw


class TestRepairJsonOutput(unittest.TestCase):

    def test_repairs_malformed_json(self):
        ok, output = repair_json_output(FakeTaskOutput('{"articles": [{"title": "A"},]}'))

        self.assertTrue(ok)
        self.assertNotIn(',]', output)

    def test_rejects_empty_output(self):
        ok, message = repair_json_output(FakeTaskOutput('   '))

        self.assertFalse(ok)
        self.assertIn('Empty output', message)


class TestRequireArticles(unittest.TestCase):
    """An empty article list must fail where it happens, not three tasks later.

    A dead search tool returns well-formed JSON with no results. Letting that
    through made the run fail on a Pydantic error about SelectedArticle.article
    being None — an error that named neither the search nor the expired key.
    """

    def test_rejects_empty_article_list(self):
        ok, message = require_articles(FakeTaskOutput('{"articles": []}'))

        self.assertFalse(ok)
        self.assertIn('No news articles were found', message)

    def test_rejects_missing_articles_key(self):
        ok, message = require_articles(FakeTaskOutput('{}'))

        self.assertFalse(ok)
        self.assertIn('No news articles were found', message)

    def test_accepts_populated_list(self):
        ok, output = require_articles(
            FakeTaskOutput('{"articles": [{"title": "A"}, {"title": "B"}]}')
        )

        self.assertTrue(ok)
        self.assertIn('title', output)

    def test_still_repairs_json_before_checking(self):
        """Malformed but non-empty output is repaired, not rejected."""
        ok, output = require_articles(FakeTaskOutput('{"articles": [{"title": "A"},]}'))

        self.assertTrue(ok)
        self.assertNotIn(',]', output)


if __name__ == '__main__':
    unittest.main()
