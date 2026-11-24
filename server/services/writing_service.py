"""Writing rules — how an article should be written, and the check that it was.

get_writing_guide() gives the rules as text for whoever writes (the rewriter,
the reviewer, outside writers over MCP). check_article() verifies the rules code
can verify. They sit together so a rule and its check change together.

No LLM and no I/O. The rules were moved from the CrewAI prompts in
adapter/crew/config/tasks.yaml, which stay as they are while both paths run.
"""

import re
from dataclasses import dataclass, field

from domain.model.article import SourceInfo
from domain.model.cefr import Level

_LEVEL_NOTES: dict[Level, str] = {
    "A1": "very common words and short, simple sentences in the present tense",
    "A2": "everyday words and simple sentences joined by basic connectors",
    "B1": "general vocabulary and clear sentences, with some subordinate clauses",
    "B2": "a wide vocabulary, including abstract and professional words, and more complex sentences",
    "C1": "academic and idiomatic vocabulary with complex, varied sentence structures",
    "C2": "literary and nuanced vocabulary with no simplification of structure",
}


def get_writing_guide(language: str, level: Level | None = None, length: str | None = None) -> str:
    """Return the writing rules as text. Lines about level and length are left out when not given.

    A level outside A1-C2 counts as no level, as in CEFRLevel.
    """
    rules = [f"Write the article in {language}."]
    level_note = _LEVEL_NOTES.get(level)
    if level_note:
        rules.append(
            f"Match CEFR level {level}: use {level_note}. "
            "Simplify sentence structures while keeping the original meaning and key information."
        )
    if length:
        rules.append(
            f"Aim for about {length} words. If the original article is shorter, keep it short. "
            "Do not pad it to reach the target length."
        )
    rules += [
        "Make the text engaging and educational, suitable as reading material for language learners.",
        "If a list of words the learner already knows is given, prefer those words where they fit naturally. "
        "Do not force words that do not fit.",
        "Never invent information that is not in the original article. Keep the main facts, context and details.",
        "Keep direct quotes from people exactly as they are written in the original.",
        "Structure the text with markdown headings. Write the body as plain text: "
        "no bold, italics, backticks or any other formatting to mark words.",
        "Do not add a vocabulary list, a key-words section or a glossary.",
        "Do not write a source section. It is added afterwards.",
    ]
    return "\n".join(f"- {rule}" for rule in rules)


# How far the word count may be from the target before it is worth a warning.
_LENGTH_TOLERANCE = 0.25

# The marks must hug the text, as markdown requires: "Fill in: ___ and ___" is not bold.
# Bold may run over a line break, but not over a blank line.
_BOLD = re.compile(
    r"\*\*(?=\S)(?:[^*\n]|\n(?!\n))+?(?<=\S)\*\*"
    r"|(?<![_\w])__(?=[^\s_])(?:[^_\n]|\n(?!\n))+?(?<=[^\s_])__(?![_\w])"
)
# A bullet ("* item") has a space after the star, so it does not match.
_ITALIC = re.compile(
    r"(?<![*\w])\*(?=[^*\s])[^*\n]*?(?<=[^*\s])\*(?!\*)"
    r"|(?<![_\w])_(?=[^_\s])[^_\n]*?(?<=[^_\s])_(?![_\w])"
)
_VOCAB_NAMES = (
    r"vocabulary|vocab|word list|words|glossary|wortschatz|vokabeln|wortliste|wörter|"
    r"vocabulaire|lexique|vocabulario|glosario|단어 목록|단어|어휘"
)
_VOCAB_MODIFIERS = r"key|new|important|useful|wichtige|neue|주요|핵심"
# A line that is nothing but the name of a word list, as a heading or a label ("## Key Vocabulary",
# "Wortschatz:"). A title that only contains such a word ("# The Vocabulary of Climate Change") is fine.
# Known limit: a word list without such a title ("- Hund: dog") is not caught.
_VOCAB_SECTION = re.compile(
    rf"^[ \t]*(?:#{{1,6}}[ \t]*)?(?:(?:{_VOCAB_MODIFIERS})[ \t]+)?(?:{_VOCAB_NAMES})[ \t]*:?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class CheckResult:
    """Result of checking an article. ok is False when anything in issues blocks it."""

    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def check_article(text: str, length: str | None = None, source: SourceInfo | None = None) -> CheckResult:
    """Check an article against the rules. Issue texts are written for an LLM to read and fix."""
    issues = _format_issues(text)
    if _VOCAB_SECTION.search(text):
        issues.append("The text has a vocabulary list or glossary section. Remove it.")
    if not _has_source(source):
        issues.append("The source is missing. Give the name of the publication or the URL of the original article.")
    return CheckResult(issues=issues, warnings=_length_warnings(text, length))


def _format_issues(text: str) -> list[str]:
    issues = []
    if _BOLD.search(text):
        issues.append("The text uses bold (**word**). Remove all bold formatting.")
    if _ITALIC.search(_BOLD.sub("", text)):
        issues.append("The text uses italics (*word*). Remove all italic formatting.")
    if "`" in text:
        issues.append("The text uses backticks (`word`). Remove all backticks.")
    return issues


def _has_source(source: SourceInfo | None) -> bool:
    return source is not None and bool(source.source_name.strip() or (source.source_url or "").strip())


def _length_warnings(text: str, length: str | None) -> list[str]:
    if not (length and length.isdigit()):
        return []
    target, words = int(length), len(text.split())
    if abs(words - target) <= target * _LENGTH_TOLERANCE:
        return []
    return [f"The text has {words} words; the target is about {target}."]
