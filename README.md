# Weekly Deploy Reporter

## 프로젝트 개요

**Weekly Deploy Reporter**는 JIRA 이슈와 배포 관련 정보를 자동으로 수집하여 주간 리포트를 생성하고, 배포 이슈를 효율적으로 관리할 수 있도록 돕는 자동화 도구입니다. Python 및 JavaScript 기반이며, Confluence 페이지 생성, 크론탭 자동화, Taskmaster 기반 워크플로우, 커밋 규칙 자동화 등 다양한 개발 생산성 기능을 제공합니다.

---

## 폴더/파일 구조

```
weekly-deploy-reporter/
├── .clinerules/           # 개발 규칙, 워크플로우, 자기개선, taskmaster 문서
├── .github/instructions/  # 개발/VSCode/Taskmaster 관련 가이드 문서
├── .husky/                # Git hook 자동화 (pre-commit, commit-msg)
├── .taskmaster/           # Taskmaster 설정, 업무 템플릿, 리포트, 상태, 문서
│   ├── docs/
│   ├── reports/
│   ├── tasks/
│   ├── templates/
│   ├── config.json
│   ├── state.json
├── tests/                 # 테스트 코드 및 캐시
├── __pycache__/           # Python 캐시
├── .env.example           # 환경 변수 예시
├── .gitignore             # Git 무시 파일
├── .cz-config.js          # 커밋 프롬프트 커스터마이즈
├── commitlint.config.js   # 커밋 메시지 규칙
├── package.json           # Node.js 프로젝트 설정
├── yarn.lock              # Yarn lock 파일
├── README.md              # 프로젝트 설명서
├── AGENTS.md, CLAUDE.md   # 에이전트/AI 관련 문서
├── create_weekly_report.py# 주간 리포트 생성 메인 스크립트
├── getJiraDeployedBy.js   # JIRA 배포자 정보 추출 스크립트
├── 기타 데이터/설정 파일  # (deploy_ticket_links.*, notified_deploy_keys.json 등)
```

---

## 주요 기능
- JIRA 이슈 및 배포 이력 자동 수집/리포트 생성
- 배포 티켓 링크 관리 (CSV/JSON)
- Confluence 페이지 콘텐츠 생성 지원
- Taskmaster 기반 업무 자동화 및 체크리스트 관리
- 크론탭 예시 및 자동화
- 커밋 메시지 규칙(Conventional Commit) 및 린트 자동화
- 테스트 코드 및 품질 관리

---

## 설치 및 환경설정
1. 저장소 클론
```bash
git clone https://github.com/Opti-kjh/weekly-deploy-reporter.git
cd weekly-deploy-reporter
```
2. Python 가상환경(선택)
```bash
python3 -m venv venv
source venv/bin/activate
```
3. Node.js 의존성 설치
```bash
yarn install
```
4. 환경 변수 설정
- `.env.example` 파일을 참고하여 `.env` 파일 생성 및 환경 변수 입력

---

## 스크립트 및 자동화
- **주간 리포트 생성:**
  ```bash
  python create_weekly_report.py
  ```
- **배포자 정보 추출:**
  ```bash
  yarn deploy-report
  ```
- **커밋 메시지 작성(규칙 자동화):**
  ```bash
  yarn cz
  ```
- **테스트 실행:**
  ```bash
  python -m unittest tests/test_create_weekly_report.py
  ```

---

## 개발/품질 관리 자동화
- **husky**: pre-commit(코드 린트/포맷), commit-msg(커밋 메시지 규칙) 자동화
- **lint-staged**: 커밋 대상 js/json 파일에 prettier, eslint 자동 적용
- **commitizen + cz-customizable**: 커밋 메시지 프롬프트 및 대소문자 자유 입력
- **commitlint**: Conventional Commit 규칙 강제

---

## Taskmaster/워크플로우/규칙 문서
- `.clinerules/` : 개발 규칙, 자기개선, 워크플로우, taskmaster 문서
- `.github/instructions/` : 개발/VSCode/Taskmaster 가이드
- `.taskmaster/` : 업무 템플릿, 리포트, 상태, config 등 자동화 기반

---

## 기타 참고사항
- **배포/업무 데이터**: deploy_ticket_links.csv/json, notified_deploy_keys.json, weekly_issues.json 등
- **테스트**: tests/test_create_weekly_report.py 등
- **라이선스**: MIT

---
문의사항은 GitHub 이슈로 등록해 주세요.
