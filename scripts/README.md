  파일: test_cases.py
  역할: 테스트 데이터 모음. 독일어(189건)/영어 테스트 케이스 (문장, 단어, 기대 lemma, 기대 related_words, 카테고리) 형식
  ────────────────────────────────────────
  파일: test_reduced_prompt.py
  역할: 1단계 reduced 프롬프트 정확도 테스트. lemma + related_words 추출 성능 측정
  ────────────────────────────────────────
  파일: test_definition_selection.py
  역할: [deprecated — benchmark_entry_selection.py로 대체됨]
    2단계 LLM definition 선택 prompt 비교. entries[0]의 senses만 대상으로 tag 기반 vs LLM 기반 정확도 비교.
    이슈 #92에서 전체 entries를 대상으로 하는 benchmark_entry_selection.py로 발전됨
  ────────────────────────────────────────
  파일: benchmark_entry_selection.py
  역할: 2단계 entry+sense+subsense 선택 벤치마크 (이슈 #92).
    Free Dictionary API의 전체 entries를 X.Y.Z(entry.sense.subsense) 포맷으로 LLM에게 제시하고,
    별도 grading agent(Claude Sonnet)가 선택 정확도를 채점. 96.2% 정확도 달성.
    Usage: PYTHONPATH=src uv run python scripts/benchmark_entry_selection.py
           PYTHONPATH=src uv run python scripts/benchmark_entry_selection.py --language German --limit 10
  ────────────────────────────────────────
  파일: test_dictionary_agent.py
  역할: Agent 방식 벤치마크. LLM이 tool use로 사전 API를 직접 호출하는 접근법 테스트. 여러 모델(gemini/gpt/haiku) 비교, 로그 파일 생성. 이슈 #81 코멘트의
    벤치마크 결과가 이 스크립트에서 나온 것
  ────────────────────────────────────────
  파일: test_hybrid_dictionary.py
  역할: 하이브리드 조회 E2E 테스트. MongoDB에서 실제 vocabulary 데이터를 가져와서 reduced LLM → API → full fallback 전체 파이프라인 동작 확인
  ────────────────────────────────────────
  파일: test_token_usage.py
  역할: 토큰 사용량 추적 테스트. call_llm_with_tracking() 유틸이 prompt/completion 토큰을 제대로 기록하는지 확인하는 간단한 스크립트
  ────────────────────────────────────────
  요약하면 dictionary 서비스의 각 단계를 독립적으로 검증하는 구조:
  - test_reduced_prompt → 1단계 (lemma 추출)
  - benchmark_entry_selection → 2단계 (entry+sense+subsense 선택, X.Y.Z 포맷)
  - test_hybrid_dictionary → 전체 파이프라인
  - test_dictionary_agent → 대안 아키텍처 비교
  - test_token_usage → 인프라 유틸 검증
