// background.js — CSP 우회를 위한 서버 통신 담당 (설정 반영 개선)

console.log('[PII Background] Service worker started');

// 설정 (기본값 enabled를 true로)
const CONFIG = {
  enabled: true,        // 기본적으로 활성화
  serverUrl: 'http://127.0.0.1:5000',
  timeout: 15000,
  maxRetries: 2
};

// 설정 로드
async function loadConfig() {
  try {
    const stored = await chrome.storage.local.get(['enabled', 'serverUrl', 'timeout', 'maxRetries']);
    Object.assign(CONFIG, {
      enabled: stored.enabled ?? true,  // 기본값을 true로
      serverUrl: stored.serverUrl ?? 'http://127.0.0.1:5000',
      timeout: stored.timeout ?? 15000,
      maxRetries: stored.maxRetries ?? 2
    });
    console.log('[PII Background] Config loaded:', CONFIG);
  } catch (e) {
    console.warn('[PII Background] Failed to load config:', e);
  }
}

// 가명화 서버 호출
async function callPseudonymizationServer(prompt, requestId) {
  console.log('[PII Background] 📡 Calling pseudonymization server...');
  console.log('[PII Background] 📝 Prompt length:', prompt.length);
  console.log('[PII Background] ⚙️ Enabled:', CONFIG.enabled);
  
  // 설정에서 비활성화되어 있으면 원본 그대로 반환
  if (!CONFIG.enabled) {
    console.log('[PII Background] ⚠️ Pseudonymizer is disabled in settings');
    return {
      ok: true,
      original_prompt: prompt,
      masked_prompt: prompt,  // 원본 그대로
      detection: { contains_pii: false, items: [] },
      substitution_map: {},
      reverse_map: {},
      mapping: []
    };
  }
  
  for (let attempt = 0; attempt <= CONFIG.maxRetries; attempt++) {
    try {
      console.log('[PII Background] 🔄 Attempt', attempt + 1, 'of', CONFIG.maxRetries + 1);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), CONFIG.timeout);
      
      const response = await fetch(`${CONFIG.serverUrl}/pseudonymize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          id: requestId
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      console.log('[PII Background] 📊 Server response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error: ${response.status} ${errorText.substring(0, 100)}`);
      }
      
      const result = await response.json();
      console.log('[PII Background] ✅ Pseudonymization successful');
      console.log('[PII Background] 📊 Items detected:', result.mapping?.length || 0);
      
      if (result.mapping && result.mapping.length > 0) {
        console.log('[PII Background] 🎭 Detected items:');
        result.mapping.forEach(item => {
          console.log(`[PII Background]    ${item.type}: "${item.value}" → "${item.replacement || item.token}"`);
        });
      }
      
      return result;
      
    } catch (error) {
      clearTimeout(timeoutId);
      
      console.warn('[PII Background] ❌ Attempt', attempt + 1, 'failed:', error.message);
      
      if (error.name === 'AbortError') {
        console.warn('[PII Background] ⏰ Request timeout');
      }
      
      // 마지막 시도였다면 에러 throw
      if (attempt === CONFIG.maxRetries) {
        throw error;
      }
      
      // 재시도 전 잠시 대기
      await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }
}

// 메인 메시지 핸들러
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[PII Background] 📨 Message received:', message.type);
  
  if (message.type === 'PSEUDONYMIZE') {
    // 비동기 처리
    (async () => {
      try {
        const result = await callPseudonymizationServer(message.prompt, message.requestId);
        
        sendResponse({
          success: true,
          result: result,
          requestId: message.requestId
        });
        
      } catch (error) {
        console.error('[PII Background] ❌ Pseudonymization failed:', error.message);
        
        sendResponse({
          success: false,
          error: error.message,
          requestId: message.requestId
        });
      }
    })();
    
    return true; // 비동기 응답을 위해 true 반환
  }
  
  // 기타 메시지 처리
  switch (message.type) {
    case 'GET_CONFIG':
      sendResponse(CONFIG);
      break;
      
    case 'UPDATE_CONFIG':
      Object.assign(CONFIG, message.config);
      chrome.storage.local.set(CONFIG);
      console.log('[PII Background] Config updated:', CONFIG);
      sendResponse({ success: true });
      break;
      
    case 'PAGE_LOADED':
      console.log('[PII Background] Page loaded:', message.url);
      break;
      
    case 'HEALTH_CHECK':
      sendResponse({ 
        status: 'ok', 
        config: CONFIG,
        timestamp: Date.now() 
      });
      break;
      
    default:
      console.log('[PII Background] Unknown message type:', message.type);
  }
});

// 확장 프로그램 생명주기
chrome.runtime.onInstalled.addListener((details) => {
  console.log('[PII Background] Extension installed/updated:', details.reason);
  
  // 기본 설정 저장 (enabled를 true로)
  chrome.storage.local.set({
    enabled: true,      // 기본적으로 활성화
    serverUrl: 'http://127.0.0.1:5000',
    timeout: 15000,
    maxRetries: 2
  });
  
  loadConfig();
});

chrome.runtime.onStartup.addListener(() => {
  console.log('[PII Background] Extension started up');
  loadConfig();
});

// 설정 변경 감지
chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === 'local') {
    console.log('[PII Background] Storage changed:', changes);
    
    // enabled 설정이 변경되었을 때 특별히 로그 출력
    if (changes.enabled) {
      console.log('[PII Background] 🔄 Pseudonymizer enabled status changed:', 
                  changes.enabled.oldValue, '→', changes.enabled.newValue);
    }
    
    loadConfig();
  }
});

// 에러 핸들링
chrome.runtime.onSuspend.addListener(() => {
  console.log('[PII Background] Service worker suspending');
});

// 초기 설정 로드
loadConfig();

console.log('[PII Background] ✅ Background script initialized');