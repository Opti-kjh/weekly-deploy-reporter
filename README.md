# Weekly Deploy Reporter

## 소개

**Weekly Deploy Reporter**는 JIRA 이슈와 배포 관련 정보를 자동으로 수집하여 주간 리포트를 생성하고, 배포 이슈를 효율적으로 관리할 수 있도록 돕는 도구입니다. Python 및 JavaScript로 작성되어 있으며, Confluence 페이지 생성과 연동, 크론탭 자동화 예시도 제공합니다.

## 주요 기능
- JIRA 이슈 및 배포 이력 자동 수집
- 주간 리포트 자동 생성 (Python)
- 배포 티켓 링크 관리 (CSV/JSON)
- Confluence 페이지 콘텐츠 생성 지원
- 크론탭을 통한 자동화 예시 제공
- 테스트 코드 포함

## 설치 방법
1. 저장소 클론
```bash
git clone <이 저장소 주소>
cd weekly-deploy-reporter
```
2. 가상환경(선택)
```bash
python3 -m venv venv
source venv/bin/activate
```
3. 의존성 설치
```bash
pip install -r requirements.txt
```
(※ requirements.txt 파일이 없다면, 필요한 패키지를 직접 설치하세요)

## 환경 변수 설정
`.env.example` 파일을 참고하여 `.env` 파일을 생성하고, JIRA 및 기타 필요한 환경변수를 설정하세요.

- `JIRA_PARENT_ISSUE_KEY`: JIRA 프로젝트별 상위 이슈 키 (브랜치명에서 자동 추출)
- 기타 JIRA 인증 정보 등

## 사용법
- 주간 리포트 생성:
```bash
python create_weekly_report.py
```
- 배포자 정보 추출:
```bash
node getJiraDeployedBy.js
```
- 크론탭 예시:
`cron_example.txt` 파일 참고

## 테스트
테스트는 `tests/` 디렉토리 내에 있습니다.
```bash
python -m unittest tests/test_create_weekly_report.py
```

## 파일/디렉토리 설명
- `create_weekly_report.py` : 주간 리포트 생성 메인 스크립트
- `getJiraDeployedBy.js` : JIRA 배포자 정보 추출 스크립트
- `deploy_ticket_links.csv/json` : 배포 티켓 링크 데이터
- `notified_deploy_keys.json` : 알림된 배포 키 기록
- `weekly_issues.json`, `weekly_issues_snapshot.json` : 주간 이슈 데이터
- `create_confluence_page_content` : Confluence 페이지 생성 관련 파일
- `cron_example.txt`, `temp_crontab_config.txt` : 크론탭 설정 예시
- `tests/` : 테스트 코드 디렉토리
- `.env.example` : 환경 변수 예시 파일

---
문의사항은 이슈로 등록해 주세요.
