"""하이브리드 사전 조회 테스트 스크립트.

실제 vocabulary 데이터를 사용하여 LLM+API 하이브리드 조회 결과를 확인합니다.
pytest에서 실행되지 않음 (수동 실행 전용).

Usage:
    PYTHONPATH=server uv run python scripts/test_hybrid_dictionary.py [--count 10]
"""

import asyncio
import argparse
import random
import time
import json
from dotenv import load_dotenv

load_dotenv()

from adapter.mongodb.connection import get_mongodb_client
from adapter.external.litellm import LiteLLMAdapter
from adapter.external.free_dictionary import FreeDictionaryAdapter

_llm = LiteLLMAdapter()
_dict_adapter = FreeDictionaryAdapter()
from services.lemma_extraction import _build_reduced_prompt as build_reduced_word_definition_prompt
from json_repair import repair_json
from services.dictionary_service import _build_full_prompt as build_word_definition_prompt


def get_random_vocabularies(count: int = 10) -> list[dict]:
    """MongoDB에서 랜덤하게 vocabulary 데이터 가져오기."""
    client = get_mongodb_client()
    if not client:
        print("MongoDB 연결 실패")
        return []

    db = client['opad']

    # sentence가 있는 데이터만 가져오기
    all_vocabs = list(db.vocabularies.find({
        'sentence': {'$exists': True, '$ne': None, '$ne': ''},
        'word': {'$exists': True, '$ne': None, '$ne': ''}
    }))

    if len(all_vocabs) < count:
        print(f"Warning: {len(all_vocabs)}개만 있음 (요청: {count}개)")
        return all_vocabs

    return random.sample(all_vocabs, count)


async def test_hybrid_lookup(vocab: dict) -> dict:
    """하이브리드 조회 테스트 (LLM + API)."""
    word = vocab.get('word')
    sentence = vocab.get('sentence')
    language = vocab.get('language', 'German')

    result = {
        'word': word,
        'language': language,
        'sentence': sentence[:60] + '...' if len(sentence) > 60 else sentence,
    }

    # Step 1: Reduced LLM call
    prompt = build_reduced_word_definition_prompt(language, sentence, word)

    llm_start = time.time()
    try:
        content, stats = await _llm.call(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-4.1",
            max_tokens=500,
            temperature=0
        )
        llm_time = time.time() - llm_start
        llm_result = repair_json(content, return_objects=True)

        result['llm_time'] = llm_time
        result['llm_tokens'] = {
            'prompt': stats.prompt_tokens,
            'completion': stats.completion_tokens
        }
        result['llm_result'] = llm_result

        lemma = llm_result.get('lemma', word) if llm_result else word
    except Exception as e:
        result['llm_error'] = str(e)
        result['llm_time'] = time.time() - llm_start
        lemma = word

    # Step 2: Free Dictionary API call
    api_start = time.time()
    try:
        entries = await _dict_adapter.fetch(lemma, language)
        api_time = time.time() - api_start

        result['api_time'] = api_time
        if entries:
            entry = entries[0]
            senses = entry.get('senses', [])
            result['api_result'] = {
                'definition': senses[0].get('definition', '') if senses else '',
                'pos': entry.get('partOfSpeech'),
                'gender': None,
                'phonetics': None,
                'forms': None,
            }
        else:
            result['api_result'] = None
    except Exception as e:
        result['api_error'] = str(e)
        result['api_time'] = time.time() - api_start

    # Total time
    result['total_time'] = result.get('llm_time', 0) + result.get('api_time', 0)

    # Merged result
    if result.get('llm_result') and result.get('api_result'):
        result['source'] = 'hybrid'
        result['merged'] = {
            'lemma': result['llm_result'].get('lemma'),
            'definition': result['api_result'].get('definition'),
            'related_words': result['llm_result'].get('related_words'),
            'pos': result['api_result'].get('pos'),
            'gender': result['api_result'].get('gender'),
            'phonetics': result['api_result'].get('phonetics'),
            'level': result['llm_result'].get('level'),
            'forms': result['api_result'].get('forms'),
        }
    elif result.get('llm_result'):
        result['source'] = 'llm_only (API failed)'
    else:
        result['source'] = 'failed'

    return result


async def test_full_llm_lookup(vocab: dict) -> dict:
    """기존 Full LLM 조회 테스트 (비교용)."""
    word = vocab.get('word')
    sentence = vocab.get('sentence')
    language = vocab.get('language', 'German')

    prompt = build_word_definition_prompt(language, sentence, word)

    start = time.time()
    try:
        content, stats = await _llm.call(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-4.1-mini",
            max_tokens=2000,
            temperature=0
        )
        elapsed = time.time() - start
        result = repair_json(content, return_objects=True)

        return {
            'time': elapsed,
            'tokens': {
                'prompt': stats.prompt_tokens,
                'completion': stats.completion_tokens
            },
            'result': result
        }
    except Exception as e:
        return {
            'time': time.time() - start,
            'error': str(e)
        }


async def run_comparison_test(vocabs: list[dict]):
    """하이브리드 vs Full LLM 비교 테스트."""

    print(f"\n{'='*80}")
    print(f"하이브리드 사전 조회 테스트 (LLM + Free Dictionary API)")
    print(f"테스트 수: {len(vocabs)}개")
    print(f"{'='*80}\n")

    hybrid_results = []
    full_llm_results = []

    for i, vocab in enumerate(vocabs):
        word = vocab.get('word')
        language = vocab.get('language', 'German')

        print(f"\n{'─'*80}")
        print(f"[{i+1}/{len(vocabs)}] '{word}' ({language})")
        print(f"문장: {vocab.get('sentence', '')[:70]}...")
        print(f"{'─'*80}")

        # Hybrid test
        print("\n📦 [하이브리드] LLM + API:")
        hybrid = await test_hybrid_lookup(vocab)
        hybrid_results.append(hybrid)

        print(f"  LLM 시간: {hybrid.get('llm_time', 0):.2f}s | 토큰: {hybrid.get('llm_tokens', {})}")
        print(f"  API 시간: {hybrid.get('api_time', 0):.2f}s | 결과: {'✅' if hybrid.get('api_result') else '❌'}")
        print(f"  총 시간: {hybrid.get('total_time', 0):.2f}s | 소스: {hybrid.get('source')}")

        if hybrid.get('merged'):
            m = hybrid['merged']
            print(f"\n  📝 병합 결과:")
            print(f"     lemma: {m.get('lemma')}")
            print(f"     definition: {(m.get('definition') or '')[:60]}...")
            print(f"     pos: {m.get('pos')}")
            print(f"     gender: {m.get('gender')}")
            print(f"     phonetics: {m.get('phonetics')}")
            print(f"     level: {m.get('level')}")
            print(f"     related_words: {m.get('related_words')}")
            if m.get('forms'):
                print(f"     forms: {list(m.get('forms', {}).keys())}")

        # Full LLM test (비교용)
        print("\n📦 [Full LLM] 기존 방식:")
        full = await test_full_llm_lookup(vocab)
        full_llm_results.append(full)

        print(f"  시간: {full.get('time', 0):.2f}s | 토큰: {full.get('tokens', {})}")
        if full.get('result'):
            r = full['result']
            print(f"     lemma: {r.get('lemma')}")
            print(f"     definition: {(r.get('definition') or '')[:60]}...")
            print(f"     pos: {r.get('pos')}")
            print(f"     gender: {r.get('gender')}")
            print(f"     level: {r.get('level')}")
            print(f"     related_words: {r.get('related_words')}")

        # 비교
        time_diff = full.get('time', 0) - hybrid.get('total_time', 0)
        token_diff = full.get('tokens', {}).get('completion', 0) - hybrid.get('llm_tokens', {}).get('completion', 0)
        print(f"\n  ⚡ 차이: 시간 {time_diff:+.2f}s | 토큰 {token_diff:+d}")

    # 요약 통계
    print(f"\n\n{'='*80}")
    print("📊 요약 통계")
    print(f"{'='*80}")

    # Hybrid stats
    hybrid_times = [r.get('total_time', 0) for r in hybrid_results]
    hybrid_llm_tokens = [r.get('llm_tokens', {}).get('completion', 0) for r in hybrid_results]
    hybrid_success = len([r for r in hybrid_results if r.get('source') == 'hybrid'])

    print(f"\n[하이브리드 LLM+API]")
    print(f"  평균 시간: {sum(hybrid_times)/len(hybrid_times):.2f}s")
    print(f"  평균 LLM 토큰: {sum(hybrid_llm_tokens)/len(hybrid_llm_tokens):.0f}")
    print(f"  API 성공률: {hybrid_success}/{len(hybrid_results)} ({100*hybrid_success/len(hybrid_results):.0f}%)")

    # Full LLM stats
    full_times = [r.get('time', 0) for r in full_llm_results]
    full_tokens = [r.get('tokens', {}).get('completion', 0) for r in full_llm_results]

    print(f"\n[Full LLM 기존 방식]")
    print(f"  평균 시간: {sum(full_times)/len(full_times):.2f}s")
    print(f"  평균 토큰: {sum(full_tokens)/len(full_tokens):.0f}")

    # 절감량
    time_saved = sum(full_times)/len(full_times) - sum(hybrid_times)/len(hybrid_times)
    token_saved = sum(full_tokens)/len(full_tokens) - sum(hybrid_llm_tokens)/len(hybrid_llm_tokens)

    print(f"\n[절감량]")
    print(f"  시간: {time_saved:.2f}s ({100*time_saved/(sum(full_times)/len(full_times)):.0f}% 절감)")
    print(f"  토큰: {token_saved:.0f} ({100*token_saved/(sum(full_tokens)/len(full_tokens)):.0f}% 절감)")


def main():
    parser = argparse.ArgumentParser(description='하이브리드 사전 조회 테스트')
    parser.add_argument('--count', type=int, default=10, help='테스트할 단어 수 (기본: 10)')
    args = parser.parse_args()

    print("MongoDB에서 데이터 로딩...")
    vocabs = get_random_vocabularies(args.count)

    if not vocabs:
        print("테스트할 데이터가 없습니다.")
        return

    print(f"{len(vocabs)}개 데이터 로드 완료")

    asyncio.run(run_comparison_test(vocabs))


if __name__ == "__main__":
    main()
