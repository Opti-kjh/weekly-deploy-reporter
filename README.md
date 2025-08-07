# Weekly Deploy Reporter

주간 배포 일정을 자동으로 수집하고 Confluence 페이지에 리포트를 생성하는 Python 스크립트입니다.

## 📋 개요

이 프로젝트는 Jira에서 배포 예정 티켓들을 자동으로 수집하여 Confluence에 주간 배포 리포트를 생성하고, 변경사항이 있을 때 Slack으로 알림을 보내는 자동화 도구입니다.

### 🚀 주요 기능

- **Jira 연동**: 배포 예정 티켓 자동 수집 (페이지네이션 지원)
- **Confluence 연동**: 주간 배포 리포트 페이지 자동 생성/업데이트
- **JIRA 매크로 테이블**: 요청 유형 필드 포함한 상세 정보 표시
- **배포 예정 목록**: 부모 IT 티켓과 연결된 배포 티켓 관계 표시
- **Slack 알림**: 변경사항 발생 시 자동 알림 (중복 방지)
- **스냅샷 관리**: 이전 상태와 비교하여 변경사항 감지
- **다양한 실행 모드**: 생성, 업데이트, 현재/다음/지난 주 지원
- **연결된 IT 티켓 조회**: "is deployed by" 관계로 연결된 배포 티켓 자동 조회
- **고급 로그 시스템**: 로그 레벨 제어 및 일일 로그 파일 관리
- **환경 변수 제어**: 로그 레벨 및 상세 로그 설정
- **TaskMaster 통합**: AI 기반 작업 관리 및 자동화
- **코드 최적화**: 사용하지 않는 함수 제거로 44% 코드 감소

## 📁 프로젝트 구조

```
weekly-deploy-reporter/
├── create_weekly_report.py      # 메인 스크립트 (최적화됨)
├── getJiraDeployedBy.js        # Jira 배포자 정보 추출
├── check_jira_fields.py        # JIRA 필드 정보 조회 스크립트
├── create_daily_log.py         # 일일 로그 생성 스크립트
├── log_manager.py              # 로그 관리 유틸리티
├── debug_deploy_issues.py      # 배포 이슈 디버깅 스크립트
├── test_pagination_options.py  # 페이지네이션 테스트
├── test_emoji_notification.py  # 이모지 알림 테스트
├── test_it_5332_links.py      # IT-5332 연결 관계 테스트
├── deploy_ticket_links.json    # 배포 티켓 링크 데이터
├── deploy_ticket_links.csv     # 배포 티켓 링크 CSV
├── weekly_issues.json          # 이슈 현황 데이터
├── weekly_issues_snapshot.json # 이슈 스냅샷
├── notified_deploy_keys.json   # 알림 전송된 배포 키
├── notified_changes.json       # 알림 전송된 변경사항
├── crontab_new_setting.txt     # 새로운 crontab 설정
├── crontab_daily_logs.txt      # 일일 로그용 crontab 설정
├── DAILY_LOG_SETUP.md          # 일일 로그 시스템 가이드
├── create_weekly_report_process_diagram.md # 프로세스 다이어그램
├── code_cleanup_summary.md     # 코드 정리 보고서
├── unused_functions_analysis.md # 사용하지 않는 함수 분석
├── logs/runtime/               # 일일 로그 파일 디렉토리
│   └── cron_YYMMDD.log         # 날짜별 로그 파일
├── cron.log                    # 기존 실행 로그 (레거시)
├── cron_test.log               # 테스트 실행 로그
├── tests/                      # 테스트 코드
│   └── test_create_weekly_report.py
├── .taskmaster/                # TaskMaster AI 통합
│   ├── tasks/tasks.json        # 작업 정의
│   ├── config.json             # AI 모델 설정
│   ├── docs/                   # 문서
│   ├── templates/              # 템플릿
│   └── reports/                # 리포트
├── package.json                # Node.js 의존성
├── yarn.lock                   # Yarn 락 파일
├── .env                        # 환경 변수 (예시)
├── CLAUDE.md                   # Claude Code 통합 가이드
├── AGENTS.md                   # TaskMaster AI 가이드
└── README.md                   # 프로젝트 문서
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

# 배포 메시지 알림 설정 (선택사항)
DEPLOY_MESSAGE=off  # on: 배포 승인 요청 메시지 활성화, off: 비활성화 (기본값)

# 로그 설정 (선택사항)
LOG_LEVEL=INFO        # DEBUG, INFO, WARNING, ERROR, CRITICAL (기본값: INFO)
VERBOSE_LOGGING=false # true/false (기본값: false)
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

# 페이지네이션 옵션 사용
python create_weekly_report.py current                   # 페이지네이션 없이 조회 (기본값)
python create_weekly_report.py create --pagination      # 페이지네이션 사용

# 강제 업데이트 (변경사항 감지 무시)
python create_weekly_report.py --force-update

# 특정 페이지 내용 확인
python create_weekly_report.py --check-page

# 특정 티켓의 연결 관계 디버깅
python create_weekly_report.py --debug-links IT-5332

# 로그 레벨 설정
LOG_LEVEL=DEBUG python create_weekly_report.py current
VERBOSE_LOGGING=true python create_weekly_report.py current

# MUTE 모드 (Slack 알림 비활성화)
python create_weekly_report.py current --test
```

### 실행 모드 설명

| 모드 | 설명 | 대상 기간 | 페이지네이션 |
|------|------|-----------|-------------|
| `create` | 다음 주 (차주) 배포 예정 티켓으로 리포트 생성 | 다음 주 | 선택적 |
| `current` | 이번 주 (현재 주) 배포 예정 티켓으로 리포트 생성/업데이트 | 이번 주 | 선택적 |
| `last` | 지난 주 배포 예정 티켓으로 리포트 생성/업데이트 | 지난 주 | 선택적 |
| `update` | 이번 주 배포 예정 티켓으로 리포트 업데이트 (기본값) | 이번 주 | 선택적 |

### 페이지네이션 옵션

| 옵션 | 설명 | 기본값 | 권장 사용 |
|------|------|--------|-----------|
| `--no-pagination` | 페이지네이션 없이 한 번에 조회 (최대 1000개) | ✅ | 빠른 실행, 소량 데이터 |
| `--pagination` | 페이지네이션을 사용하여 모든 티켓 조회 (100개씩 배치) | ❌ | 대용량 데이터, 안정성 중시 |

### 로그 레벨 옵션

| 환경 변수 | 설명 | 기본값 | 사용 예시 |
|-----------|------|--------|-----------|
| `LOG_LEVEL` | 로그 레벨 설정 | INFO | `LOG_LEVEL=DEBUG python create_weekly_report.py` |
| `VERBOSE_LOGGING` | 상세 로그 활성화 | false | `VERBOSE_LOGGING=true python create_weekly_report.py` |

## 🔧 설정 및 커스터마이징

### Jira 필드 설정

```python
# create_weekly_report.py 파일에서 수정
JIRA_DEPLOY_DATE_FIELD_ID = "customfield_10817"  # 예정된 시작 필드 ID
```

### JIRA 매크로 설정

현재 JIRA 매크로는 다음 컬럼들을 포함합니다:
- **키**: 티켓 키 (예: IT-5331)
- **유형**: 이슈 타입 (아이콘 + 텍스트)
- **Request Type**: 요청 유형 (예: "기능 변경 요청", "설정 변경 요청")
- **상태**: 현재 상태
- **요약**: 티켓 제목
- **담당자**: 담당자 정보
- **생성일**: 티켓 생성 날짜
- **변경일**: 마지막 수정 날짜
- **예정된 시작**: 배포 예정 날짜

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

### 배포 메시지 알림 설정

```env
# .env 파일에서 설정
DEPLOY_MESSAGE=off  # 기본값: 비활성화
```

**DEPLOY_MESSAGE 옵션:**
- `on`: 배포 승인 요청 메시지 활성화
- `off`: 배포 승인 요청 메시지 비활성화 (기본값)

**사용 예시:**
```bash
# 배포 메시지 활성화
export DEPLOY_MESSAGE=on
python create_weekly_report.py

# 배포 메시지 비활성화 (기본값)
export DEPLOY_MESSAGE=off
python create_weekly_report.py
```

## 📊 생성되는 리포트 구조

### 1. Jira 매크로 테이블
- 배포 예정 티켓 목록
- 키, 유형, 요청 유형, 상태, 요약, 담당자, 생성일, 수정일, 예정된 시작 정보
- 날짜 포맷: `yyyy-MM-dd HH:mm`
- 요청 유형 필드: "기능 변경 요청", "설정 변경 요청" 등 표시

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

# 일일 로그 확인
tail -f logs/runtime/cron_$(date +%y%m%d).log
```

## 🧪 테스트

```bash
# 테스트 실행
python -m pytest tests/

# 특정 테스트 실행
python -m pytest tests/test_create_weekly_report.py -v

# 디버깅 모드로 실행
python create_weekly_report.py --debug-links IT-5332

# JIRA 필드 정보 확인
python check_jira_fields.py

# 페이지네이션 옵션 테스트
python test_pagination_options.py

# 이모지 알림 테스트
python test_emoji_notification.py

# IT-5332 연결 관계 테스트
python test_it_5332_links.py
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

### 로그 관련 함수들

- `should_log()`: 로그 레벨에 따라 출력 여부 결정
- `log()`: 로그 메시지를 파일에 기록
- `print_log()`: 로그 메시지를 콘솔에 출력하고 파일에도 기록

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

5. **JIRA 매크로에서 요청 유형이 표시되지 않는 경우**
   - `customfield_10403` 필드 확인
   - JIRA Service Desk 설정 확인
   - 매크로 파라미터 확인

### 디버깅

```bash
# 상세 로그 확인
python create_weekly_report.py 2>&1 | tee debug.log

# 환경 변수 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ATLASSIAN_URL:', os.getenv('ATLASSIAN_URL'))"

# 특정 티켓의 연결 관계 확인
python create_weekly_report.py --debug-links IT-5332

# JIRA 필드 정보 확인
python check_jira_fields.py

# 로그 레벨 설정으로 디버깅
LOG_LEVEL=DEBUG python create_weekly_report.py current
```

## 📈 모니터링

### 로그 관리 시스템

이 프로젝트는 고급 로그 파일 관리 시스템을 제공합니다:

#### 로그 레벨 시스템
- **DEBUG**: 상세한 디버깅 정보
- **INFO**: 일반적인 실행 정보 (기본값)
- **WARNING**: 경고 메시지
- **ERROR**: 오류 메시지
- **CRITICAL**: 심각한 오류 메시지

#### 환경 변수 제어
```bash
# 로그 레벨 설정
LOG_LEVEL=DEBUG python create_weekly_report.py current
LOG_LEVEL=WARNING python create_weekly_report.py current

# 상세 로그 활성화
VERBOSE_LOGGING=true python create_weekly_report.py current
```

#### 일일 로그 파일
- **파일명 형식**: `cron_YYMMDD.log` (예: `cron_250724.log`)
- **위치**: `logs/runtime/` 디렉토리
- **자동 생성**: 매일 새로운 로그 파일 생성
- **실행 정보**: 시작/종료 시간, 종료 코드, 오류 정보 자동 기록

#### 로그 관리 유틸리티
```bash
# 로그 요약 정보 확인
python3 log_manager.py summary

# 실시간 로그 모니터링
python3 log_manager.py tail

# 오늘 로그 내용 확인
python3 log_manager.py today

# 오래된 로그 파일 정리 (30일 이상)
python3 log_manager.py cleanup
```

#### Crontab 설정 변경
기존 설정을 새로운 일일 로그 시스템으로 변경하려면:
```bash
# 기존 설정 백업
crontab -l > crontab_backup.txt

# 새로운 설정 적용
crontab crontab_new_setting.txt
```

자세한 설정 방법은 [DAILY_LOG_SETUP.md](DAILY_LOG_SETUP.md)를 참조하세요.

### 기존 로그 파일들

- `cron.log`: 기존 실행 로그 (레거시)
- `cron_test.log`: 테스트 실행 로그
- `weekly_issues_snapshot.json`: 이슈 스냅샷
- `notified_deploy_keys.json`: 알림 전송된 배포 키
- `notified_changes.json`: 알림 전송된 변경사항

### 성능 모니터링

- **실행 시간**: 
  - 페이지네이션 미사용: 1-2분 (빠른 실행, 기본값)
  - 페이지네이션 사용: 2-5분 (대용량 데이터 처리)
- **메모리 사용량**: 약 50-200MB (페이지네이션 사용 여부에 따라)
- **API 호출 횟수**: 
  - Jira: 1-5회 (페이지네이션 미사용 시, 기본값), 10-50회 (페이지네이션 사용 시)
  - Confluence: 1-2회
- **조회되는 티켓 수**: 5,000+ 개 (전체 프로젝트)

### 최적화 사항

- **페이지네이션**: 선택적 사용 (기본값: 페이지네이션 없음)
- **재시도 로직**: 연결된 IT 티켓 조회 시 최대 3회 재시도
- **중복 알림 방지**: 변경사항 해시 기반 중복 방지
- **시간 제한**: Slack 알림은 8시~21시에만 전송
- **빠른 실행**: 기본적으로 페이지네이션 없이 빠른 실행
- **로그 레벨 제어**: 환경 변수로 로그 출력 제어

## 🤖 TaskMaster AI 통합

이 프로젝트는 TaskMaster AI와 통합되어 AI 기반 작업 관리 및 자동화를 지원합니다.

### TaskMaster 설정

```bash
# TaskMaster 초기화
task-master init

# AI 모델 설정
task-master models --setup

# 작업 목록 확인
task-master list

# 다음 작업 확인
task-master next
```

### 주요 기능

- **AI 기반 작업 생성**: PRD 문서에서 자동으로 작업 생성
- **작업 복잡도 분석**: AI가 작업의 복잡도를 분석하고 세부 작업으로 분해
- **의존성 관리**: 작업 간 의존성을 자동으로 관리
- **상태 추적**: 작업 진행 상황을 실시간으로 추적

자세한 내용은 [CLAUDE.md](CLAUDE.md)와 [AGENTS.md](AGENTS.md)를 참조하세요.

## 📊 코드 최적화 결과

### 최적화 전후 비교

| 항목 | 최적화 전 | 최적화 후 | 개선율 |
|------|-----------|-----------|--------|
| 함수 수 | 38개 | 23개 | 39% 감소 |
| 코드 라인 | ~1,600라인 | ~900라인 | 44% 감소 |
| 사용하지 않는 함수 | 15개 | 0개 | 100% 제거 |
| 중복 함수 | 1개 | 0개 | 100% 제거 |

### 제거된 함수들

#### 완전히 사용되지 않는 함수들 (10개)
- `get_jira_issues_with_links()` - 63라인 제거
- `format_jira_datetime()` - 12라인 제거  
- `load_deploy_ticket_links()` - 8라인 제거
- `get_deployed_by_tickets()` - 35라인 제거
- `get_slack_user_id_by_email()` - 36라인 제거
- `serialize_issues()` - 25라인 제거
- `load_previous_snapshot()` - 12라인 제거
- `save_snapshot()` - 8라인 제거
- `save_issue_keys()` - 8라인 제거
- `write_cron_log()` - 3라인 제거

#### 디버깅/테스트용 함수들 (5개)
- `check_jira_field_permissions()` - 82라인 제거
- `test_jira_field_access()` - 35라인 제거
- `get_jira_issues_smart_filtering()` - 100라인 제거
- `test_customfield_10817_only()` - 40라인 제거
- `create_deploy_links_html_table()` - 200라인 제거

자세한 내용은 [code_cleanup_summary.md](code_cleanup_summary.md)를 참조하세요.

## 📞 지원

문제가 발생하거나 질문이 있으시면:

1. [Issues](../../issues) 페이지에서 이슈 생성
2. 프로젝트 담당자(김종호:kjh@deali.net)에게 문의
3. 로그 파일을 확인하여 문제 진단
4. 디버깅 모드로 실행하여 상세 정보 확인

## 📚 관련 문서

- [DAILY_LOG_SETUP.md](DAILY_LOG_SETUP.md) - 일일 로그 시스템 설정 가이드
- [create_weekly_report_process_diagram.md](create_weekly_report_process_diagram.md) - 프로세스 다이어그램
- [CLAUDE.md](CLAUDE.md) - Claude Code 통합 가이드
- [AGENTS.md](AGENTS.md) - TaskMaster AI 가이드
- [code_cleanup_summary.md](code_cleanup_summary.md) - 코드 정리 보고서
- [unused_functions_analysis.md](unused_functions_analysis.md) - 사용하지 않는 함수 분석

---

**마지막 업데이트**: 2025년 8월
**최신 버전**: JIRA 매크로 요청 유형 필드 추가, 로그 시스템, 환경 변수 제어 기능, TaskMaster AI 통합, 코드 최적화 완료