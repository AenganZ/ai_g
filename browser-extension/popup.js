// popup.js - 간단하고 안정적인 로그 UI

const AENGANZ_API = 'http://127.0.0.1:5000/prompt_logs';

const $ = (id) => document.getElementById(id);

// ===== 유틸리티 함수 =====
function formatTime(timestamp) {
  if (!timestamp) return '';
  
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('ko-KR', {
      month: '2-digit',
      day: '2-digit',  
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch {
    return timestamp;
  }
}

function truncateText(text, maxLength = 80) {
  if (!text) return '';
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// ===== 로그 렌더링 =====
function renderLogs(logs) {
  const container = $('reqList');
  const timestamp = $('ts');
  
  if (!container) return;

  // 로딩 상태 해제
  container.innerHTML = '';

  if (!Array.isArray(logs) || logs.length === 0) {
    container.innerHTML = `
      <div class="muted">
        <p>아직 가명화 로그가 없습니다.</p>
        <p>ChatGPT나 Claude에서 메시지를 보내보세요.</p>
      </div>
    `;
    if (timestamp) timestamp.textContent = '';
    return;
  }

  // 최신 로그부터 표시
  const sortedLogs = logs.slice().reverse();
  let html = '';

  sortedLogs.forEach((log, index) => {
    const prompt = log?.input?.prompt || log?.originalText || '';
    const time = log?.time || log?.timestamp || '';
    const items = log?.output?.detection?.items || log?.detection?.items || [];
    const containsPII = items.length > 0;

    html += `
      <details class="row">
        <summary class="row-head">
          <span class="pill ${containsPII ? 'warn' : 'ok'}">
            ${containsPII ? 'PII' : 'NO-PII'}
          </span>
          <span class="prompt">${truncateText(prompt)}</span>
          <span class="time">${formatTime(time)}</span>
        </summary>

        <div class="items">
          ${items.length === 0 ? 
            '<div class="muted">탐지된 개인정보 없음</div>' :
            items.map((item, idx) => `
              <div class="item">
                <div class="grid">
                  <div><b>#${idx + 1} 유형</b></div>
                  <div>${item.type || '알 수 없음'}</div>
                  <div><b>원본</b></div>
                  <div class="mono">${item.value || ''}</div>
                  <div><b>가명</b></div>
                  <div class="mono">${item.token || ''}</div>
                  <div><b>출처</b></div>
                  <div>${item.source || 'Pattern'}</div>
                </div>
              </div>
            `).join('')
          }
        </div>

        ${items.length > 0 ? `
          <div class="map">
            ${items.map(item => `
              <div class="map-row">
                <span class="tag">${item.type || '-'}</span>
                <span class="mono">${item.value || ''}</span>
                <span class="arrow">→</span>
                <span class="mono">${item.token || ''}</span>
              </div>
            `).join('')}
          </div>
        ` : ''}
      </details>
    `;
  });

  container.innerHTML = html;
  
  // 타임스탬프 업데이트
  if (timestamp && logs.length > 0) {
    const latestTime = logs[logs.length - 1]?.time || logs[logs.length - 1]?.timestamp;
    timestamp.textContent = latestTime ? `마지막: ${formatTime(latestTime)}` : '';
  }
}

// ===== 서버 로그 로드 =====
async function loadServerLogs() {
  try {
    console.log('[Popup] 서버 로그 로드 시도');
    
    const response = await fetch(AENGANZ_API, { 
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(5000) // 5초 타임아웃
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const text = await response.text();
    const data = JSON.parse(text);
    
    console.log('[Popup] 서버 로그 로드 성공:', data?.logs?.length || 0);
    return data?.logs || [];
    
  } catch (error) {
    console.warn('[Popup] 서버 로그 로드 실패:', error.message);
    return [];
  }
}

// ===== 익스텐션 로그 로드 =====
async function loadExtensionLogs() {
  try {
    console.log('[Popup] 익스텐션 로그 로드 시도');
    
    const response = await chrome.runtime.sendMessage({ action: 'getLogs' });
    console.log('[Popup] 익스텐션 로그 로드 성공:', response?.logs?.length || 0);
    
    return response?.logs || [];
    
  } catch (error) {
    console.warn('[Popup] 익스텐션 로그 로드 실패:', error.message);
    return [];
  }
}

// ===== 통합 로그 로드 =====
async function loadAllLogs() {
  const container = $('reqList');
  const timestamp = $('ts');
  
  if (container) {
    container.innerHTML = `<div class="muted">로그 로드 중...</div>`;
  }
  if (timestamp) {
    timestamp.textContent = '로딩 중...';
  }

  try {
    // 병렬로 로그 로드
    const [serverLogs, extensionLogs] = await Promise.all([
      loadServerLogs(),
      loadExtensionLogs()
    ]);

    // 로그 통합
    const allLogs = [...serverLogs, ...extensionLogs];
    
    // 시간순 정렬 (오래된 것부터)
    allLogs.sort((a, b) => {
      const timeA = new Date(a.time || a.timestamp || 0);
      const timeB = new Date(b.time || b.timestamp || 0);
      return timeA - timeB;
    });

    console.log('[Popup] 통합 로그 수:', allLogs.length);
    
    // 렌더링
    renderLogs(allLogs);

    // 연결 상태 표시
    if (timestamp) {
      const serverStatus = serverLogs.length > 0 ? '🟢' : '🔴';
      const extStatus = extensionLogs.length >= 0 ? '🟢' : '🔴';
      timestamp.textContent = `서버 ${serverStatus} 익스텐션 ${extStatus}`;
    }

  } catch (error) {
    console.error('[Popup] 로그 로드 총 실패:', error);
    
    if (container) {
      container.innerHTML = `
        <div class="muted">
          <p>❌ 로그 로드 실패</p>
          <p>서버 상태: http://127.0.0.1:5000</p>
          <p>오류: ${error.message}</p>
        </div>
      `;
    }
    
    if (timestamp) {
      timestamp.textContent = '연결 실패';
    }
  }
}

// ===== 초기화 =====
document.addEventListener('DOMContentLoaded', () => {
  console.log('[Popup] 팝업 초기화');
  
  // 새로고침 버튼
  const refreshBtn = $('refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      console.log('[Popup] 수동 새로고침');
      loadAllLogs();
    });
  }
  
  // 초기 로드
  loadAllLogs();
});