// content.js - CSP 우회를 위한 메시지 브리지
console.log('[PII Content] Loading...');

(function() {
  try {
    // injected.js 스크립트 주입
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('injected.js');
    script.onload = () => {
      script.remove();
      console.log('[PII Content] ✅ Injected script loaded');
    };
    script.onerror = () => {
      console.error('[PII Content] ❌ Failed to load injected script');
      script.remove();
    };
    
    const target = document.head || document.documentElement;
    if (target) {
      target.appendChild(script);
      console.log('[PII Content] 📝 Script injected to', target.tagName);
    } else {
      document.addEventListener('DOMContentLoaded', () => {
        (document.head || document.documentElement).appendChild(script);
        console.log('[PII Content] 📝 Script injected after DOM ready');
      });
    }
  } catch (error) {
    console.error('[PII Content] ❌ Injection failed:', error);
  }
})();

// Injected script와 Background script 간의 메시지 브리지
window.addEventListener('message', async (event) => {
  // 보안: 같은 출처만 허용
  if (event.source !== window) return;
  
  const data = event.data;
  
  // 가명화 요청 처리
  if (data.type === 'PII_PSEUDONYMIZE_REQUEST') {
    console.log('[PII Content] 📨 Received pseudonymization request:', data.requestId);
    
    try {
      // Background script에 요청 전달
      const response = await chrome.runtime.sendMessage({
        type: 'PSEUDONYMIZE',
        requestId: data.requestId,
        prompt: data.prompt,
        timestamp: data.timestamp
      });
      
      console.log('[PII Content] 📨 Background script response:', response);
      
      // Injected script에 응답 전달
      window.postMessage({
        type: 'PII_PSEUDONYMIZE_RESPONSE',
        requestId: data.requestId,
        success: response.success,
        result: response.result,
        error: response.error
      }, '*');
      
    } catch (error) {
      console.error('[PII Content] ❌ Failed to communicate with background script:', error);
      
      // 에러 응답 전달
      window.postMessage({
        type: 'PII_PSEUDONYMIZE_RESPONSE',
        requestId: data.requestId,
        success: false,
        error: error.message || 'Communication failed'
      }, '*');
    }
  }
});

// Background script 연결 상태 확인
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'pii-pseudonymizer') {
    console.log('[PII Content] 🔗 Connected to background script');
    
    port.onMessage.addListener((message) => {
      if (message.type === 'STATUS_CHECK') {
        port.postMessage({ 
          type: 'STATUS_RESPONSE', 
          active: true, 
          url: window.location.href 
        });
      }
    });
    
    port.onDisconnect.addListener(() => {
      console.log('[PII Content] 🔌 Disconnected from background script');
    });
  }
});

// 페이지 로드 완료 시 초기화 신호 전송
document.addEventListener('DOMContentLoaded', () => {
  try {
    chrome.runtime.sendMessage({ 
      type: 'PAGE_LOADED', 
      url: window.location.href,
      timestamp: Date.now()
    }).catch(error => {
      console.debug('[PII Content] Failed to send page loaded message:', error);
    });
  } catch (error) {
    console.debug('[PII Content] Page load notification failed:', error);
  }
});

// 확장 프로그램 상태 체크
function checkExtensionStatus() {
  try {
    return chrome.runtime && chrome.runtime.id;
  } catch {
    return false;
  }
}

console.log('[PII Content] ✅ Content script initialized');

if (!checkExtensionStatus()) {
  console.warn('[PII Content] Extension runtime not available');
} else {
  console.log('[PII Content] Extension runtime available');
}