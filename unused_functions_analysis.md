# 사용하지 않는 함수 분석 결과

## 🔍 분석 방법
1. main() 함수에서 실제로 호출되는 함수들 확인
2. 각 함수가 다른 함수에서 호출되는지 검색
3. 테스트 파일에서 사용되는 함수들 확인
4. 명령행 인수로 실행되는 함수들 확인

## ❌ 사용하지 않는 함수들 (제거 가능)

### 1. 완전히 사용되지 않는 함수들
- `get_jira_issues_with_links()` - 정의만 있고 호출되지 않음
- `format_jira_datetime()` - 정의만 있고 호출되지 않음
- `load_deploy_ticket_links()` - 정의만 있고 호출되지 않음
- `get_deployed_by_tickets()` - 정의만 있고 호출되지 않음
- `get_slack_user_id_by_email()` - 정의만 있고 호출되지 않음
- `serialize_issues()` - 테스트에서만 사용, 실제 코드에서는 사용되지 않음
- `load_previous_snapshot()` - 테스트에서만 사용, 실제 코드에서는 사용되지 않음
- `save_snapshot()` - 테스트에서만 사용, 실제 코드에서는 사용되지 않음
- `save_issue_keys()` - 주석에 "현재 스크립트에서는 사용되지 않음" 명시
- `write_cron_log()` - 테스트에서만 사용, 실제 코드에서는 사용되지 않음

### 2. 디버깅/테스트용 함수들 (개발 완료 후 제거 가능)
- `check_jira_field_permissions()` - 권한 체크용, 개발 완료 후 제거 가능
- `test_jira_field_access()` - 테스트용, 개발 완료 후 제거 가능
- `get_jira_issues_smart_filtering()` - 스마트 필터링 테스트용, 현재는 사용되지 않음
- `test_customfield_10817_only()` - 테스트용, 개발 완료 후 제거 가능
- `create_deploy_links_html_table()` - 기존 함수 (호환성용), 현재는 사용되지 않음

### 3. 중복된 함수들
- `get_week_dates()` - `get_week_range()`와 기능이 중복됨

## ✅ 실제로 사용되는 함수들 (유지 필요)

### 핵심 기능 함수들
- `load_env_vars()` - 환경 변수 로딩
- `get_week_range()` - 주간 날짜 범위 계산
- `get_page_title()` - 페이지 제목 생성
- `read_json()` / `write_json()` - JSON 파일 처리
- `log()` - 로그 기록
- `normalize_html_content()` - HTML 내용 정규화
- `get_jira_issues_simple()` - Jira 이슈 조회 (get_macro_table_issues에서 사용)
- `create_confluence_content()` - Confluence 콘텐츠 생성
- `create_deploy_links_html_table_with_issues()` - 배포 링크 HTML 테이블 생성
- `get_linked_it_tickets()` - 연결된 IT 티켓 조회
- `get_macro_table_issues()` - 매크로 테이블 이슈 조회
- `send_slack()` - Slack 알림 전송
- `snapshot_issues()` - 이슈 스냅샷 생성
- `issues_changed()` - 이슈 변경 감지
- `get_notified_deploy_keys()` / `save_notified_deploy_keys()` - 알림 키 관리
- `get_notified_changes()` / `save_notified_changes()` - 알림 변경사항 관리
- `generate_change_hash()` - 변경사항 해시 생성
- `notify_new_deploy_tickets()` - 새로운 배포 티켓 알림
- `get_changed_issues()` - 변경된 이슈 조회
- `get_jira_issues_by_customfield_10817()` - customfield_10817 직접 조회
- `check_confluence_page_content()` - Confluence 페이지 내용 확인
- `main()` - 메인 실행 함수

### 유틸리티 함수들
- `get_now_str()` - 현재 시간 문자열

## 📊 정리 통계

### 제거 가능한 함수들: 15개
- 완전 미사용: 10개
- 디버깅/테스트용: 5개

### 유지 필요한 함수들: 23개
- 핵심 기능: 22개
- 유틸리티: 1개

### 코드 라인 수 절약 예상
- 제거 가능한 함수들: 약 500-600 라인
- 전체 코드의 약 30-35% 절약 가능

## 🎯 권장사항

1. **즉시 제거 가능**: 완전히 사용되지 않는 10개 함수
2. **개발 완료 후 제거**: 디버깅/테스트용 5개 함수
3. **중복 함수 정리**: `get_week_dates()` 제거하고 `get_week_range()`만 사용
4. **테스트 코드 정리**: 사용하지 않는 함수들의 테스트도 함께 제거

이렇게 정리하면 코드가 훨씬 깔끔해지고 유지보수가 쉬워질 것입니다. 