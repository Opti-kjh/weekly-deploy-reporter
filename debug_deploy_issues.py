#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
배포 예정 이슈 현황과 배포 예정 목록 간의 차이점 분석 스크립트

사용법:
    python debug_deploy_issues.py [티켓키1] [티켓키2] [티켓키3] ...
    
예시:
    python debug_deploy_issues.py IT-4585 IT-5331 IT-6016
"""

import os
import sys
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from jira import JIRA

# .env 파일 로드
load_dotenv()

# Jira 설정
JIRA_DEPLOY_DATE_FIELD_ID = "customfield_10817"

def load_env_vars(keys):
    values = {k: os.getenv(k) for k in keys}
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ValueError(f"필수 환경변수 누락: {', '.join(missing)}")
    return values

def get_week_range(mode="current"):
    """주간 범위를 계산합니다."""
    today = date.today()
    
    if mode == "current":
        # 이번 주 (월요일 ~ 일요일)
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
    elif mode == "last":
        # 지난 주
        monday = today - timedelta(days=today.weekday() + 7)
        sunday = monday + timedelta(days=6)
    elif mode == "create":
        # 다음 주
        monday = today - timedelta(days=today.weekday() - 7)
        sunday = monday + timedelta(days=6)
    else:
        raise ValueError(f"지원하지 않는 모드: {mode}")
    
    return monday, sunday

def get_jira_issues_by_customfield_10817(jira, project_key, start_date, end_date, use_pagination=False):
    """customfield_10817 필드 값이 해당 주간에 속하는 모든 티켓을 조회합니다."""
    print(f"=== cf[10817] 형식으로 직접 조회 시작 ===")
    print(f"프로젝트: {project_key}")
    print(f"대상 기간: {start_date} ~ {end_date}")
    
    try:
        # cf[10817] 형식을 사용한 JQL 쿼리
        macro_jql_query = (
            f"project = '{project_key}' AND "
            f"cf[10817] >= '{start_date}' AND cf[10817] <= '{end_date}' "
            f"ORDER BY updated DESC"
        )
        fields_param = f"key,summary,status,assignee,created,updated,{JIRA_DEPLOY_DATE_FIELD_ID}"
        
        print(f"사용할 JQL: {macro_jql_query}")
        
        # 페이지네이션 없이 한 번에 조회
        all_issues = jira.search_issues(macro_jql_query, fields=fields_param, maxResults=1000)
        print(f"✅ 전체 티켓 조회 성공: {len(all_issues)}개")
        
        # 결과를 딕셔너리 형태로 변환
        filtered_issues = []
        for issue in all_issues:
            issue_dict = {
                'key': issue.key,
                'summary': getattr(issue.fields, 'summary', ''),
                'status': getattr(issue.fields, 'status', {}).name if hasattr(getattr(issue.fields, 'status', {}), 'name') else str(getattr(issue.fields, 'status', '')),
                'fields': {
                    'summary': getattr(issue.fields, 'summary', ''),
                    'status': {'name': getattr(issue.fields, 'status', {}).name if hasattr(getattr(issue.fields, 'status', {}), 'name') else str(getattr(issue.fields, 'status', ''))},
                    JIRA_DEPLOY_DATE_FIELD_ID: getattr(issue.fields, JIRA_DEPLOY_DATE_FIELD_ID, '')
                }
            }
            filtered_issues.append(issue_dict)
            print(f"✅ {issue.key}: {getattr(issue.fields, 'summary', '')} - 포함됨")
        
        print(f"\n=== 최종 결과 ===")
        print(f"cf[10817] 형식으로 조회된 티켓: {len(filtered_issues)}개")
        for i, issue in enumerate(filtered_issues, 1):
            print(f"{i}. {issue['key']}: {issue['summary']}")
            print(f"   예정된 시작: {issue['fields'][JIRA_DEPLOY_DATE_FIELD_ID]}")
            print(f"   상태: {issue['status']}")
        
        return filtered_issues
        
    except Exception as e:
        print(f"Jira 이슈 조회 실패: {e}")
        return []

def get_macro_table_issues(jira, jira_project_key, start_date_str, end_date_str, use_pagination=False):
    """macro table에 표시될 실제 티켓들을 동적으로 가져옵니다."""
    try:
        print(f"=== Confluence 페이지용 배포 예정 티켓 조회 ===")
        
        # customfield_10817 필드를 직접 사용하여 정확한 티켓 조회
        issues = get_jira_issues_by_customfield_10817(jira, jira_project_key, start_date_str, end_date_str, use_pagination)
        
        if issues:
            print(f"macro table용 티켓을 customfield_10817 필드로 조회했습니다.")
            return issues
        
        # customfield_10817에서 데이터를 찾지 못한 경우, 다른 필드로 시도
        date_fields = [
            "created",            # 생성일
            "updated",            # 수정일
            "duedate"             # 마감일
        ]
        
        for field in date_fields:
            try:
                jql_query = (
                    f"project = '{jira_project_key}' AND "
                    f"'{field}' >= '{start_date_str}' AND '{field}' <= '{end_date_str}' "
                    f"ORDER BY '{field}' ASC"
                )
                issues = jira.search_issues(jql_query, fields="key,summary,status,assignee,created,updated", maxResults=1000)
                if issues:
                    print(f"macro table용 티켓을 {field} 필드로 조회했습니다.")
                    return [{'key': i.key, 'summary': i.fields.summary, 'status': i.fields.status.name} for i in issues]
            except Exception as e:
                print(f"{field} 필드로 조회 실패: {e}")
                continue
        
        # 모든 필드에서 데이터를 찾지 못한 경우, 최근 티켓들을 가져옵니다
        print("날짜 필드에서 데이터를 찾지 못하여 최근 티켓들을 가져옵니다.")
        jql_query = (
            f"project = '{jira_project_key}' AND "
            f"status IN ('실행', '실행을 기다리는 중', '완료') "
            f"ORDER BY updated DESC"
        )
        issues = jira.search_issues(jql_query, fields="key,summary,status,assignee,created,updated", maxResults=15)
        return [{'key': i.key, 'summary': i.fields.summary, 'status': i.fields.status.name} for i in issues]
        
    except Exception as e:
        print(f"macro table 티켓 조회 실패: {e}")
        return []

def check_specific_tickets(jira, ticket_keys):
    """특정 티켓들의 상세 정보를 확인합니다."""
    print(f"\n=== 특정 티켓 상세 정보 확인 ===")
    
    for ticket_key in ticket_keys:
        try:
            issue = jira.issue(ticket_key, fields="key,summary,status,assignee,created,updated,customfield_10817")
            custom_field_value = getattr(issue.fields, JIRA_DEPLOY_DATE_FIELD_ID, None)
            
            print(f"\n티켓: {ticket_key}")
            print(f"  요약: {issue.fields.summary}")
            print(f"  상태: {issue.fields.status.name}")
            print(f"  담당자: {issue.fields.assignee.displayName if issue.fields.assignee else '미지정'}")
            print(f"  생성일: {issue.fields.created}")
            print(f"  수정일: {issue.fields.updated}")
            print(f"  예정된 시작 (customfield_10817): {custom_field_value}")
            
            if custom_field_value:
                try:
                    if isinstance(custom_field_value, str):
                        field_date_str = custom_field_value.split('T')[0]
                        field_date = datetime.strptime(field_date_str, '%Y-%m-%d').date()
                    else:
                        field_date = custom_field_value.date()
                    print(f"  파싱된 날짜: {field_date}")
                except Exception as e:
                    print(f"  날짜 파싱 오류: {e}")
            else:
                print(f"  예정된 시작 필드가 비어있음")
                
        except Exception as e:
            print(f"티켓 {ticket_key} 조회 실패: {e}")

def main():
    if len(sys.argv) < 2:
        print("사용법: python debug_deploy_issues.py [티켓키1] [티켓키2] [티켓키3] ...")
        print("예시: python debug_deploy_issues.py IT-4585 IT-5331 IT-6016")
        return
    
    # 환경 변수 로딩
    env_vars = load_env_vars([
        'ATLASSIAN_URL', 'ATLASSIAN_USERNAME', 'ATLASSIAN_API_TOKEN', 'JIRA_PROJECT_KEY'
    ])
    
    atlassian_url = env_vars['ATLASSIAN_URL']
    atlassian_username = env_vars['ATLASSIAN_USERNAME']
    atlassian_api_token = env_vars['ATLASSIAN_API_TOKEN']
    jira_project_key = env_vars['JIRA_PROJECT_KEY']
    
    # Jira 연결
    jira = JIRA(server=atlassian_url, basic_auth=(atlassian_username, atlassian_api_token))
    
    # 주간 범위 계산
    monday, sunday = get_week_range("current")
    start_date_str = monday.strftime('%Y-%m-%d')
    end_date_str = sunday.strftime('%Y-%m-%d')
    
    print(f"=== 배포 예정 이슈 현황 vs 배포 예정 목록 차이점 분석 ===")
    print(f"대상 기간: {start_date_str} ~ {end_date_str}")
    print(f"프로젝트: {jira_project_key}")
    
    # 1. 배포 예정 목록 (HTML 테이블용) 조회
    print(f"\n{'='*50}")
    print("1. 배포 예정 목록 (HTML 테이블용) 조회")
    print(f"{'='*50}")
    deploy_issues = get_jira_issues_by_customfield_10817(jira, jira_project_key, start_date_str, end_date_str)
    
    # 2. 배포 예정 이슈 현황 (매크로용) 조회
    print(f"\n{'='*50}")
    print("2. 배포 예정 이슈 현황 (매크로용) 조회")
    print(f"{'='*50}")
    macro_issues = get_macro_table_issues(jira, jira_project_key, start_date_str, end_date_str)
    
    # 3. 차이점 분석
    print(f"\n{'='*50}")
    print("3. 차이점 분석")
    print(f"{'='*50}")
    
    deploy_keys = {issue['key'] for issue in deploy_issues}
    macro_keys = {issue['key'] for issue in macro_issues}
    
    print(f"배포 예정 목록에만 있는 티켓: {deploy_keys - macro_keys}")
    print(f"배포 예정 이슈 현황에만 있는 티켓: {macro_keys - deploy_keys}")
    print(f"공통 티켓: {deploy_keys & macro_keys}")
    
    # 4. 특정 티켓 상세 확인
    specific_tickets = sys.argv[1:]
    if specific_tickets:
        check_specific_tickets(jira, specific_tickets)

if __name__ == "__main__":
    main()
