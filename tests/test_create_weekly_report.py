import pytest
import types
import datetime
import os
import sys
import json
from unittest.mock import MagicMock, patch
from freezegun import freeze_time

# 테스트 대상 함수 import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import create_weekly_report as cwr

# get_jira_issues 테스트
def test_get_jira_issues_success():
    mock_jira = MagicMock()
    mock_jira.jql.return_value = {'issues': [
        {'key': 'IT-1', 'fields': {'customfield_10817': '2024-07-15'}},
        {'key': 'IT-2', 'fields': {'customfield_10817': '2024-07-16'}},
    ]}
    issues = cwr.get_jira_issues(mock_jira, 'IT', 'customfield_10817', '2024-07-15', '2024-07-16')
    assert len(issues) == 2
    assert issues[0]['key'] == 'IT-1'
    assert issues[1]['fields']['customfield_10817'] == '2024-07-16'

def test_get_jira_issues_exception():
    mock_jira = MagicMock()
    mock_jira.jql.side_effect = Exception('Jira error')
    issues = cwr.get_jira_issues(mock_jira, 'IT', 'customfield_10817', '2024-07-15', '2024-07-16')
    assert issues == []

# create_confluence_page_content 테스트
def test_create_confluence_page_content():
    jql = "project = 'IT'"
    issues = [
        {'key': 'IT-1', 'fields': {'issuelinks': []}},
        {'key': 'IT-2', 'fields': {'issuelinks': []}},
    ]
    jira_url = 'https://jira.example.com'
    html = cwr.create_confluence_page_content(jql, issues, jira_url)
    assert '<ac:structured-macro ac:name="jira">' in html
    assert 'IT-1' in html and 'IT-2' in html

# normalize_html_content 테스트
def test_normalize_html_content():
    html1 = '  <div>Test&nbsp;Content</div>\n'
    html2 = '<div>Test Content</div>'
    assert cwr.normalize_html_content(html1) == cwr.normalize_html_content(html2)

# get_week_dates 테스트
def test_get_week_dates_create_and_update():
    # 월요일이 2024-07-15, 일요일이 2024-07-21로 가정
    # with freeze_time('datetime.date.today', return_value=datetime.date(2024, 7, 10)):
    with freeze_time('2024-07-10'):
        monday, sunday = cwr.get_week_dates('create')
        assert monday.weekday() == 0
        assert (sunday - monday).days == 6
        monday2, sunday2 = cwr.get_week_dates('update')
        assert monday2.weekday() == 0
        assert (sunday2 - monday2).days == 6

# send_slack_message 테스트
def test_send_slack_message(monkeypatch):
    called = {}
    def fake_post(url, json):
        called['url'] = url
        called['json'] = json
        class Resp: status_code = 200
        return Resp()
    monkeypatch.setattr('requests.post', fake_post)
    os.environ['SLACK_WEBHOOK_URL'] = 'http://fake'
    cwr.send_slack_message('hello')
    assert called['url'] == 'http://fake'
    assert called['json']['text'] == 'hello'

# get_notified_deploy_keys & save_notified_deploy_keys 테스트
def test_notified_deploy_keys(tmp_path):
    test_file = tmp_path / 'notified_deploy_keys.json'
    # 저장
    cwr.save_notified_deploy_keys({'A', 'B'})
    # 읽기
    keys = cwr.get_notified_deploy_keys()
    assert isinstance(keys, set)

# serialize_issues 테스트
def test_serialize_issues():
    issues = [
        {'key': 'IT-2', 'fields': {'summary': 's2', 'assignee': {'displayName': '홍길동'}, 'status': {'name': '진행중'}, 'customfield_10817': '2024-07-16'}},
        {'key': 'IT-1', 'fields': {'summary': 's1', 'assignee': None, 'status': {'name': '대기'}, 'customfield_10817': '2024-07-15'}},
    ]
    result = cwr.serialize_issues(issues)
    assert result[0]['key'] == 'IT-1'
    assert result[1]['assignee'] == '홍길동'

# load_previous_snapshot & save_snapshot 테스트
def test_snapshot(tmp_path):
    path = tmp_path / 'snap.json'
    data = [{'key': 'IT-1'}]
    cwr.save_snapshot(str(path), data)
    loaded = cwr.load_previous_snapshot(str(path))
    assert loaded == data

# get_now_str 테스트
def test_get_now_str():
    now = cwr.get_now_str()
    assert isinstance(now, str)
    assert len(now) >= 19

# write_cron_log 테스트
def test_write_cron_log(tmp_path, monkeypatch):
    log_path = tmp_path / 'cron.log'
    monkeypatch.chdir(tmp_path)
    cwr.write_cron_log('테스트 로그')
    with open('cron.log', encoding='utf-8') as f:
        assert '테스트 로그' in f.read()
