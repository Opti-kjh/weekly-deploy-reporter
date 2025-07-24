# 일일 로그 파일 관리 시스템 설치 가이드

## 개요

이 시스템은 crontab에서 실행되는 주간 리포트 스크립트의 로그를 매일 새로운 파일로 관리합니다.

### 주요 기능

- 📅 **일일 로그 파일**: 매일 `cron_YYMMDD.log` 형식으로 새로운 로그 파일 생성
- 📊 **실행 정보 기록**: 시작/종료 시간, 종료 코드, 오류 정보 자동 기록
- 🗂️ **로그 관리**: 오래된 로그 파일 자동 정리 기능
- 📈 **모니터링**: 실시간 로그 모니터링 및 요약 정보 제공

## 설치 방법

### 1. 스크립트 파일 확인

다음 파일들이 프로젝트 루트에 생성되었는지 확인하세요:

```
weekly-deploy-reporter/
├── create_daily_log.py      # 일일 로그 생성 스크립트
├── log_manager.py           # 로그 관리 유틸리티
├── crontab_daily_logs.txt   # 새로운 crontab 설정 템플릿
└── DAILY_LOG_SETUP.md      # 이 가이드 문서
```

### 2. 스크립트 실행 권한 설정

```bash
chmod +x create_daily_log.py
chmod +x log_manager.py
```

### 3. 테스트 실행

새로운 로그 시스템이 정상 작동하는지 테스트합니다:

```bash
# 오늘 로그 파일 생성 테스트
python3 create_daily_log.py

# 로그 관리 유틸리티 테스트
python3 log_manager.py summary
```

### 4. Crontab 설정 변경

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

### 5. 설정 확인

```bash
# crontab 설정 확인
crontab -l

# 로그 디렉토리 확인
ls -la /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/
```

## 사용 방법

### 로그 파일 확인

#### 오늘 로그 파일 확인
```bash
# 오늘 로그 파일 경로
ls -la /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron_$(date +%y%m%d).log

# 로그 내용 확인
cat /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/cron_$(date +%y%m%d).log
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
```

#### 특정 날짜 로그 확인
```bash
# 어제 로그 확인
python3 log_manager.py tail --days 1

# 3일 전 로그 확인
python3 log_manager.py tail --days 3
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
```

## 로그 파일 구조

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
================================================================================
[스크립트 실행 출력 내용]
================================================================================
실행 종료: 2025-07-24 08:15:30
종료 코드: 0
================================================================================
```

## 문제 해결

### 1. 로그 파일이 생성되지 않는 경우

```bash
# 스크립트 실행 권한 확인
ls -la create_daily_log.py

# 수동으로 테스트 실행
python3 create_daily_log.py

# 로그 디렉토리 권한 확인
ls -la /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/
```

### 2. Crontab이 실행되지 않는 경우

```bash
# crontab 설정 확인
crontab -l

# crontab 로그 확인 (macOS)
sudo grep CRON /var/log/system.log

# 시스템 로그 확인
log show --predicate 'process == "cron"' --last 1h
```

### 3. 로그 파일이 너무 큰 경우

```bash
# 로그 파일 크기 확인
du -h /Users/eos/Desktop/weekly-deploy-reporter/logs/runtime/*.log

# 오래된 로그 파일 정리
python3 log_manager.py cleanup --keep-days 7
```

## 자동 정리 설정 (선택사항)

매주 일요일 새벽 2시에 오래된 로그 파일을 자동으로 정리하려면:

```bash
# crontab에 자동 정리 작업 추가
(crontab -l 2>/dev/null; echo "0 2 * * 0 /Users/eos/Desktop/weekly-deploy-reporter/venv/bin/python /Users/eos/Desktop/weekly-deploy-reporter/log_manager.py cleanup --keep-days 30") | crontab -
```

## 모니터링 스크립트 예시

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
else
    echo "❌ 오늘 로그 파일 없음"
fi

echo "📊 최근 로그 파일들:"
ls -la "$LOG_DIR"/cron_*.log | tail -5
```

## 주의사항

1. **백업**: 중요한 로그 파일은 정기적으로 백업하세요
2. **디스크 공간**: 로그 파일이 디스크 공간을 많이 차지할 수 있으므로 정기적으로 정리하세요
3. **권한**: 로그 디렉토리에 쓰기 권한이 있는지 확인하세요
4. **테스트**: 새로운 설정을 적용하기 전에 반드시 테스트하세요

## 지원

문제가 발생하거나 추가 기능이 필요한 경우:

1. 로그 파일을 확인하여 오류 메시지를 확인하세요
2. `log_manager.py`의 `summary` 명령어로 시스템 상태를 점검하세요
3. 수동으로 스크립트를 실행하여 문제를 진단하세요 