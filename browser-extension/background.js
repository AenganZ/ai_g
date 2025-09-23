// background.js - 역복호화 기능만 집중 강화

// ===== 전역 상태 =====
const STATE = {
  reqLogs: [],
  maxLogs: 200,
  activeMappings: new Map()
};

// ===== 메시지 핸들러 =====
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.kind) return;
  if (msg.kind !== 'PII_PROXY_FETCH' && msg.kind !== 'PII_PROXY_XHR') {
    return sendResponse({ ok: false });
  }

  (async () => {
    const startedAt = new Date().toISOString();
    const requestId = cryptoRandomId();
    
    console.log(`🚀 [${requestId}] 요청 시작`);
    
    const logEntry = {
      id: requestId,
      time: startedAt,
      kind: msg.kind,
      url: msg?.payload?.url || '',
      method: (msg?.payload?.method || 'POST').toUpperCase(),
      request: {
        headers: safePlainObj(msg?.payload?.headers || {}),
        rawBody: msg?.payload?.bodyText || ''
      },
      response: { status: null, headers: {}, bodyText: '' },
      error: null
    };

    try {
      const { url, method, headers, bodyText } = msg.payload || {};

      // 1) 프롬프트 추출
      let reqBody; 
      try { 
        reqBody = bodyText ? JSON.parse(bodyText) : {}; 
      } catch { 
        reqBody = {}; 
      }
      
      const { joinedText, adapter } = extractTextForPseudonymization(url, reqBody);

      // 2) 서버에 가명화 요청
      const id20 = await makeId20(joinedText + '|' + startedAt);
      const pseudoResult = await postToLocalPseudonymize(joinedText || '', id20);
      
      console.log(`📝 [${requestId}] 가명화 결과:`, {
        original: joinedText,
        masked: pseudoResult.masked_prompt,
        reverse_map: pseudoResult.reverse_map
      });

      // 3) ⭐ reverse_map 저장 (복원용) - 핵심!
      const reverseMap = pseudoResult.reverse_map || {};
      console.log(`🔑 [${requestId}] reverse_map 확인:`, reverseMap);
      
      if (Object.keys(reverseMap).length > 0) {
        STATE.activeMappings.set(id20, reverseMap);
        console.log(`✅ [${requestId}] reverse_map 저장 완료 [${id20}]:`, reverseMap);
      } else {
        console.log(`❌ [${requestId}] reverse_map이 비어있음!`);
      }

      // 4) AI 서비스로 가명화된 요청 전송
      const modBody = adapter.injectPseudonymized(reqBody, pseudoResult.masked_prompt);
      const bodyOut = JSON.stringify(modBody);

      console.log(`🤖 [${requestId}] AI 서비스로 전송:`, {
        url: url,
        masked_prompt: pseudoResult.masked_prompt
      });

      // 5) AI 서비스 응답 수신
      const res = await fetch(url, { method, headers, body: bodyOut });
      let responseText = await res.text();

      console.log(`📨 [${requestId}] AI 응답 수신:`, {
        status: res.status,
        response_preview: responseText.substring(0, 200) + '...'
      });

      // 6) ⭐⭐⭐ 핵심: AI 응답 복원 ⭐⭐⭐
      const storedReverseMap = STATE.activeMappings.get(id20);
      console.log(`🔍 [${requestId}] 복원 시작:`, {
        has_stored_map: !!storedReverseMap,
        stored_map: storedReverseMap,
        original_response: responseText
      });
      
      if (storedReverseMap && Object.keys(storedReverseMap).length > 0) {
        console.log(`🔄 [${requestId}] 복원 실행 중...`);
        
        const restoredText = performRestore(responseText, storedReverseMap, requestId);
        
        if (restoredText !== responseText) {
          console.log(`✅ [${requestId}] 복원 성공!`);
          console.log(`📝 복원 전: "${responseText.substring(0, 100)}..."`);
          console.log(`📝 복원 후: "${restoredText.substring(0, 100)}..."`);
          responseText = restoredText;
        } else {
          console.log(`⚠️ [${requestId}] 복원할 내용 없음 (AI가 가명을 언급하지 않았을 수 있음)`);
        }
        
        // 매핑 정리
        STATE.activeMappings.delete(id20);
      } else {
        console.log(`❌ [${requestId}] 복원 불가 - reverse_map이 없음`);
      }

      // 7) 응답 기록
      logEntry.response.status = res.status;
      logEntry.response.headers = Object.fromEntries(res.headers.entries());
      logEntry.response.bodyText = responseText;
      logEntry.finalUrl = res.url || url;

      pushLog(logEntry);

      console.log(`🎉 [${requestId}] 요청 처리 완료`);

      return sendResponse({
        ok: true,
        status: res.status,
        headers: Object.fromEntries(res.headers.entries()),
        bodyText: responseText
      });
      
    } catch (e) {
      console.error(`❌ [${requestId}] 오류:`, e);
      logEntry.error = String(e?.message || e);
      pushLog(logEntry);
      return sendResponse({ ok: false, error: logEntry.error });
    }
  })();

  return true;
});

// ⭐⭐⭐ 핵심 복원 함수 ⭐⭐⭐
function performRestore(aiResponseText, reverseMap, requestId) {
  console.log(`🔄 [${requestId}] === 복원 함수 시작 ===`);
  console.log(`원본 AI 응답:`, aiResponseText);
  console.log(`사용할 reverse_map:`, reverseMap);

  if (!aiResponseText || !reverseMap) {
    console.log(`❌ [${requestId}] 복원 조건 불충족`);
    return aiResponseText;
  }

  let restoredText = aiResponseText;
  let totalChanges = 0;

  // reverse_map의 각 항목에 대해 복원 시도
  for (const [fakeValue, originalValue] of Object.entries(reverseMap)) {
    console.log(`🔍 [${requestId}] 처리 중: "${fakeValue}" → "${originalValue}"`);
    
    if (!fakeValue || !originalValue) {
      console.log(`❌ [${requestId}] 무효한 매핑 스킵`);
      continue;
    }
    
    // AI 응답에서 가명 찾기
    const countBefore = (restoredText.match(new RegExp(escapeRegex(fakeValue), 'g')) || []).length;
    console.log(`🔍 [${requestId}] "${fakeValue}" 출현 횟수: ${countBefore}`);
    
    if (countBefore > 0) {
      // 모든 출현을 원본으로 치환
      const beforeRestore = restoredText;
      restoredText = restoredText.split(fakeValue).join(originalValue);
      
      const countAfter = (restoredText.match(new RegExp(escapeRegex(fakeValue), 'g')) || []).length;
      const actualChanges = countBefore - countAfter;
      
      if (actualChanges > 0) {
        totalChanges += actualChanges;
        console.log(`✅ [${requestId}] 복원 성공: "${fakeValue}" → "${originalValue}" (${actualChanges}번 치환)`);
        console.log(`   치환 전: "${beforeRestore.substring(0, 100)}..."`);
        console.log(`   치환 후: "${restoredText.substring(0, 100)}..."`);
      } else {
        console.log(`❌ [${requestId}] 치환 실패`);
      }
    } else {
      console.log(`ℹ️ [${requestId}] AI 응답에서 "${fakeValue}"를 찾을 수 없음`);
    }
  }

  console.log(`🔄 [${requestId}] === 복원 함수 완료 ===`);
  console.log(`총 ${totalChanges}개 항목이 복원됨`);
  console.log(`최종 복원된 텍스트:`, restoredText);

  return restoredText;
}

// 정규식 이스케이프
function escapeRegex(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ===== 유틸 함수들 =====
function pushLog(entry) {
  try {
    STATE.reqLogs.push(entry);
    if (STATE.reqLogs.length > STATE.maxLogs) {
      STATE.reqLogs = STATE.reqLogs.slice(-STATE.maxLogs);
    }
  } catch (e) {
    console.warn('pushLog 실패', e);
  }
}

function cryptoRandomId() {
  if (crypto?.randomUUID) return crypto.randomUUID();
  return 'id-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function safePlainObj(o) {
  try { return JSON.parse(JSON.stringify(o || {})); } catch { return {}; }
}

async function makeId20(input) {
  try {
    const enc = new TextEncoder().encode(input);
    const buf = await crypto.subtle.digest('SHA-256', enc);
    const hex = [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2,'0')).join('');
    return hex.slice(0, 20);
  } catch {
    return Math.random().toString(36).slice(2).padEnd(20,'0').slice(0,20);
  }
}

// 서버 통신
async function postToLocalPseudonymize(prompt, id) {
  const payload = { prompt: String(prompt || ''), id: String(id || '') };
  
  const resp = await fetch('http://127.0.0.1:5000/pseudonymize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  
  const text = await resp.text();
  if (!resp.ok) {
    throw new Error(`pseudonymize HTTP ${resp.status}: ${text.slice(0,200)}`);
  }

  let obj = {};
  try { 
    obj = JSON.parse(text); 
  } catch { 
    obj = {};
  }
  
  return {
    masked_prompt: obj?.masked_prompt || obj?.pseudonymized_text || payload.prompt,
    reverse_map: obj?.reverse_map || {},
    mapping: obj?.mapping || []
  };
}

// 벤더별 어댑터
function extractTextForPseudonymization(url, body) {
  const u = new URL(url);

  // Anthropic v1/messages
  if (u.hostname.includes('anthropic.com')) {
    const msgs = body?.messages || [];
    const joined = msgs.map(m => m.content?.map?.(c => c.text || '').join('') || '').join('\n');
    return {
      joinedText: joined || JSON.stringify(body),
      adapter: {
        injectPseudonymized: (origBody, sanitized) => {
          const clone = structuredClone(origBody);
          if (clone.messages?.length) {
            const lastUser = [...clone.messages].reverse().find(m => m.role === 'user');
            if (lastUser) lastUser.content = [{ type: 'text', text: sanitized }];
          }
          return clone;
        }
      }
    };
  }

  // ChatGPT 웹앱 내부 API
  if (u.hostname.includes('chat.openai.com') || u.hostname.includes('chatgpt.com')) {
    const msgs = body?.messages || [];
    const joined = msgs
      .filter(m => m?.author?.role === 'user')
      .map(m => {
        const c = m?.content;
        if (!c) return '';
        if (c.content_type === 'text' && Array.isArray(c.parts)) return c.parts.join('\n');
        return typeof c === 'string' ? c : JSON.stringify(c);
      })
      .join('\n');

    return {
      joinedText: joined || JSON.stringify(body),
      adapter: {
        injectPseudonymized: (origBody, sanitized) => {
          const clone = structuredClone(origBody);
          const userMsg = (clone.messages || []).find(m => m?.author?.role === 'user');
          if (userMsg) userMsg.content = { content_type: 'text', parts: [sanitized] };
          return clone;
        }
      }
    };
  }

  // OpenAI chat.completions 등 일반
  const msgs = body?.messages || [];
  const joined = msgs.map(m => m.content || '').join('\n');
  return {
    joinedText: joined || JSON.stringify(body),
    adapter: {
      injectPseudonymized: (origBody, sanitized) => {
        const clone = structuredClone(origBody);
        if (clone.messages?.length) {
          const lastUserIdx = [...clone.messages].map(m=>m.role).lastIndexOf('user');
          if (lastUserIdx >= 0) clone.messages[lastUserIdx].content = sanitized;
        }
        return clone;
      }
    }
  };
}