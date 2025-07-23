
# -*- coding: utf-8 -*-
# 필요한 외부 라이브러리와 환경 변수들을 불러옵니다.
import os
import datetime
import sys
from dotenv import load_dotenv
from atlassian.jira import Jira
from atlassian.confluence import Confluence
import requests
import json
import re
import html
from datetime import datetime, date, timedelta

# .env 파일에서 환경 변수들을 읽어와서 현재 환경에 설정합니다.
# 예: ATLASSIAN_URL, ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN, SLACK_WEBHOOK_URL, SLACK_BOT_TOKEN 등
load_dotenv()

# --- 스크립트 설정 값 ---

# Jira에서 '예정된 시작' 날짜를 나타내는 커스텀 필드의 ID입니다.
# 이 필드를 기준으로 배포 일정을 조회합니다.
JIRA_DEPLOY_DATE_FIELD_ID = "customfield_10817" 

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
  <ac:parameter ac:name="maximumIssues">1000</ac:parameter>
</ac:structured-macro>
'''

# 각 날짜 컬럼별로 다른 포맷을 적용하는 예시 (필요시 사용)
JIRA_CUSTOM_DATE_FORMAT_TEMPLATE = '''
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="columns">key,type,summary,assignee,status,created,updated,예정된 시작</ac:parameter>
  <ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>
  <ac:parameter ac:name="dateFormat">yyyy-MM-dd HH:mm</ac:parameter>
  <ac:parameter ac:name="columnWidths">100,80,300,120,100,150,150,150</ac:parameter>
</ac:structured-macro>
'''

DEPLOY_LINKS_TABLE_HEADER = """
<h2 style="margin-top: 20px;">배포티켓 링크 목록</h2>
<table style="width: 100%; border-collapse: collapse;">
  <thead>
    <tr>
      <th>Jira Issue</th>
      <th>배포티켓(링크)</th>
    </tr>
  </thead>
  <tbody>
"""

DEPLOY_LINKS_TABLE_ROW = """
<tr>
  <td><a href=\"{ticket_url}\" target=\"_blank\">{key}</a><br/>: {summary}</td>
  <td>{deploy_tickets_html}</td>
</tr>
"""

DEPLOY_LINKS_TABLE_FOOTER = "</tbody></table>"

# === [2단계] API/알림/스냅샷 래퍼 함수 간소화 ===
def get_jira_issues_simple(jira, project_key, date_field_id, start_date, end_date):
    jql_query = (
        f"project = '{project_key}' AND "
        f"'{date_field_id}' >= '{start_date}' AND '{date_field_id}' <= '{end_date}' "
        f"ORDER BY '{date_field_id}' ASC"
    )
    print(f"JQL: {jql_query}")
    try:
        issues = jira.jql(jql_query, fields="*all")
        return issues['issues']
    except Exception as e:
        print(f"Jira 검색 오류: {e}")
        return []

def get_jira_issues_with_links(jira, project_key, date_field_id, start_date, end_date):
    """Jira 이슈를 조회하고 각 이슈의 'is deployed by' 관계를 포함하여 반환합니다."""
    jql_query = (
        f"project = '{project_key}' AND "
        f"'{date_field_id}' >= '{start_date}' AND '{date_field_id}' <= '{end_date}' "
        f"ORDER BY '{date_field_id}' ASC"
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
    macro = JIRA_FULL_MACRO_TEMPLATE.format(jql_query=jql_query)
    html_rows = []
    
    # 배포티켓 링크 데이터 로드 (기본 데이터)
    deploy_links_data = load_deploy_ticket_links()
    
    # 이슈 키와 배포티켓 링크 매핑 생성 (기본 데이터)
    deploy_links_map = {}
    for item in deploy_links_data:
        issue_key = item.get('issue', '')
        deployed_by = item.get('deployedBy', [])
        if deployed_by:  # 배포티켓이 있는 경우만 추가
            deploy_links_map[issue_key] = deployed_by
    
    # Macro table에 표시된 IT 티켓들을 배포티켓 링크 목록에 표시
    if not issues:
        print("Macro table에 이슈가 없으므로 실제 Jira 이슈를 조회하여 사용합니다.")
        # 실제 Jira 이슈를 조회하여 사용
        try:
            # Jira에서 실제 이슈들을 동적으로 조회
            jql_query = f"project = '{jira_project_key}' AND status IN ('실행', '실행을 기다리는 중', '완료') ORDER BY updated DESC"
            macro_table_issues = []
            
            # Jira에서 이슈들을 조회
            jira_issues = jira.jql(jql_query)
            
            # jql 결과가 딕셔너리인 경우 'issues' 키 사용
            if isinstance(jira_issues, dict):
                issues_list = jira_issues.get('issues', [])
                print(f"JQL 결과에서 {len(issues_list)}개의 이슈를 찾았습니다.")
            else:
                issues_list = jira_issues if isinstance(jira_issues, list) else []
            
            # 부모티켓만 필터링 (배포티켓 제외)
            parent_issues = []
            for jira_issue in issues_list:
                try:
                    # jira_issue가 딕셔너리인 경우 'key' 사용
                    if isinstance(jira_issue, dict):
                        issue_key = jira_issue.get('key', '')
                    elif isinstance(jira_issue, str):
                        issue_key = jira_issue
                    else:
                        issue_key = jira_issue.key
                    
                    if not issue_key:
                        continue
                    
                    # 배포티켓 패턴 제외 (IT-6xxx, IP-xxxx 등 배포 관련 티켓들)
                    if any(issue_key.startswith(prefix) for prefix in ['IT-6', 'IP-', 'WEB-', 'SS-', 'MP-']):
                        # 배포티켓은 건너뛰기
                        continue
                        
                    # 각 이슈의 issuelinks를 확장하여 조회
                    issue_response = jira.issue(issue_key, expand='issuelinks')
                    
                    # 응답이 딕셔너리인지 확인
                    if isinstance(issue_response, dict):
                        print(f"'{issue_key}' 응답이 딕셔너리 형태입니다.")
                        # 딕셔너리 형태인 경우 직접 접근
                        summary = issue_response.get('fields', {}).get('summary', '조회 실패')
                        issuelinks = issue_response.get('fields', {}).get('issuelinks', [])
                        
                        print(f"'{issue_key}'의 issuelinks 개수: {len(issuelinks)}")
                        
                        deployed_by_tickets = []
                        for i, link in enumerate(issuelinks):
                            link_type = link.get('type', {})
                            link_name = link_type.get('name', '')
                            print(f"  링크 {i+1}: {link_name}")
                            # 'Deployments', 'is deployed by', 'deploys' 타입 모두 포함
                            if link_name in ['is deployed by', 'deploys', 'Deployments']:
                                if 'outwardIssue' in link:
                                    deployed_ticket = link['outwardIssue']
                                    deployed_by_tickets.append({
                                        'key': deployed_ticket['key'],
                                        'status': deployed_ticket['fields']['status']['name'],
                                        'summary': deployed_ticket['fields']['summary']
                                    })
                                    print(f"    -> {link_name} outwardIssue: {deployed_ticket['key']}")
                                if 'inwardIssue' in link:
                                    deployed_ticket = link['inwardIssue']
                                    deployed_by_tickets.append({
                                        'key': deployed_ticket['key'],
                                        'status': deployed_ticket['fields']['status']['name'],
                                        'summary': deployed_ticket['fields']['summary']
                                    })
                                    print(f"    -> {link_name} inwardIssue: {deployed_ticket['key']}")
                            else:
                                print(f"    -> 다른 관계: {link_name}")
                    else:
                        # 객체 형태인 경우 기존 방식 사용
                        summary = issue_response.fields.summary
                        deployed_by_tickets = []
                        for link in issue_response.fields.issuelinks:
                            if hasattr(link, 'outwardIssue') and link.type.name == 'is deployed by':
                                deployed_ticket = link.outwardIssue
                                deployed_by_tickets.append({
                                    'key': deployed_ticket.key,
                                    'status': deployed_ticket.fields.status.name,
                                    'summary': deployed_ticket.fields.summary
                                })
                            elif hasattr(link, 'inwardIssue') and link.type.name == 'deploys':
                                deployed_ticket = link.inwardIssue
                                deployed_by_tickets.append({
                                    'key': deployed_ticket.key,
                                    'status': deployed_ticket.fields.status.name,
                                    'summary': deployed_ticket.fields.summary
                                })
                    
                    # 이슈 정보와 'is deployed by' 관계를 함께 저장
                    issue_info = {
                        'key': issue_key,
                        'summary': summary,
                        'deployed_by_tickets': deployed_by_tickets
                    }
                    parent_issues.append(issue_info)
                    print(f"'{issue_key}' 이슈 조회 성공: {len(deployed_by_tickets)}개의 deployed by 티켓 발견")
                    
                except Exception as e:
                    print(f"'{issue_key}' 이슈 조회 실패: {e}")
                    # 실패한 경우 기본 정보만 저장
                    issue_info = {
                        'key': issue_key,
                        'summary': '조회 실패',
                        'deployed_by_tickets': []
                    }
                    parent_issues.append(issue_info)
            
            if parent_issues:
                print(f"Jira에서 {len(parent_issues)}개의 부모티켓을 가져왔습니다.")
                macro_table_issues = parent_issues
            else:
                print("Jira에서 부모티켓을 찾지 못했습니다.")
                macro_table_issues = []
        except Exception as e:
            print(f"실제 Jira 이슈 조회 실패: {e}")
            macro_table_issues = []
    else:
        # Macro table에 이슈가 있으면 해당 이슈들을 사용
        print(f"Macro table에서 {len(issues)}개의 이슈를 배포티켓 링크 목록에 사용합니다.")
        macro_table_issues = issues
    
    # Macro table의 티켓들을 배포티켓 링크 목록에 표시
    for issue in macro_table_issues:
        if isinstance(issue, dict) and 'key' in issue:
            # 새로운 데이터 구조인 경우 (is deployed by 관계 포함)
            if 'deployed_by_tickets' in issue:
                key = issue['key']
                summary = issue['summary']
                deployed_by_tickets = issue['deployed_by_tickets']
                print(f"동적 티켓 처리 (is deployed by 포함): {key} - {summary}")
            else:
                # 기존 동적으로 가져온 Jira 이슈인 경우
                key = issue['key']
                summary = issue['fields'].get('summary', '') if 'fields' in issue else issue.get('summary', '')
                print(f"동적 티켓 처리: {key} - {summary}")
                # 기존 방식으로 deployed by 티켓 조회
                deployed_by_tickets = []
                if isinstance(issue, dict) and 'fields' in issue:
                    try:
                        deployed_by_tickets = get_deployed_by_tickets(jira, key)
                    except Exception as e:
                        print(f"'{key}'의 deployed by 티켓 조회 중 오류: {e}")
                        deployed_by_tickets = []
        else:
            # 기본 티켓인 경우
            key = issue['key']
            summary = issue['summary']
            deployed_by_tickets = []
            print(f"기본 티켓 처리: {key} - {summary}")
        
        ticket_url = f"{jira_url}/browse/{key}"
        
        # 배포티켓 링크 HTML 생성 (순차목록 + 링크)
        deploy_tickets_html = ""
        if deployed_by_tickets:
            deploy_links = []
            for idx, deploy_ticket in enumerate(deployed_by_tickets, 1):
                deploy_key = deploy_ticket['key']
                deploy_status = deploy_ticket['status']
                deploy_summary = deploy_ticket['summary']
                deploy_url = f"{jira_url}/browse/{deploy_key}"
                deploy_links.append(f'{idx}. <a href="{deploy_url}" target="_blank">{deploy_key}({deploy_status})</a><br/>: {deploy_summary}')
            deploy_tickets_html = "<br/>".join(deploy_links)
        else:
            # Jira API에서 가져온 데이터가 없으면 기본 데이터 사용
            deploy_tickets = deploy_links_map.get(key, [])
            if deploy_tickets:
                deploy_links = []
                for idx, deploy_key in enumerate(deploy_tickets, 1):
                    deploy_url = f"{jira_url}/browse/{deploy_key}"
                    deploy_links.append(f'{idx}. <a href="{deploy_url}" target="_blank">{deploy_key}</a>')
                deploy_tickets_html = "<br/>".join(deploy_links)
        
        html_rows.append(DEPLOY_LINKS_TABLE_ROW.format(
            ticket_url=ticket_url, 
            key=key, 
            summary=summary, 
            deploy_tickets_html=deploy_tickets_html
        ))
    
    return macro + DEPLOY_LINKS_TABLE_HEADER + ''.join(html_rows) + DEPLOY_LINKS_TABLE_FOOTER

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
    today = datetime.now()
    if today.hour < 18:  # 18시 이전에는 알림 전송하지 않음
        print("오늘은 슬랙 알림 전송을 건너뜁니다. (18시 이전)")
        return
    
    try:
        r = requests.post(url, json={"text": text})
        if r.status_code != 200:
            print(f"Slack 알림 실패: {r.text}")
    except Exception as e:
        print(f"Slack 알림 오류: {e}")

def snapshot_issues(issues, field_id):
    return sorted([
        {
            "key": i["key"],
            "summary": i["fields"].get("summary", ""),
            "assignee": (i["fields"].get("assignee", {}).get("displayName") if i["fields"].get("assignee") else "미지정"),
            "status": i["fields"].get("status", {}).get("name", ""),
            "deploy_date": i["fields"].get(field_id, ""),
        }
        for i in issues
    ], key=lambda x: x["key"])

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
    """
    새롭게 연결된 배포 티켓이 있을 경우, 부모 티켓별로 그룹화하여 Slack 알림을 보냅니다.
    'is deployed by' 관계로 연결된 배포 티켓을 감지하고, 각 배포 티켓의 상태를 포함한 상세한 알림을 생성합니다.

    Args:
        issues (list): 주간 리포트에 포함된 부모 이슈 리스트
        jira_url (str): Jira 서버 URL
        page_title (str): 관련 Confluence 페이지 제목 (알림에 포함되지 않음, 향후 확장 가능)
    """
    # 이전에 알림을 보낸 배포 티켓 목록을 불러옵니다.
    notified_keys = get_notified_deploy_keys()
    new_notified_keys = set(notified_keys) # 현재 세션에서 새로 알림 보낼 키를 추가할 집합

    # 고정된 승인자들의 이메일 주소입니다.
    approver_emails = {
        "eunbee@deali.net": "조은비",
        # "soyoun@deali.net": "박소연"
    }
    
    # Slack API를 통해 승인자들의 Slack ID를 미리 조회하여 멘션을 준비합니다.
    eunbee_id = get_slack_user_id_by_email("eunbee@deali.net")
    # soyoun_id = get_slack_user_id_by_email("soyoun@deali.net")
    
    # Slack ID가 있으면 <@U12345678> 형식의 멘션 문자열을, 없으면 실명을 사용합니다.
    eunbee_mention = f"<@{eunbee_id}>" if eunbee_id else "조은비"
    # soyoun_mention = f"<@{soyoun_id}>" if soyoun_id else "박소연"

    # 부모 티켓별로 알림을 그룹화하여 한 번에 보내기 위한 딕셔너리입니다.
    # 구조: { "부모티켓_키": {"부모티켓_정보": {...}, "배포티켓_리스트": [...]}}
    notifications_by_parent_ticket = {}

    # 1. 주간 리포트에 포함된 각 부모 티켓을 순회하며 새로운 배포 티켓 연결을 확인합니다.
    for parent_issue in issues:
        parent_key = parent_issue['key']
        parent_summary = parent_issue['fields'].get('summary', '')
        
        newly_linked_deploys = []
        # 'issuelinks' 필드에서 'is deployed by' 관계를 가진 링크를 찾습니다.
        if 'issuelinks' in parent_issue['fields'] and parent_issue['fields']['issuelinks']:
            for link in parent_issue['fields']['issuelinks']:
                if link.get('type', {}).get('inward') == 'is deployed by' and 'inwardIssue' in link:
                    deploy_ticket = link['inwardIssue']
                    deploy_ticket_key = deploy_ticket['key']
                    
                    # 이 배포 티켓에 대해 알림을 보낸 적이 없는 경우에만 처리합니다.
                    if deploy_ticket_key not in notified_keys:
                        # 배포 티켓의 상세 정보를 가져옵니다.
                        try:
                            resp = requests.get(f"{jira_url}/rest/api/2/issue/{deploy_ticket_key}",
                                auth=(os.getenv('ATLASSIAN_USERNAME'), os.getenv('ATLASSIAN_API_TOKEN')))
                            if resp.status_code == 200:
                                deploy_ticket_detail = resp.json()
                                deploy_summary = deploy_ticket_detail['fields'].get('summary', '')
                                deploy_status = deploy_ticket_detail['fields'].get('status', {}).get('name', '')
                                
                                newly_linked_deploys.append({
                                    'key': deploy_ticket_key,
                                    'summary': deploy_summary,
                                    'status': deploy_status
                                })
                                new_notified_keys.add(deploy_ticket_key) # 알림 목록에 추가
                        except Exception as e:
                            print(f"배포 티켓 {deploy_ticket_key} 상세 정보 조회 실패: {e}")
                            # 상세 정보 조회에 실패해도 기본 정보로 알림을 보냅니다.
                            newly_linked_deploys.append({
                                'key': deploy_ticket_key,
                                'summary': deploy_ticket.get('fields', {}).get('summary', ''),
                                'status': deploy_ticket.get('fields', {}).get('status', {}).get('name', '')
                            })
                            new_notified_keys.add(deploy_ticket_key)
        
        # 새로 연결된 배포 티켓이 있는 경우에만 알림 데이터를 구성합니다.
        if newly_linked_deploys:
            notifications_by_parent_ticket[parent_key] = {
                'parent_summary': parent_summary,
                'assignee': parent_issue.get('fields', {}).get('assignee', {}),
                'deploy_tickets': newly_linked_deploys
            }

    # 2. 각 부모 티켓별로 Slack 메시지를 생성하고 전송합니다.
    if notifications_by_parent_ticket:
        for parent_key, data in notifications_by_parent_ticket.items():
            parent_summary = data['parent_summary']
            parent_assignee = data['assignee']
            deploy_tickets = data['deploy_tickets']
            
            # 부모 티켓 담당자 정보
            assignee_mention = '담당자'
            if parent_assignee:
                assignee_name = parent_assignee.get('displayName') or parent_assignee.get('name')
                assignee_email = parent_assignee.get('emailAddress')
                assignee_mention = assignee_name or '담당자'
                
                # 이메일이 있으면 Slack ID를 조회하여 멘션 문자열을 만듭니다.
                if assignee_email:
                    slack_user_id = get_slack_user_id_by_email(assignee_email)
                    if slack_user_id:
                        assignee_mention = f"<@{slack_user_id}>"
            
            # 부모 티켓 URL
            parent_url = f"{jira_url}/browse/{parent_key}"
            
            # 배포 티켓 목록 생성
            deploy_tickets_list = []
            for i, deploy_ticket in enumerate(deploy_tickets, 1):
                deploy_url = f"{jira_url}/browse/{deploy_ticket['key']}"
                deploy_ticket_text = f"{deploy_ticket['key']}({deploy_ticket['status']}): {deploy_ticket['summary']}"
                deploy_tickets_list.append(
                    f"{i}. <{deploy_url}|{deploy_ticket_text}>"
                )
            
            # Slack 메시지 내용을 구성합니다.
            message = (
                f"{assignee_mention}님, 담당 IT티켓에 새로운 배포 티켓이 생성되었습니다.\n"
                f"{eunbee_mention}님, 배포 내용을 확인 후 승인해주세요.\n"
                f"**<{parent_url}|{parent_key}: {parent_summary}>**\n"
                f"{chr(10).join(deploy_tickets_list)}"
            )
            send_slack(message)

    # 알림을 보낸 배포 티켓 목록을 파일에 저장하여 다음 실행 시 중복 알림을 방지합니다.
    save_notified_deploy_keys(new_notified_keys)


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

def main():
    # 1. 환경 변수 로딩
    try:
        env = load_env_vars([
            "ATLASSIAN_URL", "ATLASSIAN_USERNAME", "ATLASSIAN_API_TOKEN",
            "JIRA_PROJECT_KEY", "CONFLUENCE_SPACE_KEY"
        ])
    except ValueError as e:
        print(f"오류: {e}")
        return
    atlassian_url = env["ATLASSIAN_URL"]
    atlassian_username = env["ATLASSIAN_USERNAME"]
    atlassian_token = env["ATLASSIAN_API_TOKEN"]
    jira_project_key = env["JIRA_PROJECT_KEY"]
    confluence_space_key = env["CONFLUENCE_SPACE_KEY"]
    parent_page_id = "4596203549"  # 고정값 사용

    # 2. API 클라이언트 생성
    try:
        jira = Jira(url=atlassian_url, username=atlassian_username, password=atlassian_token, cloud=True)
        confluence = Confluence(url=atlassian_url, username=atlassian_username, password=atlassian_token, cloud=True)
        print(f"\nJira/Confluence 서버 연결 성공!: {get_now_str()}")
    except Exception as e:
        print(f"Jira/Confluence 연결 오류: {e}")
        return

    # 3. 실행 모드 및 날짜/타이틀 계산
    mode = sys.argv[1] if len(sys.argv) > 1 else "update"
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

    # 4. Jira 이슈 조회
    jql_query = (
        f"project = '{jira_project_key}' AND "
        f"'{JIRA_DEPLOY_DATE_FIELD_ID}' >= '{start_date_str}' AND '{JIRA_DEPLOY_DATE_FIELD_ID}' <= '{end_date_str}' "
        f"ORDER BY '{JIRA_DEPLOY_DATE_FIELD_ID}' ASC"
    )
    issues = get_jira_issues_simple(jira, jira_project_key, JIRA_DEPLOY_DATE_FIELD_ID, start_date_str, end_date_str)
    if not issues:
        print(f"{mode_desc}에 배포 예정 티켓 없음. 빈 테이블로 생성/업데이트.")

    # 5. 변경 감지
    SNAPSHOT_FILE_PATH = 'weekly_issues_snapshot.json'
    prev_snapshot = read_json(SNAPSHOT_FILE_PATH)
    curr_snapshot = snapshot_issues(issues, JIRA_DEPLOY_DATE_FIELD_ID)
    
    # create, current 모드에서는 이슈 변경 여부와 관계없이 페이지 생성/업데이트 진행
    if mode in ["create", "current"]:
        changed_issues = get_changed_issues(prev_snapshot, curr_snapshot, atlassian_url)
    else:
        # update 모드에서만 이슈 변경 감지
        if not issues_changed(prev_snapshot, curr_snapshot):
            print(f"JIRA 이슈 변경 없음. 업데이트/알림 생략. {get_now_str()}")
            log(f"\n실행시간: {get_now_str()}\n업데이트 할 사항 없음.")
            return
        changed_issues = get_changed_issues(prev_snapshot, curr_snapshot, atlassian_url)

    # 6. Confluence 페이지 생성/업데이트 및 Slack 알림
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
                slack_msg = f"✅ 배포 일정 리포트가 생성되었습니다.\n\n{page_title}\n{page_url}\n\n[업데이트된 IT티켓 목록]\n{issue_list}"
                send_slack(slack_msg)
                # 알림을 보낸 변경사항 해시를 저장
                notified_changes.add(change_hash)
                save_notified_changes(notified_changes)
                print(f"Slack 알림 전송 완료 (변경사항: {len(changed_issues)}개)")
            elif changed_issues:
                print(f"동일한 변경사항에 대한 알림이 이미 전송됨 (변경사항: {len(changed_issues)}개)")
                slack_msg = f"✅ 배포 일정 리포트가 생성되었습니다.\n\n{page_title}\n{page_url}"
                send_slack(slack_msg)
            else:
                slack_msg = f"✅ 배포 일정 리포트가 생성되었습니다.\n\n{page_title}\n{page_url}"
                send_slack(slack_msg)
            
            notify_new_deploy_tickets(issues, atlassian_url, page_title)
            log(f"\n실행시간: {get_now_str()}\n내용: {page_title} 페이지 생성.")
    except Exception as e:
        print(f"Confluence 페이지 처리 오류: {e}")

    # 7. 스냅샷 저장
    write_json(SNAPSHOT_FILE_PATH, curr_snapshot)

if __name__ == "__main__":
    # 사용법 안내
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print("""
주간 배포 리포트 생성 스크립트 사용법:

python create_weekly_report.py [모드]

모드 옵션:
  create    - 다음 주 (차주) 배포 예정 티켓으로 리포트 생성
  current   - 이번 주 (현재 주) 배포 예정 티켓으로 리포트 생성/업데이트
  last      - 지난 주 배포 예정 티켓으로 리포트 생성/업데이트
  update    - 이번 주 배포 예정 티켓으로 리포트 업데이트 (기본값)

사용 예시:
  python create_weekly_report.py create    # 다음 주 리포트 생성
  python create_weekly_report.py current   # 이번 주 리포트 다시 생성
  python create_weekly_report.py last      # 지난 주 리포트 생성
  python create_weekly_report.py update    # 이번 주 리포트 업데이트
        """)
        sys.exit(0)
    
    # 이 스크립트 파일이 직접 실행될 때만 main() 함수를 호출합니다.
    # 다른 파일에서 이 스크립트를 import할 경우에는 main()이 자동으로 실행되지 않습니다.
    main()
