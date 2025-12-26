# OPAD Web Viewer

Next.js 기반 읽기 자료 뷰어입니다.

## 설치 완료 ✅

의존성이 이미 설치되어 있습니다.

## 개발 서버 실행

```bash
cd web
npm run dev
```

브라우저에서 http://localhost:3000 열기

## 사용법

1. `opad` 프로젝트에서 crewAI 실행하여 마크다운 생성:
   ```bash
   cd /Users/seung-gu/projects/opad
   crewai run
   # 또는
   uv run python src/opad/main.py
   ```

2. `output/adapted_reading_material.md` 파일이 생성됨

3. 웹 뷰어 실행:
   ```bash
   cd web
   npm run dev
   ```

4. 브라우저에서 http://localhost:3000 열기

## 단어 클릭 기능

마크다운에서 `[word:meaning]` 형식으로 작성하면 클릭 가능한 단어가 됩니다.

예: `This is a [sample:예시] text.`

단어를 클릭하면 바로 아래에 뜻이 표시됩니다.

## Vercel 배포

1. GitHub에 푸시
2. Vercel에서 프로젝트 import
3. **Root Directory를 `web`으로 설정** (중요!)
4. 자동 배포!
