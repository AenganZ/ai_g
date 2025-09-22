// background.js - 응답 복원 기능 추가
const STATE = {
  reqLogs: [],
  maxLogs: 200,
  mappingStore: new Map() // ID별 매핑 저장
};

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.kind) return;
  if (msg.kind !== 'PII_PROXY_FETCH' && msg.kind !== 'PII_PROXY_XHR') {
    return sendResponse({ ok: false });
  }

  (async () => {
    const startedAt = new Date().toISOString();
    const logEntry = {
      id: cryptoRandomId(),
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

      // 1) 본문 파싱 & 프롬프트 추출
      let reqBody;
      try { reqBody = bodyText ? JSON.parse(bodyText) : {}; } catch { reqBody = {}; }
      const { joinedText, adapter } = extractTextForPseudonymization(url, reqBody);

      // 2) 서버에 가명화 요청
      const id20 = await makeId20(joinedText + '|' + startedAt);
      const pseudoResponse = await postToLocalPseudonymize(joinedText || '', id20);
      const masked_prompt = pseudoResponse.masked_prompt;
      const mapping = pseudoResponse.mapping || {};

      // 매핑 저장 (응답 복원용)
      STATE.mappingStore.set(id20, mapping);
      
      // 3) 목적지로 전송할 본문 구성(가명화된 prompt 주입)
      const modBody = adapter.injectPseudonymized(reqBody, masked_prompt);
      const bodyOut = JSON.stringify(modBody);

      // 4) 실제 목적지 호출
      const res = await fetch(url, { method, headers, body: bodyOut });
      let responseText = await res.text();

      // 5) 응답 복원 - 가명화된 내용을 원본으로 되돌리기
      if (mapping && Object.keys(mapping).length > 0) {
        for (const [original, fake] of Object.entries(mapping)) {
          // 가명화된 값이 응답에 있으면 원본으로 복원
          const regex = new RegExp(escapeRegex(fake), 'g');
          responseText = responseText.replace(regex, original);
        }
        console.log(`[PII] 응답 복원 완료: ${Object.keys(mapping).length}개 항목`);
      }

      // 매핑 정리 (메모리 절약)
      STATE.mappingStore.delete(id20);

      // 응답 기록
      logEntry.response.status = res.status;
      logEntry.response.headers = Object.fromEntries(res.headers.entries());
      logEntry.response.bodyText = responseText;
      logEntry.finalUrl = res.url || url;
      logEntry.restored = Object.keys(mapping).length > 0;

      pushLog(logEntry);

      return sendResponse({
        ok: true,
        status: res.status,
        headers: Object.fromEntries(res.headers.entries()),
        bodyText: responseText // 복원된 응답 텍스트
      });
    } catch (e) {
      console.error('[PII] 오류:', e);
      logEntry.error = String(e?.message || e);
      pushLog(logEntry);
      return sendResponse({ ok: false, error: logEntry.error });
    }
  })();

  return true;
});

// 정규식 특수문자 이스케이프
function escapeRegex(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function pushLog(entry) {
  try {
    STATE.reqLogs.push(entry);
    if (STATE.reqLogs.length > STATE.maxLogs) {
      STATE.reqLogs = STATE.reqLogs.slice(-STATE.maxLogs);
    }
  } catch (e) {
    console.warn('pushLog failed', e);
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

// 서버로 프롬프트 전송 → 가명화 응답 수신
async function postToLocalPseudonymize(prompt, id) {
  const payload = { prompt: String(prompt || ''), id: String(id || '') };
  const resp = await fetch('http://127.0.0.1:5000/pseudonymize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const text = await resp.text();
  if (!resp.ok) throw new Error(`pseudonymize HTTP ${resp.status}: ${text.slice(0,200)}`);

  let obj = {};
  try { obj = JSON.parse(text); } catch { obj = {}; }
  return {
    masked_prompt: obj?.masked_prompt || obj?.pseudonymized_text || prompt,
    mapping: obj?.mapping || {}
  };
}

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