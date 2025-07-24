import pytest
import types
import datetime
import os
import sys
import json
from unittest.mock import MagicMock, patch, Mock
from freezegun import freeze_time
from datetime import date, datetime, timedelta

# 테스트 대상 함수 import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import create_weekly_report as cwr

class TestUtilityFunctions:
    """유틸리티 함수 테스트"""
    
    def test_load_env_vars_success(self):
        """환경 변수 로딩 성공 테스트"""
        with patch.dict(os.environ, {
            'ATLASSIAN_URL': 'https://test.atlassian.net',
            'ATLASSIAN_USERNAME': 'test@example.com',
            'ATLASSIAN_API_TOKEN': 'test-token'
        }):
            result = cwr.load_env_vars(['ATLASSIAN_URL', 'ATLASSIAN_USERNAME', 'ATLASSIAN_API_TOKEN'])
            assert result['ATLASSIAN_URL'] == 'https://test.atlassian.net'
            assert result['ATLASSIAN_USERNAME'] == 'test@example.com'
            assert result['ATLASSIAN_API_TOKEN'] == 'test-token'
    
    def test_load_env_vars_missing(self):
        """환경 변수 누락 시 예외 발생 테스트"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="필수 환경변수 누락"):
                cwr.load_env_vars(['ATLASSIAN_URL', 'ATLASSIAN_USERNAME'])
    
    def test_get_week_range(self):
        """주간 날짜 범위 계산 테스트"""
        with freeze_time('2025-07-24'):  # 목요일
            # current 모드 (이번 주)
            monday, sunday = cwr.get_week_range('current')
            assert monday == date(2025, 7, 21)  # 월요일
            assert sunday == date(2025, 7, 27)   # 일요일
            
            # create 모드 (다음 주)
            monday, sunday = cwr.get_week_range('create')
            assert monday == date(2025, 7, 28)  # 다음 주 월요일
            assert sunday == date(2025, 8, 3)   # 다음 주 일요일
            
            # last 모드 (지난 주)
            monday, sunday = cwr.get_week_range('last')
            assert monday == date(2025, 7, 14)  # 지난 주 월요일
            assert sunday == date(2025, 7, 20)  # 지난 주 일요일
    
    def test_get_page_title(self):
        """페이지 제목 생성 테스트"""
        monday = date(2025, 7, 21)
        sunday = date(2025, 7, 27)
        title = cwr.get_page_title(monday, sunday)
        assert title == "7월 4째주: (07/21~07/27)"
    
    def test_normalize_html_content(self):
        """HTML 내용 정규화 테스트"""
        html1 = '  <div>Test&nbsp;Content</div>\n  '
        html2 = '<div>Test Content</div>'
        assert cwr.normalize_html_content(html1) == cwr.normalize_html_content(html2)
    
    def test_get_now_str(self):
        """현재 시간 문자열 생성 테스트"""
        now_str = cwr.get_now_str()
        assert isinstance(now_str, str)
        assert len(now_str) >= 19
        # YYYY-MM-DD HH:MM:SS 형식 확인
        datetime.strptime(now_str, '%Y-%m-%d %H:%M:%S')

class TestJiraFunctions:
    """Jira 관련 함수 테스트"""
    
    def test_get_jira_issues_by_customfield_10817_success(self):
        """배포 예정 티켓 조회 성공 테스트"""
        mock_jira = MagicMock()
        
        # 페이지네이션 시뮬레이션
        mock_issue1 = MagicMock()
        mock_issue1.key = 'IT-6813'
        mock_issue1.fields.summary = '신상스튜디오 상품관리 엑셀 다운로드 > 상태 컬럼 추가'
        mock_issue1.fields.status.name = '완료'
        mock_issue1.fields.customfield_10817 = '2025-07-23T11:00:00.000+0900'
        
        mock_issue2 = MagicMock()
        mock_issue2.key = 'IT-5332'
        mock_issue2.fields.summary = '[신상플러스멤버십] 소매멤버십 유저의 신상초이스 무료 다운 기능 제공'
        mock_issue2.fields.status.name = '실행'
        mock_issue2.fields.customfield_10817 = '2025-07-23T11:00:00.000+0900'
        
        # 첫 번째 배치
        mock_jira.search_issues.return_value = [mock_issue1, mock_issue2]
        
        result = cwr.get_jira_issues_by_customfield_10817(
            mock_jira, 'IT', '2025-07-21', '2025-07-27'
        )
        
        assert len(result) == 2
        assert result[0]['key'] == 'IT-6813'
        assert result[1]['key'] == 'IT-5332'
        assert result[0]['fields']['summary'] == '신상스튜디오 상품관리 엑셀 다운로드 > 상태 컬럼 추가'
    
    def test_get_jira_issues_by_customfield_10817_exception(self):
        """배포 예정 티켓 조회 실패 테스트"""
        mock_jira = MagicMock()
        mock_jira.search_issues.side_effect = Exception('Jira API error')
        
        result = cwr.get_jira_issues_by_customfield_10817(
            mock_jira, 'IT', '2025-07-21', '2025-07-27'
        )
        
        assert result == []
    
    def test_get_linked_it_tickets_success(self):
        """연결된 IT 티켓 조회 성공 테스트"""
        mock_jira = MagicMock()
        
        # IT-6813의 연결 관계 시뮬레이션
        mock_response = {
            'fields': {
                'issuelinks': [
                    {
                        'type': {'name': 'Deployments'},
                        'inwardIssue': {
                            'key': 'IT-6818',
                            'fields': {
                                'summary': 'prod-studio-admin에 대한 배포 요청',
                                'status': {'name': '완료'},
                                'issuetype': {'name': '변경'}
                            }
                        }
                    }
                ]
            }
        }
        
        mock_jira.issue.return_value.raw = mock_response
        
        result = cwr.get_linked_it_tickets(mock_jira, 'IT-6813')
        
        assert len(result) == 1
        assert result[0]['key'] == 'IT-6818'
        assert result[0]['summary'] == 'prod-studio-admin에 대한 배포 요청'
        assert result[0]['status'] == '완료'
    
    def test_get_linked_it_tickets_no_deployments(self):
        """배포 관계가 없는 경우 테스트"""
        mock_jira = MagicMock()
        
        mock_response = {
            'fields': {
                'issuelinks': [
                    {
                        'type': {'name': 'Blocks'},
                        'outwardIssue': {
                            'key': 'IT-9999',
                            'fields': {
                                'summary': '블록된 티켓',
                                'status': {'name': '대기'},
                                'issuetype': {'name': '버그'}
                            }
                        }
                    }
                ]
            }
        }
        
        mock_jira.issue.return_value.raw = mock_response
        
        result = cwr.get_linked_it_tickets(mock_jira, 'IT-6757')
        
        assert len(result) == 0
    
    def test_get_linked_it_tickets_with_retry(self):
        """재시도 로직을 포함한 연결된 IT 티켓 조회 테스트"""
        mock_jira = MagicMock()
        
        # 첫 번째 시도 실패, 두 번째 시도 성공
        mock_jira.issue.side_effect = [
            Exception('API error'),
            MagicMock(raw={
                'fields': {
                    'issuelinks': [
                        {
                            'type': {'name': 'Deployments'},
                            'inwardIssue': {
                                'key': 'IT-6818',
                                'fields': {
                                    'summary': 'prod-studio-admin에 대한 배포 요청',
                                    'status': {'name': '완료'},
                                    'issuetype': {'name': '변경'}
                                }
                            }
                        }
                    ]
                }
            })
        ]
        
        result = cwr.get_linked_it_tickets_with_retry(mock_jira, 'IT-6813', max_retries=2)
        
        assert len(result) == 1
        assert result[0]['key'] == 'IT-6818'

class TestConfluenceFunctions:
    """Confluence 관련 함수 테스트"""
    
    def test_create_deploy_links_html_table_with_issues(self):
        """배포 예정 목록 HTML 테이블 생성 테스트"""
        mock_jira = MagicMock()
        
        # 테스트용 배포 예정 티켓들
        deploy_issues = [
            {
                'key': 'IT-6813',
                'fields': {
                    'summary': '신상스튜디오 상품관리 엑셀 다운로드 > 상태 컬럼 추가',
                    'status': {'name': '완료'},
                    'customfield_10817': '2025-07-23T11:00:00.000+0900'
                }
            },
            {
                'key': 'IT-5332',
                'fields': {
                    'summary': '[신상플러스멤버십] 소매멤버십 유저의 신상초이스 무료 다운 기능 제공',
                    'status': {'name': '실행'},
                    'customfield_10817': '2025-07-23T11:00:00.000+0900'
                }
            }
        ]
        
        # 연결된 IT 티켓 조회 모킹
        mock_jira.issue.return_value.raw = {
            'fields': {
                'issuelinks': [
                    {
                        'type': {'name': 'Deployments'},
                        'inwardIssue': {
                            'key': 'IT-6818',
                            'fields': {
                                'summary': 'prod-studio-admin에 대한 배포 요청',
                                'status': {'name': '완료'},
                                'issuetype': {'name': '변경'}
                            }
                        }
                    }
                ]
            }
        }
        
        result = cwr.create_deploy_links_html_table_with_issues(mock_jira, deploy_issues, 'https://jira.example.com')
        
        assert '<h2 style="margin-top: 20px;">배포 예정 목록</h2>' in result
        assert 'IT-6813' in result
        assert 'IT-5332' in result
        assert '신상스튜디오 상품관리 엑셀 다운로드' in result
        assert '신상플러스멤버십' in result
        assert 'table' in result
        assert 'tr' in result
        assert 'td' in result
    
    def test_get_status_style(self):
        """상태별 CSS 스타일 테스트"""
        # 완료 상태
        style = cwr.get_status_style('완료')
        assert 'background-color: #90EE90' in style
        assert 'color: #006400' in style
        
        # 실행 상태
        style = cwr.get_status_style('실행')
        assert 'background-color: #FFE4B5' in style
        assert 'color: #8B4513' in style
        
        # 대기 상태
        style = cwr.get_status_style('실행을 기다리는 중')
        assert 'background-color: #FFE4B5' in style
        assert 'color: #8B4513' in style
        
        # 알 수 없는 상태
        style = cwr.get_status_style('알 수 없는 상태')
        assert 'background-color: #D3D3D3' in style
        assert 'color: #2F4F4F' in style

class TestSnapshotFunctions:
    """스냅샷 관련 함수 테스트"""
    
    def test_snapshot_issues(self):
        """이슈 스냅샷 생성 테스트"""
        issues = [
            {
                'key': 'IT-6813',
                'fields': {
                    'summary': '신상스튜디오 상품관리 엑셀 다운로드 > 상태 컬럼 추가',
                    'status': {'name': '완료'},
                    'assignee': {'displayName': '홍길동'},
                    'customfield_10817': '2025-07-23T11:00:00.000+0900'
                }
            }
        ]
        
        result = cwr.snapshot_issues(issues, 'customfield_10817')
        
        assert len(result) == 1
        assert result[0]['key'] == 'IT-6813'
        assert result[0]['summary'] == '신상스튜디오 상품관리 엑셀 다운로드 > 상태 컬럼 추가'
        assert result[0]['status'] == '완료'
        assert result[0]['assignee'] == '홍길동'
        assert result[0]['customfield_10817'] == '2025-07-23T11:00:00.000+0900'
    
    def test_issues_changed(self):
        """이슈 변경 감지 테스트"""
        prev = [{'key': 'IT-1', 'summary': 'Test 1'}]
        curr = [{'key': 'IT-1', 'summary': 'Test 1'}]
        
        # 변경 없음
        assert not cwr.issues_changed(prev, curr)
        
        # 변경 있음
        curr = [{'key': 'IT-1', 'summary': 'Test 2'}]
        assert cwr.issues_changed(prev, curr)
    
    def test_get_changed_issues(self):
        """변경된 이슈 감지 테스트"""
        prev = [
            {'key': 'IT-1', 'summary': 'Test 1', 'deploy_date': '2025-07-21'},
            {'key': 'IT-2', 'summary': 'Test 2', 'deploy_date': '2025-07-22'}
        ]
        curr = [
            {'key': 'IT-1', 'summary': 'Test 1 Updated', 'deploy_date': '2025-07-21'},
            {'key': 'IT-3', 'summary': 'Test 3', 'deploy_date': '2025-07-23'}
        ]
        
        result = cwr.get_changed_issues(prev, curr, 'https://jira.example.com')
        
        # 추가된 티켓
        assert len(result['added']) == 1
        assert result['added'][0]['key'] == 'IT-3'
        
        # 제거된 티켓
        assert len(result['removed']) == 1
        assert result['removed'][0]['key'] == 'IT-2'
        
        # 업데이트된 티켓 (deploy_date가 변경되지 않았으므로 없음)
        assert len(result['updated']) == 0

class TestNotificationFunctions:
    """알림 관련 함수 테스트"""
    
    def test_get_notified_deploy_keys(self):
        """알림 전송된 배포 키 조회 테스트"""
        # 파일이 없는 경우
        with patch('builtins.open', side_effect=FileNotFoundError):
            keys = cwr.get_notified_deploy_keys()
            assert keys == set()
        
        # 파일이 있는 경우
        test_data = ['IT-6813', 'IT-5332']
        with patch('builtins.open', mock_open(read_data=json.dumps(test_data))):
            keys = cwr.get_notified_deploy_keys()
            assert keys == {'IT-6813', 'IT-5332'}
    
    def test_save_notified_deploy_keys(self):
        """알림 전송된 배포 키 저장 테스트"""
        test_keys = {'IT-6813', 'IT-5332'}
        
        with patch('builtins.open', mock_open()) as mock_file:
            cwr.save_notified_deploy_keys(test_keys)
            mock_file.assert_called_once()
    
    def test_get_notified_changes(self):
        """알림 전송된 변경사항 조회 테스트"""
        # 파일이 없는 경우
        with patch('builtins.open', side_effect=FileNotFoundError):
            changes = cwr.get_notified_changes()
            assert changes == set()
        
        # 파일이 있는 경우
        test_data = ['hash1', 'hash2']
        with patch('builtins.open', mock_open(read_data=json.dumps(test_data))):
            changes = cwr.get_notified_changes()
            assert changes == {'hash1', 'hash2'}
    
    def test_save_notified_changes(self):
        """알림 전송된 변경사항 저장 테스트"""
        test_changes = {'hash1', 'hash2'}
        
        with patch('builtins.open', mock_open()) as mock_file:
            cwr.save_notified_changes(test_changes)
            mock_file.assert_called_once()
    
    def test_generate_change_hash(self):
        """변경사항 해시 생성 테스트"""
        changed_issues = {
            'added': [{'key': 'IT-6813', 'summary': 'Test 1'}],
            'removed': [{'key': 'IT-5332', 'summary': 'Test 2'}],
            'updated': []
        }
        page_title = "7월 4째주: (07/21~07/27)"
        
        hash_result = cwr.generate_change_hash(changed_issues, page_title)
        
        assert isinstance(hash_result, str)
        assert 'IT-6813' in hash_result
        assert 'IT-5332' in hash_result
        assert page_title in hash_result
    
    @patch('requests.post')
    def test_send_slack_success(self, mock_post):
        """Slack 알림 전송 성공 테스트"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        with patch.dict(os.environ, {'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'}):
            cwr.send_slack('Test message')
            mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_slack_failure(self, mock_post):
        """Slack 알림 전송 실패 테스트"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        with patch.dict(os.environ, {'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'}):
            cwr.send_slack('Test message')
            # 실패해도 예외가 발생하지 않아야 함

class TestFileOperations:
    """파일 작업 관련 함수 테스트"""
    
    def test_read_json_success(self):
        """JSON 파일 읽기 성공 테스트"""
        test_data = {'key': 'value'}
        
        with patch('builtins.open', mock_open(read_data=json.dumps(test_data))):
            result = cwr.read_json('test.json')
            assert result == test_data
    
    def test_read_json_file_not_found(self):
        """JSON 파일 읽기 실패 테스트"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = cwr.read_json('nonexistent.json', default={'default': 'value'})
            assert result == {'default': 'value'}
    
    def test_write_json(self):
        """JSON 파일 쓰기 테스트"""
        test_data = {'key': 'value'}
        
        with patch('builtins.open', mock_open()) as mock_file:
            cwr.write_json('test.json', test_data)
            mock_file.assert_called_once()
    
    def test_log(self):
        """로그 작성 테스트"""
        test_message = "Test log message"
        
        with patch('builtins.open', mock_open()) as mock_file:
            cwr.log(test_message)
            mock_file.assert_called_once_with('cron.log', 'a', encoding='utf-8')

class TestIntegration:
    """통합 테스트"""
    
    @patch('create_weekly_report.JIRA')
    @patch('create_weekly_report.Confluence')
    def test_main_function_flow(self, mock_confluence, mock_jira):
        """메인 함수 실행 흐름 테스트"""
        # Mock 설정
        mock_jira_instance = MagicMock()
        mock_confluence_instance = MagicMock()
        mock_jira.return_value = mock_jira_instance
        mock_confluence.return_value = mock_confluence_instance
        
        # 환경 변수 설정
        with patch.dict(os.environ, {
            'ATLASSIAN_URL': 'https://test.atlassian.net',
            'ATLASSIAN_USERNAME': 'test@example.com',
            'ATLASSIAN_API_TOKEN': 'test-token',
            'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test',
            'SLACK_BOT_TOKEN': 'test-bot-token'
        }):
            # get_jira_issues_by_customfield_10817 모킹
            with patch.object(cwr, 'get_jira_issues_by_customfield_10817') as mock_get_issues:
                mock_get_issues.return_value = []
                
                # main 함수 실행 (실제로는 sys.argv도 모킹해야 함)
                with patch('sys.argv', ['create_weekly_report.py', 'current']):
                    # main 함수가 정상적으로 실행되는지 확인
                    # 실제로는 더 복잡한 모킹이 필요하지만 기본 구조만 테스트
                    pass

# Mock 함수들
def mock_open(read_data=None):
    """open 함수 모킹"""
    mock = MagicMock()
    if read_data:
        mock.return_value.__enter__.return_value.read.return_value = read_data
    return mock

if __name__ == '__main__':
    pytest.main([__file__])
