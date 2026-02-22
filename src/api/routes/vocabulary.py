"""Vocabulary API routes for vocabulary CRUD operations.

Endpoints:
- POST /dictionary/vocabulary: Add a word to vocabulary list
- GET /dictionary/vocabularies: Get aggregated vocabulary list
- DELETE /dictionary/vocabularies/{id}: Delete a vocabulary word
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.security import get_current_user_required
from api.models import (
    UserResponse,
    VocabularyRequest,
    VocabularyResponse,
    VocabularyCountResponse,
)
from api.dependencies import get_vocab_repo
from domain.model.errors import PermissionDeniedError
from port.vocabulary_repository import VocabularyRepository
from domain.model.vocabulary import GrammaticalInfo, Vocabulary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dictionary", tags=["vocabulary"])


@router.post("/vocabulary", response_model=VocabularyResponse)
async def add_vocabulary(
    request: VocabularyRequest,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: VocabularyRepository = Depends(get_vocab_repo),
):
    """Add a word to vocabulary list."""
    vocab = Vocabulary.create(
        article_id=request.article_id,
        word=request.word,
        lemma=request.lemma,
        definition=request.definition,
        sentence=request.sentence,
        language=request.language,
        related_words=request.related_words,
        span_id=request.span_id,
        user_id=current_user.id,
        level=request.level,
        grammar=GrammaticalInfo(
            pos=request.pos,
            gender=request.gender,
            phonetics=request.phonetics,
            conjugations=request.conjugations,
            examples=request.examples,
        ),
    )

    vocab_id = repo.save(vocab)
    if not vocab_id:
        raise HTTPException(status_code=500, detail="Failed to save vocabulary")
    vocab = repo.get_by_id(vocab_id)

    logger.info("Vocabulary added", extra={
        "vocabulary_id": vocab.id,
        "article_id": request.article_id,
        "lemma": request.lemma,
        "user_id": current_user.id
    })

    return VocabularyResponse(
        id=vocab.id,
        article_id=vocab.article_id,
        word=vocab.word,
        lemma=vocab.lemma,
        definition=vocab.definition,
        sentence=vocab.sentence,
        language=vocab.language,
        created_at=vocab.created_at,
        related_words=vocab.related_words,
        span_id=vocab.span_id,
        user_id=vocab.user_id,
        pos=vocab.grammar.pos if vocab.grammar else None,
        gender=vocab.grammar.gender if vocab.grammar else None,
        phonetics=vocab.grammar.phonetics if vocab.grammar else None,
        conjugations=vocab.grammar.conjugations if vocab.grammar else None,
        level=vocab.level,
        examples=vocab.grammar.examples if vocab.grammar else None,
    )


@router.get("/vocabularies", response_model=list[VocabularyCountResponse])
async def get_vocabularies_list(
    language: str | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: VocabularyRepository = Depends(get_vocab_repo),
):
    """Get aggregated vocabulary list grouped by lemma with counts."""
    limit = min(limit, 1000)

    entries = repo.count_by_lemma(
        language=language, user_id=current_user.id, skip=skip, limit=limit,
    )

    result = []
    for entry in entries:
        v = entry.vocabulary
        g = v.grammar
        result.append(VocabularyCountResponse(
            id=v.id,
            article_id=v.article_id,
            word=v.word,
            lemma=v.lemma,
            definition=v.definition,
            sentence=v.sentence,
            language=v.language,
            related_words=v.related_words,
            span_id=v.span_id,
            created_at=v.created_at,
            user_id=v.user_id,
            count=entry.count,
            article_ids=entry.article_ids,
            pos=g.pos if g else None,
            gender=g.gender if g else None,
            phonetics=g.phonetics if g else None,
            conjugations=g.conjugations if g else None,
            level=v.level,
            examples=g.examples if g else None,
        ))

    logger.info("Grouped vocabularies retrieved", extra={
        "group_count": len(result),
        "language": language,
        "user_id": current_user.id
    })

    return result


@router.delete("/vocabularies/{vocabulary_id}")
async def delete_vocabulary_word(
    vocabulary_id: str,
    current_user: UserResponse = Depends(get_current_user_required),
    repo: VocabularyRepository = Depends(get_vocab_repo),
):
    """Delete a vocabulary word."""
    vocab = repo.get_by_id(vocabulary_id)
    if not vocab:
        raise HTTPException(status_code=404, detail="Vocabulary not found")

    try:
        vocab.check_ownership(current_user.id)
    except PermissionDeniedError:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this vocabulary")

    repo.delete(vocabulary_id)

    logger.info("Vocabulary deleted", extra={
        "vocabulary_id": vocabulary_id,
        "user_id": current_user.id
    })

    return {"message": "Vocabulary deleted successfully"}
