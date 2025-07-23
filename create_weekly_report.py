# -*- coding: utf-8 -*-
# 필요한 외부 라이브러리와 환경 변수들을 불러옵니다.
import os
import datetime
import sys
from dotenv import load_dotenv
from jira import JIRA
from atlassian.confluence import Confluence
import requests
import json
import re
import html
from datetime import datetime, date, timedelta
import numpy as np # 스마트 필터링 시 사용

# .env 파일에서 환경 변수들을 읽어와서 현재 환경에 설정합니다.
# 예: ATLASSIAN_URL, ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN, SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN 등
load_dotenv()

# --- 스크립트 설정 값 ---

# Jira 필드 ID 설정
JIRA_DEPLOY_DATE_FIELD_ID = "customfield_10817"  # 예정된 시작 필드 ID

# Confluence에서 생성될 주간 리포트 페이지의 상위 페이지 제목입니다.
# 이 페이지 아래에 "X월 Y째주: (MM/DD~MM/DD)" 형식의 자식 페이지가 생성됩니다.
CONFLUENCE_PARENT_PAGE_TITLE = "25-2H 주간 배포 리스트"

# ---------------------------------------------------------

# === [1단계] 유틸리티 함수 및 템플릿 정의 ===
def load_env_vars(keys):
    values = {k: os.getenv(k) for k in keys}
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ValueError(f"필수 환경변수 누락: {', '.join(missing)}")
    return values

def get_week_range(mode):
    today = date.today()
    if mode == "create":
        # 다음 주 (차주)
        monday = today + timedelta(days=(7 - today.weekday()))
    elif mode == "current":
        # 이번 주 (현재 주)
        monday = today - timedelta(days=today.weekday())
    elif mode == "last":
        # 지난 주
        monday = today - timedelta(days=today.weekday() + 7)
    else:
        # 기본값: 이번 주
        monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday

def get_page_title(monday, sunday):
    first_day = monday.replace(day=1)
    week_num = ((monday.day + first_day.weekday() - 1) // 7) + 1
    month = monday.strftime('%m')
    return f"{int(month)}월 {week_num}째주: ({monday.strftime('%m/%d')}~{sunday.strftime('%m/%d')})"

def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log(message):
    with open("cron.log", "a", encoding="utf-8") as f:
        f.write(message + "\n")

def normalize_html_content(html_content):
    unescaped = html.unescape(html_content)
    return re.sub(r'\s+', ' ', unescaped).strip()

# 기본 Jira 매크로 (날짜 포맷 없음)
JIRA_MACRO_TEMPLATE = '''
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="columns">key,type,summary,assignee,status</ac:parameter>
  <ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>
</ac:structured-macro>
'''

# 날짜 컬럼용 매크로 (updated, created, 예정된 시작)
JIRA_DATE_MACRO_TEMPLATE = '''
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="columns">created,updated,예정된 시작</ac:parameter>
  <ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>
  <ac:parameter ac:name="dateFormat">yyyy-MM-dd HH:mm</ac:parameter>
</ac:structured-macro>
'''

# 모든 컬럼을 포함하되 날짜 포맷이 적용된 매크로
JIRA_FULL_MACRO_TEMPLATE = '''
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="columns">key,type,summary,assignee,status,created,updated,예정된 시작</ac:parameter>
  <ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>
  <ac:parameter ac:name="dateFormat">yyyy-MM-dd HH:mm</ac:parameter>
</ac:structured-macro>
'''

# 날짜 포맷이 적용된 전체 매크로 (GitHub 최신 버전)
JIRA_CUSTOM_DATE_FORMAT_TEMPLATE = '''
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="columns">key,type,summary,assignee,status,created,updated,예정된 시작</ac:parameter>
  <ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>
  <ac:parameter ac:name="dateFormat">yyyy-MM-dd HH:mm</ac:parameter>
  <ac:parameter ac:name="maximumIssues">100</ac:parameter>
</ac:structured-macro>
'''

# 배포 예정 목록 Jira 매크로 템플릿
DEPLOY_LINKS_MACRO_TEMPLATE = '''
<h2 style="margin-top: 20px;">배포 예정 목록</h2>
<p><em>아래 표는 이번 주 배포 예정인 부모 IT 티켓들을 보여줍니다. 각 티켓의 배포 관계는 Jira에서 직접 확인하실 수 있습니다.</em></p>
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="columns">key,status,issuelinks</ac:parameter>
  <ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>
  <ac:parameter ac:name="dateFormat">yyyy-MM-dd HH:mm</ac:parameter>
  <ac:parameter ac:name="columnWidths">100,80,300</ac:parameter>
</ac:structured-macro>
'''


# === [2단계] API/알림/스냅샷 래퍼 함수 간소화 ===
def get_jira_issues_simple(jira, project_key, date_field_id, start_date, end_date):
    # JQL 쿼리를 단순화하여 필드 접근 문제를 우회
    jql_query = (
        f"project = '{project_key}' "
        f"ORDER BY updated DESC"
    )
    print(f"JQL: {jql_query}")
    try:
        # fields를 구체적으로 지정하여 customfield_10817 필드 접근 문제 해결
        fields_param = f"key,summary,status,assignee,created,updated,{date_field_id}"
        issues = jira.jql(jql_query, fields=fields_param)
        
        # Python에서 날짜 필터링
        filtered_issues = []
        for issue in issues['issues']:
            field_value = issue['fields'].get(date_field_id)
            if field_value:
                try:
                    # 날짜 문자열을 파싱하여 비교
                    field_date = datetime.strptime(field_value[:10], '%Y-%m-%d').date()
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    
                    if start_date_obj <= field_date <= end_date_obj:
                        filtered_issues.append(issue)
                except Exception as e:
                    print(f"날짜 파싱 오류 ({issue['key']}): {e}")
                    continue
        
        print(f"✅ 필터링 완료: {len(filtered_issues)}개 이슈 (전체: {len(issues['issues'])}개)")
        return filtered_issues
    except Exception as e:
        print(f"Jira 검색 오류: {e}")
        return []

def get_jira_issues_with_links(jira, project_key, date_field_id, start_date, end_date):
    """Jira 이슈를 조회하고 각 이슈의 'is deployed by' 관계를 포함하여 반환합니다."""
    jql_query = (
        f"project = '{project_key}' AND "
        f"{date_field_id} >= '{start_date}' AND {date_field_id} <= '{end_date}' "
        f"ORDER BY updated DESC"
    )
    print(f"JQL: {jql_query}")
    try:
        # 먼저 이슈 키들을 조회
        issues = jira.jql(jql_query, fields="key,summary")
        issue_keys = [issue['key'] for issue in issues['issues']]
        
        # 각 이슈의 'is deployed by' 관계를 조회
        issues_with_links = []
        for issue_key in issue_keys:
            try:
                # Jira 객체로 조회하여 'is deployed by' 관계 가져오기
                issue_obj = jira.issue(issue_key, expand='issuelinks')
                
                deployed_by_tickets = []
                for link in issue_obj.fields.issuelinks:
                    # 'is deployed by' 관계인 경우 (DEP 티켓이 IT 티켓을 배포하는 관계)
                    if hasattr(link, 'outwardIssue') and link.type.name == 'is deployed by':
                        deployed_ticket = link.outwardIssue
                        deployed_by_tickets.append({
                            'key': deployed_ticket.key,
                            'status': deployed_ticket.fields.status.name,
                            'summary': deployed_ticket.fields.summary
                        })
                    elif hasattr(link, 'inwardIssue') and link.type.name == 'deploys':
                        # 'deploys' 관계인 경우 (IT 티켓이 DEP 티켓에 의해 배포되는 관계)
                        deployed_ticket = link.inwardIssue
                        deployed_by_tickets.append({
                            'key': deployed_ticket.key,
                            'status': deployed_ticket.fields.status.name,
                            'summary': deployed_ticket.fields.summary
                        })
                
                # 이슈 정보와 'is deployed by' 관계를 함께 저장
                issue_info = {
                    'key': issue_key,
                    'summary': issue_obj.fields.summary,
                    'deployed_by_tickets': deployed_by_tickets
                }
                issues_with_links.append(issue_info)
                print(f"'{issue_key}' 이슈 조회 성공: {len(deployed_by_tickets)}개의 deployed by 티켓 발견")
                
            except Exception as e:
                print(f"'{issue_key}' 이슈 조회 실패: {e}")
                # 실패한 경우 기본 정보만 저장
                issue_info = {
                    'key': issue_key,
                    'summary': '조회 실패',
                    'deployed_by_tickets': []
                }
                issues_with_links.append(issue_info)
        
        return issues_with_links
    except Exception as e:
        print(f"Jira 검색 오류: {e}")
        return []

def format_jira_datetime(dt_str):
    if not dt_str:
        return ""
    try:
        # JIRA 기본 날짜 포맷: 2024-07-16T02:30:00.000+0900
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str  # 파싱 실패 시 원본 반환

def create_confluence_content(jql_query, issues, jira_url, jira, jira_project_key, start_date_str, end_date_str): 
    # 날짜 포맷이 적용된 전체 매크로 사용
    macro = JIRA_CUSTOM_DATE_FORMAT_TEMPLATE.format(jql_query=jql_query)
    
    # get_jira_issues_by_customfield_10817 함수를 사용하여 정확한 배포 예정 티켓 조회
    print(f"=== Confluence 페이지용 배포 예정 티켓 조회 ===")
    deploy_issues = get_jira_issues_by_customfield_10817(jira, jira_project_key, start_date_str, end_date_str)
    
    # IT 티켓만 필터링하는 HTML 테이블 생성 (정확한 결과 사용)
    deploy_links_html_table = create_deploy_links_html_table_with_issues(jira, deploy_issues, jira_url)
    
    return macro + deploy_links_html_table

def create_deploy_links_html_table_with_issues(jira, deploy_issues, jira_url):
    """정확한 배포 예정 티켓들을 사용하여 HTML 테이블을 생성합니다."""
    try:
        print(f"=== 정확한 배포 예정 티켓으로 HTML 테이블 생성 ===")
        print(f"배포 예정 티켓 수: {len(deploy_issues)}")
        
        html_content = '''
<h2 style="margin-top: 20px;">배포 예정 목록</h2>
<p><em>아래 표는 이번 주 배포 예정인 부모 IT 티켓들을 보여줍니다. 각 티켓의 배포 관계는 Jira에서 직접 확인하실 수 있습니다.</em></p>

<div style="background-color: #f4f5f7; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
<h4> 배포 관계 표시 형식 안내</h4>
<p>아래 표의 <strong>연결된 이슈</strong> 컬럼에는 다음과 같은 형식으로 배포 관계가 표시됩니다:</p>
<ul>
<li><strong>부모 IT 티켓</strong>: 배포 대상이 되는 IT 티켓</li>
<li><strong>배포 티켓</strong>: "is deployed by" 관계로 연결된 IT 티켓들만 표시</li>
<li><strong>표시 형식</strong>: 각 배포 티켓이 새로운 줄로 구분되어 표시됩니다</li>
</ul>
<p><em>예시: IT-6516 티켓의 경우, prod-beluga-manager-consumer로 "deploy"에 대한 배포 Release(IT-4831, IT-5027) v1.5.0 (#166) 형태로 표시됩니다.</em></p>
</div>

<table class="wrapped" style="width: 100%;">
<colgroup>
<col style="width: 120px;" />
<col style="width: 300px;" />
<col style="width: 400px;" />
</colgroup>
<tbody>
<tr>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">키</th>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">요약</th>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">연결된 이슈</th>
</tr>
'''
        
        for i, issue in enumerate(deploy_issues, 1):
            issue_key = issue['key']
            
            # 데이터 구조에 따라 summary와 status 추출
            if 'fields' in issue:
                # get_jira_issues_by_customfield_10817 함수의 구조
                summary = issue['fields'].get('summary', '')
                status = issue['fields'].get('status', {}).get('name', '')
                custom_field = issue['fields'].get(JIRA_DEPLOY_DATE_FIELD_ID, '')
            else:
                # 기존 구조
                summary = issue.get('summary', '')
                status = issue.get('status', '')
                custom_field = issue.get('customfield_10817', '')
            
            print(f"{i}. {issue_key}: {summary}")
            print(f"   예정된 시작: {custom_field}")
            print(f"   상태: {status}")
            
            # IT 티켓만 필터링하여 연결된 이슈 조회
            linked_it_tickets = get_linked_it_tickets(jira, issue_key)
            print(f"   연결된 IT 티켓 수: {len(linked_it_tickets)}")
            
            # 연결된 IT 티켓들을 포맷팅
            if linked_it_tickets:
                linked_tickets_html = '<br>'.join([
                    f"{j}. {ticket['key']}<br>: {ticket['summary']}"
                    for j, ticket in enumerate(linked_it_tickets, 1)
                ])
            else:
                linked_tickets_html = '<em>연결된 IT 티켓 없음</em>'
            
            html_content += f'''
<tr>
<td style="padding: 8px; border: 1px solid #dfe1e6;"><a href="{jira_url}/browse/{issue_key}">{issue_key}</a></td>
<td style="padding: 8px; border: 1px solid #dfe1e6;">{summary}</td>
<td style="padding: 8px; border: 1px solid #dfe1e6;">{linked_tickets_html}</td>
</tr>
'''
        
        html_content += '''
</tbody>
</table>
'''
        
        print(f"=== HTML 테이블 생성 완료 ===")
        return html_content
        
    except Exception as e:
        print(f"배포 예정 목록 HTML 테이블 생성 실패: {e}")
        return f'<p>배포 예정 목록 HTML 테이블 생성 중 오류가 발생했습니다: {e}</p>'

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

def load_deploy_ticket_links():
    """배포티켓 링크 데이터를 로드합니다."""
    try:
        with open('deploy_ticket_links.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"배포티켓 링크 데이터 로드 실패: {e}")
        return []

def get_macro_table_issues(jira, jira_project_key, start_date_str, end_date_str):
    """macro table에 표시될 실제 티켓들을 동적으로 가져옵니다."""
    try:
        # 다양한 필드로 시도하여 실제 데이터가 있는 필드를 찾습니다
        date_fields = [
            JIRA_DEPLOY_DATE_FIELD_ID,  # 예정된 시작
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
                issues = get_jira_issues_simple(jira, jira_project_key, field, start_date_str, end_date_str)
                if issues:
                    print(f"macro table용 티켓을 {field} 필드로 조회했습니다.")
                    return issues
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
        issues = get_jira_issues_simple(jira, jira_project_key, "updated", start_date_str, end_date_str)
        return issues[:15]  # 최대 15개 티켓만 반환
        
    except Exception as e:
        print(f"macro table 티켓 조회 실패: {e}")
        return []

def get_deployed_by_tickets(jira, issue_key):
    """특정 IT 티켓의 'is deployed by' 티켓들을 가져옵니다."""
    try:
        # Jira API를 통해 해당 이슈의 'is deployed by' 관계를 조회
        issue = jira.issue(issue_key, expand='issuelinks')
        
        deployed_by_tickets = []
        for link in issue.fields.issuelinks:
            # 'is deployed by' 관계인 경우 (DEP 티켓이 IT 티켓을 배포하는 관계)
            if hasattr(link, 'outwardIssue') and link.type.name == 'is deployed by':
                deployed_ticket = link.outwardIssue
                deployed_by_tickets.append({
                    'key': deployed_ticket.key,
                    'status': deployed_ticket.fields.status.name,
                    'summary': deployed_ticket.fields.summary
                })
            elif hasattr(link, 'inwardIssue') and link.type.name == 'deploys':
                # 'deploys' 관계인 경우 (IT 티켓이 DEP 티켓에 의해 배포되는 관계)
                deployed_ticket = link.inwardIssue
                deployed_by_tickets.append({
                    'key': deployed_ticket.key,
                    'status': deployed_ticket.fields.status.name,
                    'summary': deployed_ticket.fields.summary
                })
        
        return deployed_by_tickets
    except Exception as e:
        print(f"'{issue_key}'의 deployed by 티켓 조회 실패: {e}")
        return []

def send_slack(text):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        print("SLACK_WEBHOOK_URL 미설정, Slack 알림 생략")
        return
    
    # 오늘은 슬랙 알림 전송하지 않음
    notification_start_hour = 10
    notification_end_hour = 11
    
    today = datetime.now()
    if today.hour < notification_start_hour or today.hour >= notification_end_hour:  # 지정된 시간에만 알림 전송
        print(f"현재 시간에는 슬랙 알림 전송을 건너뜁니다. (오전 {notification_start_hour}시 ~ {notification_end_hour}시 외)")
        return
    
    try:
        r = requests.post(url, json={"text": text})
        if r.status_code != 200:
            print(f"Slack 알림 실패: {r.text}")
    except Exception as e:
        print(f"Slack 알림 오류: {e}")

def snapshot_issues(issues, field_id):
    """이슈들의 스냅샷을 생성합니다."""
    snapshot = []
    for i in issues:
        # Jira 객체인지 딕셔너리인지 확인
        if hasattr(i, 'key'):
            # Jira 객체인 경우
            key = i.key
            fields = i.fields
            summary = getattr(fields, 'summary', '')
            status = getattr(fields, 'status', '')
            status_name = status.name if hasattr(status, 'name') else str(status)
            assignee = getattr(fields, 'assignee', None)
            assignee_name = assignee.displayName if assignee else "미지정"
            custom_field = getattr(fields, field_id, '')
        else:
            # 딕셔너리인 경우
            key = i['key']
            fields = i['fields']
            summary = fields.get('summary', '')
            status = fields.get('status', {})
            status_name = status.get('name', '') if isinstance(status, dict) else str(status)
            assignee = fields.get('assignee', None)
            # assignee가 딕셔너리인지 객체인지 확인
            if isinstance(assignee, dict):
                assignee_name = assignee.get('displayName', '미지정')
            elif hasattr(assignee, 'displayName'):
                assignee_name = assignee.displayName
            else:
                assignee_name = "미지정"
            custom_field = fields.get(field_id, '')
        
        snapshot.append({
            "key": key,
            "summary": summary,
            "status": status_name,
            "assignee": assignee_name,
            field_id: custom_field
        })
    return snapshot

def issues_changed(prev, curr):
    return prev != curr

def get_week_dates(mode):
    """
    실행 모드('create' 또는 'update')에 따라 해당 주의 날짜 범위를 계산합니다.

    - 'create' 모드: 다음 주의 월요일부터 일요일까지의 날짜를 계산합니다.
    - 그 외 모드('update'): 이번 주의 월요일부터 일요일까지의 날짜를 계산합니다.

    Args:
        mode (str): 실행 모드 ('create' 또는 'update')

    Returns:
        tuple: (월요일 날짜 객체, 일요일 날짜 객체)
    """
    today = datetime.date.today()
    if mode == "create":
        # 오늘 날짜를 기준으로 다음 주 월요일을 계산합니다.
        # (7 - today.weekday())는 다음 주 월요일까지 남은 날짜 수입니다.
        monday = today + timedelta(days=(7 - today.weekday()))
    else:
        # 오늘 날짜를 기준으로 이번 주 월요일을 계산합니다.
        # today.weekday()는 월요일(0)부터 일요일(6)까지의 요일을 나타냅니다.
        monday = today - timedelta(days=today.weekday())
    
    # 월요일 날짜에 6일을 더해 해당 주 일요일 날짜를 구합니다.
    sunday = monday + timedelta(days=6)
    return monday, sunday

def get_notified_deploy_keys():
    """
    이미 Slack 알림을 보낸 배포 티켓의 키 목록을 파일에서 읽어옵니다.
    이 함수는 중복 알림을 방지하기 위해 사용됩니다.

    Returns:
        set: 알림을 보낸 티켓 키들의 집합(set). 파일이 없거나 오류 발생 시 빈 집합을 반환합니다.
    """
    try:
        with open("notified_deploy_keys.json", "r") as f:
            # JSON 파일에서 리스트를 읽어와 set으로 변환하여 반환합니다.
            # set을 사용하면 중복된 키가 없고, 특정 키의 존재 여부를 O(1) 시간 복잡도로 빠르게 확인할 수 있습니다.
            return set(json.load(f))
    except Exception:
        # 파일이 존재하지 않거나 JSON 파싱 오류가 발생하면 빈 set을 반환합니다.
        return set()

def save_notified_deploy_keys(keys):
    """
    Slack 알림을 보낸 배포 티켓 키 목록을 JSON 파일에 저장합니다.

    Args:
        keys (set): 저장할 티켓 키들의 집합(set)
    """
    with open("notified_deploy_keys.json", "w") as f:
        # set을 list로 변환하여 JSON 형식으로 파일에 저장합니다.
        json.dump(list(keys), f)

def get_notified_changes():
    """
    이미 Slack 알림을 보낸 변경사항의 해시를 파일에서 읽어옵니다.
    이 함수는 중복 알림을 방지하기 위해 사용됩니다.

    Returns:
        set: 알림을 보낸 변경사항 해시들의 집합(set). 파일이 없거나 오류 발생 시 빈 집합을 반환합니다.
    """
    try:
        with open("notified_changes.json", "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_notified_changes(changes):
    """
    Slack 알림을 보낸 변경사항 해시를 JSON 파일에 저장합니다.

    Args:
        changes (set): 저장할 변경사항 해시들의 집합(set)
    """
    with open("notified_changes.json", "w") as f:
        json.dump(list(changes), f)

def generate_change_hash(changed_issues, page_title):
    """
    변경사항과 페이지 제목을 기반으로 고유한 해시를 생성합니다.
    
    Args:
        changed_issues (list): 변경된 이슈 목록
        page_title (str): 페이지 제목
        
    Returns:
        str: 변경사항의 고유 해시
    """
    # 변경사항을 정렬하여 일관된 해시 생성
    sorted_issues = sorted(changed_issues, key=lambda x: x['key'])
    change_data = {
        'page_title': page_title,
        'issues': [(issue['key'], issue['summary']) for issue in sorted_issues]
    }
    return json.dumps(change_data, sort_keys=True, ensure_ascii=False)

def get_slack_user_id_by_email(email):
    """
    Slack API를 사용하여 사용자의 이메일 주소로 Slack 내부 사용자 ID를 조회합니다.
    이 ID를 사용하여 메시지에서 사용자를 @멘션할 수 있습니다.
    .env 파일에 'SLACK_BOT_TOKEN'이 설정되어 있어야 하며, 해당 봇은 'users:read.email' 권한이 필요합니다.

    Args:
        email (str): 조회할 사용자의 이메일 주소

    Returns:
        str: Slack 사용자 ID (예: 'U12345678'). 사용자를 찾지 못하거나 오류 발생 시 None을 반환합니다.
    """
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        print("SLACK_BOT_TOKEN이 설정되어 있지 않아 사용자 태깅을 할 수 없습니다.")
        return None
    
    url = "https://slack.com/api/users.lookupByEmail"
    headers = {"Authorization": f"Bearer {slack_token}"}
    params = {"email": email}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # HTTP 에러 발생 시 예외를 발생시킵니다.
        data = response.json()
        if data.get("ok"):
            return data["user"]["id"]
        else:
            # Slack API가 'users_not_found' 에러를 반환하는 경우는 흔하므로,
            # 불필요한 로그를 줄이기 위해 해당 에러는 출력하지 않습니다.
            if data.get('error') != 'users_not_found':
                print(f"Slack에서 이메일({email})로 사용자 찾기 실패: {data.get('error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Slack API 호출 중 오류 발생: {e}")
        return None

def notify_new_deploy_tickets(issues, jira_url, page_title):
    """새로운 배포 티켓들을 Slack으로 알림을 보냅니다."""
    try:
        # 기존에 알림을 보낸 배포 키들을 로드
        notified_keys = get_notified_deploy_keys()
        
        # 새로운 배포 티켓들을 찾습니다
        new_deploy_tickets = []
        
        for issue in issues:
            issue_key = issue['key']
            
            # 이미 알림을 보낸 키는 건너뜁니다
            if issue_key in notified_keys:
                continue
            
            # 배포 관련 이슈 타입인지 확인
            issue_type = issue['fields'].get('issuetype', {}).get('name', '')
            if issue_type in ['Deploy', 'Release', '배포']:
                new_deploy_tickets.append({
                    'key': issue_key,
                    'summary': issue['fields'].get('summary', ''),
                    'status': issue['fields'].get('status', {}).get('name', ''),
                    'assignee': issue['fields'].get('assignee', {}).get('displayName', '미지정'),
                    'url': f"{jira_url}/browse/{issue_key}"
                })
        
        if new_deploy_tickets:
            # 부모 티켓별로 그룹화
            parent_ticket_groups = {}
            
            for ticket in new_deploy_tickets:
                # 부모 티켓 정보 가져오기 (실제로는 연결된 부모 티켓을 찾아야 함)
                parent_key = ticket['key'].split('-')[0] + '-PARENT'  # 예시
                
                if parent_key not in parent_ticket_groups:
                    parent_ticket_groups[parent_key] = []
                
                parent_ticket_groups[parent_key].append(ticket)
            
            # 그룹화된 알림 메시지 생성
            messages = []
            
            for parent_key, tickets in parent_ticket_groups.items():
                # 부모 티켓 정보
                parent_info = f"📋 *부모 티켓: {parent_key}*"
                
                # 배포 티켓들 정보
                ticket_details = []
                for ticket in tickets:
                    status_emoji = {
                        'To Do': '⏳',
                        'In Progress': '🔄', 
                        'Done': '✅',
                        '완료': '✅',
                        '실행': '🔄',
                        '대기': '⏳'
                    }.get(ticket['status'], '📝')
                    
                    ticket_details.append(
                        f"• {status_emoji} <{ticket['url']}|{ticket['key']}>: {ticket['summary']}\n"
                        f"  └ 담당자: {ticket['assignee']} | 상태: {ticket['status']}"
                    )
                
                group_message = f"{parent_info}\n" + "\n".join(ticket_details)
                messages.append(group_message)
            
            # 전체 알림 메시지
            if messages:
                full_message = f"🚀 *새로운 배포 티켓 알림*\n\n" + "\n\n".join(messages)
                full_message += f"\n\n📄 전체 리포트: {page_title}"
                
                send_slack(full_message)
                
                # 알림을 보낸 키들을 저장
                new_keys = [ticket['key'] for ticket in new_deploy_tickets]
                notified_keys.extend(new_keys)
                save_notified_deploy_keys(notified_keys)
                
                print(f"새로운 배포 티켓 알림 전송 완료: {len(new_deploy_tickets)}개")
        
    except Exception as e:
        print(f"배포 티켓 알림 전송 실패: {e}")
        log(f"배포 티켓 알림 전송 실패: {e}")


def serialize_issues(issues):
    """
    Jira 이슈 객체 리스트에서 비교에 필요한 주요 필드만 추출하여 정제된 리스트로 변환합니다.
    이 함수는 스냅샷 비교를 통해 이슈의 변경 여부를 감지하는 데 사용됩니다.

    Args:
        issues (list): 원본 Jira 이슈 객체 리스트

    Returns:
        list: 각 이슈의 주요 정보(key, summary, assignee, status, deploy_date)를 담은 딕셔너리 리스트.
              'key'를 기준으로 정렬되어 있어 리스트 간 비교가 용이합니다.
    """
    return sorted(
        [
            {
                "key": i["key"],
                "summary": i["fields"].get("summary", ""),
                "assignee": (
                    i["fields"].get("assignee", {}).get("displayName")
                    if i["fields"].get("assignee") else "미지정"
                ),
                "status": i["fields"].get("status", {}).get("name", ""),
                "deploy_date": i["fields"].get(JIRA_DEPLOY_DATE_FIELD_ID, ""),
            }
            for i in issues
        ],
        key=lambda x: x["key"] # 이슈 키를 기준으로 정렬하여 스냅샷 비교의 일관성을 보장합니다.
    )

def load_previous_snapshot(snapshot_path):
    """
    이전에 저장된 이슈 스냅샷을 JSON 파일에서 불러옵니다.

    Args:
        snapshot_path (str): 스냅샷 파일의 경로

    Returns:
        list: 이전에 저장된 이슈 스냅샷 데이터. 파일이 없거나 오류 발생 시 None을 반환합니다.
    """
    try:
        with open(snapshot_path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_snapshot(snapshot_path, data):
    """
    현재 이슈 스냅샷을 JSON 파일로 저장합니다.

    Args:
        snapshot_path (str): 저장할 스냅샷 파일의 경로
        data (list): 저장할 현재 이슈 스냅샷 데이터
    """
    with open(snapshot_path, "w", encoding='utf-8') as f:
        # ensure_ascii=False: 한글이 깨지지 않도록 설정
        # indent=2: 가독성을 위해 2칸 들여쓰기
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_issue_keys(issues, path='weekly_issues.json'):
    """
    Jira 이슈 리스트에서 이슈 키만 추출하여 JSON 파일로 저장합니다. (현재 스크립트에서는 사용되지 않음)

    Args:
        issues (list): Jira 이슈 객체 리스트
        path (str): 저장할 파일 경로
    """
    keys = [issue['key'] for issue in issues]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(keys, f, ensure_ascii=False, indent=2)

def get_now_str():
    """현재 시간을 'YYYY-MM-DD HH:MM:SS' 형식의 문자열로 반환합니다."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def write_cron_log(message):
    """스크립트 실행 로그를 'cron.log' 파일에 추가합니다."""
    with open("cron.log", "a", encoding="utf-8") as f:
        f.write(message + "\n")

# === [3단계] main() 간결화 및 불필요 코드/주석 제거 ===

def get_changed_issues(prev, curr, jira_url):
    """
    이전 스냅샷(prev)과 현재 스냅샷(curr)을 비교하여 변경된 IT티켓 목록을 반환합니다.
    - 새로 추가된 티켓
    - deploy_date(배포 예정일)가 변경된 티켓만 감지
    Args:
        prev (list): 이전 스냅샷
        curr (list): 현재 스냅샷
        jira_url (str): Jira base URL
    Returns:
        list: 변경된 티켓의 dict 목록 [{key, summary, url}]
    """
    prev_dict = {i['key']: i for i in prev or []}
    curr_dict = {i['key']: i for i in curr or []}
    changed = []
    for key, curr_issue in curr_dict.items():
        prev_issue = prev_dict.get(key)
        if not prev_issue:
            # 새로 추가된 티켓
            changed.append({
                'key': key,
                'summary': curr_issue.get('summary', ''),
                'url': f"{jira_url}/browse/{key}"
            })
        else:
            # deploy_date만 변경 여부 확인
            if curr_issue.get('deploy_date') != prev_issue.get('deploy_date'):
                changed.append({
                    'key': key,
                    'summary': curr_issue.get('summary', ''),
                    'url': f"{jira_url}/browse/{key}"
                })
    return changed

def check_jira_field_permissions(jira, field_id):
    """Jira 필드에 대한 권한을 체크합니다."""
    print(f"=== {field_id} 필드 권한 체크 시작 ===")
    
    results = {
        "field_exists": False,
        "metadata_access": False,
        "read_permission": False,
        "sort_permission": False,
        "filter_permission": False
    }
    
    try:
        # 1. 필드가 포함된 이슈 조회 시도
        print("1. 필드가 포함된 이슈 조회 시도...")
        test_jql = f"project = 'IT' AND {field_id} IS NOT EMPTY"
        print(f"   테스트 JQL: {test_jql}")
        try:
            issues = jira.search_issues(test_jql, fields=f"key,{field_id}", maxResults=1)
            if issues:
                print(f"   ✅ 필드가 포함된 이슈 조회 성공: {len(issues)}개")
                results["field_exists"] = True
                results["read_permission"] = True
            else:
                print("   ⚠️ 필드가 포함된 이슈가 없음 (필드가 존재하지 않거나 값이 없음)")
        except Exception as e:
            print(f"   ❌ 필드가 포함된 이슈 조회 실패: {e}")
        
        # 2. 필드로 정렬 시도
        print("2. 필드로 정렬 시도...")
        sort_jql = f"project = 'IT' ORDER BY {field_id} DESC"
        print(f"   정렬 테스트 JQL: {sort_jql}")
        try:
            issues = jira.search_issues(sort_jql, fields=f"key,{field_id}", maxResults=5)
            print(f"   ✅ 필드로 정렬 성공: {len(issues)}개")
            results["sort_permission"] = True
        except Exception as e:
            print(f"   ❌ 필드로 정렬 실패: {e}")
        
        # 3. 필드로 필터링 시도
        print("3. 필드로 필터링 시도...")
        filter_jql = f"project = 'IT' AND {field_id} >= '2024-01-01'"
        print(f"   필터링 테스트 JQL: {filter_jql}")
        try:
            issues = jira.search_issues(filter_jql, fields=f"key,{field_id}", maxResults=5)
            print(f"   ✅ 필드로 필터링 성공: {len(issues)}개")
            results["filter_permission"] = True
        except Exception as e:
            print(f"   ❌ 필드로 필터링 실패: {e}")
        
        # 4. 메타데이터 접근 시도
        print("4. 메타데이터 접근 시도...")
        try:
            # 간단한 이슈 조회로 필드 존재 여부 확인
            test_issues = jira.search_issues("project = 'IT'", fields=f"key,{field_id}", maxResults=1)
            if test_issues:
                # 첫 번째 이슈에서 필드 접근 시도
                first_issue = test_issues[0]
                field_value = getattr(first_issue.fields, field_id, None)
                if field_value is not None:
                    print(f"   ✅ 메타데이터 접근 성공: 필드 값 존재")
                    results["metadata_access"] = True
                else:
                    print(f"   ⚠️ 메타데이터 접근: 필드는 존재하지만 값이 없음")
            else:
                print("   ❌ 메타데이터 접근 실패: 이슈 조회 불가")
        except Exception as e:
            print(f"   ❌ 메타데이터 접근 실패: {e}")
        
    except Exception as e:
        print(f"권한 체크 중 오류 발생: {e}")
    
    # 결과 요약
    print("\n=== 권한 체크 결과 요약 ===")
    print(f"필드 존재: {'✅' if results['field_exists'] else '❌'}")
    print(f"메타데이터 접근: {'✅' if results['metadata_access'] else '❌'}")
    print(f"읽기 권한: {'✅' if results['read_permission'] else '❌'}")
    print(f"정렬 권한: {'✅' if results['sort_permission'] else '❌'}")
    print(f"필터링 권한: {'✅' if results['filter_permission'] else '❌'}")
    
    return results

def test_jira_field_access():
    """Jira 필드 접근 권한을 테스트합니다."""
    try:
        # 환경 변수 로딩
        env_vars = load_env_vars([
            'ATLASSIAN_URL', 'ATLASSIAN_USERNAME', 'ATLASSIAN_API_TOKEN'
        ])
        
        atlassian_url = env_vars['ATLASSIAN_URL']
        atlassian_username = env_vars['ATLASSIAN_USERNAME']
        atlassian_token = env_vars['ATLASSIAN_API_TOKEN']
        jira_project_key = os.getenv('JIRA_PROJECT_KEY', 'IT')
        
        # Jira 클라이언트 초기화
        jira = JIRA(server=atlassian_url, basic_auth=(atlassian_username, atlassian_token))
        print(f"Jira 서버 연결 성공!")
        
        # 1. 권한 체크
        result = check_jira_field_permissions(jira, JIRA_DEPLOY_DATE_FIELD_ID)
        
        # 2. 직접 조회 테스트
        print(f"\n=== 직접 조회 테스트 ===")
        start_date = "2025-07-21"
        end_date = "2025-07-27"
        
        direct_count = test_customfield_10817_only(jira, jira_project_key, start_date, end_date)
        
        print(f"\n=== 최종 결과 ===")
        print(f"권한 체크 결과: {result}")
        print(f"직접 조회 결과: {direct_count}개 이슈")
        
        if direct_count > 0:
            print("✅ customfield_10817 직접 조회 가능!")
        else:
            print("❌ customfield_10817 직접 조회 불가능 - 스마트 필터링 필요")
            
    except Exception as e:
        print(f"❌ 권한 체크 중 오류 발생: {e}")

def get_jira_issues_smart_filtering(jira, project_key, start_date, end_date):
    """스마트 필터링: 다양한 날짜 필드를 조합하여 배포 예정 이슈를 찾습니다."""
    print(f"=== 스마트 필터링 시작 ===")
    print(f"대상 기간: {start_date} ~ {end_date}")
    
    # 1단계: 기본 JQL로 모든 이슈 조회
    base_jql = f"project = '{project_key}' ORDER BY updated DESC"
    print(f"기본 JQL: {base_jql}")
    
    try:
        # 모든 필드를 조회
        fields_param = "key,summary,status,assignee,created,updated,duedate,customfield_10817"
        issues = jira.search_issues(base_jql, fields=fields_param)
        print(f"✅ 전체 이슈 조회 성공: {len(issues)}개")
        
        # 2단계: 다양한 날짜 필드로 스마트 필터링 (우선순위 적용)
        filtered_issues = []
        date_fields_used = []
        
        # 필드 우선순위 정의 (높은 우선순위가 먼저)
        field_priority = {
            JIRA_DEPLOY_DATE_FIELD_ID: 1,  # 예정된 시작 (최우선)
            'duedate': 2,                   # 마감일
            'created': 3,                   # 생성일
            'updated': 4                    # 수정일
        }
        
        for issue in issues:
            fields = issue.fields
            issue_key = issue.key
            
            # 다양한 날짜 필드 확인 (우선순위 순서로)
            date_candidates = []
            
            for field_name, priority in sorted(field_priority.items(), key=lambda x: x[1]):
                field_value = getattr(fields, field_name, None)
                if field_value:
                    try:
                        date_str = str(field_value)[:10]  # YYYY-MM-DD
                        date_candidates.append((field_name, date_str, priority))
                    except:
                        pass
            
            # 날짜 범위 내에 있는지 확인 (우선순위 높은 것부터)
            is_in_range = False
            used_field = None
            used_date = None
            
            for field_name, date_str, priority in date_candidates:
                try:
                    field_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    
                    if start_date_obj <= field_date <= end_date_obj:
                        is_in_range = True
                        used_field = field_name
                        used_date = date_str
                        break  # 우선순위가 높은 필드를 찾으면 중단
                except Exception as e:
                    continue
            
            if is_in_range:
                # 딕셔너리 형태로 변환
                issue_dict = {
                    'key': issue_key,
                    'fields': {
                        'summary': getattr(fields, 'summary', ''),
                        'status': {'name': getattr(fields, 'status', '').name if hasattr(getattr(fields, 'status', ''), 'name') else ''},
                        'assignee': getattr(fields, 'assignee', ''),
                        'created': str(getattr(fields, 'created', '')),
                        'updated': str(getattr(fields, 'updated', '')),
                        JIRA_DEPLOY_DATE_FIELD_ID: str(getattr(fields, JIRA_DEPLOY_DATE_FIELD_ID, ''))
                    }
                }
                filtered_issues.append(issue_dict)
                date_fields_used.append(used_field)
                print(f"✅ {issue_key}: {used_field} 필드 사용 ({used_date}) [우선순위: {field_priority[used_field]}]")
        
        # 3단계: 통계 분석
        field_counts = {}
        for field in date_fields_used:
            field_counts[field] = field_counts.get(field, 0) + 1
        
        print(f"=== 스마트 필터링 완료 ===")
        print(f"필터링된 이슈: {len(filtered_issues)}개")
        print(f"사용된 필드 분포: {field_counts}")
        
        # 4단계: 품질 지표 계산
        if filtered_issues:
            priority_1_count = field_counts.get(JIRA_DEPLOY_DATE_FIELD_ID, 0)
            total_count = len(filtered_issues)
            accuracy_rate = (priority_1_count / total_count) * 100
            print(f"📊 품질 지표: {accuracy_rate:.1f}% 이슈가 최우선 필드({JIRA_DEPLOY_DATE_FIELD_ID}) 사용")
        
        return filtered_issues
        
    except Exception as e:
        print(f"스마트 필터링 실패: {e}")
        return []

def test_customfield_10817_only(jira, project_key, start_date, end_date):
    """customfield_10817만 사용하여 직접 조회 테스트"""
    print(f"=== customfield_10817 직접 조회 테스트 ===")
    print(f"대상 기간: {start_date} ~ {end_date}")
    
    # customfield_10817를 직접 사용한 JQL
    jql_query = (
        f"project = '{project_key}' AND "
        f"'{JIRA_DEPLOY_DATE_FIELD_ID}' >= '{start_date}' AND '{JIRA_DEPLOY_DATE_FIELD_ID}' <= '{end_date}' "
        f"ORDER BY '{JIRA_DEPLOY_DATE_FIELD_ID}' ASC"
    )
    print(f"JQL 쿼리: {jql_query}")
    
    try:
        # search_issues 사용
        fields_param = f"key,summary,status,assignee,{JIRA_DEPLOY_DATE_FIELD_ID}"
        issues = jira.search_issues(jql_query, fields=fields_param)
        
        print(f"✅ customfield_10817 직접 조회 성공: {len(issues)}개 이슈")
        
        if issues:
            print("\n=== 조회된 이슈 목록 ===")
            for i, issue in enumerate(issues, 1):
                custom_field_value = getattr(issue.fields, JIRA_DEPLOY_DATE_FIELD_ID, None)
                print(f"{i}. {issue.key}: {issue.fields.summary}")
                print(f"   예정된 시작: {custom_field_value}")
                print(f"   상태: {issue.fields.status.name if hasattr(issue.fields.status, 'name') else issue.fields.status}")
                print()
        else:
            print("❌ customfield_10817로 조회된 이슈가 없습니다.")
            
        return len(issues)
        
    except Exception as e:
        print(f"❌ customfield_10817 직접 조회 실패: {e}")
        return 0

def get_jira_issues_by_customfield_10817(jira, project_key, start_date, end_date):
    """customfield_10817 필드 값이 해당 주간에 속하는 모든 티켓을 조회합니다."""
    print(f"=== customfield_10817 직접 조회 시작 ===")
    print(f"프로젝트: {project_key}")
    print(f"대상 기간: {start_date} ~ {end_date}")
    
    try:
        # 1단계: 프로젝트의 모든 티켓 조회 (customfield_10817 필드 포함)
        base_jql = f"project = '{project_key}' ORDER BY updated DESC"
        fields_param = f"key,summary,status,assignee,created,updated,{JIRA_DEPLOY_DATE_FIELD_ID}"
        
        print(f"기본 JQL: {base_jql}")
        print(f"조회 필드: {fields_param}")
        
        # 모든 티켓 조회
        all_issues = jira.search_issues(base_jql, fields=fields_param, maxResults=1000)
        print(f"✅ 전체 티켓 조회 성공: {len(all_issues)}개")
        
        # 2단계: customfield_10817 필드 값이 해당 주간에 속하는 티켓 필터링
        filtered_issues = []
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        print(f"\n=== customfield_10817 필드 값 필터링 ===")
        
        for issue in all_issues:
            issue_key = issue.key
            custom_field_value = getattr(issue.fields, JIRA_DEPLOY_DATE_FIELD_ID, None)
            
            if custom_field_value:
                try:
                    # 날짜 문자열 파싱 (예: "2025-07-23T11:00:00.000+0900")
                    date_str = str(custom_field_value)
                    
                    # ISO 형식 날짜 파싱
                    if 'T' in date_str:
                        # ISO 형식: "2025-07-23T11:00:00.000+0900"
                        date_part = date_str.split('T')[0]
                    else:
                        # 단순 날짜 형식: "2025-07-23"
                        date_part = date_str[:10]
                    
                    field_date = datetime.strptime(date_part, '%Y-%m-%d').date()
                    
                    # 해당 주간에 속하는지 확인
                    if start_date_obj <= field_date <= end_date_obj:
                        # 딕셔너리 형태로 변환
                        issue_dict = {
                            'key': issue_key,
                            'fields': {
                                'summary': getattr(issue.fields, 'summary', ''),
                                'status': {'name': getattr(issue.fields, 'status', '').name if hasattr(getattr(issue.fields, 'status', ''), 'name') else ''},
                                'assignee': getattr(issue.fields, 'assignee', ''),
                                'created': str(getattr(issue.fields, 'created', '')),
                                'updated': str(getattr(issue.fields, 'updated', '')),
                                JIRA_DEPLOY_DATE_FIELD_ID: str(custom_field_value)
                            }
                        }
                        filtered_issues.append(issue_dict)
                        print(f"✅ {issue_key}: {field_date} (예정된 시작: {custom_field_value})")
                    else:
                        print(f"⏭️ {issue_key}: {field_date} (범위 외)")
                        
                except Exception as e:
                    print(f"❌ {issue_key}: 날짜 파싱 오류 - {custom_field_value} ({e})")
                    continue
            else:
                print(f"⏭️ {issue_key}: customfield_10817 값 없음")
        
        print(f"\n=== 필터링 결과 ===")
        print(f"전체 티켓: {len(all_issues)}개")
        print(f"customfield_10817 값이 있는 티켓: {len([i for i in all_issues if getattr(i.fields, JIRA_DEPLOY_DATE_FIELD_ID, None)])}개")
        print(f"해당 주간에 속하는 티켓: {len(filtered_issues)}개")
        
        # 3단계: 날짜순 정렬
        filtered_issues.sort(key=lambda x: x['fields'].get(JIRA_DEPLOY_DATE_FIELD_ID, ''))
        
        print(f"\n=== 최종 결과 ===")
        for i, issue in enumerate(filtered_issues, 1):
            print(f"{i}. {issue['key']}: {issue['fields']['summary']}")
            print(f"   예정된 시작: {issue['fields'].get(JIRA_DEPLOY_DATE_FIELD_ID, 'N/A')}")
            print(f"   상태: {issue['fields']['status']['name']}")
            print()
        
        return filtered_issues
        
    except Exception as e:
        print(f"❌ customfield_10817 직접 조회 실패: {e}")
        return []

def main():
    # 1. 환경 변수 로딩
    env_vars = load_env_vars([
        'ATLASSIAN_URL', 'ATLASSIAN_USERNAME', 'ATLASSIAN_API_TOKEN',
        'SLACK_WEBHOOK_URL', 'SLACK_BOT_TOKEN'
    ])
    
    atlassian_url = env_vars['ATLASSIAN_URL']
    atlassian_username = env_vars['ATLASSIAN_USERNAME']
    atlassian_token = env_vars['ATLASSIAN_API_TOKEN']
    slack_webhook_url = env_vars['SLACK_WEBHOOK_URL']
    slack_bot_token = env_vars['SLACK_BOT_TOKEN']
    
    # 추가 환경 변수
    jira_project_key = os.getenv('JIRA_PROJECT_KEY', 'IT')
    confluence_space_key = os.getenv('CONFLUENCE_SPACE_KEY', 'DEV')
    parent_page_id = "4596203549"  # 고정값 사용
    
    # 2. API 클라이언트 생성
    try:
        jira = JIRA(server=atlassian_url, basic_auth=(atlassian_username, atlassian_token))
        confluence = Confluence(url=atlassian_url, username=atlassian_username, password=atlassian_token, cloud=True)
        print(f"\nJira/Confluence 서버 연결 성공!: {get_now_str()}")
    except Exception as e:
        print(f"Jira/Confluence 연결 오류: {e}")
        return
    
    # 3. 명령행 인수 처리
    mode = "update"  # 기본값
    force_update = False  # 강제 업데이트 플래그
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test-permissions":
            test_jira_field_access()
            return
        elif sys.argv[1] == "--check-page":
            check_confluence_page_content()
            return
        elif sys.argv[1] == "--force-update":
            mode = "update"
            force_update = True
        else:
            mode = sys.argv[1]
    
    # 4. 날짜 범위 계산
    monday, sunday = get_week_range(mode)
    start_date_str, end_date_str = monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')
    page_title = get_page_title(monday, sunday)
    
    # 모드별 설명 메시지
    mode_descriptions = {
        "create": "다음 주 (차주) 배포 예정 티켓으로 리포트 생성",
        "current": "이번 주 (현재 주) 배포 예정 티켓으로 리포트 생성/업데이트", 
        "last": "지난 주 배포 예정 티켓으로 리포트 생성/업데이트",
        "update": "이번 주 배포 예정 티켓으로 리포트 업데이트 (기본값)"
    }
    mode_desc = mode_descriptions.get(mode, "이번 주")
    print(f"실행 모드: {mode} ({mode_desc})")
    print(f"대상 기간: {start_date_str} ~ {end_date_str}")
    print(f"페이지 제목: {page_title}")

    # 5. Jira 이슈 조회 (customfield_10817 직접 조회 사용)
    jql_query = (
        f"project = '{jira_project_key}' AND "
        f"'{JIRA_DEPLOY_DATE_FIELD_ID}' >= '{start_date_str}' AND '{JIRA_DEPLOY_DATE_FIELD_ID}' <= '{end_date_str}' "
        f"ORDER BY updated DESC"
    )
    issues = get_jira_issues_by_customfield_10817(jira, jira_project_key, start_date_str, end_date_str)
    if not issues:
        print(f"{mode_desc}에 배포 예정 티켓 없음. 빈 테이블로 생성/업데이트.")

    # 6. 변경 감지
    SNAPSHOT_FILE_PATH = 'weekly_issues_snapshot.json'
    prev_snapshot = read_json(SNAPSHOT_FILE_PATH)
    curr_snapshot = snapshot_issues(issues, JIRA_DEPLOY_DATE_FIELD_ID)
    
    # create, current 모드에서는 이슈 변경 여부와 관계없이 페이지 생성/업데이트 진행
    if mode in ["create", "current"]:
        changed_issues = get_changed_issues(prev_snapshot, curr_snapshot, atlassian_url)
    else:
        # update 모드에서만 이슈 변경 감지 (강제 업데이트 제외)
        if not force_update and not issues_changed(prev_snapshot, curr_snapshot):
            print(f"JIRA 이슈 변경 없음. 업데이트/알림 생략. {get_now_str()}")
            log(f"\n실행시간: {get_now_str()}\n업데이트 할 사항 없음.")
            return
        changed_issues = get_changed_issues(prev_snapshot, curr_snapshot, atlassian_url)

    # 7. Confluence 페이지 생성/업데이트 및 Slack 알림
    page_content = create_confluence_content(jql_query, issues, atlassian_url, jira, jira_project_key, start_date_str, end_date_str)
    try:
        if confluence.page_exists(space=confluence_space_key, title=page_title):
            page_id = confluence.get_page_id(space=confluence_space_key, title=page_title)
            page_url = f"{atlassian_url}/wiki/spaces/{confluence_space_key}/pages/{page_id}"
            current_page = confluence.get_page_by_id(page_id, expand='body.storage')
            current_content = current_page.get('body', {}).get('storage', {}).get('value', '')
            if normalize_html_content(current_content) != normalize_html_content(page_content):
                confluence.update_page(
                    page_id=page_id, title=page_title, body=page_content,
                    parent_id=parent_page_id, type='page', representation='storage'
                )
                print(f"'{page_title}' 페이지 업데이트 완료.")
                
                # 중복 알림 방지를 위한 변경사항 해시 확인
                notified_changes = get_notified_changes()
                change_hash = generate_change_hash(changed_issues, page_title)
                
                # 변경사항이 있고, 아직 알림을 보내지 않은 경우에만 Slack 알림 전송
                if changed_issues and change_hash not in notified_changes:
                    issue_list = '\n'.join([
                        f"- <{i['url']}|{i['key']}: {i['summary']}>" for i in changed_issues
                    ])
                    slack_msg = f"🔄 배포 일정 리포트가 업데이트되었습니다:\n{page_title}\n{page_url}\n\n[업데이트된 IT티켓 목록]\n{issue_list}"
                    send_slack(slack_msg)
                    # 알림을 보낸 변경사항 해시를 저장
                    notified_changes.add(change_hash)
                    save_notified_changes(notified_changes)
                    print(f"Slack 알림 전송 완료 (변경사항: {len(changed_issues)}개)")
                elif changed_issues:
                    print(f"동일한 변경사항에 대한 알림이 이미 전송됨 (변경사항: {len(changed_issues)}개)")
                else:
                    slack_msg = f"🔄 배포 일정 리포트가 업데이트되었습니다:\n{page_title}\n{page_url}"
                    send_slack(slack_msg)
                
                notify_new_deploy_tickets(issues, atlassian_url, page_title)
                log(f"실행시간: {get_now_str()}\n대상: {', '.join([i['key'] for i in issues])} 업데이트.")
            else:
                print(f"'{page_title}' 페이지 내용 변경 없음. 업데이트 생략.")
                log(f"실행시간: {get_now_str()}\n업데이트 할 사항 없음.")
        else:
            confluence.create_page(
                space=confluence_space_key, title=page_title, body=page_content,
                parent_id=parent_page_id, representation='storage'
            )
            print("✅ Confluence 페이지 생성 완료!")
            page_id = confluence.get_page_id(space=confluence_space_key, title=page_title)
            page_url = f"{atlassian_url}/wiki/spaces/{confluence_space_key}/pages/{page_id}"
            
            # 중복 알림 방지를 위한 변경사항 해시 확인
            notified_changes = get_notified_changes()
            change_hash = generate_change_hash(changed_issues, page_title)
            
            # 변경사항이 있고, 아직 알림을 보내지 않은 경우에만 Slack 알림 전송
            if changed_issues and change_hash not in notified_changes:
                issue_list = '\n'.join([
                    f"- <{i['url']}|{i['key']}: {i['summary']}>" for i in changed_issues
                ])
                slack_msg = f"🔄 배포 일정 리포트가 업데이트되었습니다:\n{page_title}\n{page_url}\n\n[업데이트된 IT티켓 목록]\n{issue_list}"
                send_slack(slack_msg)
                # 알림을 보낸 변경사항 해시를 저장
                notified_changes.add(change_hash)
                save_notified_changes(notified_changes)
                print(f"Slack 알림 전송 완료 (변경사항: {len(changed_issues)}개)")
            elif changed_issues:
                print(f"동일한 변경사항에 대한 알림이 이미 전송됨 (변경사항: {len(changed_issues)}개)")
            else:
                slack_msg = f"🔄 배포 일정 리포트가 업데이트되었습니다:\n{page_title}\n{page_url}"
                send_slack(slack_msg)
            
            notify_new_deploy_tickets(issues, atlassian_url, page_title)
            log(f"실행시간: {get_now_str()}\n대상: {', '.join([i['key'] for i in issues])} 생성.")
        
        # 스냅샷 저장
        write_json(SNAPSHOT_FILE_PATH, curr_snapshot)
        
    except Exception as e:
        error_msg = f"Confluence 페이지 생성/업데이트 실패: {e}"
        print(error_msg)
        log(error_msg)
        raise

def check_confluence_page_content():
    """Confluence 페이지 내용을 확인합니다."""
    try:
        # 환경 변수 로딩
        env_vars = load_env_vars([
            'ATLASSIAN_URL', 'ATLASSIAN_USERNAME', 'ATLASSIAN_API_TOKEN'
        ])
        
        atlassian_url = env_vars['ATLASSIAN_URL']
        atlassian_username = env_vars['ATLASSIAN_USERNAME']
        atlassian_token = env_vars['ATLASSIAN_API_TOKEN']
        confluence_space_key = os.getenv('CONFLUENCE_SPACE_KEY', 'DEV')
        
        # Confluence 클라이언트 초기화
        confluence = Confluence(url=atlassian_url, username=atlassian_username, password=atlassian_token, cloud=True)
        
        # 페이지 제목
        page_title = "7월 4째주: (07/21~07/27)"
        
        # 페이지 존재 확인
        if confluence.page_exists(space=confluence_space_key, title=page_title):
            page_id = confluence.get_page_id(space=confluence_space_key, title=page_title)
            page_url = f"{atlassian_url}/wiki/spaces/{confluence_space_key}/pages/{page_id}"
            
            # 페이지 내용 가져오기
            page_content = confluence.get_page_by_id(page_id, expand='body.storage')
            content = page_content.get('body', {}).get('storage', {}).get('value', '')
            
            print(f"=== Confluence 페이지 내용 ===")
            print(f"페이지 제목: {page_title}")
            print(f"페이지 URL: {page_url}")
            print(f"페이지 ID: {page_id}")
            print(f"\n=== 페이지 내용 ===")
            print(content)
            
            return content
        else:
            print(f"페이지가 존재하지 않습니다: {page_title}")
            return None
            
    except Exception as e:
        print(f"페이지 내용 확인 실패: {e}")
        return None

def create_deploy_links_html_table(jira, jql_query, jira_url):
    """IT 티켓만 표시하는 배포 예정 목록 HTML 테이블을 생성합니다. (기존 함수 - 호환성용)"""
    try:
        # JQL 쿼리를 단순화하여 필드 접근 문제를 우회
        simple_jql = "project = 'IT' ORDER BY updated DESC"
        print(f"=== 배포 예정 목록 조회 시작 (기존 방식) ===")
        print(f"원본 JQL 쿼리: {jql_query}")
        print(f"단순화된 JQL 쿼리: {simple_jql}")
        print(f"JIRA_DEPLOY_DATE_FIELD_ID 값: '{JIRA_DEPLOY_DATE_FIELD_ID}'")
        
        # fields 파라미터에서도 변수 사용
        fields_param = f"key,summary,status,issuelinks,{JIRA_DEPLOY_DATE_FIELD_ID}"
        print(f"fields 파라미터: '{fields_param}'")
        
        issues = jira.search_issues(simple_jql, fields=fields_param)
        print(f"✅ 쿼리 성공: {len(issues)}개 이슈 발견")
        
        # Python에서 날짜 필터링
        filtered_issues = []
        for issue in issues:
            field_value = getattr(issue.fields, JIRA_DEPLOY_DATE_FIELD_ID, None)
            if field_value:
                try:
                    # 날짜 문자열을 파싱하여 비교 (JQL 쿼리에서 날짜 추출)
                    import re
                    date_match = re.search(r"'([^']+)' >= '([^']+)' AND '[^']+' <= '([^']+)'", jql_query)
                    if date_match:
                        start_date = date_match.group(2)
                        end_date = date_match.group(3)
                        
                        field_date = datetime.strptime(str(field_value)[:10], '%Y-%m-%d').date()
                        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                        
                        if start_date_obj <= field_date <= end_date_obj:
                            # 딕셔너리 형태로 변환
                            issue_dict = {
                                'key': issue.key,
                                'fields': {
                                    'summary': getattr(issue.fields, 'summary', ''),
                                    'status': {'name': getattr(issue.fields, 'status', '').name if hasattr(getattr(issue.fields, 'status', ''), 'name') else ''},
                                    JIRA_DEPLOY_DATE_FIELD_ID: str(field_value)
                                }
                            }
                            filtered_issues.append(issue_dict)
                except Exception as e:
                    print(f"날짜 파싱 오류 ({issue.key}): {e}")
                    continue
        
        print(f"✅ 날짜 필터링 완료: {len(filtered_issues)}개 이슈")
        
        # 정렬 권한이 없으므로 Python에서 정렬
        if filtered_issues:
            # customfield_10817 값으로 정렬 (None 값은 맨 뒤로)
            sorted_issues = sorted(
                filtered_issues, 
                key=lambda x: (
                    x['fields'].get(JIRA_DEPLOY_DATE_FIELD_ID) is None,
                    x['fields'].get(JIRA_DEPLOY_DATE_FIELD_ID) or ''
                )
            )
            print(f"✅ Python에서 정렬 완료: {len(sorted_issues)}개 이슈")
        else:
            sorted_issues = filtered_issues
        
        # 각 이슈의 정보 출력 (디버깅용)
        for i, issue in enumerate(sorted_issues, 1):
            issue_key = issue['key']
            summary = issue['fields'].get('summary', '')
            status = issue['fields'].get('status', {}).get('name', '')
            custom_field = issue['fields'].get(JIRA_DEPLOY_DATE_FIELD_ID, '')
            
            print(f"\n--- 이슈 {i} ---")
            print(f"키: {issue_key}")
            print(f"요약: {summary}")
            print(f"상태: {status}")
            print(f"예정된 시작 ({JIRA_DEPLOY_DATE_FIELD_ID}): {custom_field}")
            
            # IT 티켓만 필터링하여 연결된 이슈 조회
            linked_it_tickets = get_linked_it_tickets(jira, issue_key)
            print(f"연결된 IT 티켓 수: {len(linked_it_tickets)}")
            
            for j, ticket in enumerate(linked_it_tickets, 1):
                print(f"  {j}. {ticket['key']}: {ticket['summary']}")
        
        html_content = '''
<h2 style="margin-top: 20px;">배포 예정 목록</h2>
<p><em>아래 표는 이번 주 배포 예정인 부모 IT 티켓들을 보여줍니다. 각 티켓의 배포 관계는 Jira에서 직접 확인하실 수 있습니다.</em></p>

<div style="background-color: #f4f5f7; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
<h4> 배포 관계 표시 형식 안내</h4>
<p>아래 표의 <strong>연결된 이슈</strong> 컬럼에는 다음과 같은 형식으로 배포 관계가 표시됩니다:</p>
<ul>
<li><strong>부모 IT 티켓</strong>: 배포 대상이 되는 IT 티켓</li>
<li><strong>배포 티켓</strong>: "is deployed by" 관계로 연결된 IT 티켓들만 표시</li>
<li><strong>표시 형식</strong>: 각 배포 티켓이 새로운 줄로 구분되어 표시됩니다</li>
</ul>
<p><em>예시: IT-6516 티켓의 경우, prod-beluga-manager-consumer로 "deploy"에 대한 배포 Release(IT-4831, IT-5027) v1.5.0 (#166) 형태로 표시됩니다.</em></p>
</div>

<table class="wrapped" style="width: 100%;">
<colgroup>
<col style="width: 120px;" />
<col style="width: 300px;" />
<col style="width: 400px;" />
</colgroup>
<tbody>
<tr>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">키</th>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">요약</th>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">연결된 이슈</th>
</tr>
'''
        
        for i, issue in enumerate(sorted_issues, 1):
            issue_key = issue['key']
            summary = issue['fields'].get('summary', '')
            status = issue['fields'].get('status', {}).get('name', '')
            
            # IT 티켓만 필터링하여 연결된 이슈 조회
            linked_it_tickets = get_linked_it_tickets(jira, issue_key)
            
            # 연결된 IT 티켓들을 포맷팅
            if linked_it_tickets:
                linked_tickets_html = '<br>'.join([
                    f"{i}. {ticket['key']}<br>: {ticket['summary']}"
                    for i, ticket in enumerate(linked_it_tickets, 1)
                ])
            else:
                linked_tickets_html = '<em>연결된 IT 티켓 없음</em>'
            
            html_content += f'''
<tr>
<td style="padding: 8px; border: 1px solid #dfe1e6;"><a href="{jira_url}/browse/{issue_key}">{issue_key}</a></td>
<td style="padding: 8px; border: 1px solid #dfe1e6;">{summary}</td>
<td style="padding: 8px; border: 1px solid #dfe1e6;">{linked_tickets_html}</td>
</tr>
'''
        
        html_content += '''
</tbody>
</table>
'''
        
        print(f"=== 배포 예정 목록 조회 완료 (기존 방식) ===")
        return html_content
        
    except Exception as e:
        print(f"배포 예정 목록 HTML 테이블 생성 실패: {e}")
        return f'<p>배포 예정 목록 HTML 테이블 생성 중 오류가 발생했습니다: {e}</p>'

if __name__ == "__main__":
    import sys
    
    # 명령행 인수 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--check-permissions":
        print("=== Jira 필드 권한 체크 모드 ===")
        test_jira_field_access()
    else:
        # 기존 main 함수 실행
        main()
