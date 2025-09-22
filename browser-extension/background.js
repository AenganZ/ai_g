// background.js - 완벽한 투명 프록시 (사용자는 원본만 봄)

// ===== 설정 =====
const AENGANZ_SERVER_URL = 'http://127.0.0.1:5000';
const PSEUDONYMIZE_ENDPOINT = '/pseudonymize';
const LOGS_ENDPOINT = '/prompt_logs';

// ===== 전역 상태 =====
const STATE = {
  activeMappings: new Map(), // requestId -> { pseudoToOriginal, originalTopseudo }
  requestLogs: [],
  maxLogs: 200
};

// ===== 유틸리티 함수 =====
function generateId() {
  return `aenganz_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function safeHeaders(headers) {
  const result = {};
  if (headers && typeof headers === 'object') {
    for (const [key, value] of Object.entries(headers)) {
      if (typeof value === 'string' || typeof value === 'number') {
        result[key] = String(value);
      }
    }
  }
  return result;
}

// ===== AenganZ 서버 통신 =====
async function pseudonymizeText(originalText) {
  try {
    console.log('[Background] 가명화 요청:', originalText.substring(0, 50) + '...');
    
    const response = await fetch(`${AENGANZ_SERVER_URL}${PSEUDONYMIZE_ENDPOINT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        prompt: originalText,
        mode: 'enhanced'
      }),
      signal: AbortSignal.timeout(15000) // 15초 타임아웃
    });

    if (!response.ok) {
      throw new Error(`서버 오류: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log('[Background] 가명화 응답:', data);

    // 매핑 생성 (양방향)
    const items = data.detection?.items || [];
    const pseudoToOriginal = {};
    const originalTopseudo = {};
    
    items.forEach(item => {
      if (item.token && item.value) {
        pseudoToOriginal[item.token] = item.value;
        originalTopseudo[item.value] = item.token;
      }
    });

    return {
      success: true,
      pseudonymized: data.pseudonymized_text || originalText,
      mappings: { pseudoToOriginal, originalToProxy: originalTopseudo },
      detection: data.detection || {},
      requestId: data.id || generateId()
    };

  } catch (error) {
    console.error('[Background] 가명화 실패:', error);
    return {
      success: false,
      pseudonymized: originalText, // 실패 시 원본 그대로
      mappings: { pseudoToOriginal: {}, originalToProxy: {} },
      detection: {},
      error: error.message
    };
  }
}

// ===== 텍스트 복원 함수 =====
function restoreText(text, pseudoToOriginalMap) {
  if (!text || !pseudoToOriginalMap || Object.keys(pseudoToOriginalMap).length === 0) {
    return text;
  }

  let restored = text;
  
  // 가명 → 원본 복원
  for (const [pseudo, original] of Object.entries(pseudoToOriginalMap)) {
    if (pseudo && original) {
      // 정확한 단어 매칭으로 복원
      const escapedPseudo = pseudo.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`\\b${escapedPseudo}\\b`, 'g');
      restored = restored.replace(regex, original);
    }
  }

  console.log('[Background] 텍스트 복원 완료:', {
    original: text.substring(0, 50) + '...',
    restored: restored.substring(0, 50) + '...',
    mappingCount: Object.keys(pseudoToOriginalMap).length
  });

  return restored;
}

// ===== 프롬프트 추출 함수 =====
function extractPrompt(url, bodyText) {
  try {
    const body = JSON.parse(bodyText);
    const urlObj = new URL(url);

    // OpenAI API (/v1/chat/completions)
    if (urlObj.hostname.includes('api.openai.com')) {
      const messages = body.messages || [];
      const userMessage = messages.filter(m => m.role === 'user').pop();
      return userMessage?.content || '';
    }

    // ChatGPT 웹앱
    if (urlObj.hostname.includes('chat.openai.com') || urlObj.hostname.includes('chatgpt.com')) {
      const messages = body.messages || [];
      const userMessage = messages.filter(m => m?.author?.role === 'user').pop();
      
      if (userMessage?.content) {
        if (userMessage.content.content_type === 'text' && Array.isArray(userMessage.content.parts)) {
          return userMessage.content.parts.join('\n');
        }
        if (typeof userMessage.content === 'string') {
          return userMessage.content;
        }
      }
      return '';
    }

    // Claude/Anthropic
    if (urlObj.hostname.includes('anthropic.com') || urlObj.hostname.includes('claude.ai')) {
      const messages = body.messages || [];
      const userMessage = messages.filter(m => m.role === 'user').pop();
      
      if (Array.isArray(userMessage?.content)) {
        return userMessage.content.map(c => c.text || '').join('\n');
      }
      if (typeof userMessage?.content === 'string') {
        return userMessage.content;
      }
      return '';
    }

    return '';
  } catch (error) {
    console.error('[Background] 프롬프트 추출 실패:', error);
    return '';
  }
}

// ===== 요청 본문 수정 함수 =====
function injectPseudoPrompt(url, originalBody, pseudoText) {
  try {
    const body = JSON.parse(originalBody);
    const urlObj = new URL(url);

    // OpenAI API
    if (urlObj.hostname.includes('api.openai.com')) {
      const messages = body.messages || [];
      const lastUserIndex = messages.map(m => m.role).lastIndexOf('user');
      if (lastUserIndex >= 0) {
        messages[lastUserIndex].content = pseudoText;
      }
      return JSON.stringify(body);
    }

    // ChatGPT 웹앱
    if (urlObj.hostname.includes('chat.openai.com') || urlObj.hostname.includes('chatgpt.com')) {
      const messages = body.messages || [];
      const userMessage = messages.filter(m => m?.author?.role === 'user').pop();
      if (userMessage) {
        userMessage.content = {
          content_type: 'text',
          parts: [pseudoText]
        };
      }
      return JSON.stringify(body);
    }

    // Claude/Anthropic
    if (urlObj.hostname.includes('anthropic.com') || urlObj.hostname.includes('claude.ai')) {
      const messages = body.messages || [];
      const userMessage = messages.filter(m => m.role === 'user').pop();
      if (userMessage) {
        userMessage.content = [{ type: 'text', text: pseudoText }];
      }
      return JSON.stringify(body);
    }

    return originalBody;
  } catch (error) {
    console.error('[Background] 요청 수정 실패:', error);
    return originalBody;
  }
}

// ===== 응답 처리 함수 =====
function processAIResponse(responseText, pseudoToOriginalMap) {
  if (!responseText || !pseudoToOriginalMap || Object.keys(pseudoToOriginalMap).length === 0) {
    return responseText;
  }

  try {
    // JSON 응답 처리
    const responseJson = JSON.parse(responseText);
    
    // OpenAI API 응답
    if (responseJson.choices?.[0]?.message?.content) {
      responseJson.choices[0].message.content = restoreText(
        responseJson.choices[0].message.content, 
        pseudoToOriginalMap
      );
      return JSON.stringify(responseJson);
    }
    
    // Claude API 응답
    if (responseJson.content?.[0]?.text) {
      responseJson.content[0].text = restoreText(
        responseJson.content[0].text, 
        pseudoToOriginalMap
      );
      return JSON.stringify(responseJson);
    }

    // ChatGPT 스트리밍 응답 (delta)
    if (responseJson.choices?.[0]?.delta?.content) {
      responseJson.choices[0].delta.content = restoreText(
        responseJson.choices[0].delta.content,
        pseudoToOriginalMap
      );
      return JSON.stringify(responseJson);
    }

    return responseText;
    
  } catch (parseError) {
    // JSON이 아닌 경우 전체 텍스트에서 복원
    return restoreText(responseText, pseudoToOriginalMap);
  }
}

// ===== 메인 메시지 핸들러 =====
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.kind !== 'PII_PROXY_FETCH') {
    return false; // 다른 메시지는 무시
  }

  (async () => {
    const startTime = Date.now();
    const requestId = generateId();

    console.log('[Background] 프록시 요청 처리 시작:', requestId);

    try {
      const { url, method, headers, bodyText } = message.payload || {};

      // 1. 프롬프트 추출
      const originalPrompt = extractPrompt(url, bodyText);
      if (!originalPrompt || originalPrompt.length < 5) {
        console.log('[Background] 프롬프트가 너무 짧거나 없음, 원본 전달');
        return sendResponse({ ok: false, passthrough: true });
      }

      console.log('[Background] 원본 프롬프트:', originalPrompt.substring(0, 100) + '...');

      // 2. 가명화 처리
      const pseudoResult = await pseudonymizeText(originalPrompt);
      if (!pseudoResult.success) {
        console.warn('[Background] 가명화 실패, 원본 전달');
        return sendResponse({ ok: false, passthrough: true });
      }

      // 3. 매핑 저장
      STATE.activeMappings.set(requestId, pseudoResult.mappings);

      // 4. 가명화된 요청 본문 생성
      const modifiedBody = injectPseudoPrompt(url, bodyText, pseudoResult.pseudonymized);

      console.log('[Background] 가명화된 프롬프트:', pseudoResult.pseudonymized.substring(0, 100) + '...');

      // 5. AI 서비스로 실제 요청 전송
      const aiResponse = await fetch(url, {
        method: method || 'POST',
        headers: safeHeaders(headers),
        body: modifiedBody,
        signal: AbortSignal.timeout(60000) // 60초 타임아웃
      });

      // 6. AI 응답 처리
      const aiResponseText = await aiResponse.text();
      
      // 7. 응답에서 가명 복원 (사용자에게는 원본으로 보임)
      const restoredResponse = processAIResponse(
        aiResponseText, 
        pseudoResult.mappings.pseudoToOriginal
      );

      // 8. 매핑 정리 (보안상 즉시 삭제)
      STATE.activeMappings.delete(requestId);

      // 9. 로그 저장
      const logEntry = {
        id: requestId,
        time: new Date().toISOString(),
        url: url,
        input: { prompt: originalPrompt },
        output: { 
          pseudonymized_text: pseudoResult.pseudonymized,
          detection: pseudoResult.detection 
        },
        processing_time: Date.now() - startTime,
        success: true,
        restored: true
      };
      
      STATE.requestLogs.push(logEntry);
      if (STATE.requestLogs.length > STATE.maxLogs) {
        STATE.requestLogs = STATE.requestLogs.slice(-STATE.maxLogs);
      }

      // 10. 성공 응답 반환
      console.log('[Background] 프록시 처리 완료:', requestId, `${Date.now() - startTime}ms`);
      
      sendResponse({
        ok: true,
        status: aiResponse.status,
        headers: Object.fromEntries(aiResponse.headers.entries()),
        bodyText: restoredResponse // 사용자에게는 복원된 응답
      });

    } catch (error) {
      console.error('[Background] 프록시 처리 오류:', error);
      sendResponse({ 
        ok: false, 
        error: error.message,
        passthrough: true 
      });
    }
  })();

  return true; // 비동기 응답
});

// ===== 팝업 지원 API =====
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'getLogs') {
    sendResponse({ logs: STATE.requestLogs });
    return true;
  }
  
  if (message.action === 'clearLogs') {
    STATE.requestLogs = [];
    STATE.activeMappings.clear();
    sendResponse({ success: true });
    return true;
  }

  if (message.action === 'getStatus') {
    sendResponse({ 
      activeRequests: STATE.activeMappings.size,
      totalLogs: STATE.requestLogs.length,
      serverUrl: AENGANZ_SERVER_URL
    });
    return true;
  }
});

console.log('[Background] AenganZ 투명 프록시 시작됨');