"""Tests for the writing guide and the article check."""

from domain.model.article import SourceInfo
from services.writing_service import check_article, get_writing_guide

SOURCE = SourceInfo(title="Titel", source_name="Zeitung", source_url="https://example.com/a")
CLEAN = "# Titel\n\nEin einfacher Text ohne Formatierung.\n\n* erster Punkt\n* zweiter Punkt"


# ── get_writing_guide ──


def test_guide_names_language_level_and_length():
    guide = get_writing_guide("German", "B1", "300")
    assert "German" in guide
    assert "CEFR level B1" in guide
    assert "about 300 words" in guide


def test_guide_leaves_out_level_and_length_when_not_given():
    guide = get_writing_guide("German")
    assert "CEFR" not in guide
    assert "Aim for about" not in guide
    assert "Never invent information" in guide


def test_guide_treats_a_level_outside_a1_c2_as_no_level():
    for level in ("b1", "Intermediate", "B1+"):
        guide = get_writing_guide("German", level, "300")
        assert "CEFR" not in guide
        assert "about 300 words" in guide


def test_guide_asks_for_plain_engaging_text():
    guide = get_writing_guide("German")
    assert "engaging and educational" in guide
    assert "any other formatting" in guide


def test_guide_does_not_ask_for_a_source_section():
    assert "Do not write a source section" in get_writing_guide("German", "B1", "300")


# ── check_article: blocking issues ──


def test_clean_text_with_source_passes():
    result = check_article(CLEAN, source=SOURCE)
    assert result.ok
    assert result.issues == []


def test_bold_is_blocked():
    result = check_article("Ein **wichtiges** Wort.", source=SOURCE)
    assert not result.ok
    assert len(result.issues) == 1 and "bold" in result.issues[0]


def test_italic_is_blocked():
    for text in ("Ein *wichtiges* Wort.", "Ein _wichtiges_ Wort."):
        result = check_article(text, source=SOURCE)
        assert len(result.issues) == 1 and "italics" in result.issues[0]


def test_bold_over_a_line_break_is_blocked():
    result = check_article("Ein **wich\ntiges** Wort.", source=SOURCE)
    assert len(result.issues) == 1 and "bold" in result.issues[0]


def test_blanks_and_spaced_marks_are_not_formatting():
    for text in ("Fill in: ___ and ___.", "2 ** 3 ** 4", "a * b * c", "Lehrer*innen und Schüler*innen"):
        assert check_article(text, source=SOURCE).ok, text


def test_backticks_are_blocked():
    result = check_article("Ein `wichtiges` Wort.", source=SOURCE)
    assert len(result.issues) == 1 and "backticks" in result.issues[0]


def test_bullets_and_underscores_in_urls_are_not_italics():
    text = "* erster Punkt\n* zweiter Punkt\n\nSiehe https://example.com/a_b_c und snake_case_name."
    assert check_article(text, source=SOURCE).ok


def test_vocabulary_section_is_blocked():
    for text in (
        "Text.\n\n## Vocabulary\n\n- Hund: dog",
        "Text.\n\nWortschatz:\n- Hund",
        "Text.\n\n### Key Vocabulary",
        "Text.\n\nKey vocabulary:\n- Hund",
        "Text.\n\n## Wichtige Wörter",
        "Text.\n\n## New words",
        "Text.\n\n## Lexique",
        "본문.\n\n## 단어",
        "본문.\n\n## 주요 어휘",
    ):
        result = check_article(text, source=SOURCE)
        assert len(result.issues) == 1 and "vocabulary list" in result.issues[0]


def test_a_title_that_only_contains_a_vocabulary_word_is_fine():
    for title in (
        "# The Vocabulary of Climate Change",
        "# Wie Kinder ihren Wortschatz erweitern",
        "# Warum Kinder Vocabulary-Apps lieben",
        "# 학생들의 어휘 능력 향상",
        "# 어휘력이 성적을 좌우한다",
        "## New Words for a New Era",
    ):
        assert check_article(f"{title}\n\nText.", source=SOURCE).ok, title


def test_the_word_vocabulary_inside_a_sentence_is_fine():
    assert check_article("Kinder lernen neuen Wortschatz in der Schule.", source=SOURCE).ok


def test_missing_source_is_blocked():
    for source in (None, SourceInfo(title="Titel", source_name="  ")):
        result = check_article(CLEAN, source=source)
        assert len(result.issues) == 1 and "source is missing" in result.issues[0]


def test_source_with_only_name_or_only_url_passes():
    assert check_article(CLEAN, source=SourceInfo(title="T", source_name="Zeitung")).ok
    assert check_article(CLEAN, source=SourceInfo(title="T", source_name="", source_url="https://example.com")).ok


# ── check_article: length warning ──


def test_length_within_a_quarter_of_target_has_no_warning():
    assert check_article("wort " * 80, length="100", source=SOURCE).warnings == []
    assert check_article("wort " * 125, length="100", source=SOURCE).warnings == []


def test_length_outside_a_quarter_of_target_warns_but_passes():
    for count in (60, 140):
        result = check_article("wort " * count, length="100", source=SOURCE)
        assert result.ok
        assert result.warnings == [f"The text has {count} words; the target is about 100."]


def test_no_length_means_no_warning():
    assert check_article("wort " * 5, source=SOURCE).warnings == []
