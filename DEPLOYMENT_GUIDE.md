# Weekly Deploy Reporter - 배포 가이드

## 🚀 배포 환경 설정

### 1. 서버 요구사항

#### 시스템 요구사항
- **운영체제**: Ubuntu 20.04+, CentOS 7+, macOS 10.15+
- **Python**: 3.7 이상
- **Node.js**: 14.0 이상
- **메모리**: 최소 2GB RAM
- **디스크**: 최소 10GB 여유 공간
- **네트워크**: 인터넷 연결 (Jira, Confluence, Slack API 접근)

#### 권장 사양
- **CPU**: 2코어 이상
- **메모리**: 4GB RAM
- **디스크**: 20GB 여유 공간
- **네트워크**: 안정적인 인터넷 연결

### 2. 서버 초기 설정

#### Ubuntu/Debian 시스템
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl wget

# Python 가상환경 생성
python3 -m venv /opt/weekly-reporter/venv

# 프로젝트 디렉토리 생성
sudo mkdir -p /opt/weekly-reporter
sudo chown $USER:$USER /opt/weekly-reporter
```

#### CentOS/RHEL 시스템
```bash
# EPEL 저장소 활성화
sudo yum install -y epel-release

# 필수 패키지 설치
sudo yum install -y python3 python3-pip nodejs npm git curl wget

# Python 가상환경 생성
python3 -m venv /opt/weekly-reporter/venv

# 프로젝트 디렉토리 생성
sudo mkdir -p /opt/weekly-reporter
sudo chown $USER:$USER /opt/weekly-reporter
```

#### macOS 시스템
```bash
# Homebrew 설치 (없는 경우)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 필수 패키지 설치
brew install python3 node git

# Python 가상환경 생성
python3 -m venv /opt/weekly-reporter/venv

# 프로젝트 디렉토리 생성
sudo mkdir -p /opt/weekly-reporter
sudo chown $USER:$USER /opt/weekly-reporter
```

### 3. 프로젝트 배포

#### 코드 배포
```bash
# 프로젝트 디렉토리로 이동
cd /opt/weekly-reporter

# Git 저장소 클론
git clone https://github.com/your-username/weekly-deploy-reporter.git .

# 가상환경 활성화
source venv/bin/activate

# Python 의존성 설치
pip install -r requirements.txt

# Node.js 의존성 설치
npm install
```

#### 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env
```

#### 필수 환경 변수 설정
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

### 4. 권한 설정

#### 로그 디렉토리 생성
```bash
# 로그 디렉토리 생성
mkdir -p /opt/weekly-reporter/logs/runtime

# 권한 설정
chmod 755 /opt/weekly-reporter/logs/runtime
chown $USER:$USER /opt/weekly-reporter/logs/runtime
```

#### 실행 권한 설정
```bash
# 스크립트 실행 권한 설정
chmod +x /opt/weekly-reporter/create_weekly_report.py
chmod +x /opt/weekly-reporter/create_daily_log.py
chmod +x /opt/weekly-reporter/log_manager.py
```

## ⚙️ 자동화 설정

### 1. Crontab 설정

#### 기본 Crontab 설정
```bash
# Crontab 편집
crontab -e

# 다음 설정 추가
```

#### 주간 리포트 생성 (금요일 오전 9시 30분)
```bash
30 9 * * 5 /opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_weekly_report.py create >> /opt/weekly-reporter/logs/runtime/cron.log 2>&1
```

#### 일일 업데이트 (월~금 오전 9시~오후 8시, 15분마다)
```bash
15,30,45,0 8-21 * * 1-5 /opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_weekly_report.py update >> /opt/weekly-reporter/logs/runtime/cron.log 2>&1
```

#### 배포 티켓 업데이트 (화요일, 수요일 오전 11시, 오후 2시, 5분마다)
```bash
5,10,15,20,25,30,35,40,45,50,55 11,14 * * 2,3 /opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_weekly_report.py update >> /opt/weekly-reporter/logs/runtime/cron.log 2>&1
```

#### 로그 정리 (일요일 새벽 2시)
```bash
0 2 * * 0 /opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/log_manager.py cleanup --keep-days 30 >> /opt/weekly-reporter/logs/runtime/cron.log 2>&1
```

### 2. 시스템 서비스 설정

#### Systemd 서비스 생성
```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/weekly-reporter.service
```

#### 서비스 파일 내용
```ini
[Unit]
Description=Weekly Deploy Reporter
After=network.target

[Service]
Type=simple
User=weekly-reporter
WorkingDirectory=/opt/weekly-reporter
Environment=PATH=/opt/weekly-reporter/venv/bin
ExecStart=/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_weekly_report.py update
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
```

#### 서비스 활성화
```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable weekly-reporter
sudo systemctl start weekly-reporter

# 서비스 상태 확인
sudo systemctl status weekly-reporter
```

### 3. 모니터링 스크립트

#### 상태 확인 스크립트
```bash
#!/bin/bash
# /opt/weekly-reporter/scripts/health_check.sh

LOG_DIR="/opt/weekly-reporter/logs/runtime"
TODAY=$(date +%y%m%d)
LOG_FILE="$LOG_DIR/cron_$TODAY.log"

echo "=== Weekly Reporter Health Check ==="
echo "Date: $(date)"
echo ""

# 1. 프로세스 확인
if pgrep -f "create_weekly_report.py" > /dev/null; then
    echo "✅ 프로세스 실행 중"
else
    echo "❌ 프로세스 중단됨"
fi

# 2. 로그 파일 확인
if [ -f "$LOG_FILE" ]; then
    echo "✅ 오늘 로그 파일 존재"
    echo "📏 크기: $(du -h "$LOG_FILE" | cut -f1)"
    echo "🔄 실행 횟수: $(grep -c "실행 시작" "$LOG_FILE")"
    echo "❌ 오류 횟수: $(grep -c "종료 코드: [^0]" "$LOG_FILE")"
else
    echo "❌ 오늘 로그 파일 없음"
fi

# 3. 디스크 사용량 확인
echo ""
echo "💾 디스크 사용량:"
du -sh /opt/weekly-reporter/logs/runtime/

# 4. 최근 로그 확인
echo ""
echo "📊 최근 로그:"
tail -5 "$LOG_FILE" 2>/dev/null || echo "로그 파일 없음"
```

#### 알림 스크립트
```bash
#!/bin/bash
# /opt/weekly-reporter/scripts/alert.sh

WEBHOOK_URL="YOUR_SLACK_WEBHOOK_URL"
MESSAGE="Weekly Reporter 상태 알림"

# 상태 확인
if ! pgrep -f "create_weekly_report.py" > /dev/null; then
    MESSAGE="🚨 Weekly Reporter 프로세스가 중단되었습니다!"
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"$MESSAGE\"}" \
        "$WEBHOOK_URL"
fi
```

## 📊 모니터링 및 로깅

### 1. 로그 관리

#### 로그 레벨 설정
```bash
# 프로덕션 환경 (기본값)
export LOG_LEVEL=INFO

# 개발 환경
export LOG_LEVEL=DEBUG

# 문제 해결 시
export LOG_LEVEL=WARNING
```

#### 로그 모니터링
```bash
# 실시간 로그 모니터링
tail -f /opt/weekly-reporter/logs/runtime/cron_$(date +%y%m%d).log

# 로그 요약 확인
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/log_manager.py summary

# 오늘 로그 확인
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/log_manager.py today
```

### 2. 성능 모니터링

#### 시스템 리소스 모니터링
```bash
# CPU 및 메모리 사용량 확인
top -p $(pgrep -f "create_weekly_report.py")

# 디스크 사용량 확인
df -h /opt/weekly-reporter/

# 네트워크 연결 확인
netstat -an | grep :443
```

#### 실행 시간 측정
```bash
# 실행 시간 측정
time /opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_weekly_report.py current

# 성능 프로파일링
python -m cProfile -o profile.stats /opt/weekly-reporter/create_weekly_report.py current
```

### 3. 알림 설정

#### Slack 알림 설정
```bash
# 성공 알림
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"✅ Weekly Reporter 실행 완료"}' \
    "$SLACK_WEBHOOK_URL"

# 오류 알림
curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"❌ Weekly Reporter 실행 실패"}' \
    "$SLACK_WEBHOOK_URL"
```

#### 이메일 알림 설정
```bash
# 이메일 알림 스크립트
#!/bin/bash
# /opt/weekly-reporter/scripts/email_alert.sh

RECIPIENT="admin@yourcompany.com"
SUBJECT="Weekly Reporter Status"
BODY="Weekly Reporter가 성공적으로 실행되었습니다."

echo "$BODY" | mail -s "$SUBJECT" "$RECIPIENT"
```

## 🔧 문제 해결

### 1. 일반적인 배포 문제

#### 권한 문제
```bash
# 파일 권한 확인
ls -la /opt/weekly-reporter/

# 권한 수정
chmod 755 /opt/weekly-reporter/
chmod +x /opt/weekly-reporter/*.py

# 소유자 변경
sudo chown -R weekly-reporter:weekly-reporter /opt/weekly-reporter/
```

#### 환경 변수 문제
```bash
# 환경 변수 확인
source /opt/weekly-reporter/venv/bin/activate
python -c "
import os
from dotenv import load_dotenv
load_dotenv('/opt/weekly-reporter/.env')
print('ATLASSIAN_URL:', os.getenv('ATLASSIAN_URL'))
print('LOG_LEVEL:', os.getenv('LOG_LEVEL'))
"
```

#### 네트워크 연결 문제
```bash
# Jira 연결 확인
curl -I https://your-domain.atlassian.net

# DNS 확인
nslookup your-domain.atlassian.net

# 방화벽 확인
sudo ufw status
```

### 2. 성능 문제

#### 실행 시간이 오래 걸리는 경우
```bash
# 페이지네이션 비활성화
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_weekly_report.py current --no-pagination

# 로그 레벨 조정
LOG_LEVEL=WARNING /opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_weekly_report.py current

# 메모리 사용량 확인
ps aux | grep create_weekly_report.py
```

#### 메모리 부족 문제
```bash
# 메모리 사용량 확인
free -h

# 스왑 공간 확인
swapon --show

# 프로세스 메모리 사용량
ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%mem | head -10
```

### 3. 로그 관련 문제

#### 로그 파일이 생성되지 않는 경우
```bash
# 로그 디렉토리 권한 확인
ls -la /opt/weekly-reporter/logs/runtime/

# 수동 로그 생성 테스트
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_daily_log.py

# 로그 관리 유틸리티 테스트
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/log_manager.py summary
```

#### 로그 파일이 너무 큰 경우
```bash
# 로그 파일 크기 확인
du -sh /opt/weekly-reporter/logs/runtime/*.log

# 오래된 로그 파일 정리
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/log_manager.py cleanup --keep-days 7

# 로그 로테이션 설정
sudo nano /etc/logrotate.d/weekly-reporter
```

### 4. Crontab 문제

#### Crontab이 실행되지 않는 경우
```bash
# Crontab 서비스 상태 확인
sudo systemctl status cron

# Crontab 로그 확인
sudo grep CRON /var/log/syslog

# 수동 실행 테스트
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/create_weekly_report.py current
```

#### 환경 변수 문제
```bash
# Crontab 환경 변수 설정
crontab -e

# 다음 내용 추가
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=/opt/weekly-reporter
```

## 🔄 업데이트 및 유지보수

### 1. 코드 업데이트

#### 자동 업데이트 스크립트
```bash
#!/bin/bash
# /opt/weekly-reporter/scripts/update.sh

cd /opt/weekly-reporter

# 현재 상태 백업
cp -r . ../weekly-reporter-backup-$(date +%Y%m%d)

# Git에서 최신 코드 가져오기
git pull origin main

# 의존성 업데이트
source venv/bin/activate
pip install -r requirements.txt

# 테스트 실행
python -m pytest tests/ -v

# 서비스 재시작
sudo systemctl restart weekly-reporter

echo "업데이트 완료: $(date)"
```

#### 롤백 스크립트
```bash
#!/bin/bash
# /opt/weekly-reporter/scripts/rollback.sh

BACKUP_DATE=$1
BACKUP_DIR="../weekly-reporter-backup-$BACKUP_DATE"

if [ -d "$BACKUP_DIR" ]; then
    cd /opt/weekly-reporter
    
    # 현재 상태 백업
    cp -r . ../weekly-reporter-current-$(date +%Y%m%d)
    
    # 이전 버전으로 복원
    cp -r $BACKUP_DIR/* .
    
    # 서비스 재시작
    sudo systemctl restart weekly-reporter
    
    echo "롤백 완료: $BACKUP_DATE"
else
    echo "백업 디렉토리를 찾을 수 없습니다: $BACKUP_DATE"
fi
```

### 2. 정기 유지보수

#### 일일 점검
```bash
#!/bin/bash
# /opt/weekly-reporter/scripts/daily_check.sh

echo "=== 일일 점검 시작 ==="
date

# 1. 프로세스 상태 확인
if pgrep -f "create_weekly_report.py" > /dev/null; then
    echo "✅ 프로세스 정상"
else
    echo "❌ 프로세스 중단"
fi

# 2. 로그 파일 확인
TODAY_LOG="/opt/weekly-reporter/logs/runtime/cron_$(date +%y%m%d).log"
if [ -f "$TODAY_LOG" ]; then
    echo "✅ 로그 파일 정상"
else
    echo "❌ 로그 파일 없음"
fi

# 3. 디스크 사용량 확인
DISK_USAGE=$(df /opt/weekly-reporter/ | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "✅ 디스크 사용량 정상: ${DISK_USAGE}%"
else
    echo "⚠️ 디스크 사용량 높음: ${DISK_USAGE}%"
fi

echo "=== 일일 점검 완료 ==="
```

#### 주간 점검
```bash
#!/bin/bash
# /opt/weekly-reporter/scripts/weekly_check.sh

echo "=== 주간 점검 시작 ==="
date

# 1. 성능 통계
echo "📊 성능 통계:"
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/log_manager.py summary --days 7

# 2. 오류 분석
echo "🔍 오류 분석:"
grep -r "ERROR\|CRITICAL" /opt/weekly-reporter/logs/runtime/ | wc -l

# 3. 리소스 사용량
echo "💾 리소스 사용량:"
df -h /opt/weekly-reporter/
free -h

# 4. 로그 정리
echo "🧹 로그 정리:"
/opt/weekly-reporter/venv/bin/python /opt/weekly-reporter/log_manager.py cleanup --keep-days 30

echo "=== 주간 점검 완료 ==="
```

### 3. 백업 및 복구

#### 자동 백업 스크립트
```bash
#!/bin/bash
# /opt/weekly-reporter/scripts/backup.sh

BACKUP_DIR="/opt/backups/weekly-reporter"
DATE=$(date +%Y%m%d_%H%M%S)

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# 코드 백업
tar -czf $BACKUP_DIR/weekly-reporter-code-$DATE.tar.gz /opt/weekly-reporter/

# 설정 파일 백업
cp /opt/weekly-reporter/.env $BACKUP_DIR/env-$DATE.backup

# 로그 백업
tar -czf $BACKUP_DIR/weekly-reporter-logs-$DATE.tar.gz /opt/weekly-reporter/logs/

# 오래된 백업 정리 (30일 이상)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.backup" -mtime +30 -delete

echo "백업 완료: $DATE"
```

#### 복구 스크립트
```bash
#!/bin/bash
# /opt/weekly-reporter/scripts/restore.sh

BACKUP_FILE=$1
RESTORE_DIR="/opt/weekly-reporter-restore"

if [ -z "$BACKUP_FILE" ]; then
    echo "사용법: $0 <백업파일>"
    exit 1
fi

# 복구 디렉토리 생성
mkdir -p $RESTORE_DIR

# 백업 파일 압축 해제
tar -xzf $BACKUP_FILE -C $RESTORE_DIR

# 현재 상태 백업
cp -r /opt/weekly-reporter /opt/weekly-reporter-backup-$(date +%Y%m%d)

# 복구 실행
cp -r $RESTORE_DIR/opt/weekly-reporter/* /opt/weekly-reporter/

# 권한 설정
chmod +x /opt/weekly-reporter/*.py
chown -R weekly-reporter:weekly-reporter /opt/weekly-reporter/

# 서비스 재시작
sudo systemctl restart weekly-reporter

echo "복구 완료: $BACKUP_FILE"
```

## 📚 참고 자료

### 1. 시스템 관리
- [Ubuntu Server Guide](https://ubuntu.com/server/docs)
- [CentOS System Administration](https://docs.centos.org/)
- [Systemd Service Management](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

### 2. 모니터링 도구
- [Prometheus](https://prometheus.io/)
- [Grafana](https://grafana.com/)
- [Nagios](https://www.nagios.org/)

### 3. 로그 관리
- [Logrotate](https://linux.die.net/man/8/logrotate)
- [rsyslog](https://www.rsyslog.com/)

### 4. 백업 도구
- [rsync](https://rsync.samba.org/)
- [tar](https://www.gnu.org/software/tar/)
- [cron](https://man7.org/linux/man-pages/man8/cron.8.html)

---

**마지막 업데이트**: 2025년 1월
**버전**: 배포 가이드 v1.0
