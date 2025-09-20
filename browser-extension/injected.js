(() => {
  console.log('[PII] 🚀 Dual-view PII system starting...');

  // 원본 fetch 저장
  const originalFetch = window.fetch;
  
  // 현재 활성화된 치환 맵 저장 (응답 복구용)
  let activeSubstitutionMaps = new Map(); // requestId -> {substitution_map, reverse_map}
  
  // ChatGPT URL 패턴
  function shouldIntercept(url) {
    const chatgptPatterns = [
      'chatgpt.com/backend-api/f/conversation',
      'chatgpt.com/backend-api/conversation', 
      'chat.openai.com/backend-api/f/conversation',
      'chat.openai.com/backend-api/conversation'
    ];
    
    return chatgptPatterns.some(pattern => url.includes(pattern));
  }

  // 사용자 메시지 추출
  function extractUserMessage(requestBody) {
    try {
      const data = JSON.parse(requestBody);
      
      // 새로운 ChatGPT 형식
      if (data.messages && Array.isArray(data.messages)) {
        const userMessages = data.messages.filter(m => m.role === 'user');
        if (userMessages.length > 0) {
          const lastUserMessage = userMessages[userMessages.length - 1];
          let userText = '';
          
          if (lastUserMessage.content) {
            if (Array.isArray(lastUserMessage.content)) {
              userText = lastUserMessage.content
                .filter(c => c.type === 'text')
                .map(c => c.text || '')
                .join('\n');
            } else if (typeof lastUserMessage.content === 'string') {
              userText = lastUserMessage.content;
            }
          }
          
          if (userText) {
            return userText;
          }
        }
      }
      
      // 기존 ChatGPT 형식
      if (data.action === 'next' && data.messages) {
        const userMsg = data.messages.find(m => m?.author?.role === 'user');
        if (userMsg && userMsg.content && userMsg.content.parts) {
          return userMsg.content.parts.join('\n');
        }
      }
      
      return null;
    } catch (e) {
      console.error('[PII] Failed to parse request body:', e);
      return null;
    }
  }

  // 가명화 텍스트 주입 (LLM이 받을 버전)
  function injectPseudonymizedText(originalBody, pseudonymizedText) {
    try {
      const data = JSON.parse(originalBody);
      
      // 새로운 형식 처리
      if (data.messages && Array.isArray(data.messages)) {
        const userMessages = data.messages.filter(m => m.role === 'user');
        if (userMessages.length > 0) {
          const lastUserMessage = userMessages[userMessages.length - 1];
          
          if (Array.isArray(lastUserMessage.content)) {
            lastUserMessage.content = [{ 
              type: 'text', 
              text: pseudonymizedText 
            }];
          } else {
            lastUserMessage.content = pseudonymizedText;
          }
          
          return JSON.stringify(data);
        }
      }
      
      // 기존 형식 처리
      if (data.action === 'next' && data.messages) {
        const userMsg = data.messages.find(m => m?.author?.role === 'user');
        if (userMsg) {
          userMsg.content = {
            content_type: 'text',
            parts: [pseudonymizedText]
          };
          return JSON.stringify(data);
        }
      }
      
      return originalBody;
    } catch (e) {
      console.error('[PII] Failed to inject text:', e);
      return originalBody;
    }
  }

  // 가명화 서버 호출 (Content Script를 통해 우회)
  async function callPseudonymizationServer(userText) {
    return new Promise((resolve, reject) => {
      const requestId = 'pseudo_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      
      // Content Script에 메시지 전송
      window.postMessage({
        type: 'PII_PSEUDONYMIZE_REQUEST',
        requestId: requestId,
        prompt: userText,
        timestamp: Date.now()
      }, '*');
      
      // 응답 대기
      const responseHandler = (event) => {
        if (event.source !== window) return;
        
        const data = event.data;
        if (data.type === 'PII_PSEUDONYMIZE_RESPONSE' && data.requestId === requestId) {
          window.removeEventListener('message', responseHandler);
          
          if (data.success) {
            resolve(data.result);
          } else {
            reject(new Error(data.error));
          }
        }
      };
      
      window.addEventListener('message', responseHandler);
      
      // 타임아웃 설정
      setTimeout(() => {
        window.removeEventListener('message', responseHandler);
        reject(new Error('Pseudonymization timeout'));
      }, 15000);
    });
  }

  // 사용자 화면에서 메시지를 원본으로 되돌리기
  function revertUserMessageToOriginal(originalText) {
    try {
      console.log('[PII] 🔄 Reverting user message to original on UI...');
      
      // ChatGPT의 메시지 컨테이너 찾기
      const messageContainers = document.querySelectorAll('[data-message-author-role="user"]');
      
      if (messageContainers.length > 0) {
        // 가장 최근 사용자 메시지 찾기
        const lastUserMessage = messageContainers[messageContainers.length - 1];
        
        // 메시지 텍스트 영역 찾기
        const textElement = lastUserMessage.querySelector('div[class*="text"], div[class*="message"], p, span');
        
        if (textElement) {
          // 원본 텍스트로 복구
          textElement.textContent = originalText;
          console.log('[PII] ✅ User message reverted to original on UI');
        }
      }
    } catch (error) {
      console.warn('[PII] ⚠️ Failed to revert user message on UI:', error);
    }
  }

  // 메인 fetch 후킹
  window.fetch = async function(input, init = {}) {
    try {
      const url = typeof input === 'string' ? input : input.url;
      const method = init.method || (typeof input === 'string' ? 'GET' : input.method) || 'GET';
      
      // 가로챌 필요가 없는 요청은 그대로 통과
      if (method !== 'POST' || !shouldIntercept(url)) {
        return originalFetch(input, init);
      }

      console.log('[PII] 🎯 INTERCEPTING ChatGPT request');

      // 요청 바디 추출
      let requestBody = '';
      if (init.body) {
        requestBody = init.body;
      } else if (typeof input !== 'string' && input.body) {
        requestBody = await input.clone().text();
      }

      // 사용자 메시지 추출
      const originalUserText = extractUserMessage(requestBody);
      if (!originalUserText || originalUserText.length < 5) {
        return originalFetch(input, init);
      }

      console.log('[PII] 👤 USER MESSAGE detected:', originalUserText.substring(0, 100) + '...');

      // 가명화 서버 호출
      try {
        const pseudoData = await callPseudonymizationServer(originalUserText);

        if (!pseudoData.ok) {
          throw new Error('Pseudonymization failed');
        }

        const mapping = pseudoData.mapping || [];
        const maskedText = pseudoData.masked_prompt || originalUserText;
        const substitutionMap = pseudoData.substitution_map || {};
        const reverseMap = pseudoData.reverse_map || {};

        if (mapping.length > 0) {
          console.log('[PII] 🎭 PSEUDONYMIZATION complete:', mapping.length, 'items replaced');
          mapping.forEach(item => {
            console.log(`[PII]    ${item.type}: "${item.value}" → "${item.replacement}"`);
          });
          
          // 고유한 요청 ID 생성 (응답 추적용)
          const conversationId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
          
          // 치환 맵 저장 (응답 복구용)
          activeSubstitutionMaps.set(conversationId, {
            substitution_map: substitutionMap,
            reverse_map: reverseMap,
            original_text: originalUserText,
            masked_text: maskedText,
            timestamp: Date.now()
          });
          
          // 5분 후 자동 정리
          setTimeout(() => {
            activeSubstitutionMaps.delete(conversationId);
          }, 300000);
          
          console.log('[PII] 📝 Substitution map stored for conversation:', conversationId);
        } else {
          console.log('[PII] ✅ No PII detected');
        }

        // 가명화된 텍스트로 요청 수정 (LLM이 받을 버전)
        const modifiedBody = injectPseudonymizedText(requestBody, maskedText);
        const modifiedInit = {
          ...init,
          body: modifiedBody
        };

        console.log('[PII] 🚀 Sending masked request to ChatGPT...');
        console.log('[PII] 📤 LLM will receive:', maskedText.substring(0, 100) + '...');

        // 수정된 요청 실행
        const response = await originalFetch(url, modifiedInit);

        // 사용자 화면에서 메시지를 원본으로 되돌리기 (비동기)
        setTimeout(() => {
          revertUserMessageToOriginal(originalUserText);
        }, 100);

        // 응답 처리 및 복구
        if (response.ok && mapping.length > 0) {
          console.log('[PII] 📄 Processing response for restoration...');
          
          const contentType = response.headers.get('content-type') || '';
          
          if (contentType.includes('text/plain') && response.body) {
            // 스트리밍 응답 처리
            console.log('[PII] 📡 Processing streaming response...');
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            const stream = new ReadableStream({
              start(controller) {
                function pump() {
                  return reader.read().then(({ done, value }) => {
                    if (done) {
                      if (buffer) {
                        const restored = restoreText(buffer, reverseMap);
                        controller.enqueue(new TextEncoder().encode(restored));
                      }
                      controller.close();
                      return;
                    }
                    
                    const chunk = decoder.decode(value, { stream: true });
                    buffer += chunk;
                    
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                      if (line.trim()) {
                        const restored = restoreText(line + '\n', reverseMap);
                        controller.enqueue(new TextEncoder().encode(restored));
                      } else {
                        controller.enqueue(new TextEncoder().encode('\n'));
                      }
                    }
                    
                    return pump();
                  });
                }
                return pump();
              }
            });
            
            return new Response(stream, {
              status: response.status,
              statusText: response.statusText,
              headers: response.headers
            });
          } else {
            // 일반 응답 처리
            const responseText = await response.text();
            const restoredText = restoreText(responseText, reverseMap);
            console.log('[PII] ✨ Response restored');
            
            return new Response(restoredText, {
              status: response.status,
              statusText: response.statusText,
              headers: response.headers
            });
          }
        }

        return response;

      } catch (serverError) {
        console.warn('[PII] ⚠️ Pseudonymization server error:', serverError.message);
        console.log('[PII] 🔄 Falling back to original request');
        return originalFetch(input, init);
      }

    } catch (error) {
      console.error('[PII] ❌ Fetch interception error:', error.message);
      return originalFetch(input, init);
    }
  };

  // 응답 복원 함수
  function restoreText(text, reverseMap) {
    if (!reverseMap || Object.keys(reverseMap).length === 0) return text;
    
    let result = text;
    
    // 가명화된 내용을 원본으로 복구
    // 긴 것부터 치환 (부분 매칭 방지)
    const sortedEntries = Object.entries(reverseMap).sort((a, b) => b[0].length - a[0].length);
    
    for (const [pseudonym, original] of sortedEntries) {
      if (pseudonym && original) {
        // 단어 경계를 고려한 정확한 매칭
        const regex = new RegExp(pseudonym.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
        const beforeReplace = result;
        result = result.replace(regex, original);
        
        if (beforeReplace !== result) {
          console.log(`[PII] 🔄 Restored: "${pseudonym}" → "${original}"`);
        }
      }
    }
    
    return result;
  }

  // 정기적으로 오래된 치환 맵 정리
  setInterval(() => {
    const now = Date.now();
    const fiveMinutesAgo = now - 300000;
    
    for (const [conversationId, data] of activeSubstitutionMaps.entries()) {
      if (data.timestamp < fiveMinutesAgo) {
        activeSubstitutionMaps.delete(conversationId);
        console.log('[PII] 🧹 Cleaned up old substitution map:', conversationId);
      }
    }
  }, 60000); // 1분마다 정리

  // 초기화 완료
  console.log('[PII] ✅ Dual-view PII system ready!');
  console.log('[PII] 👁️ Users will see: ORIGINAL text');
  console.log('[PII] 🤖 LLM will receive: PSEUDONYMIZED text');
  console.log('[PII] 🔄 Responses will be: RESTORED to original');

})();