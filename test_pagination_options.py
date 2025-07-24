#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
페이지네이션 옵션 테스트 스크립트

이 스크립트는 create_weekly_report.py의 페이지네이션 옵션을 테스트합니다.
"""

import subprocess
import sys
import time

def test_pagination_options():
    """페이지네이션 옵션을 테스트합니다."""
    
    print("=== 페이지네이션 옵션 테스트 ===\n")
    
    # 테스트할 명령어들
    test_commands = [
        {
            "name": "기본 실행 (페이지네이션 미사용)",
            "command": ["python", "create_weekly_report.py", "current"],
            "description": "기본적으로 페이지네이션이 비활성화되어야 합니다."
        },
        {
            "name": "페이지네이션 명시적 활성화",
            "command": ["python", "create_weekly_report.py", "current", "--pagination"],
            "description": "페이지네이션을 명시적으로 활성화합니다."
        },
        {
            "name": "페이지네이션 명시적 비활성화",
            "command": ["python", "create_weekly_report.py", "current", "--no-pagination"],
            "description": "페이지네이션을 명시적으로 비활성화합니다. (기본값)"
        },
        {
            "name": "다른 모드에서 페이지네이션 활성화",
            "command": ["python", "create_weekly_report.py", "create", "--pagination"],
            "description": "create 모드에서 페이지네이션을 활성화합니다."
        }
    ]
    
    for i, test in enumerate(test_commands, 1):
        print(f"테스트 {i}: {test['name']}")
        print(f"설명: {test['description']}")
        print(f"명령어: {' '.join(test['command'])}")
        print("-" * 50)
        
        try:
            start_time = time.time()
            result = subprocess.run(
                test['command'],
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )
            end_time = time.time()
            
            print(f"실행 시간: {end_time - start_time:.2f}초")
            print(f"종료 코드: {result.returncode}")
            
            if result.stdout:
                print("표준 출력:")
                print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            
            if result.stderr:
                print("오류 출력:")
                print(result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
            
            if result.returncode == 0:
                print("✅ 테스트 성공")
            else:
                print("❌ 테스트 실패")
                
        except subprocess.TimeoutExpired:
            print("⏰ 테스트 타임아웃 (5분 초과)")
        except Exception as e:
            print(f"❌ 테스트 실행 오류: {e}")
        
        print("\n" + "=" * 60 + "\n")

def test_help_option():
    """도움말 옵션을 테스트합니다."""
    print("=== 도움말 옵션 테스트 ===\n")
    
    try:
        result = subprocess.run(
            ["python", "create_weekly_report.py", "--help"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ 도움말 출력 성공")
            print("출력 내용:")
            print(result.stdout)
        else:
            print("❌ 도움말 출력 실패")
            print("오류:", result.stderr)
            
    except Exception as e:
        print(f"❌ 도움말 테스트 오류: {e}")

if __name__ == "__main__":
    print("페이지네이션 옵션 테스트를 시작합니다...\n")
    
    # 도움말 테스트
    test_help_option()
    print("\n" + "=" * 60 + "\n")
    
    # 페이지네이션 옵션 테스트
    test_pagination_options()
    
    print("테스트 완료!") 