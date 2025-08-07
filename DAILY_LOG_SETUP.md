# 일일 로그 파일 관리 시스템 설치 가이드

## 📋 개요

이 시스템은 crontab에서 실행되는 주간 리포트 스크립트의 로그를 매일 새로운 파일로 관리합니다.

### 🚀 주요 기능

- 📅 **일일 로그 파일**: 매일 `cron_YYMMDD.log` 형식으로 새로운 로그 파일 생성
- 📊 **실행 정보 기록**: 시작/종료 시간, 종료 코드, 오류 정보 자동 기록
- 🗂️ **로그 관리**: 오래된 로그 파일 자동 정리 기능
- 📈 **모니터링**: 실시간 로그 모니터링 및 요약 정보 제공
- 🔧 **로그 레벨 제어**: 환경 변수를 통한 로그 출력 제어
- 📝 **상세 로그**: VERBOSE_LOGGING 옵션으로 상세한 디버깅 정보 제공

## 🛠️ 설치 방법

### 1. 스크립트 파일 확인

다음 파일들이 프로젝트 루트에 생성되었는지 확인하세요:

```
weekly-deploy-reporter/
├── create_daily_log.py      # 일일 로그 생성 스크립트
├── log_manager.py           # 로그 관리 유틸리티
├── crontab_daily_logs.txt   # 새로운 crontab 설정 템플릿
├── crontab_new_setting.txt  # 기존 crontab 설정 (백업용)
└── DAILY_LOG_SETUP.md      # 이 가이드 문서
```

### 2. 스크립트 실행 권한 설정

```bash
chmod +x create_daily_log.py
chmod +x log_manager.py
```

### 3. 로그 디렉토리 생성

```bash
# 로그 디렉토리 생성
mkdir -p logs/runtime

# 권한 설정
chmod 755 logs/runtime
```

### 4. 테스트 실행

새로운 로그 시스템이 정상 작동하는지 테스트합니다:

```bash
# 오늘 로그 파일 생성 테스트
python3 create_daily_log.py

# 로그 관리 유틸리티 테스트
python3 log_manager.py summary

# 실시간 로그 모니터링 테스트
python3 log_manager.py tail
```

### 5. Crontab 설정 변경

#### 현재 crontab 확인
```bash
crontab -l
```

#### 기존 설정 백업 (선택사항)
```bash
crontab -l > crontab_backup.txt
```

#### 새로운 설정 적용

**방법 1: 기존 설정 유지하면서 추가**
```bash
# 기존 crontab에 새 설정 추가
(crontab -l 2>/dev/null; echo "15,30,45,0 8-21 * * 1-5 /Users/eos/Desktop/weekly-deploy-reporter/venv/bin/python /Users/eos/Desktop/weekly-deploy-reporter/create_daily_log.py") | crontab -
```

**방법 2: 완전히 새로운 설정으로 교체**
```bash
# 기존 설정 제거 (주의: 모든 crontab 설정이 삭제됩니다)
crontab -r

# 새 설정 추가
crontab crontab_daily_logs.txt
```

### 6. 설정 확인

```bash
# crontab 설정 확인
crontab -l

# 로그 디렉토리 확인
ls -la /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/

# 오늘 로그 파일 확인
ls -la /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron_$(date +%y%m%d).log
```

## 📖 사용 방법

### 로그 파일 확인

#### 오늘 로그 파일 확인
```bash
# 오늘 로그 파일 경로
ls -la /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron_$(date +%y%m%d).log

# 로그 내용 확인
cat /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron_$(date +%y%m%d).log

# 또는 로그 관리 유틸리티 사용
python3 log_manager.py today
```

#### 실시간 로그 모니터링
```bash
# 오늘 로그 실시간 모니터링
tail -f /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron_$(date +%y%m%d).log

# 또는 로그 관리 유틸리티 사용
python3 log_manager.py tail
```

### 로그 관리 유틸리티 사용

#### 로그 요약 정보 확인
```bash
# 최근 7일 로그 요약
python3 log_manager.py summary

# 최근 30일 로그 요약
python3 log_manager.py summary --days 30

# 특정 날짜 범위 로그 요약
python3 log_manager.py summary --days 14
```

#### 특정 날짜 로그 확인
```bash
# 어제 로그 확인
python3 log_manager.py tail --days 1

# 3일 전 로그 확인
python3 log_manager.py tail --days 3

# 특정 날짜 로그 확인 (YYYY-MM-DD 형식)
python3 log_manager.py tail --date 2025-01-15
```

#### 오늘 로그 내용 확인
```bash
python3 log_manager.py today
```

#### 오래된 로그 파일 정리
```bash
# 30일보다 오래된 로그 파일 삭제
python3 log_manager.py cleanup

# 60일보다 오래된 로그 파일 삭제
python3 log_manager.py cleanup --keep-days 60

# 정리 전 미리보기 (실제 삭제하지 않음)
python3 log_manager.py cleanup --dry-run
```

### 환경 변수 제어

#### 로그 레벨 설정
```bash
# DEBUG 레벨로 실행
LOG_LEVEL=DEBUG python create_weekly_report.py current

# WARNING 레벨로 실행
LOG_LEVEL=WARNING python create_weekly_report.py current

# 기본값 (INFO)
python create_weekly_report.py current
```

#### 상세 로그 활성화
```bash
# 상세 로그 활성화
VERBOSE_LOGGING=true python create_weekly_report.py current

# 상세 로그 비활성화 (기본값)
VERBOSE_LOGGING=false python create_weekly_report.py current
```

## 📁 로그 파일 구조

### 파일명 형식
```
cron_YYMMDD.log
```
예시:
- `cron_250724.log` (2025년 7월 24일)
- `cron_250725.log` (2025년 7월 25일)

### 로그 내용 구조
```
================================================================================
실행 시작: 2025-07-24 08:15:00
명령어: /Users/eos/Desktop/weekly-deploy-reporter/venv/bin/python /Users/eos/Desktop/weekly-deploy-reporter/create_weekly_report.py update
환경 변수: LOG_LEVEL=INFO, VERBOSE_LOGGING=false
================================================================================
[스크립트 실행 출력 내용]
================================================================================
실행 종료: 2025-07-24 08:15:30
종료 코드: 0
실행 시간: 30초
================================================================================
```

### 로그 레벨별 출력 내용

| 로그 레벨 | 출력 내용 | 사용 시기 |
|-----------|----------|-----------|
| **DEBUG** | 모든 디버깅 정보, API 호출 상세, 변수 값 등 | 개발/디버깅 시 |
| **INFO** | 일반적인 실행 정보, 주요 단계별 진행 상황 | 일반 운영 시 (기본값) |
| **WARNING** | 경고 메시지만 | 문제 해결 시 |
| **ERROR** | 오류 메시지만 | 오류 발생 시 |
| **CRITICAL** | 심각한 오류 메시지만 | 시스템 장애 시 |

## 🔧 고급 설정

### 자동 정리 설정 (선택사항)

매주 일요일 새벽 2시에 오래된 로그 파일을 자동으로 정리하려면:

```bash
# crontab에 자동 정리 작업 추가
(crontab -l 2>/dev/null; echo "0 2 * * 0 /Users/eos/Desktop/weekly-deploy-reporter/venv/bin/python /Users/eos/Desktop/weekly-deploy-reporter/log_manager.py cleanup --keep-days 30") | crontab -
```

### 로그 모니터링 스크립트

로그 파일 상태를 주기적으로 확인하는 스크립트:

```bash
#!/bin/bash
# log_monitor.sh

LOG_DIR="/Users/eos/Desktop/weekly-deploy-reporter/logs/runtime"
TODAY=$(date +%y%m%d)
LOG_FILE="$LOG_DIR/cron_$TODAY.log"

echo "=== 로그 파일 모니터링 ==="
echo "날짜: $(date)"
echo "로그 파일: $LOG_FILE"

if [ -f "$LOG_FILE" ]; then
    echo "✅ 오늘 로그 파일 존재"
    echo "📏 파일 크기: $(du -h "$LOG_FILE" | cut -f1)"
    echo "🔄 실행 횟수: $(grep -c "실행 시작" "$LOG_FILE")"
    echo "❌ 오류 횟수: $(grep -c "종료 코드: [^0]" "$LOG_FILE")"
else
    echo "❌ 오늘 로그 파일 없음"
fi

echo "📊 최근 로그 파일들:"
ls -la "$LOG_DIR"/cron_*.log | tail -5

echo "💾 디스크 사용량:"
du -sh "$LOG_DIR"
```

### 로그 분석 스크립트

로그 파일에서 유용한 정보를 추출하는 스크립트:

```bash
#!/bin/bash
# log_analyzer.sh

LOG_DIR="/Users/eos/Desktop/weekly-deploy-reporter/logs/runtime"
DAYS=${1:-7}

echo "=== 로그 분석 리포트 ==="
echo "분석 기간: 최근 $DAYS일"
echo "분석 시간: $(date)"
echo ""

# 실행 성공률 계산
TOTAL_RUNS=0
SUCCESSFUL_RUNS=0

for i in $(seq 0 $((DAYS-1))); do
    DATE=$(date -d "$i days ago" +%y%m%d)
    LOG_FILE="$LOG_DIR/cron_$DATE.log"
    
    if [ -f "$LOG_FILE" ]; then
        RUNS=$(grep -c "실행 시작" "$LOG_FILE")
        SUCCESSES=$(grep -c "종료 코드: 0" "$LOG_FILE")
        TOTAL_RUNS=$((TOTAL_RUNS + RUNS))
        SUCCESSFUL_RUNS=$((SUCCESSFUL_RUNS + SUCCESSES))
        
        echo "📅 $DATE: $SUCCESSES/$RUNS 성공"
    fi
done

echo ""
echo "📈 전체 성공률: $SUCCESSFUL_RUNS/$TOTAL_RUNS ($((SUCCESSFUL_RUNS * 100 / TOTAL_RUNS))%)"
```

## 🚨 문제 해결

### 1. 로그 파일이 생성되지 않는 경우

```bash
# 스크립트 실행 권한 확인
ls -la create_daily_log.py

# 수동으로 테스트 실행
python3 create_daily_log.py

# 로그 디렉토리 권한 확인
ls -la /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/

# 환경 변수 확인
echo "LOG_LEVEL: $LOG_LEVEL"
echo "VERBOSE_LOGGING: $VERBOSE_LOGGING"
```

### 2. Crontab이 실행되지 않는 경우

```bash
# crontab 설정 확인
crontab -l

# crontab 로그 확인 (macOS)
sudo grep CRON /var/log/system.log

# 시스템 로그 확인
log show --predicate 'process == "cron"' --last 1h

# crontab 서비스 상태 확인
sudo launchctl list | grep cron
```

### 3. 로그 파일이 너무 큰 경우

```bash
# 로그 파일 크기 확인
du -h /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/*.log

# 오래된 로그 파일 정리
python3 log_manager.py cleanup --keep-days 7

# 로그 레벨 조정 (INFO로 설정)
export LOG_LEVEL=INFO
```

### 4. 로그 관리 유틸리티 오류

```bash
# Python 경로 확인
which python3

# 의존성 확인
python3 -c "import json, os, sys; print('의존성 OK')"

# 권한 확인
ls -la log_manager.py
```

### 5. 환경 변수 문제

```bash
# .env 파일 확인
cat .env | grep -E "(LOG_LEVEL|VERBOSE_LOGGING)"

# 환경 변수 테스트
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'LOG_LEVEL: {os.getenv(\"LOG_LEVEL\", \"INFO\")}')
print(f'VERBOSE_LOGGING: {os.getenv(\"VERBOSE_LOGGING\", \"false\")}')
"
```

## 📊 모니터링 대시보드

### 일일 모니터링 체크리스트

```bash
#!/bin/bash
# daily_monitor.sh

echo "=== 일일 모니터링 체크리스트 ==="
echo "날짜: $(date)"
echo ""

# 1. 오늘 로그 파일 존재 확인
TODAY_LOG="/Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron_$(date +%y%m%d).log"
if [ -f "$TODAY_LOG" ]; then
    echo "✅ 오늘 로그 파일 존재"
    echo "📏 크기: $(du -h "$TODAY_LOG" | cut -f1)"
else
    echo "❌ 오늘 로그 파일 없음"
fi

# 2. 최근 실행 상태 확인
echo ""
echo "📊 최근 실행 상태:"
python3 log_manager.py summary --days 1

# 3. 디스크 사용량 확인
echo ""
echo "💾 디스크 사용량:"
du -sh /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/

# 4. 오래된 로그 파일 확인
echo ""
echo "🗑️ 오래된 로그 파일:"
find /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/ -name "cron_*.log" -mtime +30 | wc -l | xargs echo "30일 이상:"
```

## 🔄 마이그레이션 가이드

### 기존 시스템에서 새 로그 시스템으로 전환

#### 1단계: 기존 설정 백업
```bash
# 현재 crontab 백업
crontab -l > crontab_old_backup.txt

# 기존 로그 파일 백업
mkdir -p logs/backup
cp cron*.log logs/backup/ 2>/dev/null || true
```

#### 2단계: 새 시스템 설치
```bash
# 로그 디렉토리 생성
mkdir -p logs/runtime

# 스크립트 권한 설정
chmod +x create_daily_log.py log_manager.py
```

#### 3단계: 테스트 실행
```bash
# 새 로그 시스템 테스트
python3 create_daily_log.py

# 로그 관리 유틸리티 테스트
python3 log_manager.py summary
```

#### 4단계: Crontab 업데이트
```bash
# 새 설정 적용
crontab crontab_daily_logs.txt

# 설정 확인
crontab -l
```

#### 5단계: 검증
```bash
# 로그 파일 생성 확인
ls -la logs/runtime/

# 실행 테스트
python3 create_weekly_report.py current
```

## 📚 관련 문서

- [README.md](README.md) - 프로젝트 전체 개요
- [create_weekly_report_process_diagram.md](create_weekly_report_process_diagram.md) - 프로세스 다이어그램
- [code_cleanup_summary.md](code_cleanup_summary.md) - 코드 정리 보고서
- [log_manager.py](log_manager.py) - 로그 관리 유틸리티 소스 코드
- [create_daily_log.py](create_daily_log.py) - 일일 로그 생성 스크립트 소스 코드

## ⚠️ 주의사항

1. **백업**: 중요한 로그 파일은 정기적으로 백업하세요
2. **디스크 공간**: 로그 파일이 디스크 공간을 많이 차지할 수 있으므로 정기적으로 정리하세요
3. **권한**: 로그 디렉토리에 쓰기 권한이 있는지 확인하세요
4. **테스트**: 새로운 설정을 적용하기 전에 반드시 테스트하세요
5. **환경 변수**: LOG_LEVEL과 VERBOSE_LOGGING 설정을 적절히 조정하세요

## 🆘 지원

문제가 발생하거나 추가 기능이 필요한 경우:

1. 로그 파일을 확인하여 오류 메시지를 확인하세요
2. `log_manager.py`의 `summary` 명령어로 시스템 상태를 점검하세요
3. 수동으로 스크립트를 실행하여 문제를 진단하세요
4. 환경 변수 설정을 확인하세요
5. 프로젝트 담당자(김종호:kjh@deali.net)에게 문의하세요

---

**마지막 업데이트**: 2025년 1월
**최신 버전**: 로그 레벨 제어, 상세 로그 기능, 자동 정리 기능 추가 