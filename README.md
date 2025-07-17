# Weekly Deploy Reporter

## 1. 프로젝트 개요

**Weekly Deploy Reporter**는 JIRA에 기록된 배포 티켓 정보를 자동으로 수집하여 주간 배포 현황 리포트를 생성하는 자동화 도구입니다. 수동으로 진행하던 주간 배포 현황 취합 및 보고서 작성 업무를 자동화하여 개발 생산성을 높이는 것을 목표로 합니다.

주요 로직은 Python으로 작성되었으며, Confluence 페이지 콘텐츠 생성, 크론탭을 이용한 주기적 실행, Taskmaster 기반의 워크플로우 관리 등 다양한 기능을 포함하고 있습니다.

## 2. 주요 기능

- **JIRA 이슈 자동 수집**: 특정 기간의 배포 관련 티켓 정보를 JIRA API를 통해 자동으로 가져옵니다.
- **주간 리포트 생성**: 수집된 데이터를 분석하여 보고서 형식에 맞게 가공하고, `weekly_issues.json`과 같은 파일로 저장합니다.
- **Confluence 콘텐츠 생성**: `create_confluence_page_content` 스크립트를 통해 Confluence에 게시할 수 있는 콘텐츠를 생성합니다.
- **배포 티켓 관리**: 배포된 티켓 링크를 `CSV` 또는 `JSON` 형식으로 관리합니다.
- **개발 워크플로우 자동화**: `husky`, `commitlint`, `lint-staged` 등을 활용하여 커밋 메시지 규칙, 코드 스타일, 린팅을 자동화합니다.

## 3. 설치 및 환경설정

1.  **저장소 클론**
    ```bash
    git clone https://github.com/Opti-kjh/weekly-deploy-reporter.git
    cd weekly-deploy-reporter
    ```
2.  **Python 가상환경 설정 (권장)**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Node.js 의존성 설치**
    ```bash
    yarn install
    ```
4.  **환경 변수 설정**
    `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, JIRA URL, 계정 정보 등 필요한 환경 변수를 입력합니다.

## 4. 사용법

-   **주간 리포트 생성:**
    ```bash
    python create_weekly_report.py
    ```
-   **JIRA 배포자 정보 추출:**
    ```bash
    yarn deploy-report
    ```
-   **커밋 메시지 작성 (규칙 자동화):**
    ```bash
    yarn cz
    ```
-   **테스트 실행:**
    ```bash
    python -m unittest tests/test_create_weekly_report.py
    ```

## 5. 프로젝트 구조

```
weekly-deploy-reporter/
├── .clinerules/           # 개발 규칙, 워크플로우, 자기개선 문서
├── .github/instructions/  # 개발/VSCode/Taskmaster 관련 가이드
├── .husky/                # Git hook 자동화 (pre-commit, commit-msg)
├── .taskmaster/           # Taskmaster 설정, 업무 템플릿, 리포트
├── tests/                 # 테스트 코드
├── .env.example           # 환경 변수 예시 파일
├── create_weekly_report.py# 주간 리포트 생성 메인 스크립트
├── getJiraDeployedBy.js   # JIRA 배포자 정보 추출 스크립트
├── package.json           # Node.js 프로젝트 설정 파일
└── README.md              # 프로젝트 설명서
```

## 6. 개발/품질 관리 자동화

-   **husky**: `pre-commit`(코드 린트/포맷), `commit-msg`(커밋 메시지 규칙) 자동화를 지원합니다.
-   **lint-staged**: 커밋 대상 `js`/`json` 파일에 `prettier`, `eslint`를 자동으로 적용합니다.
-   **commitizen + cz-customizable**: 정해진 형식에 맞는 커밋 메시지를 쉽게 작성할 수 있도록 돕습니다.
-   **commitlint**: Conventional Commit 규칙을 준수하도록 강제합니다.

---