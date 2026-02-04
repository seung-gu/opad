"""LLM 응답 시간 벤치마크 스크립트.

실제 vocabulary 데이터를 사용하여 LLM 응답 시간을 측정합니다.
pytest에서 실행되지 않음 (수동 실행 전용).

Usage:
    PYTHONPATH=src uv run python scripts/benchmark_llm_response_time.py [--count 50] [--model openai/gpt-4.1-mini]
"""

import asyncio
import argparse
import random
import time
from dotenv import load_dotenv

load_dotenv()

from utils.mongodb import get_mongodb_client
from utils.llm import call_llm_with_tracking
from utils.prompts import build_word_definition_prompt


def get_random_vocabularies(count: int = 50) -> list[dict]:
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


async def test_llm_response_time(vocabs: list[dict], model: str = "openai/gpt-4.1-mini"):
    """LLM 응답 시간 테스트."""
    results = []

    print(f"\n{'='*60}")
    print(f"LLM 응답 시간 테스트")
    print(f"모델: {model}")
    print(f"테스트 수: {len(vocabs)}개")
    print(f"{'='*60}\n")

    for i, vocab in enumerate(vocabs):
        word = vocab.get('word')
        sentence = vocab.get('sentence')
        language = vocab.get('language', 'German')

        prompt = build_word_definition_prompt(language, sentence, word)

        try:
            start = time.time()
            content, stats = await call_llm_with_tracking(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                max_tokens=2000,
                temperature=0
            )
            elapsed = time.time() - start

            results.append({
                'word': word,
                'language': language,
                'time': elapsed,
                'prompt_tokens': stats.prompt_tokens,
                'completion_tokens': stats.completion_tokens,
                'success': True
            })

            print(f"{i+1:3}. {word:20} | {elapsed:5.2f}s | in:{stats.prompt_tokens:4} out:{stats.completion_tokens:4}")

        except Exception as e:
            results.append({
                'word': word,
                'language': language,
                'time': 0,
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'success': False,
                'error': str(e)
            })
            print(f"{i+1:3}. {word:20} | ERROR: {str(e)[:40]}")

    # 통계 출력
    successful = [r for r in results if r['success']]

    if successful:
        times = [r['time'] for r in successful]
        completions = [r['completion_tokens'] for r in successful]
        prompts = [r['prompt_tokens'] for r in successful]

        print(f"\n{'='*60}")
        print("통계 요약")
        print(f"{'='*60}")
        print(f"성공: {len(successful)}/{len(results)}")
        print(f"\n응답 시간:")
        print(f"  평균: {sum(times)/len(times):.2f}s")
        print(f"  최소: {min(times):.2f}s")
        print(f"  최대: {max(times):.2f}s")
        print(f"  중앙값: {sorted(times)[len(times)//2]:.2f}s")

        print(f"\nCompletion 토큰:")
        print(f"  평균: {sum(completions)/len(completions):.0f}")
        print(f"  최소: {min(completions)}")
        print(f"  최대: {max(completions)}")

        print(f"\nPrompt 토큰:")
        print(f"  평균: {sum(prompts)/len(prompts):.0f}")

        # 분포
        print(f"\n응답 시간 분포:")
        brackets = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, float('inf'))]
        for low, high in brackets:
            count = len([t for t in times if low <= t < high])
            bar = '█' * count
            label = f"{low}-{high}s" if high != float('inf') else f"{low}s+"
            print(f"  {label:6} | {bar} ({count})")

    return results


def main():
    parser = argparse.ArgumentParser(description='LLM 응답 시간 테스트')
    parser.add_argument('--count', type=int, default=50, help='테스트할 단어 수 (기본: 50)')
    parser.add_argument('--model', type=str, default='openai/gpt-4.1-mini', help='사용할 모델')
    args = parser.parse_args()

    print("MongoDB에서 데이터 로딩...")
    vocabs = get_random_vocabularies(args.count)

    if not vocabs:
        print("테스트할 데이터가 없습니다.")
        return

    print(f"{len(vocabs)}개 데이터 로드 완료")

    asyncio.run(test_llm_response_time(vocabs, args.model))


if __name__ == "__main__":
    main()
