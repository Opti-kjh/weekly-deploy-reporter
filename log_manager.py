#!/usr/bin/env python3
"""
로그 파일 관리 유틸리티

이 스크립트는 일일 로그 파일들을 관리하고 모니터링하는 기능을 제공합니다.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import subprocess


class LogManager:
    """로그 파일 관리 클래스"""
    
    def __init__(self, log_dir="/Users/eos/Desktop/weekly-deploy-reporter/logs/runtime"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_today_log_file(self):
        """오늘 날짜의 로그 파일 경로를 반환합니다."""
        today = datetime.now()
        date_str = today.strftime("%y%m%d")
        return self.log_dir / f"cron_{date_str}.log"
    
    def list_log_files(self, days_back=7):
        """지정된 일수만큼의 최근 로그 파일들을 나열합니다."""
        log_files = []
        for i in range(days_back):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%y%m%d")
            log_file = self.log_dir / f"cron_{date_str}.log"
            if log_file.exists():
                stat = log_file.stat()
                log_files.append({
                    'file': log_file,
                    'date': date,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime)
                })
        
        return sorted(log_files, key=lambda x: x['date'], reverse=True)
    
    def show_log_summary(self, days_back=7):
        """로그 파일들의 요약 정보를 표시합니다."""
        log_files = self.list_log_files(days_back)
        
        print(f"\n📊 로그 파일 요약 (최근 {days_back}일)")
        print("=" * 80)
        
        if not log_files:
            print("❌ 로그 파일이 없습니다.")
            return
        
        total_size = 0
        for log_info in log_files:
            size_mb = log_info['size'] / (1024 * 1024)
            total_size += log_info['size']
            
            # 실행 횟수 계산 (구분선 개수로 추정)
            try:
                with open(log_info['file'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    executions = content.count('=' * 80) // 2  # 시작/종료 구분선
            except:
                executions = 0
            
            print(f"📅 {log_info['date'].strftime('%Y-%m-%d')} ({log_info['file'].name})")
            print(f"   📏 크기: {size_mb:.2f} MB")
            print(f"   🔄 실행 횟수: {executions}회")
            print(f"   📝 수정: {log_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
        total_size_mb = total_size / (1024 * 1024)
        print(f"📈 총 크기: {total_size_mb:.2f} MB")
        print(f"📁 로그 파일 수: {len(log_files)}개")
    
    def tail_log(self, days_back=0):
        """지정된 일수 전의 로그 파일을 tail로 모니터링합니다."""
        if days_back == 0:
            log_file = self.get_today_log_file()
        else:
            date = datetime.now() - timedelta(days=days_back)
            date_str = date.strftime("%y%m%d")
            log_file = self.log_dir / f"cron_{date_str}.log"
        
        if not log_file.exists():
            print(f"❌ 로그 파일이 존재하지 않습니다: {log_file}")
            return
        
        print(f"📋 로그 파일 모니터링: {log_file}")
        print("=" * 80)
        
        try:
            # tail -f 명령어로 실시간 모니터링
            process = subprocess.Popen(
                ['tail', '-f', str(log_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            print("실시간 로그 모니터링 중... (Ctrl+C로 종료)")
            for line in process.stdout:
                print(line.rstrip())
                
        except KeyboardInterrupt:
            print("\n🛑 모니터링을 종료합니다.")
            process.terminate()
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
    
    def cleanup_old_logs(self, days_to_keep=30):
        """지정된 일수보다 오래된 로그 파일들을 삭제합니다."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        deleted_size = 0
        
        for log_file in self.log_dir.glob("cron_*.log"):
            try:
                # 파일명에서 날짜 추출
                date_str = log_file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, "%y%m%d")
                
                if file_date < cutoff_date:
                    size = log_file.stat().st_size
                    log_file.unlink()
                    deleted_count += 1
                    deleted_size += size
                    print(f"🗑️  삭제: {log_file.name} ({size / 1024:.1f} KB)")
            except (ValueError, IndexError) as e:
                print(f"⚠️  파일명 파싱 오류 ({log_file.name}): {e}")
        
        if deleted_count > 0:
            deleted_size_mb = deleted_size / (1024 * 1024)
            print(f"\n✅ 총 {deleted_count}개 파일 삭제 완료")
            print(f"💾 절약된 공간: {deleted_size_mb:.2f} MB")
        else:
            print("✅ 삭제할 오래된 로그 파일이 없습니다.")
    
    def show_today_log(self):
        """오늘 로그 파일의 내용을 표시합니다."""
        log_file = self.get_today_log_file()
        
        if not log_file.exists():
            print(f"❌ 오늘 로그 파일이 없습니다: {log_file}")
            return
        
        print(f"📋 오늘 로그 파일: {log_file}")
        print("=" * 80)
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    print(content)
                else:
                    print("📝 로그 파일이 비어있습니다.")
        except Exception as e:
            print(f"❌ 로그 파일 읽기 오류: {e}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="로그 파일 관리 유틸리티")
    parser.add_argument('action', choices=['summary', 'tail', 'today', 'cleanup'], 
                       help='실행할 작업')
    parser.add_argument('--days', type=int, default=7, 
                       help='조회할 일수 (기본값: 7일)')
    parser.add_argument('--keep-days', type=int, default=30, 
                       help='보관할 로그 파일 일수 (기본값: 30일)')
    
    args = parser.parse_args()
    
    log_manager = LogManager()
    
    if args.action == 'summary':
        log_manager.show_log_summary(args.days)
    elif args.action == 'tail':
        log_manager.tail_log(args.days)
    elif args.action == 'today':
        log_manager.show_today_log()
    elif args.action == 'cleanup':
        log_manager.cleanup_old_logs(args.keep_days)


if __name__ == "__main__":
    main() 