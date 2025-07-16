
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
# 예: ATLASSIAN_URL, ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN 등
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
        monday = today + timedelta(days=(7 - today.weekday()))
    else:
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

JIRA_MACRO_TEMPLATE = '''
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="columns">key,type,summary,assignee,status,updated,created,예정된 시작</ac:parameter>
  <ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>
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

def format_jira_datetime(dt_str):
    if not dt_str:
        return ""
    try:
        # JIRA 기본 날짜 포맷: 2024-07-16T02:30:00.000+0900
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str  # 파싱 실패 시 원본 반환

def create_confluence_content(jql_query, issues, jira_url):
    macro = JIRA_MACRO_TEMPLATE.format(jql_query=jql_query)
    html_rows = []
    # 배포티켓(링크) summary 캐싱용 딕셔너리
    deploy_ticket_summaries = {}
    # 1차 패스: 모든 이슈의 key-summary 매핑 생성 (자기 자신 및 링크용)
    for issue in issues:
        deploy_ticket_summaries[issue['key']] = issue['fields'].get('summary', '')
    # 2차 패스: 표 생성
    for issue in issues:
        key = issue['key']
        summary = issue['fields'].get('summary', '')
        ticket_url = f"{jira_url}/browse/{key}"
        fields = issue['fields']
        deploy_tickets = []
        if 'issuelinks' in fields and fields['issuelinks']:
            for link in fields['issuelinks']:
                link_type = link.get('type', {})
                # outwardIssue: 내가 배포티켓의 부모일 때 (ex: deploys)
                if link_type.get('name') == 'deploys' and 'outwardIssue' in link:
                    linked = link['outwardIssue']
                    linked_key = linked['key']
                    # summary가 없으면 API로 조회 (최적화: 이미 캐시에 있으면 사용)
                    linked_summary = deploy_ticket_summaries.get(linked_key)
                    if linked_summary is None:
                        # API로 개별 조회 (성능상 이슈가 있을 수 있음)
                        try:
                            resp = requests.get(f"{jira_url}/rest/api/2/issue/{linked_key}",
                                               auth=(os.getenv('ATLASSIAN_USERNAME'), os.getenv('ATLASSIAN_API_TOKEN')))
                            if resp.status_code == 200:
                                linked_summary = resp.json()['fields'].get('summary', '')
                                deploy_ticket_summaries[linked_key] = linked_summary
                            else:
                                linked_summary = ''
                        except Exception:
                            linked_summary = ''
                    deploy_tickets.append(f'<a href="{jira_url}/browse/{linked_key}" target="_blank">{linked_key}</a><br/>: {linked_summary}')
                # inwardIssue: 내가 배포티켓일 때 (ex: is deployed by)
                if link_type.get('inward') == 'is deployed by' and 'inwardIssue' in link:
                    linked = link['inwardIssue']
                    linked_key = linked['key']
                    linked_summary = deploy_ticket_summaries.get(linked_key)
                    if linked_summary is None:
                        try:
                            resp = requests.get(f"{jira_url}/rest/api/2/issue/{linked_key}",
                                               auth=(os.getenv('ATLASSIAN_USERNAME'), os.getenv('ATLASSIAN_API_TOKEN')))
                            if resp.status_code == 200:
                                linked_summary = resp.json()['fields'].get('summary', '')
                                deploy_ticket_summaries[linked_key] = linked_summary
                            else:
                                linked_summary = ''
                        except Exception:
                            linked_summary = ''
                    deploy_tickets.append(f'<a href="{jira_url}/browse/{linked_key}" target="_blank">{linked_key}</a><br/>: {linked_summary}')
        deploy_tickets_html = "<br/>".join(deploy_tickets) if deploy_tickets else ''
        html_rows.append(DEPLOY_LINKS_TABLE_ROW.format(ticket_url=ticket_url, key=key, summary=summary, deploy_tickets_html=deploy_tickets_html))
    return macro + DEPLOY_LINKS_TABLE_HEADER + ''.join(html_rows) + DEPLOY_LINKS_TABLE_FOOTER

def send_slack(text):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        print("SLACK_WEBHOOK_URL 미설정, Slack 알림 생략")
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
    새롭게 연결된 배포 티켓이 있을 경우, 부모 티켓의 담당자와 승인자에게 Slack 알림을 보냅니다.
    'is deployed by' 관계로 연결된 배포 티켓을 감지합니다.

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
        "soyoun@deali.net": "박소연"
    }
    
    # Slack API를 통해 승인자들의 Slack ID를 미리 조회하여 멘션을 준비합니다.
    eunbee_id = get_slack_user_id_by_email("eunbee@deali.net")
    soyoun_id = get_slack_user_id_by_email("soyoun@deali.net")
    
    # Slack ID가 있으면 <@U12345678> 형식의 멘션 문자열을, 없으면 실명을 사용합니다.
    eunbee_mention = f"<@{eunbee_id}>" if eunbee_id else "조은비"
    soyoun_mention = f"<@{soyoun_id}>" if soyoun_id else "박소연"

    # 부모 티켓별로 알림을 그룹화하여 한 번에 보내기 위한 딕셔너리입니다.
    # 구조: { "부모티켓_키": {"담당자_멘션": "...", "새로운_배포티켓_리스트": [...]}}
    notifications_by_parent_ticket = {}

    # 1. 주간 리포트에 포함된 각 부모 티켓을 순회하며 새로운 배포 티켓 연결을 확인합니다.
    for parent_issue in issues:
        parent_key = parent_issue['key']
        
        newly_linked_deploys = []
        # 'issuelinks' 필드에서 'is deployed by' 관계를 가진 링크를 찾습니다.
        if 'issuelinks' in parent_issue['fields'] and parent_issue['fields']['issuelinks']:
            for link in parent_issue['fields']['issuelinks']:
                if link.get('type', {}).get('inward') == 'is deployed by' and 'inwardIssue' in link:
                    deploy_ticket = link['inwardIssue']
                    deploy_ticket_key = deploy_ticket['key']
                    
                    # 이 배포 티켓에 대해 알림을 보낸 적이 없는 경우에만 처리합니다.
                    if deploy_ticket_key not in notified_keys:
                        newly_linked_deploys.append(deploy_ticket_key)
                        new_notified_keys.add(deploy_ticket_key) # 알림 목록에 추가
        
        # 새로 연결된 배포 티켓이 있는 경우에만 알림 데이터를 구성합니다.
        if newly_linked_deploys:
            assignee = parent_issue.get('fields', {}).get('assignee')
            if not assignee:
                continue # 담당자가 없으면 알림을 보낼 수 없으므로 건너뜁니다.

            # 담당자의 이메일, 이름 정보를 가져옵니다.
            assignee_email = assignee.get('emailAddress')
            assignee_name = assignee.get('displayName') or assignee.get('name')
            assignee_mention = assignee_name or '담당자' # 기본값 설정
            
            # 이메일이 있으면 Slack ID를 조회하여 멘션 문자열을 만듭니다。
            if assignee_email:
                slack_user_id = get_slack_user_id_by_email(assignee_email)
                if slack_user_id:
                    assignee_mention = f"<@{slack_user_id}>"
            
            # 알림 그룹화 딕셔너리에 추가합니다.
            notifications_by_parent_ticket[parent_key] = {
                'assignee_mention': assignee_mention,
                'new_deploys': newly_linked_deploys
            }

    # 2. 그룹화된 알림 정보를 바탕으로 실제 Slack 메시지를 생성하고 전송합니다.
    if notifications_by_parent_ticket:
        for parent_key, data in notifications_by_parent_ticket.items():
            assignee_mention = data['assignee_mention']
            parent_url = f"{jira_url}/browse/{parent_key}"
            parent_summary = ''
            # IT 티켓 제목 추출 (없으면 빈 문자열)
            if parent_key in [i['key'] for i in issues]:
                parent_summary = issues[[i['key'] for i in issues].index(parent_key)]['fields'].get('summary', '')
            # Slack 메시지 내용을 구성합니다.
            message = (
                f"{assignee_mention}님, 담당 IT티켓에 새로운 배포 티켓이 생성되었습니다.\n"
                f"{eunbee_mention}님, 배포 내용을 확인 후 승인해주세요.\n"
                f"- <{parent_url}|{parent_key}: {parent_summary}>"
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
        print(f"Jira/Confluence 서버 연결 성공!: {get_now_str()}\n")
    except Exception as e:
        print(f"Jira/Confluence 연결 오류: {e}")
        return

    # 3. 실행 모드 및 날짜/타이틀 계산
    mode = sys.argv[1] if len(sys.argv) > 1 else "update"
    monday, sunday = get_week_range(mode)
    start_date_str, end_date_str = monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')
    page_title = get_page_title(monday, sunday)

    # 4. Jira 이슈 조회
    jql_query = (
        f"project = '{jira_project_key}' AND "
        f"'customfield_10817' >= '{start_date_str}' AND 'customfield_10817' <= '{end_date_str}' "
        f"ORDER BY 'customfield_10817' ASC"
    )
    issues = get_jira_issues_simple(jira, jira_project_key, "customfield_10817", start_date_str, end_date_str)
    if not issues:
        print(f"{mode == 'create' and '다음 주' or '이번 주'}에 배포 예정 티켓 없음. 빈 테이블로 생성/업데이트.")

    # 5. 변경 감지
    SNAPSHOT_FILE_PATH = 'weekly_issues_snapshot.json'
    prev_snapshot = read_json(SNAPSHOT_FILE_PATH)
    curr_snapshot = snapshot_issues(issues, "customfield_10817")
    if not issues_changed(prev_snapshot, curr_snapshot):
        print(f"JIRA 이슈 변경 없음. 업데이트/알림 생략. {get_now_str()}")
        log(f"실행시간: {get_now_str()}\n업데이트 할 사항 없음.")
        return

    # 6. Confluence 페이지 생성/업데이트 및 Slack 알림
    page_content = create_confluence_content(jql_query, issues, atlassian_url)
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
                send_slack(f"🔄 배포 일정 리포트가 업데이트되었습니다: {page_title}\n{page_url}")
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
            send_slack(f"✅ 배포 일정 리포트가 생성되었습니다.\n\n{page_title}\n{page_url}")
            notify_new_deploy_tickets(issues, atlassian_url, page_title)
            log(f"실행시간: {get_now_str()}\n내용: {page_title} 페이지 생성.")
    except Exception as e:
        print(f"Confluence 페이지 처리 오류: {e}")

    # 7. 스냅샷 저장
    write_json(SNAPSHOT_FILE_PATH, curr_snapshot)

if __name__ == "__main__":
    # 이 스크립트 파일이 직접 실행될 때만 main() 함수를 호출합니다.
    # 다른 파일에서 이 스크립트를 import할 경우에는 main()이 자동으로 실행되지 않습니다.
    main()
