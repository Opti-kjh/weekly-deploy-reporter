module.exports = {
  types: [
    { value: 'feat',     name: 'feat:     새로운 기능' },
    { value: 'fix',      name: 'fix:      버그 수정' },
    { value: 'docs',     name: 'docs:     문서 변경' },
    { value: 'style',    name: 'style:    코드 포맷팅, 세미콜론 누락, 코드 변경 없음' },
    { value: 'refactor', name: 'refactor: 리팩토링' },
    { value: 'perf',     name: 'perf:     성능 개선' },
    { value: 'test',     name: 'test:     테스트 추가/수정' },
    { value: 'chore',    name: 'chore:    빌드 업무, 패키지 매니저 설정 등' },
  ],
  messages: {
    type: '변경 사항의 타입을 선택하세요:',
    scope: '변경 범위(선택):',
    subject: '변경 사항을 간결하게 작성하세요:',
    body: '상세한 설명(선택):',
    breaking: 'BREAKING CHANGES(선택):',
    footer: '이슈 번호(선택):',
    confirmCommit: '위 내용으로 커밋할까요?'
  },
  allowCustomScopes: true,
  allowBreakingChanges: ['feat', 'fix'],
  subjectLimit: 100
}; 