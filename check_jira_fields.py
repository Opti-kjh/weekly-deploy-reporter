#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jira 필드 정보 조회 스크립트
요청 유형 필드와 customfield_10817 필드의 정확한 정보를 확인합니다.
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
        
        # 요청 유형 관련 필드 찾기
        request_type_fields = []
        for field in fields:
            field_id = field.get('id', '')
            field_name = field.get('name', '')
            
            # 요청 유형 관련 키워드 검색
            keywords = ['요청', '유형', '기능', '변경', 'request', 'type', 'category']
            if any(keyword in field_name.lower() for keyword in keywords):
                request_type_fields.append(field)
        
        print(f"\n2. 요청 유형 관련 필드:")
        for field in request_type_fields:
            print(f"  - ID: {field.get('id')}")
            print(f"  - Name: {field.get('name')}")
            print(f"  - Type: {field.get('schema', {}).get('type')}")
            print(f"  - Custom: {field.get('schema', {}).get('custom')}")
            print()
        
        # 3. 특정 티켓에서 요청 유형 필드 값 확인
        print("3. IT 프로젝트 티켓에서 요청 유형 필드 값 확인:")
        try:
            # 최근 IT 티켓 조회 (모든 필드 포함)
            issues = jira.jql("project = 'IT' ORDER BY updated DESC", limit=3)
            
            for issue in issues['issues']:
                key = issue['key']
                summary = issue['fields'].get('summary', '')
                
                print(f"  - {key}: {summary}")
                
                # 모든 필드 값 출력
                for field_id, field_value in issue['fields'].items():
                    if field_value and isinstance(field_value, (str, dict)):
                        if isinstance(field_value, dict):
                            # 딕셔너리인 경우 값 추출
                            if 'value' in field_value:
                                field_value = field_value['value']
                            elif 'name' in field_value:
                                field_value = field_value['name']
                            else:
                                field_value = str(field_value)
                        
                        # 요청 유형 관련 키워드가 포함된 값 찾기
                        if any(keyword in str(field_value).lower() for keyword in ['기능', '변경', '요청', 'request', 'change']):
                            print(f"    {field_id}: {field_value}")
                
                print()
                
        except Exception as e:
            print(f"    티켓 조회 오류: {e}")
        
        # 4. customfield_10817 관련 필드 찾기
        target_fields = []
        for field in fields:
            field_id = field.get('id', '')
            field_name = field.get('name', '')
            if 'customfield_10817' in field_id or '예정' in field_name or '시작' in field_name:
                target_fields.append(field)
        
        print(f"\n4. customfield_10817 관련 필드:")
        for field in target_fields:
            print(f"  - ID: {field.get('id')}")
            print(f"  - Name: {field.get('name')}")
            print(f"  - Type: {field.get('schema', {}).get('type')}")
            print(f"  - Custom: {field.get('schema', {}).get('custom')}")
            print()
        
        # 5. 필드 메타데이터 확인
        print("5. customfield_10817 필드 메타데이터:")
        try:
            field_meta = jira.get_field_by_id('customfield_10817')
            print(f"  - Field Metadata: {field_meta}")
        except Exception as e:
            print(f"    필드 메타데이터 조회 오류: {e}")
        
    except Exception as e:
        print(f"전체 오류: {e}")

if __name__ == "__main__":
    check_jira_fields() 