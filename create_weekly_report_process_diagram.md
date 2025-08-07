# create_weekly_report.py 프로세스 다이어그램

## 📋 전체 프로세스 플로우

```mermaid
flowchart TD
    A[스크립트 시작] --> B[환경 변수 로딩<br/>LOG_LEVEL, VERBOSE_LOGGING]
    B --> C[API 클라이언트 생성<br/>Jira & Confluence]
    C --> D[명령행 인수 처리]
    
    D --> E{특수 옵션 확인}
    E -->|--check-page| F[Confluence 페이지 내용 확인]
    E -->|--debug-links| G[특정 티켓 연결 관계 디버깅]
    E -->|일반 실행| H[날짜 범위 계산]
    
    H --> I[모드별 날짜 계산<br/>create/current/update/last]
    I --> J[Jira 이슈 조회<br/>customfield_10817 필드 사용]
    
    J --> K[스냅샷 파일 처리]
    K --> L{모드 확인}
    L -->|create/current| M[페이지 생성/업데이트 진행]
    L -->|update| N{변경 감지}
    
    N -->|변경 있음| M
    N -->|변경 없음| O[업데이트 생략]
    
    M --> P[Confluence 페이지 생성/업데이트]
    P --> Q[변경사항 해시 생성]
    Q --> R{변경사항 확인}
    
    R -->|변경 있음| S[Slack 알림 전송]
    R -->|변경 없음| T[알림 생략]
    
    S --> U[새로운 배포 티켓 알림]
    T --> U
    U --> V[스냅샷 저장]
    V --> W[프로세스 완료]
    
    F --> W
    G --> W
    O --> W
```

## 📅 날짜 계산 프로세스

```mermaid
flowchart TD
    A[날짜 계산 시작] --> B[현재 날짜 확인]
    B --> C{모드 확인}
    
    C -->|create| D[다음 주 계산<br/>today + (7 - weekday)]
    C -->|current| E[이번 주 계산<br/>today - weekday]
    C -->|update| F[이번 주 계산<br/>today - weekday]
    C -->|last| G[지난 주 계산<br/>today - weekday - 7]
    
    D --> H[월요일 ~ 일요일 범위 설정]
    E --> H
    F --> H
    G --> H
    
    H --> I[페이지 제목 생성<br/>X월 Y째주 형식]
    I --> J[날짜 계산 완료]
```

## 🔍 Jira 이슈 조회 프로세스

```mermaid
flowchart TD
    A[Jira 이슈 조회 시작] --> B[customfield_10817 필드 조회]
    B --> C{페이지네이션 사용?}
    
    C -->|Yes| D[페이지네이션으로 모든 티켓 조회<br/>1000개씩 배치 처리]
    C -->|No| E[한 번에 조회<br/>최대 1000개]
    
    D --> F[날짜 필터링]
    E --> F
    
    F --> G[Python에서 날짜 파싱]
    G --> H{해당 주간에 속하는가?}
    
    H -->|Yes| I[필터링된 이슈에 추가]
    H -->|No| J[제외]
    
    I --> K[최종 이슈 목록 반환]
    J --> K
```

## 📄 Confluence 페이지 생성/업데이트 프로세스

```mermaid
flowchart TD
    A[페이지 처리 시작] --> B{페이지 존재 확인}
    
    B -->|존재함| C[기존 페이지 내용 가져오기]
    B -->|존재하지 않음| D[새 페이지 생성]
    
    C --> E[내용 비교]
    E --> F{내용 변경됨?}
    
    F -->|Yes| G[페이지 업데이트]
    F -->|No| H[업데이트 생략]
    
    D --> I[페이지 생성]
    G --> J[변경사항 알림 처리]
    H --> K[로그 기록]
    I --> J
    
    J --> L[Slack 알림 전송]
    K --> M[프로세스 완료]
    L --> M
```

## 📢 Slack 알림 프로세스

```mermaid
flowchart TD
    A[알림 처리 시작] --> B{MUTE 모드?}
    
    B -->|Yes| C[알림 전송 생략]
    B -->|No| D[시간 제한 확인<br/>8시~21시]
    
    D --> E{시간 범위 내?}
    E -->|No| F[알림 전송 생략]
    E -->|Yes| G[변경사항 해시 확인]
    
    G --> H{이미 알림 전송됨?}
    H -->|Yes| I[알림 전송 생략]
    H -->|No| J[변경사항 메시지 구성]
    
    J --> K[Slack Webhook 전송]
    K --> L[알림 해시 저장]
    L --> M[새로운 배포 티켓 알림]
    
    C --> N[프로세스 완료]
    F --> N
    I --> N
    M --> N
```

## 🔗 배포 티켓 연결 관계 조회 프로세스

```mermaid
flowchart TD
    A[연결 관계 조회 시작] --> B[Jira API 호출<br/>expand=issuelinks]
    B --> C[issuelinks 필드 확인]
    
    C --> D[각 연결 관계 순회]
    D --> E{배포 관련 링크 타입?<br/>Deployments/is deployed by}
    
    E -->|Yes| F[연결된 티켓 확인]
    E -->|No| G[다음 연결 관계로]
    
    F --> H{IT 관련 이슈 타입?}
    H -->|Yes| I[IT 티켓으로 추가]
    H -->|No| J[제외]
    
    I --> K[티켓 정보 구성<br/>key, summary, status]
    J --> L[다음 연결 관계로]
    G --> L
    
    K --> M[IT 티켓 목록에 추가]
    L --> N{모든 연결 관계 확인 완료?}
    
    N -->|No| D
    N -->|Yes| O[최종 IT 티켓 목록 반환]
```

## 📸 스냅샷 관리 프로세스

```mermaid
flowchart TD
    A[스냅샷 처리 시작] --> B[모드별 스냅샷 파일 경로 결정]
    
    B --> C{스냅샷 파일 존재?}
    C -->|Yes| D[기존 스냅샷 로드]
    C -->|No| E[빈 스냅샷으로 초기화]
    
    D --> F[현재 이슈 스냅샷 생성]
    E --> F
    
    F --> G[변경사항 비교]
    G --> H{변경사항 감지}
    
    H -->|Yes| I[변경 유형 분류<br/>추가/제거/갱신]
    H -->|No| J[변경 없음 처리]
    
    I --> K[변경사항 해시 생성]
    K --> L[중복 알림 방지 확인]
    L --> M[Slack 알림 전송]
    
    J --> N[업데이트 생략]
    M --> O[새 스냅샷 저장]
    N --> O
    
    O --> P[스냅샷 처리 완료]
```

## 📝 로그 시스템 프로세스

```mermaid
flowchart TD
    A[로그 시스템 시작] --> B[환경 변수 확인<br/>LOG_LEVEL, VERBOSE_LOGGING]
    
    B --> C{로그 레벨 확인}
    C -->|DEBUG| D[모든 디버깅 정보 출력]
    C -->|INFO| E[일반 실행 정보 출력]
    C -->|WARNING| F[경고 메시지만 출력]
    C -->|ERROR| G[오류 메시지만 출력]
    C -->|CRITICAL| H[심각한 오류만 출력]
    
    D --> I[상세 로그 활성화 확인]
    E --> I
    F --> I
    G --> I
    H --> I
    
    I --> J{VERBOSE_LOGGING?}
    J -->|true| K[상세한 디버깅 정보 추가]
    J -->|false| L[기본 로그만 출력]
    
    K --> M[로그 파일에 기록]
    L --> M
    
    M --> N[콘솔에 출력]
    N --> O[로그 시스템 완료]
```

## 🤖 TaskMaster AI 통합 프로세스

```mermaid
flowchart TD
    A[TaskMaster 통합 시작] --> B[작업 목록 확인<br/>task-master list]
    
    B --> C[다음 작업 선택<br/>task-master next]
    C --> D[작업 상세 정보 확인<br/>task-master show <id>]
    
    D --> E[작업 상태 업데이트<br/>task-master set-status]
    E --> F{작업 완료?}
    
    F -->|Yes| G[작업 완료 처리]
    F -->|No| H[작업 계속 진행]
    
    G --> I[다음 작업으로 이동]
    H --> J[작업 세부 분해<br/>task-master expand]
    
    I --> K[TaskMaster 프로세스 완료]
    J --> K
```

## 🔧 주요 함수별 역할

```mermaid
graph TB
    subgraph "유틸리티 함수"
        A1[load_env_vars]
        A2[get_week_range]
        A3[get_page_title]
        A4[read_json/write_json]
        A5[log]
        A6[should_log]
        A7[print_log]
    end
    
    subgraph "Jira 관련 함수"
        B1[get_jira_issues_by_customfield_10817]
        B2[get_linked_it_tickets]
        B3[get_linked_it_tickets_with_retry]
        B4[snapshot_issues]
        B5[get_jira_issues_simple]
    end
    
    subgraph "Confluence 관련 함수"
        C1[create_confluence_content]
        C2[create_deploy_links_html_table_with_issues]
        C3[normalize_html_content]
        C4[check_confluence_page_content]
    end
    
    subgraph "알림 관련 함수"
        D1[send_slack]
        D2[notify_new_deploy_tickets]
        D3[get_notified_deploy_keys]
        D4[generate_change_hash]
        D5[get_notified_changes]
        D6[save_notified_changes]
    end
    
    subgraph "변경 감지 함수"
        E1[get_changed_issues]
        E2[issues_changed]
    end
    
    subgraph "디버깅 함수"
        F1[debug_issue_links]
        F2[get_now_str]
    end
```

## ⚙️ 환경 변수 및 설정

```mermaid
graph LR
    subgraph "필수 환경 변수"
        A1[ATLASSIAN_URL]
        A2[ATLASSIAN_USERNAME]
        A3[ATLASSIAN_API_TOKEN]
        A4[SLACK_WEBHOOK_URL]
        A5[SLACK_BOT_TOKEN]
    end
    
    subgraph "선택적 환경 변수"
        B1[JIRA_PROJECT_KEY]
        B2[CONFLUENCE_SPACE_KEY]
        B3[DEPLOY_MESSAGE]
        B4[LOG_LEVEL]
        B5[VERBOSE_LOGGING]
    end
    
    subgraph "하드코딩된 설정"
        C1[JIRA_DEPLOY_DATE_FIELD_ID]
        C2[CONFLUENCE_PARENT_PAGE_TITLE]
        C3[parent_page_id]
        C4[notification_start_hour]
        C5[notification_end_hour]
    end
```

## 🎯 실행 모드별 동작

```mermaid
flowchart TD
    A[실행 모드 확인] --> B{모드 선택}
    
    B -->|create| C[다음 주 배포 예정 티켓<br/>새 페이지 생성]
    B -->|current| D[이번 주 배포 예정 티켓<br/>페이지 생성/업데이트]
    B -->|update| E[이번 주 배포 예정 티켓<br/>변경 시에만 업데이트]
    B -->|last| F[지난 주 배포 예정 티켓<br/>페이지 생성/업데이트]
    
    C --> G[스냅샷 파일: next_week]
    D --> H[스냅샷 파일: current_week]
    E --> H
    F --> I[스냅샷 파일: last_week]
    
    G --> J[페이지 생성/업데이트 진행]
    H --> J
    I --> J
```

## 📊 코드 최적화 결과

### 최적화 전후 비교

```mermaid
graph LR
    subgraph "최적화 전"
        A1[38개 함수]
        A2[~1,600라인]
        A3[15개 미사용 함수]
        A4[1개 중복 함수]
    end
    
    subgraph "최적화 후"
        B1[23개 함수]
        B2[~900라인]
        B3[0개 미사용 함수]
        B4[0개 중복 함수]
    end
    
    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4
```

### 제거된 함수 분류

```mermaid
pie title 제거된 함수 분류
    "완전 미사용 함수" : 10
    "디버깅/테스트용 함수" : 5
    "중복 함수" : 1
```

## 🔄 성능 최적화 프로세스

```mermaid
flowchart TD
    A[성능 최적화 시작] --> B[사용하지 않는 함수 분석]
    
    B --> C[함수 호출 관계 분석]
    C --> D[중복 함수 식별]
    
    D --> E[안전한 제거 대상 선별]
    E --> F[코드 제거 실행]
    
    F --> G[기능 테스트]
    G --> H{테스트 통과?}
    
    H -->|Yes| I[최적화 완료]
    H -->|No| J[롤백 및 재분석]
    
    I --> K[성능 측정]
    J --> B
    
    K --> L[결과 문서화]
    L --> M[최적화 프로세스 완료]
```

## 📈 모니터링 및 로그 시스템

```mermaid
flowchart TD
    A[모니터링 시작] --> B[로그 레벨 확인]
    
    B --> C{로그 레벨}
    C -->|DEBUG| D[상세 디버깅 정보]
    C -->|INFO| E[일반 실행 정보]
    C -->|WARNING| F[경고 메시지]
    C -->|ERROR| G[오류 메시지]
    C -->|CRITICAL| H[심각한 오류]
    
    D --> I[VERBOSE_LOGGING 확인]
    E --> I
    F --> I
    G --> I
    H --> I
    
    I --> J{상세 로그?}
    J -->|true| K[추가 디버깅 정보]
    J -->|false| L[기본 로그]
    
    K --> M[로그 파일 기록]
    L --> M
    
    M --> N[콘솔 출력]
    N --> O[실행 시간 측정]
    O --> P[종료 코드 기록]
    P --> Q[모니터링 완료]
```

## 🎯 주요 개선사항

### 1. 코드 최적화
- **44% 코드 라인 감소**: ~1,600라인 → ~900라인
- **39% 함수 수 감소**: 38개 → 23개
- **100% 미사용 함수 제거**: 15개 함수 완전 제거
- **100% 중복 함수 제거**: 1개 중복 함수 제거

### 2. 로그 시스템 개선
- **로그 레벨 제어**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **상세 로그 기능**: VERBOSE_LOGGING 옵션
- **일일 로그 파일**: cron_YYMMDD.log 형식
- **자동 정리 기능**: 오래된 로그 파일 자동 삭제

### 3. TaskMaster AI 통합
- **AI 기반 작업 관리**: PRD 문서에서 자동 작업 생성
- **작업 복잡도 분석**: AI가 작업을 세부 작업으로 분해
- **의존성 관리**: 작업 간 의존성 자동 관리
- **상태 추적**: 실시간 작업 진행 상황 추적

### 4. 성능 최적화
- **페이지네이션 선택적 사용**: 기본값은 빠른 실행
- **재시도 로직**: 연결된 IT 티켓 조회 시 최대 3회 재시도
- **중복 알림 방지**: 변경사항 해시 기반 중복 방지
- **시간 제한**: Slack 알림은 8시~21시에만 전송

이 다이어그램들은 `create_weekly_report.py` 스크립트의 전체적인 프로세스와 각 단계별 동작을 시각적으로 보여줍니다. 주요 특징은 다음과 같습니다:

1. **모듈화된 구조**: 각 기능이 독립적인 함수로 분리되어 있음
2. **에러 처리**: 각 단계에서 예외 상황을 고려한 처리
3. **중복 방지**: 변경사항 해시를 통한 중복 알림 방지
4. **유연한 모드**: 다양한 실행 모드 지원
5. **디버깅 지원**: 특정 티켓의 연결 관계 디버깅 기능
6. **로그 시스템**: 고급 로그 레벨 제어 및 일일 로그 관리
7. **AI 통합**: TaskMaster AI를 통한 작업 관리 자동화
8. **성능 최적화**: 사용하지 않는 함수 제거로 코드 효율성 향상 