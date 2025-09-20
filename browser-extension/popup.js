// popup.js - 단순화된 팝업

const $ = (id) => document.getElementById(id);

// 서버 상태 확인
async function checkServerStatus() {
  const statusEl = $('status');
  const refreshBtn = $('refreshBtn');
  
  try {
    statusEl.textContent = '서버 확인 중...';
    statusEl.className = 'status checking';
    
    const response = await fetch('http://127.0.0.1:5000/health', {
      method: 'GET',
      signal: AbortSignal.timeout(3000)
    });
    
    if (response.ok) {
      const data = await response.json();
      statusEl.textContent = `✅ 서버 온라인 (모델: ${data.model_loaded ? '로드됨' : '정규식 모드'})`;
      statusEl.className = 'status online';
      
      // 로그 로드
      loadLogs();
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    statusEl.textContent = `❌ 서버 오프라인: ${error.message}`;
    statusEl.className = 'status offline';
    
    $('logs').innerHTML = `
      <div class="error">
        <h3>서버 연결 실패</h3>
        <p>Python 서버가 실행 중인지 확인하세요:</p>
        <code>python app.py</code>
        <p>또는</p>
        <code>start.bat</code> (Windows) / <code>./start.sh</code> (macOS/Linux)
      </div>
    `;
  }
}

// 로그 로드
async function loadLogs() {
  const logsEl = $('logs');
  
  try {
    logsEl.innerHTML = '<div class="loading">로그 로딩 중...</div>';
    
    const response = await fetch('http://127.0.0.1:5000/prompt_logs', {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    const logs = data.logs || [];
    
    if (logs.length === 0) {
      logsEl.innerHTML = `
        <div class="empty">
          <h3>📋 로그가 없습니다</h3>
          <p>ChatGPT에서 개인정보가 포함된 메시지를 보내보세요.</p>
          <div class="test-example">
            <strong>테스트 예시:</strong><br>
            "안녕하세요, 제 이름은 홍길동이고 연락처는 010-1234-5678입니다."
          </div>
        </div>
      `;
      return;
    }
    
    // 최신 로그부터 표시
    const sortedLogs = logs.slice().reverse();
    
    let html = `<h3>📊 처리된 요청 (${logs.length}개)</h3>`;
    
    sortedLogs.forEach((log, index) => {
      const input = log.input || {};
      const detection = log.detection || {};
      const items = detection.items || [];
      const performance = log.performance || {};
      
      const prompt = input.prompt || '';
      const time = log.time || '';
      const itemCount = items.length;
      const processingTime = performance.total_time_ms || 0;
      
      html += `
        <div class="log-entry ${itemCount > 0 ? 'has-pii' : 'no-pii'}">
          <div class="log-header">
            <span class="badge ${itemCount > 0 ? 'pii' : 'clean'}">
              ${itemCount > 0 ? `PII (${itemCount})` : 'CLEAN'}
            </span>
            <span class="time">${time}</span>
            <span class="performance">${processingTime}ms</span>
          </div>
          
          <div class="prompt">
            ${prompt.length > 100 ? prompt.substring(0, 100) + '...' : prompt}
          </div>
          
          ${itemCount > 0 ? `
            <div class="detection-details">
              <strong>🔍 탐지된 개인정보:</strong>
              <ul>
                ${items.map(item => `
                  <li>
                    <span class="type">${item.type}</span>: 
                    <span class="value">${item.value}</span> → 
                    <span class="token">${item.token}</span>
                  </li>
                `).join('')}
              </ul>
            </div>
          ` : '<div class="no-detection">개인정보가 탐지되지 않았습니다.</div>'}
        </div>
      `;
    });
    
    logsEl.innerHTML = html;
    
  } catch (error) {
    logsEl.innerHTML = `
      <div class="error">
        <h3>로그 로드 실패</h3>
        <p>오류: ${error.message}</p>
      </div>
    `;
  }
}

// 로그 삭제
async function clearLogs() {
  if (!confirm('모든 로그를 삭제하시겠습니까?')) {
    return;
  }
  
  try {
    const response = await fetch('http://127.0.0.1:5000/prompt_logs', {
      method: 'DELETE'
    });
    
    if (response.ok) {
      loadLogs();
      alert('로그가 삭제되었습니다.');
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    alert('로그 삭제 실패: ' + error.message);
  }
}

// 테스트 함수
async function testConnection() {
  const testBtn = $('testBtn');
  const originalText = testBtn.textContent;
  
  try {
    testBtn.textContent = '테스트 중...';
    testBtn.disabled = true;
    
    // 테스트 요청
    const response = await fetch('http://127.0.0.1:5000/pseudonymize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: '테스트입니다. 제 이름은 김철수이고 연락처는 010-1234-5678입니다.',
        id: 'popup_test_' + Date.now()
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      alert(`✅ 테스트 성공!\n탐지된 항목: ${data.mapping?.length || 0}개`);
      loadLogs(); // 로그 새로고침
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    alert('❌테스트 실패: ' + error.message);
  } finally {
    testBtn.textContent = originalText;
    testBtn.disabled = false;
  }
}

// 이벤트 리스너
document.addEventListener('DOMContentLoaded', () => {
  $('refreshBtn').addEventListener('click', checkServerStatus);
  $('clearBtn').addEventListener('click', clearLogs);
  $('testBtn').addEventListener('click', testConnection);
  $('optionsBtn').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
  
  // 초기 로드
  checkServerStatus();
});