// content.js - 안정적인 메시지 전달 (사용자 UI 절대 건드리지 않음)

(function() {
  'use strict';

  console.log('[AenganZ Content] 초기화:', window.location.href);

  // ===== injected.js 주입 =====
  function injectProxyScript() {
    try {
      const script = document.createElement('script');
      script.src = chrome.runtime.getURL('injected.js');
      
      script.onload = () => {
        script.remove();
        console.log('[AenganZ Content] 프록시 스크립트 주입 완료');
      };
      
      script.onerror = (error) => {
        console.error('[AenganZ Content] 프록시 스크립트 주입 실패:', error);
      };

      (document.head || document.documentElement).appendChild(script);
      
    } catch (error) {
      console.error('[AenganZ Content] 스크립트 주입 오류:', error);
    }
  }

  // ===== 메시지 릴레이 (injected.js ↔ background.js) =====
  window.addEventListener('message', async (event) => {
    // 보안 체크
    if (event.source !== window) return;

    const data = event.data;
    if (!data || data.type !== 'PII_PROXY_FETCH') return;

    const { msgId } = data;
    console.log('[AenganZ Content] 프록시 요청 수신:', msgId);

    try {
      // background.js로 요청 전달
      const response = await chrome.runtime.sendMessage({ 
        kind: 'PII_PROXY_FETCH', 
        payload: data 
      });

      console.log('[AenganZ Content] 백그라운드 응답 수신:', response?.ok);

      // injected.js로 응답 전달
      window.postMessage({ 
        type: 'PII_PROXY_FETCH_RESULT', 
        msgId: msgId, 
        ...response 
      }, '*');

    } catch (error) {
      console.error('[AenganZ Content] 메시지 릴레이 오류:', error);
      
      // 오류 응답 전달
      window.postMessage({ 
        type: 'PII_PROXY_FETCH_RESULT', 
        msgId: msgId, 
        ok: false,
        error: error.message,
        passthrough: true
      }, '*');
    }
  });

  // ===== 즉시 주입 또는 DOM 준비 후 주입 =====
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectProxyScript);
  } else {
    injectProxyScript();
  }

  console.log('[AenganZ Content] 메시지 릴레이 준비 완료');

})();