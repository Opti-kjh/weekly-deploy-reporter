# -*- coding: utf-8 -*-
"""
주간 배포 리포트 생성 스크립트

사용법:
    python create_weekly_report.py [mode] [options]
    
모드:
    current  - 이번 주 배포 예정 티켓으로 리포트 생성/업데이트 (기본값)
    create   - 다음 주 (차주) 배포 예정 티켓으로 리포트 생성
    update   - 이번 주 배포 예정 티켓으로 리포트 업데이트
    last     - 지난 주 배포 예정 티켓으로 리포트 생성/업데이트
    
옵션:
    --no-pagination  - 페이지네이션 없이 한 번에 조회 (기본값, 최대 1000개)
    --pagination     - 페이지네이션을 사용하여 모든 티켓 조회
    --force-update   - 강제 업데이트 (변경사항 없어도 업데이트)
    --check-page     - Confluence 페이지 내용 확인
    --debug-links [티켓키] - 특정 티켓의 연결 관계 디버깅
    --mute           - MUTE 모드 (Slack 알림 전송 비활성화)

환경 변수:
    LOG_LEVEL        - 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                      기본값: INFO (crontab 실행 시 간략한 로그)
    VERBOSE_LOGGING  - 상세 로그 활성화 (true/false)
                      기본값: false (crontab 실행 시 간략한 로그)

예시:
    python create_weekly_report.py current
    python create_weekly_report.py create --pagination
    python create_weekly_report.py update --force-update
    python create_weekly_report.py --debug-links IT-5027
    python create_weekly_report.py current --mute
    LOG_LEVEL=DEBUG python create_weekly_report.py current
    VERBOSE_LOGGING=true python create_weekly_report.py current
"""

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

# 로그 레벨 설정
LOG_LEVELS = {
    'DEBUG': 0,
    'INFO': 1, 
    'WARNING': 2,
    'ERROR': 3,
    'CRITICAL': 4
}

# 현재 로그 레벨 (환경 변수에서 읽어오거나 기본값 사용)
CURRENT_LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'

# ---------------------------------------------------------

# === [1단계] 유틸리티 함수 및 템플릿 정의 ===
def load_env_vars(keys):
    values = {k: os.getenv(k) for k in keys}
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ValueError(f"필수 환경변수 누락: {', '.join(missing)}")
    return values

def should_log(level):
    """로그 레벨에 따라 출력 여부를 결정합니다."""
    if VERBOSE_LOGGING:
        return True
    return LOG_LEVELS.get(level.upper(), 1) >= LOG_LEVELS.get(CURRENT_LOG_LEVEL, 1)

def log(message, level='INFO'):
    """로그 메시지를 파일에 기록합니다."""
    if should_log(level):
        with open("cron.log", "a", encoding="utf-8") as f:
            f.write(f"[{level}] {message}\n")

def print_log(message, level='INFO'):
    """로그 메시지를 콘솔에 출력하고 파일에도 기록합니다."""
    if should_log(level):
        print(message)
        log(message, level)

def get_week_range(mode):
    """
    모든 모드에서 동일한 날짜 계산 방식을 사용합니다.
    해당 주간에 속하는 모든 IT 티켓을 포함하는 것이 목표입니다.
    """
    today = date.today()
    
    # 모든 모드에서 동일한 계산 방식 사용
    if mode == "create":
        # 다음 주 (차주) - 현재 주의 다음 주
        monday = today + timedelta(days=(7 - today.weekday()))
    elif mode == "current":
        # 이번 주 (현재 주) - 오늘이 속한 주
        monday = today - timedelta(days=today.weekday())
    elif mode == "last":
        # 지난 주 - 현재 주의 이전 주
        monday = today - timedelta(days=today.weekday() + 7)
    elif mode == "update":
        # 업데이트 모드도 현재 주와 동일
        monday = today - timedelta(days=today.weekday())
    else:
        # 기본값: 이번 주
        monday = today - timedelta(days=today.weekday())
    
    # 일요일은 월요일 + 6일
    sunday = monday + timedelta(days=6)
    
    # 디버깅 정보 출력 (DEBUG 레벨로 변경)
    print_log(f"=== 날짜 계산 디버깅 ===", 'DEBUG')
    print_log(f"모드: {mode}", 'DEBUG')
    print_log(f"현재 날짜: {today}", 'DEBUG')
    print_log(f"계산된 월요일: {monday}", 'DEBUG')
    print_log(f"계산된 일요일: {sunday}", 'DEBUG')
    print_log(f"주간 범위: {monday.strftime('%m/%d')}~{sunday.strftime('%m/%d')}", 'DEBUG')
    
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

def normalize_html_content(html_content):
    unescaped = html.unescape(html_content)
    return re.sub(r'\s+', ' ', unescaped).strip()

# 날짜 포맷이 적용된 전체 매크로 (GitHub 최신 버전)
JIRA_CUSTOM_DATE_FORMAT_TEMPLATE = '''
<ac:structured-macro ac:name="jira">
  <ac:parameter ac:name="jqlQuery">{jql_query}</ac:parameter>
  <ac:parameter ac:name="columns">key,type,Request Type,status,summary,assignee,created,updated,예정된 시작</ac:parameter>
  <ac:parameter ac:name="dateFormat">yyyy-MM-dd HH:mm</ac:parameter>
  <ac:parameter ac:name="maximumIssues">1000</ac:parameter>
  <ac:parameter ac:name="showRefreshButton">true</ac:parameter>
  <ac:parameter ac:name="showView">true</ac:parameter>
  <ac:parameter ac:name="sortBy">예정된 시작</ac:parameter>
  <ac:parameter ac:name="sortOrder">asc</ac:parameter>
  <ac:parameter ac:name="showIcons">true</ac:parameter>
  <ac:parameter ac:name="showText">true</ac:parameter>
  <ac:parameter ac:name="columnWidths">80,30,120,80,300,100,120,120,120</ac:parameter>
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
  <ac:parameter ac:name="maximumIssues">1000</ac:parameter>
  <ac:parameter ac:name="sortBy">key</ac:parameter>
  <ac:parameter ac:name="sortOrder">asc</ac:parameter>
</ac:structured-macro>
'''


# === [2단계] API/알림/스냅샷 래퍼 함수 간소화 ===
def get_jira_issues_simple(jira, project_key, date_field_id, start_date, end_date):
    # JQL 쿼리를 단순화하여 필드 접근 문제를 우회
    jql_query = (
        f"project = '{jira_project_key}' AND "
        f"'{field}' >= '{start_date_str}' AND '{field}' <= '{end_date_str}' "
        f"ORDER BY '{field}' ASC"
    )
    print_log(f"JQL: {jql_query}", 'DEBUG')
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
                    print_log(f"날짜 파싱 오류 ({issue['key']}): {e}", 'WARNING')
                    continue
        
        print_log(f"✅ 필터링 완료: {len(filtered_issues)}개 이슈 (전체: {len(issues['issues'])}개)", 'INFO')
        return filtered_issues
    except Exception as e:
        print_log(f"Jira 검색 오류: {e}", 'ERROR')
        return []


def create_confluence_content(jql_query, issues, jira_url, jira, jira_project_key, start_date_str, end_date_str, use_pagination=False): 
    # 이슈 수 계산
    issue_count = len(issues) if issues else 0
    
    # 날짜 포맷이 적용된 전체 매크로 사용 (이슈 수 포함)
    macro = JIRA_CUSTOM_DATE_FORMAT_TEMPLATE.format(jql_query=jql_query)
    
    # 이슈 수 표시 섹션 추가
    issue_count_section = f'''
<div style="background-color: #f8f9fa; padding: 12px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #007bff;">
<h3 style="margin: 0 0 8px 0; color: #007bff;">📈 이번 주 배포 예정 이슈 현황</h3>
<em>• 매크로 로딩 중에는 "검색된 이슈가 없습니다" 메시지가 표시될 수 있습니다<br>
• 로딩이 완료되면 실제 이슈 목록이 표시됩니다<br>
• 새로고침 버튼을 클릭하여 최신 데이터를 확인할 수 있습니다</em>
</div>

<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 12px; margin-bottom: 15px;">
<div style="display: flex; align-items: center; margin-bottom: 8px;">
<span style="color: #856404; font-size: 16px; margin-right: 8px;">⚠️</span>
<strong style="color: #856404; font-size: 14px;">주의사항</strong>
</div>
<p style="margin: 0; color: #856404; font-size: 13px; line-height: 1.4;">
<strong>절대 현재 화면을 직접 편집하지 마세요.</strong><br>
이 페이지는 자동으로 생성되는 페이지입니다. 직접 편집하면 다음 업데이트 시 변경사항이 사라집니다.
</p>
</div>
'''
    
    # 매크로와 동일한 cf[10817] 형식을 사용하여 배포 예정 티켓 조회
    print_log(f"\n=== Confluence 페이지용 배포 예정 티켓 조회 ===", 'DEBUG')
    print_log(f"1. 매크로 JQL 쿼리 정보", 'DEBUG')
    print_log(f"원본 JQL: {jql_query}", 'DEBUG')
    
    # 매크로용 JQL 쿼리와 API 조회용 JQL 쿼리를 동일하게 설정
    macro_jql_query = (
        f"project = '{jira_project_key}' AND "
        f"cf[10817] >= '{start_date_str}' AND cf[10817] <= '{end_date_str}' "
        f"ORDER BY created DESC"
    )
    print_log(f"매크로 JQL: {macro_jql_query}", 'DEBUG')
    print_log(f"2. API 조회 정보", 'DEBUG')
    print_log(f"API JQL: {jql_query}", 'DEBUG')
    print_log(f"조회된 이슈 수: {len(issues)}", 'INFO')
    
    # 매크로와 동일한 cf[10817] 형식으로 티켓 조회
    try:
        deploy_issues = jira.search_issues(macro_jql_query, fields="key,summary,status,assignee,created,updated,customfield_10817", maxResults=1000)
        print_log(f"매크로 JQL로 조회된 이슈 수: {len(deploy_issues)}", 'INFO')
        deploy_issues_list = []
        
        for issue in deploy_issues:
            issue_dict = {
                'key': issue.key,
                'summary': getattr(issue.fields, 'summary', ''),
                'status': getattr(issue.fields, 'status', {}).name if hasattr(getattr(issue.fields, 'status', {}), 'name') else str(getattr(issue.fields, 'status', '')),
                'assignee': getattr(issue.fields, 'assignee', {}).displayName if hasattr(getattr(issue.fields, 'assignee', {}), 'displayName') else str(getattr(issue.fields, 'assignee', '')),
                'created': getattr(issue.fields, 'created', ''),
                'updated': getattr(issue.fields, 'updated', ''),
                'fields': {
                    'summary': getattr(issue.fields, 'summary', ''),
                    'status': {'name': getattr(issue.fields, 'status', {}).name if hasattr(getattr(issue.fields, 'status', {}), 'name') else str(getattr(issue.fields, 'status', ''))},
                    'customfield_10817': getattr(issue.fields, 'customfield_10817', '')
                }
            }
            deploy_issues_list.append(issue_dict)
        
        print_log(f"매크로와 동일한 cf[10817] 형식으로 조회된 티켓 수: {len(deploy_issues_list)}", 'INFO')
        
    except Exception as e:
        print_log(f"매크로와 동일한 cf[10817] 형식으로 조회 실패: {e}", 'ERROR')
        # 기존 방식으로 폴백
        deploy_issues_list = get_jira_issues_by_customfield_10817(jira, jira_project_key, start_date_str, end_date_str, use_pagination)
    
    # IT 티켓만 필터링하는 HTML 테이블 생성 (매크로와 동일한 결과 사용)
    deploy_links_html_table = create_deploy_links_html_table_with_issues(jira, deploy_issues_list, jira_url)
    
    # 전체 너비 레이아웃을 위한 컨테이너 추가 (이슈 현황 섹션 제외)
    full_width_container = '''
<div style="width: 100%; max-width: none; margin: 0; padding: 0; overflow-x: auto;">
<style>
.ac-content-wrapper {
    max-width: none !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
}
.ac-content {
    max-width: none !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
}
</style>
'''
    
    return issue_count_section + full_width_container + macro + deploy_links_html_table + '</div>'

def create_deploy_links_html_table_with_issues(jira, deploy_issues, jira_url):
    """정확한 배포 예정 티켓들을 사용하여 HTML 테이블을 생성합니다."""
    try:
        print_log(f"=== 정확한 배포 예정 티켓으로 HTML 테이블 생성 ===", 'DEBUG')
        print_log(f"배포 예정 티켓 수: {len(deploy_issues)}", 'INFO')
        
        html_content = '''
<h2 style="margin-top: 20px;">배포 예정 목록</h2>
<p><em>아래 표는 이번 주 배포 예정인 부모 IT 티켓들을 보여줍니다. 각 티켓의 배포 관계는 Jira에서 직접 확인하실 수 있습니다.</em></p>

<div style="background-color: #f4f5f7; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
<h4> 배포 관계 표시 형식 안내</h4>
<p>아래 표의 <strong>연결된 이슈</strong> 컬럼에는 다음과 같은 형식으로 배포 관계가 표시됩니다:</p>
<ul>
<li><strong>부모 IT 티켓</strong>: 배포 대상이 되는 IT 티켓</li>
<li><strong>배포 티켓</strong>: "is deployed by" 관계로 연결된 IT 티켓들만 표시</li>
<li><strong>생성 일시</strong>: 각 배포 티켓의 생성 일시가 최근 10분 이내에 생성된 경우 <span style="color: #FF0000; font-weight: bold;">빨간색</span>으로 표시됩니다</li>
<li><strong>표시 형식</strong>: 각 배포 티켓이 새로운 줄로 구분되어 표시됩니다</li>
</ul>
<p><em>예시: IT-6516 티켓의 경우, prod-beluga-manager-consumer로 "deploy"에 대한 배포 Release(IT-4831, IT-5027) v1.5.0 (#166) 형태로 표시됩니다.</em></p>
</div>

<table class="wrapped" style="width: 100%;">
<colgroup>
<col style="width: 120px;" />
<col style="width: 300px;" />
<col style="width: 150px;" />
<col style="width: 400px;" />
</colgroup>
<tbody>
<tr>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">키</th>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">요약</th>
<th style="text-align: left; background-color: #f4f5f7; padding: 8px; border: 1px solid #dfe1e6;">생성 일시(최근 배포티켓)</th>
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
            
            print_log(f"{i}. {issue_key}: {summary}", 'DEBUG')
            print_log(f"   예정된 시작: {custom_field}", 'DEBUG')
            print_log(f"   상태: {status}", 'DEBUG')
            
            # IT 티켓만 필터링하여 연결된 이슈 조회 (재시도 로직 포함)
            linked_it_tickets = get_linked_it_tickets_with_retry(jira, issue_key)
            print_log(f"   연결된 IT 티켓 수: {len(linked_it_tickets)}", 'DEBUG')
            
            # 연결된 IT 티켓들 중 가장 최근에 생성된 티켓의 생성 일시(최근 배포티켓) 조회
            latest_date_obj, latest_created_date = get_latest_created_date_from_linked_tickets(jira, linked_it_tickets)
            
            # 연결된 IT 티켓들을 포맷팅
            if linked_it_tickets:
                linked_tickets_html = '<br>'.join([
                    f"{j}. <a href=\"{jira_url}/browse/{ticket['key']}\">{ticket['key']}</a><span style=\"display: inline-block; padding: 2px 8px; margin-left: 4px; border-radius: 12px; font-size: 11px; font-weight: 500; {get_status_style(ticket['status'])}\">{ticket['status']}</span><br>: {ticket['summary']}"
                    for j, ticket in enumerate(linked_it_tickets, 1)
                ])
            else:
                linked_tickets_html = '<em>연결된 IT 티켓 없음</em>'
            
            # 생성 일시(최근 배포티켓) 표시 - 10분 이내면 빨간색으로 표시
            if latest_date_obj and latest_created_date:
                from datetime import datetime, timedelta
                current_time = datetime.now()
                time_diff = current_time - latest_date_obj
                
                print_log(f"    생성 일시 비교: {latest_created_date} vs 현재시간 {current_time.strftime('%Y-%m-%d %H:%M')}", 'DEBUG')
                print_log(f"    시간 차이: {time_diff.total_seconds() / 3600:.2f}시간", 'DEBUG')
                
                # 10분 이내인지 확인
                if time_diff <= timedelta(minutes=10):
                    created_date_html = f'<span style="color: #FF0000; font-weight: bold;">{latest_created_date}</span>'
                    print_log(f"    ✅ 빨간색으로 표시: {latest_created_date}", 'DEBUG')
                else:
                    created_date_html = latest_created_date
                    print_log(f"    ⏭️ 일반 표시: {latest_created_date}", 'DEBUG')
            else:
                created_date_html = '<em>정보 없음</em>'
                print_log(f"    ❌ 생성 일시 정보 없음", 'DEBUG')
            
            html_content += f'''
<tr>
<td style="padding: 8px; border: 1px solid #dfe1e6;"><a href="{jira_url}/browse/{issue_key}">{issue_key}</a></td>
<td style="padding: 8px; border: 1px solid #dfe1e6;">{summary}</td>
<td style="padding: 8px; border: 1px solid #dfe1e6;">{created_date_html}</td>
<td style="padding: 8px; border: 1px solid #dfe1e6;">{linked_tickets_html}</td>
</tr>
'''
        
        html_content += '''
</tbody>
</table>
'''
        
        print_log(f"=== HTML 테이블 생성 완료 ===", 'DEBUG')
        return html_content
        
    except Exception as e:
        print_log(f"배포 예정 목록 HTML 테이블 생성 실패: {e}", 'ERROR')
        return f'<p>배포 예정 목록 HTML 테이블 생성 중 오류가 발생했습니다: {e}</p>'

def get_latest_created_date_from_linked_tickets(jira, linked_tickets):
    """연결된 IT 티켓들 중 가장 최근에 생성된 티켓의 생성 일시를 반환합니다."""
    try:
        if not linked_tickets:
            return None, None
        
        latest_date = None
        latest_ticket_key = None
        
        for ticket in linked_tickets:
            ticket_key = ticket['key']
            try:
                # Jira API에서 티켓의 상세 정보 조회 (created 필드 포함)
                ticket_detail = jira.issue(ticket_key, fields='created')
                
                # created 필드에서 날짜 추출
                created_date_str = ticket_detail.fields.created
                if created_date_str:
                    # ISO 형식의 날짜를 파싱 (예: 2024-01-15T10:30:00.000+0900)
                    from datetime import datetime
                    
                    # 이미 한국 시간(+0900)으로 되어 있으므로 그대로 사용
                    if '+0900' in created_date_str:
                        created_date = datetime.fromisoformat(created_date_str)
                        created_date_kr = created_date.replace(tzinfo=None)
                    else:
                        # UTC 시간인 경우 한국 시간으로 변환
                        created_date = datetime.fromisoformat(created_date_str.replace('Z', '+00:00'))
                        created_date_kr = created_date.replace(tzinfo=None) + timedelta(hours=9)
                    
                    # 가장 최근 날짜 업데이트
                    if latest_date is None or created_date_kr > latest_date:
                        latest_date = created_date_kr
                        latest_ticket_key = ticket_key
                        
                    print_log(f"    티켓 {ticket_key} 생성일: {created_date_kr.strftime('%Y-%m-%d %H:%M')}", 'DEBUG')
                    
            except Exception as e:
                print_log(f"    티켓 {ticket_key} 생성일 조회 실패: {e}", 'WARNING')
                continue
        
        if latest_date:
            formatted_date = latest_date.strftime('%Y-%m-%d %H:%M')
            print_log(f"    최근 생성 티켓: {latest_ticket_key} ({formatted_date})", 'DEBUG')
            return latest_date, formatted_date
        else:
            print_log("    생성일 정보를 찾을 수 없습니다.", 'WARNING')
            return None, None
            
    except Exception as e:
        print_log(f"연결된 티켓들의 생성일 조회 실패: {e}", 'ERROR')
        return None, None

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
        print_log(f"=== '{issue_key}'의 연결된 IT 티켓 조회 시작 ===", 'DEBUG')
        
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
            print_log(f"발견된 issuelinks 수: {len(issue_data['fields']['issuelinks'])}", 'DEBUG')
            
            for i, link in enumerate(issue_data['fields']['issuelinks']):
                link_type = link.get('type', {}).get('name', '')
                print_log(f"  링크 {i+1}: {link_type}", 'DEBUG')
                
                linked_ticket = None
                
                # 배포 관련 링크 타입만 확인 (Deployments, is deployed by로 제한)
                deployment_link_types = ['Deployments', 'is deployed by']
                if link_type in deployment_link_types:
                    # IT-5332의 경우: IT-5332가 배포되는 관계이므로 inwardIssue가 배포 티켓
                    if 'inwardIssue' in link:
                        linked_ticket = link['inwardIssue']
                        print_log(f"    inwardIssue 발견: {linked_ticket.get('key', 'Unknown')}", 'DEBUG')
                    elif 'outwardIssue' in link:
                        linked_ticket = link['outwardIssue']
                        print_log(f"    outwardIssue 발견: {linked_ticket.get('key', 'Unknown')}", 'DEBUG')
                
                # 연결된 티켓이 IT 관련 타입인 경우 추가
                if linked_ticket:
                    issue_type = linked_ticket.get('fields', {}).get('issuetype', {}).get('name', '')
                    print_log(f"    티켓 타입: {issue_type}", 'DEBUG')
                    
                    # IT 관련 이슈 타입들 (더 유연한 필터링)
                    it_issue_types = ['변경', 'Change', 'IT', '개발', 'Development', 'Task', 'Sub-task']
                    if any(it_type in issue_type for it_type in it_issue_types):
                        ticket_info = {
                            'key': linked_ticket['key'],
                            'summary': linked_ticket['fields'].get('summary', ''),
                            'status': linked_ticket['fields'].get('status', {}).get('name', '')
                        }
                        linked_it_tickets.append(ticket_info)
                        print_log(f"    ✅ IT 티켓 추가: {ticket_info['key']} - {ticket_info['summary']}", 'DEBUG')
                    else:
                        print_log(f"    ⏭️ IT 타입이 아님: {linked_ticket.get('key', 'Unknown')} ({issue_type})", 'DEBUG')
                else:
                    print_log(f"    ⏭️ 연결된 티켓 없음", 'DEBUG')
        else:
            print_log("issuelinks 필드를 찾을 수 없습니다.", 'WARNING')
        
        print_log(f"=== '{issue_key}' 연결된 IT 티켓 조회 완료: {len(linked_it_tickets)}개 ===", 'DEBUG')
        return linked_it_tickets
        
    except Exception as e:
        print_log(f"'{issue_key}'의 연결된 IT 티켓 조회 실패: {e}", 'ERROR')
        return []

def get_linked_it_tickets_with_retry(jira, issue_key, max_retries=3):
    """재시도 로직을 포함한 연결된 IT 티켓 조회"""
    for attempt in range(max_retries):
        try:
            result = get_linked_it_tickets(jira, issue_key)
            if result is not None:  # 성공적인 결과
                return result
        except Exception as e:
            print_log(f"'{issue_key}' 조회 시도 {attempt + 1}/{max_retries} 실패: {e}", 'WARNING')
            if attempt < max_retries - 1:
                import time
                time.sleep(1)  # 1초 대기 후 재시도
            else:
                print_log(f"'{issue_key}' 최대 재시도 횟수 초과", 'ERROR')
                return []
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
    
    # 시간 제한 확인 (9시~22시 사이에만 알림 전송)
    notification_start_hour =9
    notification_end_hour = 22
    
    today = datetime.now()
    if today.hour < notification_start_hour or today.hour >= notification_end_hour:
        print(f"현재 시간에는 슬랙 알림 전송을 건너뜁니다. (오전 {notification_start_hour}시 ~ {notification_end_hour}시 외)")
        return
    
    try:
        r = requests.post(url, json={"text": text})
        if r.status_code != 200:
            print(f"Slack 알림 실패: {r.text}")
        else:
            print(f"Slack 알림 전송 성공: {len(text)}자")
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
        changed_issues (dict): 변경 유형별 이슈 목록 {'added': [], 'removed': [], 'updated': []}
        page_title (str): 페이지 제목
        
    Returns:
        str: 변경사항의 고유 해시
    """
    # 모든 변경사항을 하나의 리스트로 합치고 정렬하여 일관된 해시 생성
    all_issues = []
    for change_type, issues in changed_issues.items():
        for issue in issues:
            all_issues.append({
                'key': issue['key'],
                'summary': issue['summary'],
                'type': change_type
            })
    
    # 키로 정렬하여 일관된 해시 생성
    sorted_issues = sorted(all_issues, key=lambda x: x['key'])
    change_data = {
        'page_title': page_title,
        'issues': [(issue['key'], issue['summary'], issue['type']) for issue in sorted_issues]
    }
    return json.dumps(change_data, sort_keys=True, ensure_ascii=False)


def notify_new_deploy_tickets(issues, jira_url, page_title, deploy_message_enabled=False):
    """새로운 배포 티켓들을 Slack으로 알림을 보냅니다."""
    # 배포 메시지 알림이 비활성화된 경우 함수 종료
    if not deploy_message_enabled:
        print("🔕 배포 메시지 알림이 비활성화되어 있습니다. (DEPLOY_MESSAGE=off)")
        return
    
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
                full_message = f"@박소연 님, 배포 내용을 확인 후 승인해주세요.\n\n" + "\n\n".join(messages)
                
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

def get_snapshot_file_path(mode):
    """
    모드별로 별도의 스냅샷 파일 경로를 반환합니다.

    Args:
        mode (str): 실행 모드 (create, current, update, last)

    Returns:
        str: 모드별 스냅샷 파일 경로
    """
    mode_suffix = {
        "create": "next_week",      # 다음 주
        "current": "current_week",   # 이번 주
        "update": "current_week",    # 이번 주 (update는 current와 동일)
        "last": "last_week"          # 지난 주
    }

    suffix = mode_suffix.get(mode, "current_week")
    return f'weekly_issues_snapshot_{suffix}.json'

def get_changed_issues(prev, curr, jira_url):
    """
    이전 스냅샷(prev)과 현재 스냅샷(curr)을 비교하여 변경된 IT티켓 목록을 반환합니다.
    - 새로 추가된 티켓 (+)
    - 제거된 티켓 (-)
    - deploy_date(배포 예정일)가 변경된 티켓 (🔄)
    Args:
        prev (list): 이전 스냅샷
        curr (list): 현재 스냅샷
        jira_url (str): Jira base URL
    Returns:
        dict: 변경 유형별 티켓 목록 {'added': [], 'removed': [], 'updated': []}
    """
    prev_dict = {i['key']: i for i in prev or []}
    curr_dict = {i['key']: i for i in curr or []}
    
    added = []
    removed = []
    updated = []
    
    # 새로 추가된 티켓과 업데이트된 티켓 확인
    for key, curr_issue in curr_dict.items():
        prev_issue = prev_dict.get(key)
        if not prev_issue:
            # 새로 추가된 티켓
            added.append({
                'key': key,
                'summary': curr_issue.get('summary', ''),
                'url': f"{jira_url}/browse/{key}"
            })
        else:
            # deploy_date만 변경 여부 확인
            if curr_issue.get('deploy_date') != prev_issue.get('deploy_date'):
                updated.append({
                    'key': key,
                    'summary': curr_issue.get('summary', ''),
                    'url': f"{jira_url}/browse/{key}"
                })
    
    # 제거된 티켓 확인
    for key, prev_issue in prev_dict.items():
        if key not in curr_dict:
            removed.append({
                'key': key,
                'summary': prev_issue.get('summary', ''),
                'url': f"{jira_url}/browse/{key}"
            })
    
    return {
        'added': added,
        'removed': removed,
        'updated': updated
    }


def get_jira_issues_by_customfield_10817(jira, project_key, start_date, end_date, use_pagination=False):
    """customfield_10817 필드 값이 해당 주간에 속하는 모든 티켓을 조회합니다."""
    print_log(f"=== customfield_10817 직접 조회 시작 ===", 'DEBUG')
    print_log(f"프로젝트: {project_key}", 'INFO')
    print_log(f"대상 기간: {start_date} ~ {end_date}", 'INFO')
    print_log(f"페이지네이션 사용: {'예' if use_pagination else '아니오'}", 'INFO')
    
    try:
        # 1단계: cf[10817] 형식으로 JQL 쿼리 (매크로와 동일한 조건 사용)
        base_jql = (
            f"project = '{project_key}' AND "
            f"cf[10817] >= '{start_date}' AND cf[10817] <= '{end_date}' "
            f"ORDER BY created DESC"
        )
        fields_param = f"key,summary,status,assignee,created,updated,{JIRA_DEPLOY_DATE_FIELD_ID}"
        
        print_log(f"기본 JQL: {base_jql}", 'DEBUG')
        print_log(f"조회 필드: {fields_param}", 'DEBUG')
        
        # 페이지네이션 사용 여부에 따른 티켓 조회
        if use_pagination:
            # 페이지네이션을 사용하여 모든 티켓 조회
            all_issues = []
            start_at = 0
            max_results = 1000  # 한 번에 1000개씩 조회
            
            while True:
                batch = jira.search_issues(base_jql, fields=fields_param, startAt=start_at, maxResults=max_results)
                if not batch:
                    break
                all_issues.extend(batch)
                start_at += len(batch)
                print_log(f"배치 조회: {len(batch)}개 (총 {len(all_issues)}개)", 'DEBUG')
                if len(batch) < max_results:
                    break
            
            print_log(f"✅ 전체 티켓 조회 성공 (페이지네이션 사용): {len(all_issues)}개", 'INFO')
        else:
            # 페이지네이션 없이 한 번에 조회 (기본값: 최대 1000개)
            all_issues = jira.search_issues(base_jql, fields=fields_param, maxResults=1000)
            print_log(f"✅ 전체 티켓 조회 성공 (페이지네이션 미사용): {len(all_issues)}개", 'INFO')
        
        # 2단계: customfield_10817 필드 값이 해당 주간에 속하는 티켓 필터링
        filtered_issues = []
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        print_log(f"\n=== customfield_10817 필드 값 필터링 ===", 'DEBUG')
        print_log(f"필터링 범위: {start_date_obj} ~ {end_date_obj}", 'DEBUG')
        print_log(f"목표: 해당 주간에 속하는 모든 IT 티켓 포함", 'DEBUG')
        
        # 제거된 티켓들을 확인하기 위한 디버깅 리스트
        removed_tickets = []
        included_tickets = []
        
        for issue in all_issues:
            issue_key = issue.key
            custom_field_value = getattr(issue.fields, JIRA_DEPLOY_DATE_FIELD_ID, None)
            
            if custom_field_value:
                # customfield_10817 값이 있는 경우, 날짜 파싱 및 필터링
                try:
                    # ISO 형식 날짜 문자열을 파싱
                    if isinstance(custom_field_value, str):
                        # "2025-07-23T11:00:00.000+0900" 형식 파싱
                        field_date_str = custom_field_value.split('T')[0]  # 날짜 부분만 추출
                        field_date = datetime.strptime(field_date_str, '%Y-%m-%d').date()
                    else:
                        # datetime 객체인 경우
                        field_date = custom_field_value.date()
                    
                    # 해당 주간에 속하는지 확인
                    if start_date_obj <= field_date <= end_date_obj:
                        # 포함되는 티켓
                        issue_dict = {
                            'key': issue_key,
                            'summary': getattr(issue.fields, 'summary', ''),
                            'status': getattr(issue.fields, 'status', {}).name if hasattr(getattr(issue.fields, 'status', {}), 'name') else str(getattr(issue.fields, 'status', '')),
                            'assignee': getattr(issue.fields, 'assignee', {}).displayName if hasattr(getattr(issue.fields, 'assignee', {}), 'displayName') else str(getattr(issue.fields, 'assignee', '')),
                            'created': getattr(issue.fields, 'created', ''),
                            'updated': getattr(issue.fields, 'updated', ''),
                            'fields': {
                                'summary': getattr(issue.fields, 'summary', ''),
                                'status': {'name': getattr(issue.fields, 'status', {}).name if hasattr(getattr(issue.fields, 'status', {}), 'name') else str(getattr(issue.fields, 'status', ''))},
                                JIRA_DEPLOY_DATE_FIELD_ID: custom_field_value
                            }
                        }
                        filtered_issues.append(issue_dict)
                        included_tickets.append(f"✅ {issue_key}: {field_date} (예정된 시작: {custom_field_value}) - 포함됨")
                    else:
                        # 범위 외 티켓
                        removed_tickets.append(f"⏭️ {issue_key}: {field_date} (범위 외: {start_date_obj} ~ {end_date_obj})")
                except Exception as e:
                    print_log(f"날짜 파싱 오류 ({issue_key}): {e}", 'WARNING')
                    removed_tickets.append(f"⏭️ {issue_key}: 날짜 파싱 오류")
            else:
                # customfield_10817 값이 없는 티켓 (이 경우는 발생하지 않아야 함)
                removed_tickets.append(f"⏭️ {issue_key}: customfield_10817 값 없음")
        
        # 필터링 결과 출력 (간략화)
        print_log(f"\n=== 필터링 결과 ===", 'INFO')
        print_log(f"전체 티켓: {len(all_issues)}개", 'INFO')
        print_log(f"customfield_10817 값이 있는 티켓: {len([i for i in all_issues if getattr(i.fields, JIRA_DEPLOY_DATE_FIELD_ID, None)])}개", 'INFO')
        print_log(f"해당 주간에 속하는 티켓: {len(filtered_issues)}개", 'INFO')
        print_log(f"제거된 티켓: {len(removed_tickets)}개", 'INFO')
        
        # 포함된 티켓 상세 정보 출력 (DEBUG 레벨로 변경)
        print_log(f"\n=== 포함된 티켓 상세 정보 ===", 'DEBUG')
        for ticket_info in included_tickets:
            print_log(f"  {ticket_info}", 'DEBUG')
        
        # 제거된 티켓 상세 정보 출력 (DEBUG 레벨로 변경, 최대 10개만)
        if removed_tickets:
            print_log(f"\n=== 제거된 티켓 상세 정보 ===", 'DEBUG')
            for i, ticket_info in enumerate(removed_tickets[:10]):
                print_log(f"  {ticket_info}", 'DEBUG')
            if len(removed_tickets) > 10:
                print_log(f"  ... 외 {len(removed_tickets) - 10}개", 'DEBUG')
        
        print_log(f"\n=== 최종 결과 ===", 'DEBUG')
        for i, issue in enumerate(filtered_issues, 1):
            print_log(f"{i}. {issue['key']}: {issue['summary']}", 'DEBUG')
            print_log(f"   예정된 시작: {issue['fields'][JIRA_DEPLOY_DATE_FIELD_ID]}", 'DEBUG')
            print_log(f"   상태: {issue['status']}", 'DEBUG')
        
        return filtered_issues
        
    except Exception as e:
        print_log(f"Jira 이슈 조회 실패: {e}", 'ERROR')
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
    
    # 배포 메시지 알림 설정 (기본값: off)
    deploy_message_enabled = os.getenv('DEPLOY_MESSAGE', 'off').lower() == 'on'
    
    # 배포 메시지 알림 설정 상태 출력
    deploy_status = "🟢 활성화" if deploy_message_enabled else "🔴 비활성화"
    print_log(f"📢 배포 메시지 알림: {deploy_status} (DEPLOY_MESSAGE={os.getenv('DEPLOY_MESSAGE', 'off')})", 'INFO')
    
    # 2. API 클라이언트 생성
    try:
        jira = JIRA(server=atlassian_url, basic_auth=(atlassian_username, atlassian_token))
        confluence = Confluence(url=atlassian_url, username=atlassian_username, password=atlassian_token, cloud=True)
        print_log(f"\nJira/Confluence 서버 연결 성공!: {get_now_str()}", 'INFO')
    except Exception as e:
        print_log(f"Jira/Confluence 연결 오류: {e}", 'ERROR')
        return
    
    # 3. 명령행 인수 처리
    mode = "update"  # 기본값
    force_update = False  # 강제 업데이트 플래그
    use_pagination = False  # 페이지네이션 사용 여부 (기본값: False)
    test_mode = False  # MUTE 모드 플래그 (Slack 알림 비활성화)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check-page":
            check_confluence_page_content()
            return
        elif sys.argv[1] == "--debug-links" and len(sys.argv) > 2:
            # 특정 티켓의 연결 관계 디버깅
            env_vars = load_env_vars([
                'ATLASSIAN_URL', 'ATLASSIAN_USERNAME', 'ATLASSIAN_API_TOKEN'
            ])
            jira = JIRA(server=env_vars['ATLASSIAN_URL'], 
                       basic_auth=(env_vars['ATLASSIAN_USERNAME'], env_vars['ATLASSIAN_API_TOKEN']))
            debug_issue_links(jira, sys.argv[2])
            return
        elif sys.argv[1] == "--force-update":
            mode = "update"
            force_update = True
        else:
            mode = sys.argv[1]
    
    # --pagination 옵션 확인
    if "--pagination" in sys.argv:
        use_pagination = True
        print_log("페이지네이션 옵션이 활성화되었습니다.", 'INFO')
    elif "--no-pagination" in sys.argv:
        use_pagination = False
        print_log("페이지네이션 옵션이 비활성화되었습니다. (기본값)", 'INFO')
    
    # --mute 옵션 확인 (Slack 알림 비활성화)
    if "--mute" in sys.argv:
        test_mode = True
        print_log("🧪 MUTE 모드가 활성화되었습니다. Slack 알림이 전송되지 않습니다.", 'INFO')
    
    # 4. 날짜 범위 계산
    monday, sunday = get_week_range(mode)
    start_date_str, end_date_str = monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')
    page_title = get_page_title(monday, sunday)
    
    # 디버깅: 날짜 범위 상세 정보 출력 (DEBUG 레벨로 변경)
    print_log(f"\n=== 날짜 범위 계산 디버깅 ===", 'DEBUG')
    print_log(f"현재 날짜: {date.today()}", 'DEBUG')
    print_log(f"요일: {date.today().weekday()} (0=월요일, 6=일요일)", 'DEBUG')
    print_log(f"계산된 월요일: {monday}", 'DEBUG')
    print_log(f"계산된 일요일: {sunday}", 'DEBUG')
    print_log(f"시작일: {start_date_str}", 'DEBUG')
    print_log(f"종료일: {end_date_str}", 'DEBUG')
    print_log(f"페이지 제목: {page_title}", 'DEBUG')
    print_log(f"사용자 의도 확인: 7월 4째주 (07/21~07/27)와 일치하는가?", 'DEBUG')
    print_log("", 'DEBUG')
    
    # 모드별 설명 메시지
    mode_descriptions = {
        "create": "다음 주 (차주) 배포 예정 티켓으로 리포트 생성",
        "current": "이번 주 (현재 주) 배포 예정 티켓으로 리포트 생성/업데이트", 
        "last": "지난 주 배포 예정 티켓으로 리포트 생성/업데이트",
        "update": "이번 주 배포 예정 티켓으로 리포트 업데이트 (기본값)"
    }
    mode_desc = mode_descriptions.get(mode, "이번 주")
    print_log(f"실행 모드: {mode} ({mode_desc})", 'INFO')
    print_log(f"대상 기간: {start_date_str} ~ {end_date_str}", 'INFO')
    print_log(f"페이지 제목: {page_title}", 'INFO')

    # 5. Jira 이슈 조회 (customfield_10817 직접 조회 사용)
    jql_query = (
        f"project = '{jira_project_key}' AND "
        f"'{JIRA_DEPLOY_DATE_FIELD_ID}' >= '{start_date_str}' AND '{JIRA_DEPLOY_DATE_FIELD_ID}' <= '{end_date_str}' "
        f"ORDER BY updated DESC"
    )
    issues = get_jira_issues_by_customfield_10817(jira, jira_project_key, start_date_str, end_date_str, use_pagination)
    if not issues:
        print_log(f"{mode_desc}에 배포 예정 티켓 없음. 빈 테이블로 생성/업데이트.", 'INFO')

    # 6. 변경 감지
    SNAPSHOT_FILE_PATH = get_snapshot_file_path(mode)
    print_log(f"\n=== 스냅샷 파일 정보 ===", 'DEBUG')
    print_log(f"모드: {mode}", 'DEBUG')
    print_log(f"스냅샷 파일: {SNAPSHOT_FILE_PATH}", 'DEBUG')
    print_log(f"대상 기간: {start_date_str} ~ {end_date_str}", 'DEBUG')
    
    prev_snapshot = read_json(SNAPSHOT_FILE_PATH)
    curr_snapshot = snapshot_issues(issues, JIRA_DEPLOY_DATE_FIELD_ID)
    
    # create, current 모드에서는 이슈 변경 여부와 관계없이 페이지 생성/업데이트 진행
    if mode in ["create", "current"]:
        changed_issues = get_changed_issues(prev_snapshot, curr_snapshot, atlassian_url)
    else:
        # update 모드에서만 이슈 변경 감지 (강제 업데이트 제외)
        if not force_update and not issues_changed(prev_snapshot, curr_snapshot):
            print_log(f"JIRA 이슈 변경 없음. 업데이트/알림 생략. {get_now_str()}", 'INFO')
            log(f"\n실행시간: {get_now_str()}\n업데이트 할 사항 없음.")
            return
        changed_issues = get_changed_issues(prev_snapshot, curr_snapshot, atlassian_url)

    # 7. Confluence 페이지 생성/업데이트 및 Slack 알림
    page_content = create_confluence_content(jql_query, issues, atlassian_url, jira, jira_project_key, start_date_str, end_date_str, use_pagination)
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
                total_changes = len(changed_issues.get('added', [])) + len(changed_issues.get('removed', [])) + len(changed_issues.get('updated', []))
                if total_changes > 0 and change_hash not in notified_changes:
                    # 변경 유형별로 메시지 구성
                    added_list = '\n'.join([
                        f"➕ <{i['url']}|{i['key']}: {i['summary']}>" for i in changed_issues.get('added', [])
                    ])
                    removed_list = '\n'.join([
                        f"➖ <{i['url']}|{i['key']}: {i['summary']}>" for i in changed_issues.get('removed', [])
                    ])
                    updated_list = '\n'.join([
                        f"🔄 <{i['url']}|{i['key']}: {i['summary']}>" for i in changed_issues.get('updated', [])
                    ])
                    
                    # 변경사항 요약 메시지 구성
                    change_summary = []
                    if changed_issues.get('added'):
                        change_summary.append(f"➕ 추가: {len(changed_issues['added'])}개")
                    if changed_issues.get('removed'):
                        change_summary.append(f"➖ 제거: {len(changed_issues['removed'])}개")
                    if changed_issues.get('updated'):
                        change_summary.append(f"🔄 갱신: {len(changed_issues['updated'])}개")
                    
                    # 전체 변경사항 목록
                    all_changes = []
                    if added_list:
                        all_changes.append(f"[추가된 티켓]\n{added_list}")
                    if removed_list:
                        all_changes.append(f"[제거된 티켓]\n{removed_list}")
                    if updated_list:
                        all_changes.append(f"[갱신된 티켓]\n{updated_list}")
                    
                    changes_text = '\n\n'.join(all_changes)
                    summary_text = ' | '.join(change_summary)
                    
                    # MUTE 모드가 아닌 경우에만 Slack 알림 전송
                    if not test_mode:
                        slack_msg = f"📊 배포 일정 리포트가 업데이트되었습니다:\n{page_title}\n{page_url}\n\n{summary_text}\n\n{changes_text}"
                        send_slack(slack_msg)
                        # 알림을 보낸 변경사항 해시를 저장
                        notified_changes.add(change_hash)
                        save_notified_changes(notified_changes)
                        
                        print(f"Slack 알림 전송 완료 (변경사항: {total_changes}개)")
                    else:
                        print(f"🧪 MUTE 모드: Slack 알림 전송 생략 (변경사항: {total_changes}개)")
                elif total_changes > 0:
                    print(f"동일한 변경사항에 대한 알림이 이미 전송됨 (변경사항: {total_changes}개)")
                else:
                    print("변경사항이 없어 Slack 알림을 전송하지 않습니다.")
                
                # MUTE 모드가 아닌 경우에만 새로운 배포 티켓 알림 전송
                if not test_mode:
                    notify_new_deploy_tickets(issues, atlassian_url, page_title, deploy_message_enabled)
                else:
                    print("🧪 MUTE 모드: 새로운 배포 티켓 알림 전송 생략")
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
            total_changes = len(changed_issues.get('added', [])) + len(changed_issues.get('removed', [])) + len(changed_issues.get('updated', []))
            if total_changes > 0 and change_hash not in notified_changes:
                # 변경 유형별로 메시지 구성
                added_list = '\n'.join([
                    f"➕ <{i['url']}|{i['key']}: {i['summary']}>" for i in changed_issues.get('added', [])
                ])
                removed_list = '\n'.join([
                    f"➖ <{i['url']}|{i['key']}: {i['summary']}>" for i in changed_issues.get('removed', [])
                ])
                updated_list = '\n'.join([
                    f"🔄 <{i['url']}|{i['key']}: {i['summary']}>" for i in changed_issues.get('updated', [])
                ])
                
                # 변경사항 요약 메시지 구성
                change_summary = []
                if changed_issues.get('added'):
                    change_summary.append(f"➕ 추가: {len(changed_issues['added'])}개")
                if changed_issues.get('removed'):
                    change_summary.append(f"➖ 제거: {len(changed_issues['removed'])}개")
                if changed_issues.get('updated'):
                    change_summary.append(f"🔄 갱신: {len(changed_issues['updated'])}개")
                
                # 전체 변경사항 목록
                all_changes = []
                if added_list:
                    all_changes.append(f"[추가된 티켓]\n{added_list}")
                if removed_list:
                    all_changes.append(f"[제거된 티켓]\n{removed_list}")
                if updated_list:
                    all_changes.append(f"[갱신된 티켓]\n{updated_list}")
                
                changes_text = '\n\n'.join(all_changes)
                summary_text = ' | '.join(change_summary)
                
                # MUTE 모드가 아닌 경우에만 Slack 알림 전송
                if not test_mode:
                    slack_msg = f"📊 배포 일정 리포트가 업데이트되었습니다:\n{page_title}\n{page_url}\n\n{summary_text}\n\n{changes_text}"
                    send_slack(slack_msg)
                    # 알림을 보낸 변경사항 해시를 저장
                    notified_changes.add(change_hash)
                    save_notified_changes(notified_changes)
                    
                    print(f"Slack 알림 전송 완료 (변경사항: {total_changes}개)")
                else:
                    print(f"�� MUTE 모드: Slack 알림 전송 생략 (변경사항: {total_changes}개)")
            elif total_changes > 0:
                print(f"동일한 변경사항에 대한 알림이 이미 전송됨 (변경사항: {total_changes}개)")
            else:
                print("변경사항이 없어 Slack 알림을 전송하지 않습니다.")
            
            # MUTE 모드가 아닌 경우에만 새로운 배포 티켓 알림 전송
            if not test_mode:
                notify_new_deploy_tickets(issues, atlassian_url, page_title, deploy_message_enabled)
            else:
                print("🧪 MUTE 모드: 새로운 배포 티켓 알림 전송 생략")
            log(f"실행시간: {get_now_str()}\n대상: {', '.join([i['key'] for i in issues])} 생성.")
        
        # 스냅샷 저장
        write_json(SNAPSHOT_FILE_PATH, curr_snapshot)
        print(f"✅ 스냅샷 저장 완료: {SNAPSHOT_FILE_PATH} ({len(curr_snapshot)}개 이슈)")
        
    except Exception as e:
        error_msg = f"Confluence 페이지 생성/업데이트 실패: {e}"
        print(error_msg)
        log(error_msg)
        raise

def debug_issue_links(jira, issue_key):
    """특정 이슈의 모든 연결 관계를 디버깅합니다."""
    try:
        print(f"=== '{issue_key}' 연결 관계 디버깅 ===")
        
        # Jira API에서 이슈 정보를 가져옵니다 (issuelinks 확장)
        issue_response = jira.issue(issue_key, expand='issuelinks')
        
        # 응답이 딕셔너리인지 확인
        if isinstance(issue_response, dict):
            issue_data = issue_response
        else:
            # 객체인 경우 딕셔너리로 변환
            issue_data = issue_response.raw
        
        print(f"이슈 키: {issue_key}")
        print(f"이슈 타입: {issue_data.get('fields', {}).get('issuetype', {}).get('name', 'Unknown')}")
        print(f"이슈 요약: {issue_data.get('fields', {}).get('summary', 'Unknown')}")
        
        # customfield_10817 필드 확인
        customfield_10817 = issue_data.get('fields', {}).get('customfield_10817')
        if customfield_10817:
            print(f"예정된 시작: {customfield_10817}")
        else:
            print("예정된 시작: 설정되지 않음")
        
        # issuelinks 필드가 있는지 확인
        if 'fields' in issue_data and 'issuelinks' in issue_data['fields']:
            links = issue_data['fields']['issuelinks']
            print(f"총 연결 관계 수: {len(links)}")
            
            for i, link in enumerate(links, 1):
                link_type = link.get('type', {}).get('name', 'Unknown')
                print(f"\n  연결 {i}: {link_type}")
                
                # inwardIssue 확인
                if 'inwardIssue' in link:
                    inward = link['inwardIssue']
                    inward_type = inward.get('fields', {}).get('issuetype', {}).get('name', 'Unknown')
                    print(f"    Inward: {inward.get('key', 'Unknown')} ({inward_type})")
                    print(f"    Inward 요약: {inward.get('fields', {}).get('summary', 'Unknown')}")
                
                # outwardIssue 확인
                if 'outwardIssue' in link:
                    outward = link['outwardIssue']
                    outward_type = outward.get('fields', {}).get('issuetype', {}).get('name', 'Unknown')
                    print(f"    Outward: {outward.get('key', 'Unknown')} ({outward_type})")
                    print(f"    Outward 요약: {outward.get('fields', {}).get('summary', 'Unknown')}")
        else:
            print("issuelinks 필드를 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"'{issue_key}' 연결 관계 디버깅 실패: {e}")

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
