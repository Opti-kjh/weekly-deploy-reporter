require('dotenv').config();
const axios = require('axios');
const fs = require('fs');
const path = require('path');

// 환경변수에서 값 읽기 (우선순위별)
const JIRA_BASE_URL =
  process.env.ATLASSIAN_URL ||
  process.env.JIRA_URL ||
  process.env.JIRA_API_URL;

const JIRA_EMAIL =
  process.env.ATLASSIAN_USERNAME ||
  process.env.JIRA_USER_EMAIL ||
  process.env.JIRA_USER;

const JIRA_API_TOKEN =
  process.env.ATLASSIAN_API_TOKEN ||
  process.env.JIRA_API_TOKEN ||
  process.env.JIRA_TOKEN;

function getAuthHeaders() {
  return {
    'Authorization': `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString('base64')}`,
    'Accept': 'application/json'
  };
}

async function sendSlackMessage(text) {
  const webhookUrl = process.env.SLACK_WEBHOOK_URL;
  if (!webhookUrl) {
    console.log('SLACK_WEBHOOK_URL이 설정되어 있지 않아 Slack 알림을 건너뜁니다.');
    return;
  }
  try {
    await axios.post(webhookUrl, { text });
  } catch (e) {
    console.error('Slack 알림 실패:', e.message);
  }
}

/**
 * 특정 이슈의 "is deployed by" 링크된 이슈 키 목록 반환
 * @param {string} issueKey - 예: 'IT-4319'
 * @returns {Promise<string[]>}
 */
async function getDeployedByIssueKeys(issueKey) {
  try {
    const url = `${JIRA_BASE_URL}/rest/api/3/issue/${issueKey}?fields=issuelinks`;
    const res = await axios.get(url, { headers: getAuthHeaders() });
    const links = res.data.fields.issuelinks || [];
    return links
      .filter(link => link.type && link.type.inward === 'is deployed by' && link.inwardIssue)
      .map(link => link.inwardIssue.key);
  } catch (e) {
    console.error(`[${issueKey}] 배포티켓 링크 조회 실패:`, e.message);
    return [];
  }
}

/**
 * 여러 이슈에 대해 "is deployed by" 링크 정보를 표 데이터로 가공
 * @param {string[]} issueKeys
 * @returns {Promise<Array<{issue: string, deployedBy: string[]}>>}
 */
async function getDeployTicketTable(issueKeys) {
  const table = [];
  for (const key of issueKeys) {
    const deployedBy = await getDeployedByIssueKeys(key);
    table.push({ issue: key, deployedBy });
  }
  return table;
}

// 사용 예시
(async () => {
  let issueKeys = [];
  try {
    issueKeys = JSON.parse(fs.readFileSync('weekly_issues.json', 'utf-8'));
  } catch (e) {
    console.error('weekly_issues.json 파일을 읽을 수 없습니다:', e.message);
    process.exit(1);
  }
  let table = [];
  try {
    table = await getDeployTicketTable(issueKeys);
  } catch (e) {
    console.error('배포티켓 테이블 생성 중 오류:', e.message);
    process.exit(1);
  }

  // 콘솔 표 출력
  console.table(
    table.map(row => ({
      'Jira Issue': row.issue,
      '배포티켓(링크)': row.deployedBy.length > 0 ? row.deployedBy.join(', ') : '-'
    }))
  );

  // CSV 파일로 저장
  try {
    const csvRows = [
      'Jira Issue,배포티켓(링크)',
      ...table.map(row =>
        `"${row.issue}","${row.deployedBy.join(', ')}"`
      )
    ];
    fs.writeFileSync(path.join(__dirname, 'deploy_ticket_links.csv'), csvRows.join('\n'), 'utf-8');
  } catch (e) {
    console.error('CSV 파일 저장 실패:', e.message);
  }

  // JSON 파일로 저장
  try {
    fs.writeFileSync(path.join(__dirname, 'deploy_ticket_links.json'), JSON.stringify(table, null, 2), 'utf-8');
  } catch (e) {
    console.error('JSON 파일 저장 실패:', e.message);
  }

  // 배포티켓이 있는 이슈만 요약해서 슬랙 전송
  const deployedRows = table.filter(row => row.deployedBy.length > 0);
  if (deployedRows.length > 0) {
    const slackText =
      '*배포티켓 링크 요약*\n' +
      deployedRows.map(row =>
        `• ${row.issue}: ${row.deployedBy.join(', ')}`
      ).join('\n');
    await sendSlackMessage(slackText);
  } else {
    await sendSlackMessage('이번 주 배포티켓 링크가 없습니다.');
  }
})();
