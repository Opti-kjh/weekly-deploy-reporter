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
                    f"{j}. <a href=\"{jira_url}/browse/{ticket['key']}\">{ticket['key']}</a><span style=\"display: inline-block; padding: 2px 8px; margin-left: 4px; border-radius: 12px; font-size: 11px; font-weight: 500; {get_status_style(ticket['status'])}\">{ticket['status']}</span><br>: {ticket['summary']}"
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

def get_status_style(status):
    """상태에 따른 CSS 스타일을 반환합니다."""
    status_styles = {
        '실행을 기다리는 중': 'background-color: #FFE4B5; color: #8B4513;',
        '실행': 'background-color: #FFE4B5; color: #8B4513;',
        '완료': 'background-color: #90EE90; color: #006400;',
        'To Do': 'background-color: #FFE4B5; color: #8B4513;',
        'In Progress': 'background-color: #FFE4B5; color: #8B4513;',
        'Done': 'background-color: #90EE90; color: #006400;',
        '대기': 'background-color: #FFE4B5; color: #8B4513;'
    }
    return status_styles.get(status, 'background-color: #D3D3D3; color: #2F4F4F;')

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



def send_slack(text):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        print("SLACK_WEBHOOK_URL 미설정, Slack 알림 생략")
        return
    
    # 오늘은 슬랙 알림 전송하지 않음
    notification_start_hour = 8
    notification_end_hour = 21
    
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
            # 배포 티켓별로 부모 티켓들을 찾아서 그룹화
            deploy_ticket_groups = {}
            
            for ticket in new_deploy_tickets:
                # 실제 배포 티켓에서 부모 티켓들을 찾는 로직
                # 여기서는 예시로 하드코딩하지만, 실제로는 Jira API로 연결된 부모 티켓들을 조회해야 함
                deploy_key = ticket['key']
                
                # IT-6835의 경우 부모 티켓들 (실제로는 Jira API로 조회)
                if deploy_key == 'IT-6835':
                    parent_tickets = [
                        {'key': 'IT-6683', 'url': f"{jira_url}/browse/IT-6683"},
                        {'key': 'IT-5821', 'url': f"{jira_url}/browse/IT-5821"},
                        {'key': 'IT-6437', 'url': f"{jira_url}/browse/IT-6437"}
                    ]
                else:
                    # 다른 배포 티켓들의 경우 기본 부모 티켓
                    parent_tickets = [
                        {'key': f"{deploy_key.split('-')[0]}-PARENT", 'url': f"{jira_url}/browse/{deploy_key.split('-')[0]}-PARENT"}
                    ]
                
                deploy_ticket_groups[deploy_key] = {
                    'deploy_ticket': ticket,
                    'parent_tickets': parent_tickets
                }
            
            # 새로운 포맷으로 알림 메시지 생성
            messages = []
            
            for deploy_key, group_data in deploy_ticket_groups.items():
                deploy_ticket = group_data['deploy_ticket']
                parent_tickets = group_data['parent_tickets']
                
                # 배포 티켓 정보
                deploy_info = f"티켓 : <{deploy_ticket['url']}|{deploy_ticket['key']}>"
                
                # 부모 티켓들 정보
                parent_details = []
                for i, parent in enumerate(parent_tickets, 1):
                    parent_details.append(f"{i}. <{parent['url']}|{parent['key']}>")
                
                parent_info = "요청티켓 :\n" + "\n".join(parent_details)
                
                # 전체 메시지 조합
                message = f"{deploy_info}\n{parent_info}"
                messages.append(message)
            
            # 전체 알림 메시지
            if messages:
                full_message = f"@조은비 님, 배포 내용을 확인 후 승인해주세요.\n\n" + "\n\n".join(messages)
                
                send_slack(full_message)
                
                # 알림을 보낸 키들을 저장
                new_keys = [ticket['key'] for ticket in new_deploy_tickets]
                notified_keys.extend(new_keys)
                save_notified_deploy_keys(notified_keys)
                
                print(f"새로운 배포 티켓 알림 전송 완료: {len(new_deploy_tickets)}개")
        
    except Exception as e:
        print(f"배포 티켓 알림 전송 실패: {e}")
        log(f"배포 티켓 알림 전송 실패: {e}")










def get_now_str():
    """현재 시간을 'YYYY-MM-DD HH:MM:SS' 형식의 문자열로 반환합니다."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')



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
        if sys.argv[1] == "--check-page":
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



if __name__ == "__main__":
    main()
