# Weekly Deploy Reporter

주간 배포 일정을 자동으로 수집하고 Confluence 페이지에 리포트를 생성하는 Python 스크립트입니다.

## 📋 개요

이 프로젝트는 Jira에서 배포 예정 티켓들을 자동으로 수집하여 Confluence에 주간 배포 리포트를 생성하고, 변경사항이 있을 때 Slack으로 알림을 보내는 자동화 도구입니다.

## 🚀 주요 기능

- **Jira 연동**: 배포 예정 티켓 자동 수집 (페이지네이션 지원)
- **Confluence 연동**: 주간 배포 리포트 페이지 자동 생성/업데이트
- **배포 예정 목록**: 부모 IT 티켓과 연결된 배포 티켓 관계 표시
- **Slack 알림**: 변경사항 발생 시 자동 알림 (중복 방지)
- **스냅샷 관리**: 이전 상태와 비교하여 변경사항 감지
- **다양한 실행 모드**: 생성, 업데이트, 현재/다음/지난 주 지원
- **연결된 IT 티켓 조회**: "is deployed by" 관계로 연결된 배포 티켓 자동 조회

## 📁 프로젝트 구조

```
weekly-deploy-reporter/
├── create_weekly_report.py      # 메인 스크립트
├── getJiraDeployedBy.js        # Jira 배포자 정보 추출
├── deploy_ticket_links.json    # 배포 티켓 링크 데이터
├── deploy_ticket_links.csv     # 배포 티켓 링크 CSV
├── weekly_issues.json          # 이슈 현황 데이터
├── weekly_issues_snapshot.json # 이슈 스냅샷
├── notified_deploy_keys.json   # 알림 전송된 배포 키
├── notified_changes.json       # 알림 전송된 변경사항
├── cron.log                   # 실행 로그
├── cron_test.log              # 테스트 실행 로그
├── tests/                     # 테스트 코드
│   └── test_create_weekly_report.py
├── reports/                   # 리포트 디렉토리
├── package.json               # Node.js 의존성
├── yarn.lock                  # Yarn 락 파일
├── .env                       # 환경 변수 (예시)
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

# 특정 페이지 내용 확인
python create_weekly_report.py --check-page

# 특정 티켓의 연결 관계 디버깅
python create_weekly_report.py --debug-links IT-5332
```

### 실행 모드 설명

| 모드 | 설명 | 대상 기간 | 페이지네이션 |
|------|------|-----------|-------------|
| `create` | 다음 주 (차주) 배포 예정 티켓으로 리포트 생성 | 다음 주 | ✅ |
| `current` | 이번 주 (현재 주) 배포 예정 티켓으로 리포트 생성/업데이트 | 이번 주 | ✅ |
| `last` | 지난 주 배포 예정 티켓으로 리포트 생성/업데이트 | 지난 주 | ✅ |
| `update` | 이번 주 배포 예정 티켓으로 리포트 업데이트 (기본값) | 이번 주 | ✅ |

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
# 알림 전송 시간 설정 (8시~21시)
notification_start_hour = 8
notification_end_hour = 21
```

## 📊 생성되는 리포트 구조

### 1. Jira 매크로 테이블
- 배포 예정 티켓 목록
- 키, 타입, 요약, 담당자, 상태, 생성일, 수정일, 예정된 시작 정보
- 날짜 포맷: `yyyy-MM-dd HH:mm`

### 2. 배포 예정 목록 HTML 테이블
- **부모 IT 티켓**: 배포 대상이 되는 IT 티켓
- **배포 티켓**: "is deployed by" 관계로 연결된 IT 티켓들만 표시
- **상태별 색상 구분**: 완료(초록), 실행(주황), 대기(회색)
- **Jira 링크**: 각 티켓의 Jira 페이지로 직접 연결
- **표시 형식**: 각 배포 티켓이 새로운 줄로 구분되어 표시

### 3. 배포 관계 표시 예시

```
IT-6813: 신상스튜디오 상품관리 엑셀 다운로드 > 상태 컬럼 추가
├── IT-6818 (완료): prod-studio-admin에 대한 배포 요청

IT-6754: 도매웹 컨버팅 - 후속 디자인 수정
├── IT-6819 (완료): prod-ssm-partner-react로 "deploy"에 대한 배포
```

## 🔄 자동화 설정

### Cron 작업 설정

```bash
# crontab 편집
crontab -e

# 매주 금요일 오전 9시 30분: 다음 주 리포트 생성
30 9 * * 5 /Users/eos/Desktop/weekly-deploy-reporter/venv/bin/python /Users/eos/Desktop/weekly-deploy-reporter/create_weekly_report.py create >> /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron.log 2>&1

# 매주 월~금 오전 9시~오후 8시: 15분 마다 이번 주 리포트 업데이트
15,30,45,0 8-21 * * 1-5 /Users/eos/Desktop/weekly-deploy-reporter/venv/bin/python /Users/eos/Desktop/weekly-deploy-reporter/create_weekly_report.py update >> /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron.log 2>&1

# 화요일, 수요일 오전 11시, 오후 2시: 5분 마다 배포 티켓 업데이트
5,10,15,20,25,30,35,40,45,50,55 11,14 * * 2,3 /Users/eos/Desktop/weekly-deploy-reporter/venv/bin/python /Users/eos/Desktop/weekly-deploy-reporter/create_weekly_report.py update >> /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron.log 2>&1
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

# 디버깅 모드로 실행
python create_weekly_report.py --debug-links IT-5332
```

## 📝 주요 함수 설명

### 핵심 함수들

- `get_jira_issues_by_customfield_10817()`: 배포 예정 티켓 조회 (페이지네이션 지원)
- `create_confluence_content()`: Confluence 페이지 내용 생성
- `create_deploy_links_html_table_with_issues()`: 배포 예정 목록 HTML 테이블 생성
- `get_linked_it_tickets()`: 연결된 IT 티켓 조회 ("is deployed by" 관계)
- `get_linked_it_tickets_with_retry()`: 재시도 로직을 포함한 연결된 IT 티켓 조회
- `notify_new_deploy_tickets()`: 새로운 배포 티켓 Slack 알림
- `snapshot_issues()`: 이슈 스냅샷 생성
- `get_changed_issues()`: 변경사항 감지

### 유틸리티 함수들

- `load_env_vars()`: 환경 변수 로딩
- `get_week_range()`: 주간 날짜 범위 계산
- `get_page_title()`: 페이지 제목 생성
- `send_slack()`: Slack 알림 전송
- `debug_issue_links()`: 특정 티켓의 연결 관계 디버깅

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

4. **배포 예정 티켓이 조회되지 않는 경우**
   - `customfield_10817` 필드 값 확인
   - 날짜 범위 확인
   - 페이지네이션 로그 확인

### 디버깅

```bash
# 상세 로그 확인
python create_weekly_report.py 2>&1 | tee debug.log

# 환경 변수 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ATLASSIAN_URL:', os.getenv('ATLASSIAN_URL'))"

# 특정 티켓의 연결 관계 확인
python create_weekly_report.py --debug-links IT-5332
```

## 📈 모니터링

### 로그 파일들

- `cron.log`: 일반 실행 로그
- `cron_test.log`: 테스트 실행 로그
- `weekly_issues_snapshot.json`: 이슈 스냅샷
- `notified_deploy_keys.json`: 알림 전송된 배포 키
- `notified_changes.json`: 알림 전송된 변경사항

### 성능 모니터링

- **실행 시간**: 일반적으로 1-3분 (페이지네이션으로 인한 증가)
- **메모리 사용량**: 약 100-200MB (대용량 데이터 처리)
- **API 호출 횟수**: 
  - Jira: 10-50회 (페이지네이션으로 인한 증가)
  - Confluence: 1-2회
- **조회되는 티켓 수**: 5,000+ 개 (전체 프로젝트)

### 최적화 사항

- **페이지네이션**: 모든 모드에서 100개씩 배치 조회
- **재시도 로직**: 연결된 IT 티켓 조회 시 최대 3회 재시도
- **중복 알림 방지**: 변경사항 해시 기반 중복 방지
- **시간 제한**: Slack 알림은 8시~21시에만 전송

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
4. 디버깅 모드로 실행하여 상세 정보 확인

---

**마지막 업데이트**: 2025년 7월
**최신 버전**: 페이지네이션 개선, 배포 예정 목록 HTML 테이블, 연결된 IT 티켓 조회 기능 추가