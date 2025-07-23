# Weekly Deploy Reporter

주간 배포 일정을 자동으로 수집하고 Confluence 페이지에 리포트를 생성하는 Python 스크립트입니다.

## 📋 개요

이 프로젝트는 Jira에서 배포 예정 티켓들을 자동으로 수집하여 Confluence에 주간 배포 리포트를 생성하고, 변경사항이 있을 때 Slack으로 알림을 보내는 자동화 도구입니다.

## 🚀 주요 기능

- **Jira 연동**: 배포 예정 티켓 자동 수집
- **Confluence 연동**: 주간 배포 리포트 페이지 자동 생성/업데이트
- **Slack 알림**: 변경사항 발생 시 자동 알림
- **스냅샷 관리**: 이전 상태와 비교하여 변경사항 감지
- **다양한 실행 모드**: 생성, 업데이트, 현재/다음/지난 주 지원

## 📁 프로젝트 구조

```
weekly-deploy-reporter/
├── create_weekly_report.py      # 메인 스크립트
├── getJiraDeployedBy.js        # Jira 배포자 정보 추출
├── deploy_ticket_links.json    # 배포 티켓 링크 데이터
├── weekly_issues.json          # 이슈 현황 데이터
├── weekly_issues_snapshot.json # 이슈 스냅샷
├── notified_deploy_keys.json   # 알림 전송된 배포 키
├── notified_changes.json       # 알림 전송된 변경사항
├── cron.log                   # 실행 로그
├── tests/                     # 테스트 코드
│   └── test_create_weekly_report.py
├── reports/                   # 리포트 디렉토리
├── package.json               # Node.js 의존성
├── yarn.lock                  # Yarn 락 파일
└── README.md                  # 프로젝트 문서
```

## ⚙️ 설치 및 설정

### 1. 환경 요구사항

- Python 3.7+
- Node.js (getJiraDeployedBy.js 실행용)
- Jira 및 Confluence 접근 권한
- Slack Webhook URL

### 2. 의존성 설치

```bash
# Python 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Python 패키지 설치
pip install jira atlassian-python-api python-dotenv requests numpy

# Node.js 패키지 설치
npm install
# 또는
yarn install
```

### 3. 환경 변수 설정

`.env` 파일을 생성하고 다음 환경 변수들을 설정하세요:

```env
# Atlassian 설정
ATLASSIAN_URL=https://your-domain.atlassian.net
ATLASSIAN_USERNAME=your-email@domain.com
ATLASSIAN_API_TOKEN=your-api-token

# Slack 설정
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token

# 프로젝트 설정 (선택사항)
JIRA_PROJECT_KEY=IT
CONFLUENCE_SPACE_KEY=DEV
```

### 4. Jira API 토큰 생성

1. [Atlassian 계정 설정](https://id.atlassian.com/manage-profile/security/api-tokens)에서 API 토큰 생성
2. 생성된 토큰을 `ATLASSIAN_API_TOKEN` 환경 변수에 설정

## 🎯 사용법

### 기본 실행

```bash
# 이번 주 배포 예정 티켓으로 리포트 업데이트 (기본값)
python create_weekly_report.py

# 다음 주 배포 예정 티켓으로 리포트 생성
python create_weekly_report.py create

# 이번 주 배포 예정 티켓으로 리포트 생성/업데이트
python create_weekly_report.py current

# 지난 주 배포 예정 티켓으로 리포트 생성/업데이트
python create_weekly_report.py last

# 강제 업데이트 (변경사항 감지 무시)
python create_weekly_report.py --force-update
```

### 실행 모드 설명

| 모드 | 설명 | 대상 기간 |
|------|------|-----------|
| `create` | 다음 주 (차주) 배포 예정 티켓으로 리포트 생성 | 다음 주 |
| `current` | 이번 주 (현재 주) 배포 예정 티켓으로 리포트 생성/업데이트 | 이번 주 |
| `last` | 지난 주 배포 예정 티켓으로 리포트 생성/업데이트 | 지난 주 |
| `update` | 이번 주 배포 예정 티켓으로 리포트 업데이트 (기본값) | 이번 주 |

### Confluence 페이지 확인

```bash
# 특정 페이지 내용 확인
python create_weekly_report.py --check-page
```

## 🔧 설정 및 커스터마이징

### Jira 필드 설정

```python
# create_weekly_report.py 파일에서 수정
JIRA_DEPLOY_DATE_FIELD_ID = "customfield_10817"  # 예정된 시작 필드 ID
```

### Confluence 페이지 설정

```python
# 상위 페이지 제목 설정
CONFLUENCE_PARENT_PAGE_TITLE = "25-2H 주간 배포 리스트"

# 페이지 ID 설정 (필요시)
parent_page_id = "4596203549"
```

### Slack 알림 시간 설정

```python
# 알림 전송 시간 설정 (10시~11시)
notification_start_hour = 10
notification_end_hour = 11
```

## 📊 생성되는 리포트 구조

### 1. Jira 매크로 테이블
- 배포 예정 티켓 목록
- 키, 타입, 요약, 담당자, 상태, 생성일, 수정일, 예정된 시작 정보

### 2. 배포 예정 목록 HTML 테이블
- 부모 IT 티켓과 연결된 배포 티켓 관계 표시
- 상태별 색상 구분
- Jira 링크 포함

## 🔄 자동화 설정

### Cron 작업 설정

```bash
# crontab 편집
crontab -e

# 매주 월요일 오전 9시 실행
0 9 * * 1 cd /path/to/weekly-deploy-reporter && /path/to/venv/bin/python create_weekly_report.py

# 매일 오전 10시 실행 (업데이트 모드)
0 10 * * * cd /path/to/weekly-deploy-reporter && /path/to/venv/bin/python create_weekly_report.py
```

### 로그 확인

```bash
# 실행 로그 확인
tail -f cron.log

# 테스트 로그 확인
tail -f cron_test.log
```

## 🧪 테스트

```bash
# 테스트 실행
python -m pytest tests/

# 특정 테스트 실행
python -m pytest tests/test_create_weekly_report.py -v
```

## 📝 주요 함수 설명

### 핵심 함수들

- `get_jira_issues_by_customfield_10817()`: 배포 예정 티켓 조회
- `create_confluence_content()`: Confluence 페이지 내용 생성
- `get_linked_it_tickets()`: 연결된 IT 티켓 조회
- `notify_new_deploy_tickets()`: 새로운 배포 티켓 Slack 알림
- `snapshot_issues()`: 이슈 스냅샷 생성
- `get_changed_issues()`: 변경사항 감지

### 유틸리티 함수들

- `load_env_vars()`: 환경 변수 로딩
- `get_week_range()`: 주간 날짜 범위 계산
- `get_page_title()`: 페이지 제목 생성
- `send_slack()`: Slack 알림 전송

## 🔍 문제 해결

### 일반적인 문제들

1. **Jira 연결 실패**
   - API 토큰 확인
   - 네트워크 연결 확인
   - 권한 설정 확인

2. **Confluence 페이지 생성 실패**
   - Space Key 확인
   - 부모 페이지 ID 확인
   - 권한 설정 확인

3. **Slack 알림 전송 실패**
   - Webhook URL 확인
   - 네트워크 연결 확인

### 디버깅

```bash
# 상세 로그 확인
python create_weekly_report.py 2>&1 | tee debug.log

# 환경 변수 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ATLASSIAN_URL:', os.getenv('ATLASSIAN_URL'))"
```

## 📈 모니터링

### 로그 파일들

- `cron.log`: 일반 실행 로그
- `cron_test.log`: 테스트 실행 로그
- `weekly_issues_snapshot.json`: 이슈 스냅샷
- `notified_deploy_keys.json`: 알림 전송된 배포 키
- `notified_changes.json`: 알림 전송된 변경사항

### 성능 모니터링

- 실행 시간: 일반적으로 30초~2분
- 메모리 사용량: 약 50-100MB
- API 호출 횟수: Jira 2-3회, Confluence 1-2회

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원

문제가 발생하거나 질문이 있으시면:

1. [Issues](../../issues) 페이지에서 이슈 생성
2. 프로젝트 담당자에게 직접 문의
3. 로그 파일을 확인하여 문제 진단

---

**마지막 업데이트**: 2024년 12월