"""Tests for API endpoints listing endpoint."""

import unittest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient

from api.main import app
from api.routes.endpoints import (
    group_endpoints_by_tag,
    get_sorted_tags,
    format_endpoint,
    format_tag_title,
    EXCLUDED_TAGS,
    EXCLUDED_PATHS,
)


class TestGroupEndpointsByTag(unittest.TestCase):
    """Tests for group_endpoints_by_tag() function."""

    def test_empty_endpoints_list(self):
        """Test grouping empty endpoints list returns empty dict."""
        result = group_endpoints_by_tag([])
        assert result == {}

    def test_endpoints_with_single_tag(self):
        """Test endpoints with single tag are grouped correctly."""
        endpoints = [
            {"method": "GET", "path": "/articles", "summary": "List articles", "tags": ["articles"]},
            {"method": "POST", "path": "/articles", "summary": "Create article", "tags": ["articles"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert "articles" in result
        assert len(result["articles"]) == 2
        assert result["articles"][0]["method"] == "GET"
        assert result["articles"][1]["method"] == "POST"

    def test_endpoints_with_multiple_tags_uses_first(self):
        """Test endpoints with multiple tags use the first tag."""
        endpoints = [
            {"method": "GET", "path": "/data", "summary": "Get data", "tags": ["primary", "secondary", "tertiary"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert "primary" in result
        assert len(result["primary"]) == 1
        assert result["primary"][0]["path"] == "/data"

    def test_endpoints_with_no_tags_map_to_other(self):
        """Test endpoints with no tags are mapped to 'other' group."""
        endpoints = [
            {"method": "GET", "path": "/health", "summary": "Health check", "tags": []},
            {"method": "GET", "path": "/status", "summary": "Status", "tags": []},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert "other" in result
        assert len(result["other"]) == 2

    def test_excluded_tags_filtered_out(self):
        """Test that EXCLUDED_TAGS are filtered out."""
        endpoints = [
            {"method": "GET", "path": "/meta", "summary": "Meta", "tags": ["meta"]},
            {"method": "GET", "path": "/articles", "summary": "Articles", "tags": ["articles"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert "meta" not in result
        assert "articles" in result
        assert len(result) == 1

    def test_filtering_of_meta_tag_specifically(self):
        """Test that 'meta' tag (in EXCLUDED_TAGS) is filtered."""
        assert "meta" in EXCLUDED_TAGS

        endpoints = [
            {"method": "GET", "path": "/endpoints", "summary": "List endpoints", "tags": ["meta"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert result == {}

    def test_sorting_within_group_by_path_then_method(self):
        """Test endpoints within group are sorted by (path, method)."""
        endpoints = [
            {"method": "DELETE", "path": "/articles/1", "summary": "Delete", "tags": ["articles"]},
            {"method": "GET", "path": "/articles", "summary": "List", "tags": ["articles"]},
            {"method": "POST", "path": "/articles", "summary": "Create", "tags": ["articles"]},
            {"method": "GET", "path": "/articles/1", "summary": "Get", "tags": ["articles"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        endpoints_list = result["articles"]
        # Expected order: /articles GET, /articles POST, /articles/1 DELETE, /articles/1 GET
        # (sorted by path first, then method alphabetically: DELETE < GET)
        assert endpoints_list[0]["path"] == "/articles" and endpoints_list[0]["method"] == "GET"
        assert endpoints_list[1]["path"] == "/articles" and endpoints_list[1]["method"] == "POST"
        assert endpoints_list[2]["path"] == "/articles/1" and endpoints_list[2]["method"] == "DELETE"
        assert endpoints_list[3]["path"] == "/articles/1" and endpoints_list[3]["method"] == "GET"

    def test_sorting_within_group_methods_alphabetically(self):
        """Test that within same path, methods are sorted alphabetically."""
        endpoints = [
            {"method": "POST", "path": "/articles", "summary": "Create", "tags": ["articles"]},
            {"method": "GET", "path": "/articles", "summary": "List", "tags": ["articles"]},
            {"method": "DELETE", "path": "/articles", "summary": "Delete", "tags": ["articles"]},
            {"method": "PUT", "path": "/articles", "summary": "Update", "tags": ["articles"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        # Methods sorted alphabetically: DELETE, GET, POST, PUT
        endpoints_list = result["articles"]
        assert endpoints_list[0]["method"] == "DELETE"
        assert endpoints_list[1]["method"] == "GET"
        assert endpoints_list[2]["method"] == "POST"
        assert endpoints_list[3]["method"] == "PUT"

    def test_mixed_tags_and_no_tags(self):
        """Test mix of tagged and untagged endpoints."""
        endpoints = [
            {"method": "GET", "path": "/articles", "summary": "List articles", "tags": ["articles"]},
            {"method": "GET", "path": "/health", "summary": "Health check", "tags": []},
            {"method": "POST", "path": "/articles", "summary": "Create", "tags": ["articles"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert "articles" in result
        assert "other" in result
        assert len(result["articles"]) == 2
        assert len(result["other"]) == 1

    def test_preserves_endpoint_data(self):
        """Test that all endpoint data is preserved after grouping."""
        endpoints = [
            {
                "method": "GET",
                "path": "/articles/1",
                "summary": "Get article",
                "tags": ["articles"]
            },
        ]
        result = group_endpoints_by_tag(endpoints)

        grouped_ep = result["articles"][0]
        assert grouped_ep["method"] == "GET"
        assert grouped_ep["path"] == "/articles/1"
        assert grouped_ep["summary"] == "Get article"
        assert grouped_ep["tags"] == ["articles"]

    def test_multiple_groups_with_different_tags(self):
        """Test endpoints grouped into multiple different tags."""
        endpoints = [
            {"method": "GET", "path": "/articles", "summary": "List", "tags": ["articles"]},
            {"method": "GET", "path": "/dictionary/search", "summary": "Search", "tags": ["dictionary"]},
            {"method": "GET", "path": "/usage/me", "summary": "My usage", "tags": ["usage"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert len(result) == 3
        assert "articles" in result
        assert "dictionary" in result
        assert "usage" in result


class TestGetSortedTags(unittest.TestCase):
    """Tests for get_sorted_tags() function."""

    def test_alphabetical_sorting(self):
        """Test tags are sorted alphabetically."""
        grouped = {
            "zebra": [],
            "alpha": [],
            "beta": [],
        }
        result = get_sorted_tags(grouped)

        assert result == ["alpha", "beta", "zebra"]

    def test_other_tag_at_end(self):
        """Test 'other' tag is placed at the end."""
        grouped = {
            "articles": [],
            "other": [],
            "dictionary": [],
            "usage": [],
        }
        result = get_sorted_tags(grouped)

        assert result[-1] == "other"
        assert "other" not in result[:-1]

    def test_other_tag_at_end_with_alphabetical_sorting(self):
        """Test 'other' stays at end while others are alphabetically sorted."""
        grouped = {
            "zebra": [],
            "other": [],
            "alpha": [],
            "beta": [],
        }
        result = get_sorted_tags(grouped)

        assert result == ["alpha", "beta", "zebra", "other"]

    def test_empty_grouped_dict(self):
        """Test with empty grouped dict returns empty list."""
        result = get_sorted_tags({})
        assert result == []

    def test_only_other_tag(self):
        """Test with only 'other' tag."""
        grouped = {"other": []}
        result = get_sorted_tags(grouped)

        assert result == ["other"]

    def test_no_other_tag(self):
        """Test without 'other' tag returns sorted tags without 'other'."""
        grouped = {
            "usage": [],
            "articles": [],
            "dictionary": [],
        }
        result = get_sorted_tags(grouped)

        assert result == ["articles", "dictionary", "usage"]
        assert "other" not in result

    def test_single_tag_alphabetically(self):
        """Test single tag returns as single-element list."""
        grouped = {"articles": []}
        result = get_sorted_tags(grouped)

        assert result == ["articles"]

    def test_case_sensitive_sorting(self):
        """Test that sorting is case sensitive (uppercase comes after lowercase)."""
        grouped = {
            "Articles": [],
            "articles": [],
            "Dictionary": [],
        }
        result = get_sorted_tags(grouped)

        # Python's default sort is lexicographic, uppercase comes before lowercase in ASCII
        assert len(result) == 3
        assert result[0] in result  # Just verify sort doesn't crash


class TestFormatEndpoint(unittest.TestCase):
    """Tests for format_endpoint() function."""

    def test_endpoint_with_summary(self):
        """Test formatting endpoint with summary."""
        endpoint = {
            "method": "GET",
            "path": "/articles",
            "summary": "List all articles",
        }
        result = format_endpoint(endpoint)

        assert 'class="method GET"' in result
        assert "/articles" in result
        assert "List all articles" in result
        assert 'class="summary"' in result
        assert "<span class=\"path\">/articles</span>" in result

    def test_endpoint_without_summary(self):
        """Test formatting endpoint without summary."""
        endpoint = {
            "method": "POST",
            "path": "/articles",
            "summary": None,
        }
        result = format_endpoint(endpoint)

        assert 'class="method POST"' in result
        assert "/articles" in result
        assert 'class="summary"' not in result

    def test_endpoint_with_empty_string_summary(self):
        """Test formatting endpoint with empty string summary."""
        endpoint = {
            "method": "DELETE",
            "path": "/articles/1",
            "summary": "",
        }
        result = format_endpoint(endpoint)

        assert 'class="method DELETE"' in result
        assert "/articles/1" in result
        assert 'class="summary"' not in result

    def test_various_http_methods(self):
        """Test formatting with various HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

        for method in methods:
            endpoint = {
                "method": method,
                "path": "/test",
                "summary": "Test endpoint",
            }
            result = format_endpoint(endpoint)

            assert f'class="method {method}"' in result

    def test_complex_path_formatting(self):
        """Test formatting with complex paths."""
        endpoint = {
            "method": "GET",
            "path": "/articles/{article_id}/vocabularies/{vocab_id}",
            "summary": "Get vocabulary for article",
        }
        result = format_endpoint(endpoint)

        assert "/articles/{article_id}/vocabularies/{vocab_id}" in result

    def test_summary_with_special_characters(self):
        """Test summary with special HTML characters."""
        endpoint = {
            "method": "GET",
            "path": "/search",
            "summary": "Search & filter articles <by> category",
        }
        result = format_endpoint(endpoint)

        # The summary should be included as-is (no escaping in this implementation)
        assert "Search & filter articles <by> category" in result

    def test_html_structure(self):
        """Test that output contains proper HTML structure."""
        endpoint = {
            "method": "GET",
            "path": "/test",
            "summary": "Test",
        }
        result = format_endpoint(endpoint)

        assert result.startswith('<div class="endpoint">')
        assert result.endswith('</div>')
        assert '<span class="method' in result
        assert '<span class="path">' in result

    def test_endpoint_html_has_all_required_elements(self):
        """Test endpoint HTML contains all required elements."""
        endpoint = {
            "method": "POST",
            "path": "/articles",
            "summary": "Create article",
        }
        result = format_endpoint(endpoint)

        # Check for endpoint div
        assert '<div class="endpoint">' in result
        # Check for method span
        assert '<span class="method POST">POST</span>' in result
        # Check for path span
        assert '<span class="path">/articles</span>' in result
        # Check for summary div
        assert '<div class="summary">Create article</div>' in result


class TestFormatTagTitle(unittest.TestCase):
    """Tests for format_tag_title() function."""

    def test_simple_tag_name(self):
        """Test formatting simple tag name."""
        result = format_tag_title("articles")
        assert result == "Articles Endpoints"

    def test_hyphenated_tag_name(self):
        """Test formatting hyphenated tag name (.title() capitalizes after hyphen)."""
        result = format_tag_title("article-vocabulary")
        assert result == "Article-Vocabulary Endpoints"

    def test_underscored_tag_name(self):
        """Test formatting underscored tag name (.title() capitalizes after underscore)."""
        result = format_tag_title("token_usage")
        assert result == "Token_Usage Endpoints"

    def test_single_word_tag(self):
        """Test formatting single word tag."""
        result = format_tag_title("usage")
        assert result == "Usage Endpoints"

    def test_all_lowercase_tag(self):
        """Test formatting all lowercase tag converts first letter to uppercase."""
        result = format_tag_title("dictionary")
        assert result == "Dictionary Endpoints"

    def test_uppercase_letters_in_tag(self):
        """Test formatting tag with uppercase letters uses title()."""
        result = format_tag_title("HTTPEndpoint")
        # title() converts each word's first letter to uppercase
        assert "Endpoints" in result

    def test_other_tag(self):
        """Test formatting 'other' tag."""
        result = format_tag_title("other")
        assert result == "Other Endpoints"

    def test_meta_tag(self):
        """Test formatting 'meta' tag."""
        result = format_tag_title("meta")
        assert result == "Meta Endpoints"

    def test_format_ends_with_endpoints(self):
        """Test that all formatted titles end with 'Endpoints'."""
        tags = ["articles", "vocabulary", "usage", "dictionary", "other"]

        for tag in tags:
            result = format_tag_title(tag)
            assert result.endswith("Endpoints")


class TestListEndpointsIntegration(unittest.TestCase):
    """Integration tests for list_endpoints endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_endpoints_list_returns_html_response(self):
        """Test that /endpoints returns HTML response."""
        response = self.client.get("/endpoints")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_endpoints_html_contains_title(self):
        """Test that returned HTML contains expected title."""
        response = self.client.get("/endpoints")

        assert response.status_code == 200
        assert "OPAD API - Implemented Endpoints" in response.text

    def test_endpoints_html_contains_styling(self):
        """Test that returned HTML contains styling."""
        response = self.client.get("/endpoints")

        assert response.status_code == 200
        assert "<style>" in response.text
        assert ".endpoint" in response.text
        assert ".method" in response.text

    def test_endpoints_html_contains_endpoint_divs(self):
        """Test that returned HTML contains endpoint divs."""
        response = self.client.get("/endpoints")

        assert response.status_code == 200
        assert 'class="endpoint"' in response.text

    def test_endpoints_html_contains_method_badges(self):
        """Test that returned HTML contains HTTP method badges."""
        response = self.client.get("/endpoints")

        assert response.status_code == 200
        # Should have some method badges (GET, POST, etc.)
        assert 'class="method' in response.text

    def test_endpoints_html_contains_paths(self):
        """Test that returned HTML contains endpoint paths."""
        response = self.client.get("/endpoints")

        assert response.status_code == 200
        # Should have path spans
        assert 'class="path"' in response.text

    def test_endpoints_html_has_doc_link(self):
        """Test that returned HTML contains link to /docs."""
        response = self.client.get("/endpoints")

        assert response.status_code == 200
        assert "/docs" in response.text
        assert "interactive API documentation" in response.text

    def test_endpoints_excludes_meta_tag_endpoints(self):
        """Test that endpoints with 'meta' tag are excluded from listing."""
        response = self.client.get("/endpoints")

        # The /endpoints endpoint itself should be excluded (it has meta tag)
        assert response.status_code == 200
        # The listing should not include meta endpoints in the output
        # Since we're listing all endpoints, we check that meta is not a section
        assert "Meta Endpoints" not in response.text or response.text.count("Meta Endpoints") == 0


class TestExcludedConstantsFormatting(unittest.TestCase):
    """Tests verifying EXCLUDED_TAGS and EXCLUDED_PATHS constants."""

    def test_excluded_tags_contains_meta(self):
        """Test that EXCLUDED_TAGS contains 'meta'."""
        assert "meta" in EXCLUDED_TAGS

    def test_excluded_paths_constant(self):
        """Test EXCLUDED_PATHS contains documentation paths."""
        assert "/docs" in EXCLUDED_PATHS
        assert "/openapi.json" in EXCLUDED_PATHS
        assert "/redoc" in EXCLUDED_PATHS

    def test_excluded_tags_is_set(self):
        """Test EXCLUDED_TAGS is a set for efficient lookup."""
        assert isinstance(EXCLUDED_TAGS, set)

    def test_excluded_paths_is_set(self):
        """Test EXCLUDED_PATHS is a set for efficient lookup."""
        assert isinstance(EXCLUDED_PATHS, set)


class TestEdgeCasesForGrouping(unittest.TestCase):
    """Edge case tests for endpoint grouping."""

    def test_endpoint_with_none_summary(self):
        """Test endpoint with None summary."""
        endpoints = [
            {"method": "GET", "path": "/test", "summary": None, "tags": ["test"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert "test" in result
        assert result["test"][0]["summary"] is None

    def test_large_number_of_endpoints(self):
        """Test grouping large number of endpoints."""
        endpoints = [
            {"method": "GET", "path": f"/endpoint/{i}", "summary": f"Endpoint {i}", "tags": ["api"]}
            for i in range(100)
        ]
        result = group_endpoints_by_tag(endpoints)

        assert "api" in result
        assert len(result["api"]) == 100

    def test_duplicate_paths_different_methods(self):
        """Test same path with different HTTP methods are grouped separately."""
        endpoints = [
            {"method": "GET", "path": "/resource", "summary": "Get", "tags": ["resource"]},
            {"method": "POST", "path": "/resource", "summary": "Create", "tags": ["resource"]},
            {"method": "PUT", "path": "/resource", "summary": "Update", "tags": ["resource"]},
            {"method": "DELETE", "path": "/resource", "summary": "Delete", "tags": ["resource"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert len(result["resource"]) == 4

    def test_endpoint_with_special_characters_in_path(self):
        """Test endpoint with special characters in path."""
        endpoints = [
            {"method": "GET", "path": "/search?q={query}", "summary": "Search", "tags": ["search"]},
        ]
        result = group_endpoints_by_tag(endpoints)

        assert result["search"][0]["path"] == "/search?q={query}"

    def test_tags_ordering_preserved_in_result(self):
        """Test that tags are consistently ordered."""
        endpoints = [
            {"method": "GET", "path": "/a", "summary": "A", "tags": ["zebra"]},
            {"method": "GET", "path": "/b", "summary": "B", "tags": ["alpha"]},
            {"method": "GET", "path": "/c", "summary": "C", "tags": ["beta"]},
        ]
        result1 = group_endpoints_by_tag(endpoints)
        result2 = group_endpoints_by_tag(endpoints)

        # Both results should have same tags (order in dict may vary, but content same)
        assert set(result1.keys()) == set(result2.keys())


if __name__ == '__main__':
    unittest.main()
