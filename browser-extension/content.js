// content.js - 중복 주입 방지 및 강력한 스크립트 주입
console.log("🚀 GenAI Pseudonymizer content.js 로드됨!");

// 중복 주입 방지
if (window.pseudonymizerInjected) {
  console.log("⚠️ 이미 주입되어 있음, 중복 주입 방지");
} else {
  window.pseudonymizerInjected = true;
  
  // 다중 주입 방법 시도
  function injectScript() {
    try {
      // 방법 1: 기본 방법
      const script1 = document.createElement('script');
      script1.src = chrome.runtime.getURL('injected.js');
      script1.onload = function() {
        console.log("✅ injected.js 로드 완료 (방법 1)");
        this.remove();
        
        // 후킹 확인
        setTimeout(() => {
          if (window.fetch && window.fetch.toString().includes('PII_PROXY_FETCH')) {
            console.log("✅ fetch 후킹 확인됨!");
          } else {
            console.log("⚠️ fetch 후킹이 여전히 안됨, 재시도...");
            // 재시도하지 않음 - 무한루프 방지
          }
        }, 1000);
      };
      script1.onerror = function() {
        console.log("⚠️ 방법 1 실패");
        this.remove();
      };
      
      (document.head || document.documentElement).appendChild(script1);
      console.log("📤 injected.js 주입 시도 (방법 1)");
      
    } catch (e) {
      console.error("❌ 스크립트 주입 실패:", e);
    }
  }

  // DOM이 준비되면 주입
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectScript);
  } else {
    injectScript();
  }
}

// 메시지 리스너 (중복 방지)
if (!window.pseudonymizerMessageListener) {
  window.pseudonymizerMessageListener = true;
  
  window.addEventListener('message', async (e) => {
    const d = e.data;
    if (!d || (d.type !== 'PII_PROXY_FETCH' && d.type !== 'PII_PROXY_XHR')) return;

    console.log(`📨 content.js 메시지 수신: ${d.type} [${d.msgId}]`);

    const replyType = d.type === 'PII_PROXY_FETCH' ? 'PII_PROXY_FETCH_RESULT' : 'PII_PROXY_XHR_RESULT';
    
    try {
      console.log(`🔄 background.js로 전달 중...`);
      const resp = await chrome.runtime.sendMessage({ kind: d.type, payload: d });
      console.log(`✅ background.js 응답 수신:`, { ok: resp.ok, msgId: d.msgId });
      
      window.postMessage({ 
        type: replyType, 
        msgId: d.msgId, 
        ...resp 
      }, '*');
    } catch (err) {
      console.error(`❌ background.js 통신 오류:`, err);
      window.postMessage({ 
        type: replyType, 
        msgId: d.msgId, 
        ok: false, 
        error: err.message 
      }, '*');
    }
  });
  
  console.log("📡 메시지 리스너 등록 완료");
}