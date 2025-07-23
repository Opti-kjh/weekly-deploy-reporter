#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jira 필드 정보 조회 스크립트
customfield_10817 필드의 정확한 정보를 확인합니다.
"""

import os
import sys
from dotenv import load_dotenv
from atlassian.jira import Jira

# .env 파일 로드
load_dotenv()

def load_env_vars(keys):
    """환경 변수를 로드합니다."""
    values = {k: os.getenv(k) for k in keys}
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ValueError(f"필수 환경변수 누락: {', '.join(missing)}")
    return values

def check_jira_fields():
    """Jira 필드 정보를 조회합니다."""
    try:
        # 환경 변수 로드
        env = load_env_vars([
            "ATLASSIAN_URL", "ATLASSIAN_USERNAME", "ATLASSIAN_API_TOKEN"
        ])
        
        # Jira 클라이언트 생성
        jira = Jira(
            url=env["ATLASSIAN_URL"], 
            username=env["ATLASSIAN_USERNAME"], 
            password=env["ATLASSIAN_API_TOKEN"], 
            cloud=True
        )
        
        print("=== Jira 필드 정보 조회 ===")
        
        # 1. 모든 필드 조회
        print("\n1. 모든 필드 목록:")
        fields = jira.get_all_fields()
        
        # customfield_10817 관련 필드 찾기
        target_fields = []
        for field in fields:
            field_id = field.get('id', '')
            field_name = field.get('name', '')
            if 'customfield_10817' in field_id or '예정' in field_name or '시작' in field_name:
                target_fields.append(field)
        
        print(f"\n2. customfield_10817 관련 필드:")
        for field in target_fields:
            print(f"  - ID: {field.get('id')}")
            print(f"  - Name: {field.get('name')}")
            print(f"  - Type: {field.get('schema', {}).get('type')}")
            print(f"  - Custom: {field.get('schema', {}).get('custom')}")
            print()
        
        # 3. 특정 티켓에서 필드 값 확인
        print("3. IT 프로젝트 티켓에서 customfield_10817 값 확인:")
        try:
            # 최근 IT 티켓 조회
            issues = jira.jql("project = 'IT' ORDER BY updated DESC", fields="key,summary,customfield_10817", limit=5)
            
            for issue in issues['issues']:
                key = issue['key']
                summary = issue['fields'].get('summary', '')
                custom_field = issue['fields'].get('customfield_10817', '')
                
                print(f"  - {key}: {summary}")
                print(f"    customfield_10817: {custom_field}")
                print()
                
        except Exception as e:
            print(f"    티켓 조회 오류: {e}")
        
        # 4. 필드 메타데이터 확인
        print("4. customfield_10817 필드 메타데이터:")
        try:
            field_meta = jira.get_field_by_id('customfield_10817')
            print(f"  - Field Metadata: {field_meta}")
        except Exception as e:
            print(f"    필드 메타데이터 조회 오류: {e}")
        
        # 5. JQL 테스트
        print("5. JQL 쿼리 테스트:")
        test_queries = [
            "project = 'IT' AND customfield_10817 IS NOT EMPTY",
            "project = 'IT' AND customfield_10817 >= '2025-07-21'",
            "project = 'IT' AND customfield_10817 IS NOT NULL"
        ]
        
        for i, query in enumerate(test_queries, 1):
            try:
                print(f"  {i}. {query}")
                result = jira.jql(query, fields="key,summary,customfield_10817", limit=3)
                print(f"     결과: {len(result['issues'])}개 티켓")
                for issue in result['issues']:
                    print(f"       - {issue['key']}: {issue['fields'].get('customfield_10817', 'N/A')}")
            except Exception as e:
                print(f"     오류: {e}")
            print()
        
    except Exception as e:
        print(f"전체 오류: {e}")

if __name__ == "__main__":
    check_jira_fields() 