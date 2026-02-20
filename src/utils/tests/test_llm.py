"""Unit tests for parse_json_content — JSON extraction from LLM responses.

Tests for:
- parse_json_content() JSON extraction from various formats
"""

import unittest

from utils.json_parsing import parse_json_content


class TestParseJsonContent(unittest.TestCase):
    """Test cases for parse_json_content()."""

    def test_parse_plain_json(self):
        """Test parsing plain JSON content."""
        content = '{"key": "value", "number": 42}'
        result = parse_json_content(content)
        self.assertEqual(result, {"key": "value", "number": 42})

    def test_parse_json_in_markdown_code_block(self):
        """Test parsing JSON from markdown code block."""
        content = '```json\n{"key": "value"}\n```'
        result = parse_json_content(content)
        self.assertEqual(result, {"key": "value"})

    def test_parse_json_in_generic_code_block(self):
        """Test parsing JSON from generic markdown code block."""
        content = '```\n{"key": "value"}\n```'
        result = parse_json_content(content)
        self.assertEqual(result, {"key": "value"})

    def test_parse_json_with_surrounding_text(self):
        """Test parsing JSON with surrounding text."""
        content = 'Here is some JSON: {"key": "value"} and more text'
        result = parse_json_content(content)
        self.assertEqual(result, {"key": "value"})

    def test_parse_invalid_json_returns_none(self):
        """Test that invalid JSON returns None."""
        content = '{"incomplete": '
        result = parse_json_content(content)
        self.assertIsNone(result)

    def test_parse_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = parse_json_content("")
        self.assertIsNone(result)

    def test_parse_no_json_in_content_returns_none(self):
        """Test that content without JSON returns None."""
        result = parse_json_content("just some plain text")
        self.assertIsNone(result)

    def test_parse_json_with_nested_objects(self):
        """Test parsing JSON with nested objects."""
        content = '{"outer": {"inner": "value"}}'
        result = parse_json_content(content)
        self.assertEqual(result, {"outer": {"inner": "value"}})

    def test_parse_json_with_arrays(self):
        """Test parsing JSON with arrays."""
        content = '{"items": [1, 2, 3]}'
        result = parse_json_content(content)
        self.assertEqual(result, {"items": [1, 2, 3]})

    def test_parse_json_with_whitespace_in_markdown(self):
        """Test parsing JSON with extra whitespace in markdown."""
        content = '```json\n  \n  {"key": "value"}  \n  \n```'
        result = parse_json_content(content)
        self.assertEqual(result, {"key": "value"})


if __name__ == "__main__":
    unittest.main()
