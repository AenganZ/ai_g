// injected.js - 사용자 UI는 절대 건드리지 않고 백그라운드에서만 처리

(function() {
  'use strict';

  if (window.aenganzInjected) {
    console.log('[AenganZ] 이미 주입됨, 중복 방지');
    return;
  }
  window.aenganzInjected = true;

  console.log('[AenganZ] 백그라운드 프록시 시작 (사용자 UI 보존)');

  // ===== 원본 함수 백업 =====
  const _fetch = window.fetch;

  // ===== 요청 추출 함수 =====
  function extractRequestInfo(input, init = {}) {
    let url, method, headers, body;

    if (typeof input === 'string') {
      url = input;
    } else if (input instanceof URL) {
      url = input.href;
    } else if (input instanceof Request) {
      url = input.url;
      method = input.method;
      headers = Object.fromEntries(input.headers.entries());
      body = input.body;
    } else {
      url = String(input);
    }

    method = method || init.method || 'GET';
    headers = { ...headers, ...init.headers };
    body = body || init.body;

    return { url, method, headers, body };
  }

  // ===== 인터셉트 판단 =====
  function shouldIntercept(url, method, body) {
    if (method !== 'POST') return false;
    if (!body) return false;

    try {
      const urlObj = new URL(url);
      const bodyText = String(body);
      
      // OpenAI API
      if (urlObj.hostname.includes('api.openai.com')) {
        return bodyText.includes('messages') && bodyText.includes('content');
      }
      
      // ChatGPT 웹앱 
      if (urlObj.hostname.includes('chat.openai.com') || urlObj.hostname.includes('chatgpt.com')) {
        if (urlObj.pathname.includes('/backend-api/conversation')) {
          return bodyText.includes('messages') && bodyText.includes('user');
        }
      }
      
      // Claude/Anthropic
      if (urlObj.hostname.includes('anthropic.com') || urlObj.hostname.includes('claude.ai')) {
        return bodyText.includes('messages') && bodyText.includes('user');
      }

      return false;
    } catch (e) {
      return false;
    }
  }

  // ===== Fetch 후킹 (사용자 UI 절대 건드리지 않음) =====
  window.fetch = async function(input, init = {}) {
    const { url, method, headers, body } = extractRequestInfo(input, init);

    // 인터셉트 대상이 아니면 원본 그대로 전달
    if (!shouldIntercept(url, method, body)) {
      return _fetch(input, init);
    }

    console.log('[AenganZ] API 요청 가로챔 (사용자 UI는 그대로 유지)');
    console.log('[AenganZ] URL:', url.substring(0, 50));
    console.log('[AenganZ] Body 일부:', String(body).substring(0, 100) + '...');

    try {
      // 백그라운드로 프록시 요청 (사용자는 모름)
      const msgId = crypto.randomUUID();
      
      // content script로 메시지 전송
      window.postMessage({
        type: 'PII_PROXY_FETCH',
        msgId,
        url,
        method,
        headers: headers || {},
        bodyText: String(body)
      }, '*');

      // 응답 대기 (백그라운드 처리)
      const proxyResponse = await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          window.removeEventListener('message', onMessage);
          reject(new Error('프록시 타임아웃'));
        }, 45000); // 45초 타임아웃

        const onMessage = (e) => {
          const data = e.data;
          if (data && data.type === 'PII_PROXY_FETCH_RESULT' && data.msgId === msgId) {
            clearTimeout(timeout);
            window.removeEventListener('message', onMessage);
            resolve(data);
          }
        };

        window.addEventListener('message', onMessage);
      });

      // 프록시 처리 실패 시 원본 요청 실행
      if (!proxyResponse.ok) {
        console.warn('[AenganZ] 프록시 실패, 원본 요청 실행');
        return _fetch(input, init);
      }

      console.log('[AenganZ] 가명화 프록시 완료 (사용자는 모름)');
      
      // 프록시된 응답 반환 (사용자에게는 복원된 응답)
      const response = new Response(proxyResponse.bodyText, { 
        status: proxyResponse.status || 200, 
        statusText: 'OK',
        headers: new Headers(proxyResponse.headers || {})
      });

      // Response 객체 완전 복제 (원본과 동일하게)
      Object.defineProperty(response, 'url', { value: url });
      
      return response;

    } catch (error) {
      console.warn('[AenganZ] 프록시 오류, 원본 요청 실행:', error.message);
      // 모든 오류 시 원본 요청 그대로 실행
      return _fetch(input, init);
    }
  };

  // ===== fetch 함수 프로퍼티 복원 =====
  Object.setPrototypeOf(window.fetch, _fetch);
  for (const key in _fetch) {
    if (_fetch.hasOwnProperty(key)) {
      window.fetch[key] = _fetch[key];
    }
  }

  console.log('[AenganZ] 백그라운드 프록시 설정 완료');
  console.log('[AenganZ] 사용자 UI는 변경되지 않으며, API 요청만 가명화됩니다');

})();