# Weekly Deploy Reporter - 프로젝트 구조 가이드

## 📁 전체 프로젝트 구조

```
weekly-deploy-reporter/
├── 📄 핵심 스크립트 파일들
│   ├── create_weekly_report.py      # 메인 스크립트 (최적화됨)
│   ├── getJiraDeployedBy.js        # Jira 배포자 정보 추출
│   ├── check_jira_fields.py        # JIRA 필드 정보 조회
│   ├── create_daily_log.py         # 일일 로그 생성
│   └── log_manager.py              # 로그 관리 유틸리티
│
├── 🧪 테스트 파일들
│   ├── test_pagination_options.py  # 페이지네이션 테스트
│   ├── test_emoji_notification.py  # 이모지 알림 테스트
│   ├── test_it_5332_links.py      # IT-5332 연결 관계 테스트
│   ├── debug_deploy_issues.py      # 배포 이슈 디버깅
│   └── tests/                      # 테스트 디렉토리
│       └── test_create_weekly_report.py
│
├── 📊 데이터 파일들
│   ├── deploy_ticket_links.json    # 배포 티켓 링크 데이터
│   ├── deploy_ticket_links.csv     # 배포 티켓 링크 CSV
│   ├── weekly_issues.json          # 이슈 현황 데이터
│   ├── weekly_issues_snapshot.json # 이슈 스냅샷
│   ├── notified_deploy_keys.json   # 알림 전송된 배포 키
│   └── notified_changes.json       # 알림 전송된 변경사항
│
├── 📝 문서 파일들
│   ├── README.md                   # 프로젝트 메인 문서
│   ├── DAILY_LOG_SETUP.md         # 일일 로그 시스템 가이드
│   ├── create_weekly_report_process_diagram.md # 프로세스 다이어그램
│   ├── code_cleanup_summary.md    # 코드 정리 보고서
│   ├── unused_functions_analysis.md # 사용하지 않는 함수 분석
│   ├── PROJECT_STRUCTURE.md       # 이 파일 (프로젝트 구조 가이드)
│   ├── DEVELOPMENT_GUIDE.md       # 개발 가이드
│   └── DEPLOYMENT_GUIDE.md        # 배포 가이드
│
├── ⚙️ 설정 파일들
│   ├── crontab_new_setting.txt    # 새로운 crontab 설정
│   ├── crontab_daily_logs.txt     # 일일 로그용 crontab 설정
│   ├── cron_example.txt           # crontab 예시
│   ├── temp_crontab.txt           # 임시 crontab 설정
│   ├── temp_crontab_config.txt    # 임시 crontab 설정
│   ├── package.json               # Node.js 의존성
│   ├── yarn.lock                  # Yarn 락 파일
│   ├── .env                       # 환경 변수 (예시)
│   ├── .gitignore                 # Git 무시 파일
│   ├── .cursorignore              # Cursor 무시 파일
│   ├── .cursorindexingignore      # Cursor 인덱싱 무시 파일
│   ├── commitlint.config.js       # 커밋 린트 설정
│   └── .cz-config.js              # 커밋젠 설정
│
├── 📁 로그 파일들
│   ├── logs/runtime/              # 일일 로그 파일 디렉토리
│   │   └── cron_YYMMDD.log        # 날짜별 로그 파일
│   ├── cron.log                   # 기존 실행 로그 (레거시)
│   ├── cron_test.log              # 테스트 실행 로그
│   └── security_events.log        # 보안 이벤트 로그
│
├── 🤖 TaskMaster AI 통합
│   ├── .taskmaster/               # TaskMaster 설정 디렉토리
│   │   ├── tasks/                 # 작업 파일 디렉토리
│   │   │   ├── tasks.json         # 메인 작업 데이터베이스
│   │   │   ├── task-1.md         # 개별 작업 파일들
│   │   │   └── task-2.md
│   │   ├── docs/                  # 문서 디렉토리
│   │   │   └── prd.txt           # 제품 요구사항
│   │   ├── reports/               # 분석 리포트 디렉토리
│   │   │   └── task-complexity-report.json
│   │   ├── templates/             # 템플릿 파일들
│   │   │   └── example_prd.txt   # 예시 PRD 템플릿
│   │   ├── config.json            # AI 모델 및 설정
│   │   └── state.json             # 상태 파일
│   ├── CLAUDE.md                  # Claude Code 통합 가이드
│   ├── AGENTS.md                  # TaskMaster AI 가이드
│   └── .mcp.json                  # MCP 서버 설정
│
├── 🔧 개발 도구 설정
│   ├── .claude/                   # Claude 설정 디렉토리
│   │   ├── settings.json          # Claude Code 설정
│   │   └── commands/              # 커스텀 슬래시 명령어
│   ├── .github/                   # GitHub 설정
│   ├── .husky/                    # Git hooks
│   ├── .clinerules/               # Cline 규칙
│   ├── .cursor/                   # Cursor 설정
│   ├── .pytest_cache/             # pytest 캐시
│   ├── .specstory/                # SpecStory 설정
│   └── .roomodes                  # Roomodes 설정
│
├── 📦 의존성 디렉토리들
│   ├── node_modules/              # Node.js 의존성
│   ├── venv/                      # Python 가상환경
│   └── __pycache__/               # Python 캐시
│
└── 📁 스냅샷 파일들
    ├── weekly_issues_snapshot_current_week.json  # 이번 주 스냅샷
    ├── weekly_issues_snapshot_last_week.json     # 지난 주 스냅샷
    └── weekly_issues_snapshot_next_week.json     # 다음 주 스냅샷
```

## 📄 핵심 스크립트 파일 상세 설명

### 1. create_weekly_report.py
**역할**: 메인 스크립트 (최적화됨)
**크기**: ~900라인 (44% 감소)
**주요 기능**:
- Jira 이슈 조회 및 필터링
- Confluence 페이지 생성/업데이트
- Slack 알림 전송
- 변경사항 감지 및 스냅샷 관리
- 연결된 IT 티켓 조회

**최적화 결과**:
- 38개 함수 → 23개 함수 (39% 감소)
- ~1,600라인 → ~900라인 (44% 감소)
- 15개 미사용 함수 완전 제거

### 2. getJiraDeployedBy.js
**역할**: Jira 배포자 정보 추출
**크기**: 133라인
**주요 기능**:
- Jira API를 통한 배포 관계 조회
- "is deployed by" 관계 추출
- Node.js 기반 실행

### 3. check_jira_fields.py
**역할**: JIRA 필드 정보 조회 스크립트
**크기**: 126라인
**주요 기능**:
- Jira 필드 권한 확인
- 커스텀 필드 정보 조회
- API 연결 테스트

### 4. create_daily_log.py
**역할**: 일일 로그 생성 스크립트
**크기**: 165라인
**주요 기능**:
- 매일 새로운 로그 파일 생성
- 실행 정보 자동 기록
- 환경 변수 기반 로그 레벨 제어

### 5. log_manager.py
**역할**: 로그 관리 유틸리티
**크기**: 191라인
**주요 기능**:
- 로그 요약 정보 확인
- 실시간 로그 모니터링
- 오래된 로그 파일 정리
- 로그 분석 및 통계

## 🧪 테스트 파일 상세 설명

### 1. test_pagination_options.py
**역할**: 페이지네이션 옵션 테스트
**크기**: 113라인
**테스트 내용**:
- 페이지네이션 사용/미사용 비교
- 대용량 데이터 처리 성능
- API 호출 횟수 측정

### 2. test_emoji_notification.py
**역할**: 이모지 알림 테스트
**크기**: 82라인
**테스트 내용**:
- Slack 이모지 알림 기능
- 알림 메시지 포맷 검증
- 다양한 상태별 이모지 테스트

### 3. test_it_5332_links.py
**역할**: IT-5332 연결 관계 테스트
**크기**: 110라인
**테스트 내용**:
- 특정 티켓의 연결 관계 확인
- "is deployed by" 관계 검증
- 연결된 IT 티켓 조회 기능

### 4. debug_deploy_issues.py
**역할**: 배포 이슈 디버깅 스크립트
**크기**: 243라인
**주요 기능**:
- 배포 관련 이슈 진단
- API 응답 분석
- 오류 원인 추적

## 📊 데이터 파일 상세 설명

### 1. deploy_ticket_links.json
**역할**: 배포 티켓 링크 데이터
**크기**: 110라인
**내용**: 배포 티켓과 IT 티켓 간의 연결 관계 데이터

### 2. deploy_ticket_links.csv
**역할**: 배포 티켓 링크 CSV
**크기**: 29라인
**내용**: 배포 티켓 연결 관계를 CSV 형식으로 저장

### 3. weekly_issues.json
**역할**: 이슈 현황 데이터
**크기**: 13라인
**내용**: 현재 주간 이슈 현황 정보

### 4. weekly_issues_snapshot.json
**역할**: 이슈 스냅샷
**크기**: 65라인
**내용**: 이전 상태와 비교하기 위한 이슈 스냅샷

### 5. notified_deploy_keys.json
**역할**: 알림 전송된 배포 키
**크기**: 1라인
**내용**: 이미 알림을 보낸 배포 티켓 키 목록

### 6. notified_changes.json
**역할**: 알림 전송된 변경사항
**크기**: 1라인
**내용**: 이미 알림을 보낸 변경사항 해시 목록

## 📝 문서 파일 상세 설명

### 1. README.md
**역할**: 프로젝트 메인 문서
**크기**: 473라인
**내용**:
- 프로젝트 개요 및 주요 기능
- 설치 및 설정 가이드
- 사용법 및 예제
- 문제 해결 가이드

### 2. DAILY_LOG_SETUP.md
**역할**: 일일 로그 시스템 가이드
**크기**: 253라인
**내용**:
- 로그 시스템 설치 방법
- 로그 관리 유틸리티 사용법
- 모니터링 및 분석 도구

### 3. create_weekly_report_process_diagram.md
**역할**: 프로세스 다이어그램
**크기**: 293라인
**내용**:
- 전체 프로세스 플로우
- 각 단계별 다이어그램
- 함수별 역할 설명

### 4. code_cleanup_summary.md
**역할**: 코드 정리 보고서
**크기**: 113라인
**내용**:
- 최적화 전후 비교
- 제거된 함수 목록
- 성능 개선 결과

### 5. unused_functions_analysis.md
**역할**: 사용하지 않는 함수 분석
**크기**: 83라인
**내용**:
- 미사용 함수 분석 결과
- 제거 가능한 함수 목록
- 정리 통계

## ⚙️ 설정 파일 상세 설명

### 1. crontab_new_setting.txt
**역할**: 새로운 crontab 설정
**크기**: 13라인
**내용**: 일일 로그 시스템을 사용하는 새로운 crontab 설정

### 2. crontab_daily_logs.txt
**역할**: 일일 로그용 crontab 설정
**크기**: 25라인
**내용**: 로그 관리 시스템이 포함된 crontab 설정

### 3. package.json
**역할**: Node.js 의존성
**크기**: 36라인
**내용**: Node.js 패키지 의존성 및 스크립트 정의

### 4. .env
**역할**: 환경 변수 (예시)
**내용**:
- Atlassian API 설정
- Slack Webhook 설정
- 로그 레벨 설정
- 프로젝트 설정

## 📁 로그 파일 상세 설명

### 1. logs/runtime/
**역할**: 일일 로그 파일 디렉토리
**파일 형식**: cron_YYMMDD.log
**예시**: cron_250124.log (2025년 1월 24일)

### 2. cron.log
**역할**: 기존 실행 로그 (레거시)
**크기**: 3543라인
**내용**: 기존 crontab 실행 로그

### 3. cron_test.log
**역할**: 테스트 실행 로그
**내용**: 테스트 실행 시 생성되는 로그

### 4. security_events.log
**역할**: 보안 이벤트 로그
**크기**: 86라인
**내용**: 보안 관련 이벤트 기록

## 🤖 TaskMaster AI 통합 상세 설명

### 1. .taskmaster/tasks/tasks.json
**역할**: 메인 작업 데이터베이스
**크기**: 522라인
**내용**: 모든 작업 정의 및 상태 정보

### 2. .taskmaster/config.json
**역할**: AI 모델 및 설정
**크기**: 38라인
**내용**:
- AI 모델 설정 (Claude, Perplexity 등)
- 글로벌 설정 (로그 레벨, 기본값 등)
- 프로젝트 설정

### 3. .taskmaster/docs/
**역할**: 문서 디렉토리
**내용**: PRD 문서 및 기타 문서

### 4. .taskmaster/reports/
**역할**: 분석 리포트 디렉토리
**내용**: 작업 복잡도 분석 리포트 등

### 5. .taskmaster/templates/
**역할**: 템플릿 파일들
**내용**: PRD 템플릿 등

## 🔧 개발 도구 설정 상세 설명

### 1. .claude/
**역할**: Claude 설정 디렉토리
**내용**:
- settings.json: Claude Code 설정
- commands/: 커스텀 슬래시 명령어

### 2. .github/
**역할**: GitHub 설정
**내용**: GitHub Actions, Pull Request 템플릿 등

### 3. .husky/
**역할**: Git hooks
**내용**: 커밋 전 검사, 린트 검사 등

### 4. .cursor/
**역할**: Cursor 설정
**내용**: Cursor IDE 설정

## 📦 의존성 디렉토리 상세 설명

### 1. node_modules/
**역할**: Node.js 의존성
**내용**: npm/yarn으로 설치된 Node.js 패키지들

### 2. venv/
**역할**: Python 가상환경
**내용**: Python 패키지 및 가상환경 설정

### 3. __pycache__/
**역할**: Python 캐시
**내용**: Python 바이트코드 캐시 파일들

## 📁 스냅샷 파일 상세 설명

### 1. weekly_issues_snapshot_current_week.json
**역할**: 이번 주 스냅샷
**크기**: 79라인
**내용**: 현재 주간 이슈 스냅샷

### 2. weekly_issues_snapshot_last_week.json
**역할**: 지난 주 스냅샷
**크기**: 72라인
**내용**: 지난 주간 이슈 스냅샷

### 3. weekly_issues_snapshot_next_week.json
**역할**: 다음 주 스냅샷
**크기**: 44라인
**내용**: 다음 주간 이슈 스냅샷

## 🎯 파일 관리 가이드

### 중요 파일들 (백업 필수)
- `.env`: 환경 변수 (민감 정보 포함)
- `.taskmaster/tasks/tasks.json`: 작업 데이터베이스
- `.taskmaster/config.json`: AI 모델 설정
- `logs/runtime/`: 로그 파일들

### 정기 정리 대상
- `logs/runtime/`: 30일 이상 된 로그 파일
- `__pycache__/`: Python 캐시 파일
- `node_modules/`: Node.js 의존성 (재설치 가능)

### 버전 관리 제외
- `.env`: 민감 정보 포함
- `logs/`: 로그 파일들
- `__pycache__/`: 캐시 파일들
- `node_modules/`: 의존성 파일들

## 📊 프로젝트 통계

### 파일 수 분포
- **핵심 스크립트**: 5개
- **테스트 파일**: 5개
- **데이터 파일**: 6개
- **문서 파일**: 7개
- **설정 파일**: 12개
- **로그 파일**: 4개
- **TaskMaster 파일**: 8개
- **개발 도구 설정**: 6개
- **의존성 디렉토리**: 3개
- **스냅샷 파일**: 3개

### 총 파일 수: 59개

### 코드 라인 수
- **Python**: ~1,500라인
- **JavaScript**: ~150라인
- **Markdown**: ~2,000라인
- **JSON**: ~1,000라인
- **설정 파일**: ~500라인

### 총 코드 라인 수: ~5,150라인

---

**마지막 업데이트**: 2025년 1월
**버전**: 프로젝트 구조 가이드 v1.0
