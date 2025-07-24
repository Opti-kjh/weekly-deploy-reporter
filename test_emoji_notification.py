#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
이모지 알림 기능 테스트 스크립트
"""

def test_emoji_notification():
    """이모지 알림 메시지 형식을 테스트합니다."""
    
    # 테스트 데이터
    changed_issues = {
        'added': [
            {'key': 'IT-6609', 'summary': '특정 은행 신상캐시 환불 불가 안내 문구 추가', 'url': 'https://jira.example.com/browse/IT-6609'},
            {'key': 'IT-6813', 'summary': '신상스튜디오 상품관리 엑셀 다운로드 > 상태 컬럼 추가', 'url': 'https://jira.example.com/browse/IT-6813'}
        ],
        'removed': [
            {'key': 'IT-5332', 'summary': '기존 예정된 시작 필드가 제거된 티켓', 'url': 'https://jira.example.com/browse/IT-5332'}
        ],
        'updated': [
            {'key': 'IT-6501', 'summary': '배포 예정일이 변경된 티켓', 'url': 'https://jira.example.com/browse/IT-6501'}
        ]
    }
    
    page_title = "7월 4째주: (07/21~07/27)"
    page_url = "https://confluence.example.com/pages/12345"
    
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
    
    slack_msg = f"📊 배포 일정 리포트가 업데이트되었습니다:\n{page_title}\n{page_url}\n\n{summary_text}\n\n{changes_text}"
    
    print("=== 이모지 알림 메시지 테스트 ===")
    print(slack_msg)
    print("\n=== 예상 결과 ===")
    print("📊 배포 일정 리포트가 업데이트되었습니다:")
    print("7월 4째주: (07/21~07/27)")
    print("https://confluence.example.com/pages/12345")
    print("")
    print("➕ 추가: 2개 | ➖ 제거: 1개 | 🔄 갱신: 1개")
    print("")
    print("[추가된 티켓]")
    print("➕ IT-6609: 특정 은행 신상캐시 환불 불가 안내 문구 추가")
    print("➕ IT-6813: 신상스튜디오 상품관리 엑셀 다운로드 > 상태 컬럼 추가")
    print("")
    print("[제거된 티켓]")
    print("➖ IT-5332: 기존 예정된 시작 필드가 제거된 티켓")
    print("")
    print("[갱신된 티켓]")
    print("🔄 IT-6501: 배포 예정일이 변경된 티켓")

if __name__ == "__main__":
    test_emoji_notification() 