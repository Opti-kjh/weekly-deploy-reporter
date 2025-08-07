# Weekly Deploy Reporter - 개발 가이드

## 🚀 개발 환경 설정

### 1. 필수 요구사항

#### 시스템 요구사항
- **Python**: 3.7 이상
- **Node.js**: 14.0 이상
- **Git**: 2.0 이상
- **운영체제**: macOS, Linux, Windows

#### 권장 개발 도구
- **IDE**: VS Code, PyCharm, Cursor
- **터미널**: iTerm2 (macOS), Windows Terminal
- **버전 관리**: Git, GitHub Desktop

### 2. 초기 설정

#### 저장소 클론
```bash
# 저장소 클론
git clone https://github.com/your-username/weekly-deploy-reporter.git
cd weekly-deploy-reporter

# 브랜치 확인
git branch -a
```

#### Python 가상환경 설정
```bash
# Python 가상환경 생성
python -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

#### Node.js 의존성 설치
```bash
# Node.js 패키지 설치
npm install
# 또는
yarn install
```

### 3. 환경 변수 설정

#### .env 파일 생성
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

#### 필수 환경 변수
```env
# Atlassian 설정
ATLASSIAN_URL=https://your-domain.atlassian.net
ATLASSIAN_USERNAME=your-email@domain.com
ATLASSIAN_API_TOKEN=your-api-token

# Slack 설정
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token

# 프로젝트 설정
JIRA_PROJECT_KEY=IT
CONFLUENCE_SPACE_KEY=DEV

# 로그 설정
LOG_LEVEL=INFO
VERBOSE_LOGGING=false

# 배포 메시지 설정
DEPLOY_MESSAGE=off
```

### 4. 개발 도구 설정

#### VS Code 설정
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

#### Git Hooks 설정
```bash
# Husky 설치 (이미 설정됨)
npm install husky --save-dev

# Git hooks 활성화
npx husky install
```

## 📝 코딩 표준

### 1. Python 코딩 표준

#### PEP 8 준수
```python
# 좋은 예시
def get_jira_issues_by_customfield_10817():
    """Jira 이슈를 customfield_10817로 조회합니다."""
    try:
        # 구현 내용
        pass
    except Exception as e:
        log(f"오류 발생: {e}")
        return None
```

#### 함수 명명 규칙
- **함수명**: snake_case 사용
- **클래스명**: PascalCase 사용
- **상수**: UPPER_SNAKE_CASE 사용
- **변수명**: snake_case 사용

#### 주석 작성 규칙
```python
def create_confluence_content(issues, page_title):
    """
    Confluence 페이지 내용을 생성합니다.
    
    Args:
        issues (list): Jira 이슈 목록
        page_title (str): 페이지 제목
        
    Returns:
        str: 생성된 HTML 내용
        
    Raises:
        ValueError: 이슈 목록이 비어있는 경우
    """
    if not issues:
        raise ValueError("이슈 목록이 비어있습니다")
    
    # HTML 내용 생성
    content = generate_html_content(issues)
    
    return content
```

### 2. JavaScript 코딩 표준

#### ESLint 설정
```javascript
// .eslintrc.js
module.exports = {
  extends: ['eslint:recommended'],
  env: {
    node: true,
    es6: true
  },
  rules: {
    'indent': ['error', 2],
    'quotes': ['error', 'single'],
    'semi': ['error', 'always']
  }
};
```

#### 함수 명명 규칙
```javascript
// 좋은 예시
function getJiraDeployedBy(issueKey) {
  // 구현 내용
}

const JIRA_API_ENDPOINT = 'https://api.atlassian.com';
```

### 3. 문서 작성 표준

#### Markdown 작성 규칙
```markdown
# 제목 (H1)
## 부제목 (H2)
### 소제목 (H3)

**굵은 글씨**와 *기울임꼴*을 적절히 사용

```python
# 코드 블록
def example():
    return "Hello World"
```

> 인용문은 이렇게 작성
```

## 🧪 테스트 방법

### 1. Python 테스트

#### 테스트 실행
```bash
# 모든 테스트 실행
python -m pytest tests/

# 특정 테스트 실행
python -m pytest tests/test_create_weekly_report.py -v

# 커버리지 포함 테스트
python -m pytest tests/ --cov=create_weekly_report --cov-report=html
```

#### 테스트 작성 예시
```python
# tests/test_create_weekly_report.py
import pytest
from unittest.mock import Mock, patch
from create_weekly_report import get_week_range

def test_get_week_range():
    """주간 날짜 범위 계산 테스트"""
    start_date, end_date = get_week_range('current')
    
    assert start_date is not None
    assert end_date is not None
    assert start_date <= end_date

@pytest.mark.parametrize("mode,expected", [
    ("current", "이번 주"),
    ("next", "다음 주"),
    ("last", "지난 주")
])
def test_get_page_title(mode, expected):
    """페이지 제목 생성 테스트"""
    title = get_page_title(mode)
    assert expected in title
```

### 2. JavaScript 테스트

#### 테스트 실행
```bash
# Jest 테스트 실행
npm test

# 특정 테스트 실행
npm test -- --testNamePattern="getJiraDeployedBy"
```

#### 테스트 작성 예시
```javascript
// test/getJiraDeployedBy.test.js
const { getJiraDeployedBy } = require('../getJiraDeployedBy');

describe('getJiraDeployedBy', () => {
  test('should return deployed tickets for valid issue key', async () => {
    const result = await getJiraDeployedBy('IT-5332');
    expect(result).toBeDefined();
    expect(Array.isArray(result)).toBe(true);
  });
});
```

### 3. 통합 테스트

#### API 연결 테스트
```bash
# Jira API 연결 테스트
python check_jira_fields.py

# Slack Webhook 테스트
python test_emoji_notification.py

# 페이지네이션 테스트
python test_pagination_options.py
```

## 🔍 디버깅 기법

### 1. 로그 레벨 활용

#### 디버그 모드 실행
```bash
# DEBUG 레벨로 실행
LOG_LEVEL=DEBUG python create_weekly_report.py current

# 상세 로그 활성화
VERBOSE_LOGGING=true python create_weekly_report.py current

# 특정 티켓 디버깅
python create_weekly_report.py --debug-links IT-5332
```

#### 로그 분석
```bash
# 오늘 로그 확인
python3 log_manager.py today

# 실시간 로그 모니터링
python3 log_manager.py tail

# 로그 요약 확인
python3 log_manager.py summary
```

### 2. 환경 변수 디버깅

#### 환경 변수 확인
```bash
# 환경 변수 테스트
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('ATLASSIAN_URL:', os.getenv('ATLASSIAN_URL'))
print('LOG_LEVEL:', os.getenv('LOG_LEVEL'))
print('VERBOSE_LOGGING:', os.getenv('VERBOSE_LOGGING'))
"
```

### 3. API 연결 디버깅

#### Jira API 테스트
```python
# check_jira_fields.py 실행
python check_jira_fields.py

# 특정 필드 확인
python -c "
from create_weekly_report import jira
issue = jira.issue('IT-5332')
print('Fields:', issue.fields.__dict__.keys())
"
```

### 4. 성능 디버깅

#### 실행 시간 측정
```python
import time
import cProfile
import pstats

# 프로파일링 실행
def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 테스트할 함수 실행
    create_weekly_report()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
```

## 🚀 개발 워크플로우

### 1. TaskMaster AI 활용

#### 작업 관리
```bash
# 다음 작업 확인
task-master next

# 작업 상세 정보 확인
task-master show <id>

# 작업 완료 표시
task-master set-status --id=<id> --status=done

# 작업 진행 상황 업데이트
task-master update-subtask --id=<id> --prompt="구현 진행 상황"
```

#### 복잡한 작업 분해
```bash
# 작업을 세부 작업으로 분해
task-master expand --id=<id> --research --force

# 작업 복잡도 분석
task-master analyze-complexity --research
```

### 2. Git 워크플로우

#### 브랜치 관리
```bash
# 새로운 기능 브랜치 생성
git checkout -b feature/new-feature

# 개발 진행
git add .
git commit -m "feat: 새로운 기능 추가"

# 메인 브랜치로 병합
git checkout main
git merge feature/new-feature
```

#### 커밋 메시지 규칙
```bash
# 커밋 메시지 형식
git commit -m "feat: 새로운 기능 추가"
git commit -m "fix: 버그 수정"
git commit -m "docs: 문서 업데이트"
git commit -m "refactor: 코드 리팩토링"
git commit -m "test: 테스트 추가"
```

### 3. 코드 리뷰 프로세스

#### Pull Request 생성
```bash
# PR 생성
gh pr create --title "새로운 기능 추가" --body "구현 내용 설명"

# 리뷰 요청
gh pr request-review --reviewer username
```

#### 리뷰 체크리스트
- [ ] 코드가 요구사항을 만족하는가?
- [ ] 테스트가 충분한가?
- [ ] 문서가 업데이트되었는가?
- [ ] 성능에 영향을 주지 않는가?
- [ ] 보안 문제가 없는가?

## 📊 성능 최적화

### 1. 코드 최적화

#### 사용하지 않는 함수 제거
```python
# 제거된 함수들 (예시)
# - get_jira_issues_with_links()
# - format_jira_datetime()
# - load_deploy_ticket_links()
# - get_deployed_by_tickets()
```

#### 메모리 사용량 최적화
```python
# 대용량 데이터 처리 시 제너레이터 사용
def process_large_dataset(issues):
    for issue in issues:
        yield process_issue(issue)

# 리스트 컴프리헨션 대신 제너레이터 표현식 사용
processed_issues = (process_issue(issue) for issue in issues)
```

### 2. API 호출 최적화

#### 페이지네이션 활용
```python
# 페이지네이션 사용 (대용량 데이터)
python create_weekly_report.py current --pagination

# 페이지네이션 미사용 (빠른 실행)
python create_weekly_report.py current --no-pagination
```

#### 캐싱 구현
```python
import functools
import time

def cache_with_ttl(ttl_seconds=300):
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            current_time = time.time()
            
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl_seconds:
                    return result
            
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result
        
        return wrapper
    return decorator
```

### 3. 로그 최적화

#### 로그 레벨 조정
```bash
# 프로덕션 환경
LOG_LEVEL=INFO python create_weekly_report.py current

# 개발 환경
LOG_LEVEL=DEBUG python create_weekly_report.py current

# 문제 해결 시
LOG_LEVEL=WARNING python create_weekly_report.py current
```

#### 로그 파일 정리
```bash
# 오래된 로그 파일 정리
python3 log_manager.py cleanup --keep-days 30

# 로그 파일 크기 확인
du -sh logs/runtime/
```

## 🔧 문제 해결

### 1. 일반적인 문제들

#### Jira 연결 실패
```bash
# API 토큰 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ATLASSIAN_API_TOKEN:', '***' if os.getenv('ATLASSIAN_API_TOKEN') else 'NOT SET')"

# 네트워크 연결 확인
curl -I https://your-domain.atlassian.net

# 권한 확인
python check_jira_fields.py
```

#### Confluence 페이지 생성 실패
```bash
# Space Key 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('CONFLUENCE_SPACE_KEY:', os.getenv('CONFLUENCE_SPACE_KEY'))"

# 부모 페이지 ID 확인
python create_weekly_report.py --check-page
```

#### Slack 알림 전송 실패
```bash
# Webhook URL 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('SLACK_WEBHOOK_URL:', os.getenv('SLACK_WEBHOOK_URL'))"

# 테스트 메시지 전송
python test_emoji_notification.py
```

### 2. 성능 문제

#### 실행 시간이 오래 걸리는 경우
```bash
# 페이지네이션 비활성화
python create_weekly_report.py current --no-pagination

# 로그 레벨 조정
LOG_LEVEL=WARNING python create_weekly_report.py current

# 특정 기능만 테스트
python create_weekly_report.py --debug-links IT-5332
```

#### 메모리 사용량이 높은 경우
```bash
# 프로세스 모니터링
ps aux | grep python

# 메모리 사용량 확인
python -c "
import psutil
process = psutil.Process()
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

### 3. 로그 관련 문제

#### 로그 파일이 생성되지 않는 경우
```bash
# 로그 디렉토리 권한 확인
ls -la logs/runtime/

# 수동 로그 생성 테스트
python3 create_daily_log.py

# 로그 관리 유틸리티 테스트
python3 log_manager.py summary
```

#### 로그 파일이 너무 큰 경우
```bash
# 로그 파일 크기 확인
du -sh logs/runtime/*.log

# 오래된 로그 파일 정리
python3 log_manager.py cleanup --keep-days 7

# 로그 레벨 조정
export LOG_LEVEL=WARNING
```

## 📚 참고 자료

### 1. 공식 문서
- [Python 공식 문서](https://docs.python.org/)
- [Jira REST API 문서](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Confluence REST API 문서](https://developer.atlassian.com/cloud/confluence/rest/v1/)
- [Slack Webhook 문서](https://api.slack.com/messaging/webhooks)

### 2. 개발 도구
- [VS Code Python 확장](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [PyCharm Professional](https://www.jetbrains.com/pycharm/)
- [Cursor AI](https://cursor.sh/)

### 3. 테스트 도구
- [pytest 공식 문서](https://docs.pytest.org/)
- [Jest 공식 문서](https://jestjs.io/)

### 4. 성능 분석 도구
- [cProfile 문서](https://docs.python.org/3/library/profile.html)
- [memory_profiler](https://pypi.org/project/memory-profiler/)

---

**마지막 업데이트**: 2025년 1월
**버전**: 개발 가이드 v1.0
