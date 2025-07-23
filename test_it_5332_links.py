#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from dotenv import load_dotenv
from jira import JIRA

# .env 파일 로드
load_dotenv()

def load_env_vars(keys):
    values = {k: os.getenv(k) for k in keys}
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ValueError(f"필수 환경변수 누락: {', '.join(missing)}")
    return values

def get_linked_it_tickets(jira, issue_key):
    """특정 이슈의 'is deployed by' 관계로 연결된 IT 티켓들을 가져옵니다."""
    try:
        print(f"=== '{issue_key}'의 연결된 IT 티켓 조회 시작 ===")
        
        # Jira API에서 이슈 정보를 가져옵니다 (issuelinks 확장)
        issue_response = jira.issue(issue_key, expand='issuelinks')
        
        # 응답이 딕셔너리인지 확인
        if isinstance(issue_response, dict):
            issue_data = issue_response
        else:
            # 객체인 경우 딕셔너리로 변환
            issue_data = issue_response.raw
        
        linked_it_tickets = []
        
        # issuelinks 필드가 있는지 확인
        if 'fields' in issue_data and 'issuelinks' in issue_data['fields']:
            print(f"발견된 issuelinks 수: {len(issue_data['fields']['issuelinks'])}")
            
            for i, link in enumerate(issue_data['fields']['issuelinks']):
                link_type = link.get('type', {}).get('name', '')
                print(f"  링크 {i+1}: {link_type}")
                
                linked_ticket = None
                
                # "Deployments" 타입의 링크에서 "is deployed by" 관계 확인
                if link_type == 'Deployments':
                    # IT-5332의 경우: IT-5332가 배포되는 관계이므로 inwardIssue가 배포 티켓
                    if 'inwardIssue' in link:
                        linked_ticket = link['inwardIssue']
                        print(f"    inwardIssue 발견: {linked_ticket.get('key', 'Unknown')}")
                    elif 'outwardIssue' in link:
                        linked_ticket = link['outwardIssue']
                        print(f"    outwardIssue 발견: {linked_ticket.get('key', 'Unknown')}")
                
                # 연결된 티켓이 "변경" 타입인 경우만 추가 (IT 티켓)
                if linked_ticket:
                    issue_type = linked_ticket.get('fields', {}).get('issuetype', {}).get('name', '')
                    print(f"    티켓 타입: {issue_type}")
                    
                    if issue_type == '변경':  # "변경" 타입이 실제 IT 티켓
                        ticket_info = {
                            'key': linked_ticket['key'],
                            'summary': linked_ticket['fields'].get('summary', ''),
                            'status': linked_ticket['fields'].get('status', {}).get('name', '')
                        }
                        linked_it_tickets.append(ticket_info)
                        print(f"    ✅ 변경 티켓 추가: {ticket_info['key']} - {ticket_info['summary']}")
                    else:
                        print(f"    ⏭️ 변경 타입이 아님: {linked_ticket.get('key', 'Unknown')} ({issue_type})")
                else:
                    print(f"    ⏭️ 연결된 티켓 없음")
        else:
            print("issuelinks 필드를 찾을 수 없습니다.")
        
        print(f"=== '{issue_key}' 연결된 IT 티켓 조회 완료: {len(linked_it_tickets)}개 ===")
        return linked_it_tickets
        
    except Exception as e:
        print(f"'{issue_key}'의 연결된 IT 티켓 조회 실패: {e}")
        return []

def main():
    # 환경 변수 로딩
    env_vars = load_env_vars([
        'ATLASSIAN_URL', 'ATLASSIAN_USERNAME', 'ATLASSIAN_API_TOKEN'
    ])
    
    atlassian_url = env_vars['ATLASSIAN_URL']
    atlassian_username = env_vars['ATLASSIAN_USERNAME']
    atlassian_token = env_vars['ATLASSIAN_API_TOKEN']
    
    # Jira 클라이언트 초기화
    jira = JIRA(server=atlassian_url, basic_auth=(atlassian_username, atlassian_token))
    print(f"Jira 서버 연결 성공!")
    
    # IT-5332 티켓 테스트
    issue_key = "IT-5332"
    linked_tickets = get_linked_it_tickets(jira, issue_key)
    
    print(f"\n=== 최종 결과 ===")
    print(f"IT-5332의 연결된 IT 티켓: {len(linked_tickets)}개")
    
    for i, ticket in enumerate(linked_tickets, 1):
        print(f"{i}. {ticket['key']}: {ticket['summary']}")
        print(f"   상태: {ticket['status']}")

if __name__ == "__main__":
    main() 