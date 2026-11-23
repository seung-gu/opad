"""Tests for find_known_words."""

from unittest.mock import MagicMock

from services.vocabulary_service import find_known_words


def test_asks_for_a1_to_one_level_above_and_at_most_50():
    vocab = MagicMock()
    vocab.find_lemmas.return_value = ["Haus", "Arbeit"]

    assert find_known_words("u1", "German", "B1", vocab) == ["Haus", "Arbeit"]
    vocab.find_lemmas.assert_called_once_with(
        user_id="u1", language="German", levels=["A1", "A2", "B1", "B2"], limit=50
    )


def test_no_level_asks_for_all_levels():
    vocab = MagicMock()
    find_known_words("u1", "German", None, vocab)
    assert vocab.find_lemmas.call_args.kwargs["levels"] == ["A1", "A2", "B1", "B2", "C1", "C2"]


def test_no_user_language_or_repository_gives_nothing():
    vocab = MagicMock()
    assert find_known_words(None, "German", "B1", vocab) == []
    assert find_known_words("u1", "", "B1", vocab) == []
    assert find_known_words("u1", "German", "B1", None) == []
    vocab.find_lemmas.assert_not_called()


def test_repository_returning_none_gives_nothing():
    vocab = MagicMock()
    vocab.find_lemmas.return_value = None
    assert find_known_words("u1", "German", "B1", vocab) == []
