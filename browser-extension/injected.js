(() => {
  console.log("🚀 GenAI Pseudonymizer injected.js 로드됨 (사용자 메시지 복원 버전)!");
  
  // 원본 메시지 저장소
  const originalMessages = new Map();
  
  // ---- 1) 허용/차단 엔드포인트 정의 ----
  const ALLOW = [
    /https:\/\/chatgpt\.com\/backend-(anon|api)\/.*\/conversation/,
    /https:\/\/chat\.openai\.com\/backend-(anon|api)\/.*\/conversation/,
    /https:\/\/chatgpt\.com\/backend-api\/f\/conversation/
  ];
  const BLOCK = [
    /\/auth\//, /\/login/, /\/session/, /csrf/, /turnstile/i, /sentinel/i,
    /check/, /account/, /device/, /verify/, /callback/, /ces\//, /lat\//, /rgstr/,
    /strings/, /stream_status/, /textdocs/, /prepare/, /statsc/, /requirements/
  ];

  const _fetch = window.fetch;
  const urlMatch = (u, arr) => arr.some(rx => rx.test(u));

  // Request 또는 init에서 URL/메서드/헤더/본문을 통합 추출
  async function extractRequest(input, init = {}) {
    let url, method, headers = {}, bodyText = '';

    if (typeof input === 'string') {
      url = input;
      method = (init.method || 'GET').toUpperCase();
      if (init.headers) headers = Object.fromEntries(new Headers(init.headers).entries());
      if (init.body) bodyText = await bodyToText(init.body);
    } else {
      const req = input;
      url = req.url;
      method = (init.method || req.method || 'GET').toUpperCase();
      headers = Object.fromEntries(req.headers.entries());

      if (init.headers) {
        const override = Object.fromEntries(new Headers(init.headers).entries());
        headers = { ...headers, ...override };
      }

      if (init.body) {
        bodyText = await bodyToText(init.body);
      } else {
        try {
          bodyText = await req.clone().text();
        } catch {
          bodyText = '';
        }
      }
    }

    return { url, method, headers, bodyText };
  }

  async function bodyToText(body) {
    if (!body) return '';
    if (typeof body === 'string') return body;
    if (body instanceof Blob) return await body.text();
    if (body instanceof ArrayBuffer) return new TextDecoder().decode(body);
    return '';
  }

  function shouldIntercept(url, method, bodyText) {
    console.log("🔍 요청 분석:", { url, method, bodyLength: bodyText.length });

    if (!urlMatch(url, ALLOW)){
      return false;  
    }
    console.log("✅ ChatGPT 대화 URL 감지!");
    
    if (urlMatch(url, BLOCK)){
      console.log("❌ URL 차단 목록에 있음");
      return false;
    }

    if (method !== 'POST') return false;
    console.log("✅ POST 메서드 확인!");

    if (!bodyText) return false;
    try {
      const b = JSON.parse(bodyText);
      const isValidChatGPT = !!(b && b.action === 'next' && Array.isArray(b.messages) &&
                b.messages.some(m => m?.author?.role === 'user'));
      
      if (isValidChatGPT) {
        console.log("✅ ChatGPT 대화 형식 확인!");
        return true;
      } else {
        return false;
      }
    } catch {
      return false;
    }
  }

  // ⭐ 사용자 메시지 DOM 복원 함수 ⭐
  function restoreUserMessageInDOM(originalText, requestId) {
    console.log(`🔄 [${requestId}] DOM 복원 시작: "${originalText.substring(0, 50)}..."`);
    
    // ChatGPT 메시지 요소 찾기 시도
    const attempts = [
      // 다양한 ChatGPT 메시지 셀렉터들
      '[data-message-author-role="user"]',
      '.group.w-full.text-token-text-primary',
      '[class*="user"]',
      'div[data-testid*="conversation-turn"]',
      'div[class*="message"]'
    ];
    
    let restored = false;
    
    for (const selector of attempts) {
      const messageElements = document.querySelectorAll(selector);
      
      // 가장 최근 사용자 메시지 찾기
      for (let i = messageElements.length - 1; i >= 0; i--) {
        const element = messageElements[i];
        const textContent = element.textContent || element.innerText;
        
        console.log(`🔍 [${requestId}] 검사 중: "${textContent.substring(0, 50)}..."`);
        
        // 가명화된 내용이 포함되어 있는지 확인
        if (textContent && textContent.length > 10 && textContent !== originalText) {
          // 원본 텍스트로 교체 시도
          const textNodes = getTextNodes(element);
          
          for (const node of textNodes) {
            if (node.textContent && node.textContent.trim().length > 10) {
              const oldText = node.textContent;
              node.textContent = originalText;
              
              console.log(`✅ [${requestId}] DOM 복원 성공!`);
              console.log(`📝 복원 전: "${oldText.substring(0, 50)}..."`);
              console.log(`📝 복원 후: "${originalText.substring(0, 50)}..."`);
              
              restored = true;
              return true;
            }
          }
        }
      }
    }
    
    if (!restored) {
      console.log(`⚠️ [${requestId}] DOM 복원 실패 - 대상 요소를 찾을 수 없음`);
      
      // 5초 후 재시도
      setTimeout(() => {
        console.log(`🔄 [${requestId}] DOM 복원 재시도...`);
        restoreUserMessageInDOM(originalText, requestId);
      }, 5000);
    }
    
    return restored;
  }

  // 텍스트 노드 찾기 헬퍼 함수
  function getTextNodes(element) {
    const textNodes = [];
    const walker = document.createTreeWalker(
      element,
      NodeFilter.SHOW_TEXT,
      null,
      false
    );
    
    let node;
    while (node = walker.nextNode()) {
      if (node.textContent.trim().length > 0) {
        textNodes.push(node);
      }
    }
    
    return textNodes;
  }

  // ---- 2) fetch 후킹 (사용자 메시지 저장 및 복원 포함) ----
  window.fetch = async function(input, init = {}) {
    if (typeof input === 'string' && input.includes('chatgpt.com')) {
      console.log("🌐 Fetch 호출:", (init?.method || 'GET'), input);
    }
    
    try {
      const { url, method, headers, bodyText } = await extractRequest(input, init);

      if (!shouldIntercept(url, method, bodyText)) {
        console.log("❌ 가로채기 조건 불일치");
        return _fetch(input, init);
      }

      console.log("🎯 요청 가로채기 실행!");
      
      // ⭐ 원본 사용자 메시지 추출 및 저장 ⭐
      let originalUserMessage = '';
      try {
        const reqBody = JSON.parse(bodyText);
        const userMessages = reqBody.messages?.filter(m => m?.author?.role === 'user') || [];
        
        if (userMessages.length > 0) {
          const lastUserMsg = userMessages[userMessages.length - 1];
          const content = lastUserMsg.content;
          
          if (content && content.content_type === 'text' && Array.isArray(content.parts)) {
            originalUserMessage = content.parts.join('\n');
          } else if (typeof content === 'string') {
            originalUserMessage = content;
          }
        }
      } catch (e) {
        console.log("❌ 원본 메시지 추출 실패:", e);
      }
      
      const msgId = crypto.randomUUID();
      
      if (originalUserMessage) {
        originalMessages.set(msgId, originalUserMessage);
        console.log(`📝 원본 메시지 저장 [${msgId}]: "${originalUserMessage.substring(0, 50)}..."`);
      }
      
      // 확장으로 메시지 전송
      window.postMessage({
        type: 'PII_PROXY_FETCH',
        msgId,
        url,
        method,
        headers,
        bodyText
      }, '*');

      // 응답 대기
      const reply = await new Promise((resolve, reject) => {
        const onMsg = (e) => {
          const d = e.data;
          if (d && d.type === 'PII_PROXY_FETCH_RESULT' && d.msgId === msgId) {
            window.removeEventListener('message', onMsg);
            console.log("✅ 가명화된 응답 수신:", d);
            resolve(d);
          }
        };
        window.addEventListener('message', onMsg);
        
        setTimeout(() => {
          window.removeEventListener('message', onMsg);
          console.log("⏰ 응답 타임아웃, 원본 요청 실행");
          reject(new Error('pseudonymizer timeout (3 minutes)'));
        }, 180000);
      });

      if (!reply.ok) {
        console.log("❌ 가명화 실패, 원본 요청 실행");
        return _fetch(input, init);
      }
      
      console.log("✅ 가명화된 요청/응답 처리 완료!");
      
      // ⭐ 응답 후 DOM에서 사용자 메시지 복원 ⭐
      if (originalUserMessage) {
        setTimeout(() => {
          restoreUserMessageInDOM(originalUserMessage, msgId);
        }, 2000); // 2초 후 DOM 복원 시도
        
        // 추가 재시도 (ChatGPT 렌더링이 늦을 수 있음)
        setTimeout(() => {
          restoreUserMessageInDOM(originalUserMessage, msgId);
        }, 10000); // 10초 후 재시도
        
        originalMessages.delete(msgId); // 메모리 정리
      }
      
      return new Response(reply.bodyText, { 
        status: reply.status, 
        headers: reply.headers 
      });

    } catch (e) {
      console.log("❌ fetch 후킹 오류, 원본 요청 실행:", e.message);
      return _fetch(input, init);
    }
  };
  
  console.log("✅ fetch 후킹 완료 (사용자 메시지 DOM 복원 포함)!");
})();