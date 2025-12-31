# Vercel Root Directory 설정 방법

## 방법 1: 프로젝트 재설정 (가장 확실함)

1. Vercel 대시보드에서 현재 프로젝트 삭제:
   - 프로젝트 이름 클릭
   - 맨 아래로 스크롤
   - "Delete Project" 클릭

2. 새로 Import:
   - "Add New..." → "Project" 클릭
   - GitHub 저장소 선택
   - **"Configure Project" 화면에서:**
     - Root Directory 옆 "Edit" 클릭
     - `web` 입력
     - "Deploy" 클릭

## 방법 2: Settings에서 찾기

1. 프로젝트 대시보드에서:
   - 상단 메뉴에서 "Settings" 클릭
   - 왼쪽 사이드바에서 "General" 클릭
   - "Root Directory" 섹션 찾기
   - "Edit" 클릭 → `web` 입력 → Save

## 방법 3: vercel.json 파일 사용 (자동 설정)

프로젝트 루트에 `vercel.json` 파일 생성:

```json
{
  "buildCommand": "cd web && npm run build",
  "devCommand": "cd web && npm run dev",
  "installCommand": "cd web && npm install",
  "outputDirectory": "web/.next"
}
```

하지만 이 방법은 복잡할 수 있으므로 방법 1을 추천합니다.

