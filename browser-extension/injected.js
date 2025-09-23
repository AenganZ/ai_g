(() => {
  console.log("🚀 GenAI Pseudonymizer injected.js 로드됨 (메시지 개별 복원 버전)!");
  
  // 메시지별 복원 정보 저장소
  const messageRestorationMap = new Map();
  let messageCounter = 0;
  
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

  // ⭐ 개선된 사용자 메시지 DOM 복원 함수 ⭐
  function restoreSpecificUserMessage(originalText, messageId, attempt = 1) {
    console.log(`🔄 [${messageId}] DOM 복원 시도 ${attempt}: "${originalText.substring(0, 50)}..."`);
    
    // 복원 완료된 메시지는 스킵
    const restorationInfo = messageRestorationMap.get(messageId);
    if (restorationInfo && restorationInfo.restored) {
      console.log(`✅ [${messageId}] 이미 복원 완료된 메시지, 스킵`);
      return true;
    }
    
    // ChatGPT 메시지 요소 찾기
    const messageSelectors = [
      '[data-message-author-role="user"]',
      '.group.w-full.text-token-text-primary',
      'div[data-testid*="conversation-turn"]',
      'div[class*="group"][class*="w-full"]'
    ];
    
    let targetElement = null;
    let currentMessageIndex = 0;
    
    // 현재 메시지의 인덱스 계산 (가장 최근 것 우선)
    const expectedMessageIndex = messageCounter - (restorationInfo ? restorationInfo.messageOrder : 0);
    
    for (const selector of messageSelectors) {
      const messageElements = document.querySelectorAll(selector);
      console.log(`🔍 [${messageId}] ${selector}로 ${messageElements.length}개 메시지 요소 발견`);
      
      // 사용자 메시지만 필터링
      const userMessageElements = Array.from(messageElements).filter(el => {
        const textContent = el.textContent || '';
        // ChatGPT 응답 시작 패턴 제외
        return !textContent.includes('김가명 고객님') && 
               !textContent.includes('좋은 질문입니다') &&
               !textContent.includes('도움을 드릴 수 있어') &&
               textContent.length > 20; // 의미있는 길이
      });
      
      if (userMessageElements.length > 0) {
        console.log(`📝 [${messageId}] ${userMessageElements.length}개 사용자 메시지 요소 발견`);
        
        // ⭐ 특정 메시지만 타겟팅 (역순으로 최근 메시지부터)
        for (let i = userMessageElements.length - 1; i >= 0; i--) {
          const element = userMessageElements[i];
          const textContent = element.textContent || element.innerText || '';
          
          console.log(`🔍 [${messageId}] 검사 중 [${i}]: "${textContent.substring(0, 50)}..."`);
          
          // ⭐ 핵심: 정확한 메시지 매칭 (원본과 길이가 비슷하고, 가명화된 내용 포함)
          const lengthSimilar = Math.abs(textContent.length - originalText.length) < 50;
          const containsPseudonym = textContent.includes('가명') || 
                                   textContent.includes('강원') || 
                                   textContent.includes('010-0000-') ||
                                   textContent.match(/[가-힣]+가명/);
          
          if (lengthSimilar && (containsPseudonym || i === userMessageElements.length - 1)) {
            console.log(`🎯 [${messageId}] 타겟 메시지 발견! [${i}]: "${textContent.substring(0, 50)}..."`);
            targetElement = element;
            currentMessageIndex = i;
            break;
          }
        }
        
        if (targetElement) break;
      }
    }
    
    if (!targetElement) {
      console.log(`⚠️ [${messageId}] 타겟 요소를 찾을 수 없음 (시도 ${attempt})`);
      
      // 3회까지 재시도
      if (attempt <= 3) {
        setTimeout(() => {
          restoreSpecificUserMessage(originalText, messageId, attempt + 1);
        }, 2000 * attempt);
      }
      return false;
    }
    
    // ⭐ 텍스트 노드만 정밀하게 교체
    const success = replaceTextInElement(targetElement, originalText, messageId);
    
    if (success) {
      // 복원 완료 표시
      messageRestorationMap.set(messageId, { 
        ...restorationInfo,
        restored: true, 
        restoredAt: Date.now(),
        elementIndex: currentMessageIndex
      });
      
      // 복원 완료 표시 (DOM 속성 추가)
      targetElement.setAttribute('data-pseudonymizer-restored', messageId);
      
      console.log(`✅ [${messageId}] DOM 복원 성공! 인덱스: ${currentMessageIndex}`);
      return true;
    } else {
      console.log(`❌ [${messageId}] DOM 복원 실패`);
      return false;
    }
  }

  // 요소 내 텍스트 정밀 교체
  function replaceTextInElement(element, newText, messageId) {
    try {
      // 이미 복원된 요소는 스킵
      if (element.getAttribute('data-pseudonymizer-restored')) {
        console.log(`🔄 [${messageId}] 이미 복원 마킹된 요소, 스킵`);
        return false;
      }
      
      const textNodes = getTextNodes(element);
      console.log(`📝 [${messageId}] ${textNodes.length}개 텍스트 노드 발견`);
      
      // 가장 긴 텍스트 노드를 메인 콘텐츠로 간주
      let mainTextNode = null;
      let maxLength = 0;
      
      for (const node of textNodes) {
        const content = node.textContent || '';
        if (content.length > maxLength && content.trim().length > 10) {
          maxLength = content.length;
          mainTextNode = node;
        }
      }
      
      if (mainTextNode) {
        const oldText = mainTextNode.textContent;
        console.log(`🔄 [${messageId}] 메인 텍스트 교체:`);
        console.log(`  이전: "${oldText.substring(0, 50)}..."`);
        console.log(`  이후: "${newText.substring(0, 50)}..."`);
        
        mainTextNode.textContent = newText;
        return true;
      } else {
        console.log(`❌ [${messageId}] 적절한 텍스트 노드를 찾을 수 없음`);
        return false;
      }
      
    } catch (error) {
      console.error(`💥 [${messageId}] 텍스트 교체 오류:`, error);
      return false;
    }
  }

  // 텍스트 노드 찾기 헬퍼 함수
  function getTextNodes(element) {
    const textNodes = [];
    const walker = document.createTreeWalker(
      element,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: function(node) {
          // 의미있는 텍스트만 선택
          const content = node.textContent.trim();
          if (content.length > 5 && 
              !content.match(/^[\s\n\r]*$/) &&
              !node.parentNode.matches('script, style, noscript')) {
            return NodeFilter.FILTER_ACCEPT;
          }
          return NodeFilter.FILTER_SKIP;
        }
      },
      false
    );
    
    let node;
    while (node = walker.nextNode()) {
      textNodes.push(node);
    }
    
    return textNodes;
  }

  // ---- 2) fetch 후킹 (개선된 메시지 관리) ----
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
      
      // ⭐ 메시지 카운터 증가 및 고유 ID 생성
      messageCounter++;
      const msgId = crypto.randomUUID();
      const messageOrder = messageCounter;
      
      // ⭐ 원본 사용자 메시지 추출 및 저장
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
      
      if (originalUserMessage) {
        messageRestorationMap.set(msgId, {
          originalText: originalUserMessage,
          messageOrder: messageOrder,
          created: Date.now(),
          restored: false
        });
        console.log(`📝 [${msgId}] 원본 메시지 저장 (순서: ${messageOrder}): "${originalUserMessage.substring(0, 50)}..."`);
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
      
      // ⭐ 응답 후 해당 메시지만 정밀하게 DOM 복원 ⭐
      if (originalUserMessage) {
        // 첫 번째 복원 시도 (즉시)
        setTimeout(() => {
          restoreSpecificUserMessage(originalUserMessage, msgId);
        }, 1000);
        
        // 두 번째 복원 시도 (지연 - ChatGPT 렌더링 완료 후)
        setTimeout(() => {
          const restorationInfo = messageRestorationMap.get(msgId);
          if (!restorationInfo || !restorationInfo.restored) {
            console.log(`🔄 [${msgId}] 두 번째 복원 시도...`);
            restoreSpecificUserMessage(originalUserMessage, msgId);
          }
        }, 5000);
        
        // 메모리 정리 (10분 후)
        setTimeout(() => {
          messageRestorationMap.delete(msgId);
          console.log(`🗑️ [${msgId}] 메모리 정리 완료`);
        }, 600000);
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
  
  // 상태 확인 함수 (디버깅용)
  window.pseudonymizerDebug = {
    getMessages: () => Array.from(messageRestorationMap.entries()),
    getMessageCount: () => messageCounter,
    clearMessages: () => messageRestorationMap.clear(),
    forceRestore: (messageId) => {
      const info = messageRestorationMap.get(messageId);
      if (info) {
        restoreSpecificUserMessage(info.originalText, messageId);
      }
    }
  };
  
  console.log("✅ fetch 후킹 완료 (개별 메시지 복원 시스템)!");
  console.log("🛠️ 디버깅: window.pseudonymizerDebug 사용 가능");
})();