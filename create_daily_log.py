#!/usr/bin/env python3
"""
일일 로그 파일 생성 및 관리 스크립트

이 스크립트는 매일 새로운 로그 파일을 생성하고,
crontab에서 실행되는 스크립트의 출력을 해당 날짜의 로그 파일로 리다이렉트합니다.
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path


def get_daily_log_filename():
    """
    오늘 날짜를 기반으로 로그 파일명을 생성합니다.
    
    Returns:
        str: YYMMDD 형식의 로그 파일명 (예: cron_250724.log)
    """
    today = datetime.now()
    date_str = today.strftime("%y%m%d")
    return f"cron_{date_str}.log"


def ensure_log_directory():
    """
    로그 디렉토리가 존재하는지 확인하고, 없으면 생성합니다.
    """
    log_dir = Path("/Users/eos/Desktop/weekly-deploy-reporter/logs/runtime")
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def create_daily_log_file():
    """
    오늘 날짜의 로그 파일을 생성하고 경로를 반환합니다.
    
    Returns:
        Path: 생성된 로그 파일의 전체 경로
    """
    log_dir = ensure_log_directory()
    log_filename = get_daily_log_filename()
    log_file_path = log_dir / log_filename
    
    # 로그 파일이 없으면 생성 (빈 파일)
    if not log_file_path.exists():
        log_file_path.touch()
        print(f"새로운 로그 파일이 생성되었습니다: {log_file_path}")
    
    return log_file_path


def run_weekly_report_with_logging():
    """
    주간 리포트 스크립트를 실행하고 결과를 일일 로그 파일에 기록합니다.
    """
    log_file_path = create_daily_log_file()
    
    # 실행할 스크립트 경로
    script_path = "/Users/eos/Desktop/weekly-deploy-reporter/create_weekly_report.py"
    venv_python = "/Users/eos/Desktop/weekly-deploy-reporter/venv/bin/python"
    
    # 명령어 구성
    command = [venv_python, script_path, "update"]
    
    try:
        # 로그 파일에 실행 시작 시간 기록
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"\n{'='*80}\n")
            log_file.write(f"실행 시작: {start_time}\n")
            log_file.write(f"명령어: {' '.join(command)}\n")
            log_file.write(f"{'='*80}\n")
        
        # 스크립트 실행 및 로그 파일에 출력 리다이렉트
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 실시간으로 출력을 로그 파일에 기록
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()  # 즉시 파일에 쓰기
            
            process.wait()
            
            # 실행 종료 시간 기록
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            exit_code = process.returncode
            log_file.write(f"\n{'='*80}\n")
            log_file.write(f"실행 종료: {end_time}\n")
            log_file.write(f"종료 코드: {exit_code}\n")
            log_file.write(f"{'='*80}\n")
        
        return exit_code
        
    except Exception as e:
        # 오류 발생 시 로그 파일에 기록
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            error_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"\n{'='*80}\n")
            log_file.write(f"오류 발생: {error_time}\n")
            log_file.write(f"오류 내용: {str(e)}\n")
            log_file.write(f"{'='*80}\n")
        
        print(f"오류가 발생했습니다: {e}", file=sys.stderr)
        return 1


def cleanup_old_logs(days_to_keep=30):
    """
    지정된 일수보다 오래된 로그 파일들을 삭제합니다.
    
    Args:
        days_to_keep (int): 보관할 로그 파일의 일수 (기본값: 30일)
    """
    from datetime import timedelta
    
    log_dir = Path("/Users/eos/Desktop/weekly-deploy-reporter/logs/runtime")
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    deleted_count = 0
    for log_file in log_dir.glob("cron_*.log"):
        try:
            # 파일명에서 날짜 추출 (cron_YYMMDD.log 형식)
            date_str = log_file.stem.split('_')[1]  # YYMMDD 부분
            file_date = datetime.strptime(date_str, "%y%m%d")
            
            if file_date < cutoff_date:
                log_file.unlink()
                deleted_count += 1
                print(f"오래된 로그 파일 삭제: {log_file.name}")
        except (ValueError, IndexError) as e:
            print(f"로그 파일명 파싱 오류 ({log_file.name}): {e}")
    
    if deleted_count > 0:
        print(f"총 {deleted_count}개의 오래된 로그 파일이 삭제되었습니다.")


def main():
    """
    메인 함수: 주간 리포트 실행 및 로그 관리
    """
    print(f"일일 로그 관리 스크립트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 오래된 로그 파일 정리 (선택적)
    # cleanup_old_logs(days_to_keep=30)
    
    # 주간 리포트 실행
    exit_code = run_weekly_report_with_logging()
    
    print(f"스크립트 실행 완료. 종료 코드: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 