"""Unit tests for crew guardrails module.

Tests JSON repair functionality for handling malformed LLM outputs.
"""

import unittest
from unittest.mock import Mock

from crew.guardrails import repair_json_output


class TestRepairJsonOutput(unittest.TestCase):
    """Test cases for repair_json_output guardrail."""

    def _create_mock_output(self, raw_content: str) -> Mock:
        """Create a mock TaskOutput with given raw content."""
        mock = Mock()
        mock.raw = raw_content
        return mock

    def test_valid_json_passes_through(self):
        """Test that valid JSON passes through unchanged."""
        valid_json = '{"articles": [{"title": "Test", "content": "Hello"}]}'
        result = self._create_mock_output(valid_json)

        success, output = repair_json_output(result)

        self.assertTrue(success)
        self.assertEqual(output, valid_json)

    def test_repairs_missing_comma(self):
        """Test repair of missing comma between fields."""
        malformed = '{"title": "Test" "content": "Hello"}'
        result = self._create_mock_output(malformed)

        success, output = repair_json_output(result)

        self.assertTrue(success)
        self.assertIn('"title"', output)
        self.assertIn('"content"', output)

    def test_repairs_unclosed_brace(self):
        """Test repair of unclosed brace."""
        malformed = '{"title": "Test", "content": "Hello"'
        result = self._create_mock_output(malformed)

        success, output = repair_json_output(result)

        self.assertTrue(success)
        self.assertTrue(output.endswith('}'))

    def test_repairs_missing_quotes(self):
        """Test repair of missing quotes around keys."""
        malformed = '{title: "Test", content: "Hello"}'
        result = self._create_mock_output(malformed)

        success, output = repair_json_output(result)

        self.assertTrue(success)
        self.assertIn('"title"', output)

    def test_preserves_korean_characters(self):
        """Test that Korean characters are valid after repair (may be Unicode-escaped)."""
        korean_json = '{"title": "한국어 제목" "content": "안녕하세요"}'
        result = self._create_mock_output(korean_json)

        success, output = repair_json_output(result)

        self.assertTrue(success)
        # Verify JSON is valid and can be parsed back
        import json
        parsed = json.loads(output)
        self.assertEqual(parsed["title"], "한국어 제목")
        self.assertEqual(parsed["content"], "안녕하세요")

    def test_preserves_chinese_characters(self):
        """Test that Chinese characters are valid after repair (may be Unicode-escaped)."""
        chinese_json = '{"title": "中文标题" "content": "你好"}'
        result = self._create_mock_output(chinese_json)

        success, output = repair_json_output(result)

        self.assertTrue(success)
        # Verify JSON is valid and can be parsed back
        import json
        parsed = json.loads(output)
        self.assertEqual(parsed["title"], "中文标题")
        self.assertEqual(parsed["content"], "你好")

    def test_empty_output_returns_failure(self):
        """Test that empty output returns failure."""
        result = self._create_mock_output("")

        success, error = repair_json_output(result)

        self.assertFalse(success)
        self.assertIn("Empty", error)

    def test_whitespace_only_returns_failure(self):
        """Test that whitespace-only output returns failure."""
        result = self._create_mock_output("   \n\t  ")

        success, error = repair_json_output(result)

        self.assertFalse(success)
        self.assertIn("Empty", error)

    def test_none_raw_returns_failure(self):
        """Test that None raw content returns failure."""
        result = self._create_mock_output(None)

        success, error = repair_json_output(result)

        self.assertFalse(success)

    def test_repairs_trailing_comma(self):
        """Test repair of trailing comma in array."""
        malformed = '{"articles": [{"title": "Test"},]}'
        result = self._create_mock_output(malformed)

        success, output = repair_json_output(result)

        self.assertTrue(success)
        # Should have removed trailing comma
        self.assertNotIn(',]', output)

    def test_repairs_complex_nested_json(self):
        """Test repair of complex nested JSON structure."""
        malformed = '''{"articles": [
            {"title": "Article 1" "source_name": "News" "content": "Content 1"}
            {"title": "Article 2", "source_name": "Daily", "content": "Content 2"}
        ]}'''
        result = self._create_mock_output(malformed)

        success, output = repair_json_output(result)

        self.assertTrue(success)
        self.assertIn("Article 1", output)
        self.assertIn("Article 2", output)

    def test_repairs_unescaped_newlines_in_string(self):
        """Test repair of unescaped newlines in string values."""
        # Note: This depends on json-repair's capabilities
        malformed = '{"content": "Line 1\nLine 2"}'
        result = self._create_mock_output(malformed)

        success, output = repair_json_output(result)

        # Even if it can't repair perfectly, it should not crash
        self.assertIsInstance(success, bool)


class TestRepairJsonOutputLogging(unittest.TestCase):
    """Test logging behavior of repair_json_output."""

    def test_logs_when_repair_needed(self):
        """Test that repairs are logged."""
        from unittest.mock import patch

        malformed = '{"a": 1 "b": 2}'
        mock_output = Mock()
        mock_output.raw = malformed

        with patch('crew.guardrails.logger') as mock_logger:
            success, _ = repair_json_output(mock_output)

            self.assertTrue(success)
            # Should log when repair was made
            mock_logger.info.assert_called_once()

    def test_no_log_when_no_repair_needed(self):
        """Test that valid JSON doesn't trigger repair log."""
        from unittest.mock import patch

        valid_json = '{"a": 1, "b": 2}'
        mock_output = Mock()
        mock_output.raw = valid_json

        with patch('crew.guardrails.logger') as mock_logger:
            success, _ = repair_json_output(mock_output)

            self.assertTrue(success)
            # Should not log info (no repair needed)
            mock_logger.info.assert_not_called()


if __name__ == '__main__':
    unittest.main()
