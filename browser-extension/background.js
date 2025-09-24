// background.js - Future-Challenge 방식 기반 (복원 로직 강화)

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
    
    console.log(`🚀🚀🚀 [${requestId}] 요청 시작 🚀🚀🚀`);
    
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
      console.log(`📝 [${requestId}] 추출된 프롬프트: "${joinedText.substring(0, 100)}..."`);

      // 2) 서버에 가명화 요청
      const id20 = await makeId20(joinedText + '|' + startedAt);
      console.log(`🔄 [${requestId}] 서버 가명화 요청 시작... ID: ${id20}`);
      
      const pseudoResult = await postToLocalPseudonymize(joinedText || '', id20);
      
      console.log(`📝📝📝 [${requestId}] 가명화 결과 상세:`, {
        masked_prompt: pseudoResult.masked_prompt.substring(0, 100) + "...",
        reverse_map_size: Object.keys(pseudoResult.reverse_map || {}).length,
        reverse_map_full: pseudoResult.reverse_map
      });

      // 3) ⭐⭐⭐ reverse_map 저장 (복원용) - 핵심! ⭐⭐⭐
      const reverseMap = pseudoResult.reverse_map || {};
      console.log(`🔑🔑🔑 [${requestId}] reverse_map 완전 상세:`, reverseMap);
      
      if (Object.keys(reverseMap).length > 0) {
        STATE.activeMappings.set(id20, reverseMap);
        console.log(`✅✅✅ [${requestId}] reverse_map 저장 완료 [${id20}]:`, reverseMap);
        console.log(`🗂️ [${requestId}] 현재 저장된 mappings:`, Array.from(STATE.activeMappings.entries()));
      } else {
        console.log(`❌❌❌ [${requestId}] reverse_map이 비어있음!`);
      }

      // 4) AI 서비스로 가명화된 요청 전송
      const modBody = adapter.injectPseudonymized(reqBody, pseudoResult.masked_prompt);
      const bodyOut = JSON.stringify(modBody);

      console.log(`🤖 [${requestId}] AI 서비스로 전송:`, {
        url: url,
        masked_prompt_preview: pseudoResult.masked_prompt.substring(0, 100) + "..."
      });

      // 5) AI 서비스 응답 수신
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2분

      const res = await fetch(url, { 
        method, 
        headers, 
        body: bodyOut,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      let responseText = await res.text();

      console.log(`📨📨📨 [${requestId}] AI 응답 수신:`, {
        status: res.status,
        response_preview: responseText.substring(0, 200) + '...',
        response_length: responseText.length
      });

      // 6) ⭐⭐⭐ 핵심: AI 응답 복원 (강화된 로직) ⭐⭐⭐
      const storedReverseMap = STATE.activeMappings.get(id20);
      console.log(`🔍🔍🔍 [${requestId}] 복원 준비:`, {
        id20: id20,
        has_stored_map: !!storedReverseMap,
        stored_map_keys: storedReverseMap ? Object.keys(storedReverseMap) : [],
        stored_map_full: storedReverseMap,
        all_stored_mappings: Array.from(STATE.activeMappings.keys()),
        original_response_preview: responseText.substring(0, 200) + '...'
      });
      
      if (storedReverseMap && Object.keys(storedReverseMap).length > 0) {
        console.log(`🔄🔄🔄 [${requestId}] 복원 실행 시작...`);
        
        const restoredText = performRestore(responseText, storedReverseMap, requestId);
        
        if (restoredText !== responseText) {
          console.log(`✅✅✅ [${requestId}] 복원 성공!`);
          console.log(`📝 복원 전: "${responseText.substring(0, 200)}..."`);
          console.log(`📝 복원 후: "${restoredText.substring(0, 200)}..."`);
          responseText = restoredText;
        } else {
          console.log(`⚠️⚠️⚠️ [${requestId}] 복원할 내용이 없었음 (AI가 가명을 언급하지 않았을 수 있음)`);
        }
        
        // 매핑 정리
        STATE.activeMappings.delete(id20);
        console.log(`🗑️ [${requestId}] 매핑 정리 완료`);
      } else {
        console.log(`❌❌❌ [${requestId}] 복원 불가:`, {
          reason: !storedReverseMap ? "reverse_map이 없음" : "reverse_map이 비어있음",
          id20: id20,
          available_mappings: Array.from(STATE.activeMappings.keys())
        });
      }

      // 7) 응답 기록
      logEntry.response.status = res.status;
      logEntry.response.headers = Object.fromEntries(res.headers.entries());
      logEntry.response.bodyText = responseText;
      logEntry.finalUrl = res.url || url;

      pushLog(logEntry);

      console.log(`🎉🎉🎉 [${requestId}] 요청 처리 완료`);

      return sendResponse({
        ok: true,
        status: res.status,
        headers: Object.fromEntries(res.headers.entries()),
        bodyText: responseText,
        reverseMapFromBackground: storedReverseMap // ⭐ reverse_map 전달
      });
      
    } catch (e) {
      console.error(`❌❌❌ [${requestId}] 오류:`, e);
      
      if (e.name === 'AbortError') {
        console.error(`⏰⏰⏰ [${requestId}] 타임아웃 발생 (2분 초과)`);
        logEntry.error = 'Request timeout (2 minutes)';
      } else {
        logEntry.error = String(e?.message || e);
      }
      
      pushLog(logEntry);
      return sendResponse({ ok: false, error: logEntry.error });
    }
  })();

  return true;
});

// ⭐⭐⭐ 강화된 복원 함수 (Unicode 문제 해결) ⭐⭐⭐
function performRestore(aiResponseText, reverseMap, requestId) {
  console.log(`🔄🔄🔄 [${requestId}] === 강화된 복원 함수 시작 ===`);
  console.log(`원본 AI 응답 길이: ${aiResponseText.length}`);
  console.log(`원본 AI 응답 내용: "${aiResponseText.substring(0, 500)}..."`);
  console.log(`사용할 reverse_map:`, reverseMap);

  if (!aiResponseText || !reverseMap) {
    console.log(`❌ [${requestId}] 복원 조건 불충족:`, {
      has_response: !!aiResponseText,
      has_reverse_map: !!reverseMap
    });
    return aiResponseText;
  }

  let restoredText = aiResponseText;
  let totalChanges = 0;

  // ⭐ 길이 순으로 정렬 (긴 것부터 복원 - 중요!)
  const sortedMappings = Object.entries(reverseMap).sort((a, b) => b[0].length - a[0].length);
  console.log(`📋 [${requestId}] 정렬된 매핑 목록:`, sortedMappings);

  // reverse_map의 각 항목에 대해 복원 시도
  for (const [fakeValue, originalValue] of sortedMappings) {
    console.log(`🔍🔍🔍 [${requestId}] 처리 중: "${fakeValue}" → "${originalValue}"`);
    
    if (!fakeValue || !originalValue) {
      console.log(`❌ [${requestId}] 무효한 매핑 스킵:`, { fakeValue, originalValue });
      continue;
    }
    
    // ⭐ Unicode 정규화 및 여러 방법으로 복원 시도
    const normalizedFake = normalizeUnicodeString(fakeValue);
    const normalizedOriginal = normalizeUnicodeString(originalValue);
    
    console.log(`🔤 [${requestId}] Unicode 정규화:`, {
      original_fake: fakeValue,
      normalized_fake: normalizedFake,
      original_original: originalValue,
      normalized_original: normalizedOriginal
    });
    
    // ⭐ 여러 방법으로 복원 시도
    let hasReplacements = false;
    const beforeRestore = restoredText;
    
    // 방법 1: 원본 문자열로 직접 치환
    if (restoredText.includes(fakeValue)) {
      restoredText = replaceAll(restoredText, fakeValue, originalValue);
      hasReplacements = true;
      console.log(`✅ [${requestId}] 방법1(직접) 치환: "${fakeValue}" → "${originalValue}"`);
    }
    
    // 방법 2: 정규화된 문자열로 치환
    if (normalizedFake !== fakeValue && restoredText.includes(normalizedFake)) {
      restoredText = replaceAll(restoredText, normalizedFake, normalizedOriginal);
      hasReplacements = true;
      console.log(`✅ [${requestId}] 방법2(정규화) 치환: "${normalizedFake}" → "${normalizedOriginal}"`);
    }
    
    // 방법 3: Unicode 이스케이프 형태로 치환
    const escapedFake = escapeUnicode(fakeValue);
    if (restoredText.includes(escapedFake)) {
      restoredText = replaceAll(restoredText, escapedFake, originalValue);
      hasReplacements = true;
      console.log(`✅ [${requestId}] 방법3(Unicode이스케이프) 치환: "${escapedFake}" → "${originalValue}"`);
    }
    
    // 방법 4: JSON 이스케이프 해제 후 치환
    try {
      const jsonUnescaped = JSON.parse('"' + fakeValue.replace(/"/g, '\\"') + '"');
      if (jsonUnescaped !== fakeValue && restoredText.includes(jsonUnescaped)) {
        restoredText = replaceAll(restoredText, jsonUnescaped, originalValue);
        hasReplacements = true;
        console.log(`✅ [${requestId}] 방법4(JSON언이스케이프) 치환: "${jsonUnescaped}" → "${originalValue}"`);
      }
    } catch (e) {
      // JSON 파싱 실패는 무시
    }
    
    // 방법 5: 정규식 기반 치환 (단어 경계)
    try {
      const regex = new RegExp(escapeRegex(fakeValue), 'g');
      const regexResult = restoredText.replace(regex, originalValue);
      if (regexResult !== restoredText) {
        restoredText = regexResult;
        hasReplacements = true;
        console.log(`✅ [${requestId}] 방법5(정규식) 치환: "${fakeValue}" → "${originalValue}"`);
      }
    } catch (e) {
      console.log(`⚠️ [${requestId}] 정규식 오류:`, e);
    }
    
    // 실제 변경 확인
    if (hasReplacements && beforeRestore !== restoredText) {
      totalChanges += 1;
      console.log(`✅✅✅ [${requestId}] 복원 성공: "${fakeValue}" → "${originalValue}"`);
      console.log(`   치환 전: "${beforeRestore.substring(0, 100)}..."`);
      console.log(`   치환 후: "${restoredText.substring(0, 100)}..."`);
    } else if (!hasReplacements) {
      console.log(`ℹ️ [${requestId}] AI 응답에서 "${fakeValue}"를 찾을 수 없음`);
      
      // ⭐ 디버깅: AI 응답에서 비슷한 문자열 찾기
      const similar = findSimilarStrings(restoredText, fakeValue);
      if (similar.length > 0) {
        console.log(`🔍 [${requestId}] 비슷한 문자열들:`, similar);
      }
      
      // ⭐ 디버깅: Unicode 분석
      console.log(`🔤 [${requestId}] Unicode 분석:`, {
        fake_chars: Array.from(fakeValue).map(c => c.charCodeAt(0).toString(16)),
        response_includes_unicode: restoredText.includes('\\u'),
        response_sample: restoredText.substring(0, 200)
      });
    }
  }

  console.log(`🔄🔄🔄 [${requestId}] === 강화된 복원 함수 완료 ===`);
  console.log(`총 ${totalChanges}개 항목이 복원됨`);
  console.log(`최종 복원된 텍스트 길이: ${restoredText.length}`);

  return restoredText;
}

// ⭐ Unicode 처리 보조 함수들
function normalizeUnicodeString(str) {
  if (typeof str !== 'string') return str;
  
  // Unicode 정규화 (NFC)
  if (str.normalize) {
    return str.normalize('NFC');
  }
  return str;
}

function escapeUnicode(str) {
  return str.replace(/[\u0080-\uFFFF]/g, function(match) {
    return '\\u' + ('0000' + match.charCodeAt(0).toString(16)).substr(-4);
  });
}

function unescapeUnicode(str) {
  return str.replace(/\\u[\dA-F]{4}/gi, function(match) {
    return String.fromCharCode(parseInt(match.replace(/\\u/g, ''), 16));
  });
}

// ⭐ 보조 함수들 (복원 정확도 향상)

function countOccurrences(text, searchString) {
  return (text.split(searchString).length - 1);
}

function countOccurrencesRegex(text, searchString) {
  try {
    const regex = new RegExp(escapeRegex(searchString), 'g');
    return (text.match(regex) || []).length;
  } catch (e) {
    return 0;
  }
}

function countOccurrencesIgnoreSpaces(text, searchString) {
  const textNoSpaces = text.replace(/\s+/g, '');
  const searchNoSpaces = searchString.replace(/\s+/g, '');
  return countOccurrences(textNoSpaces, searchNoSpaces);
}

function replaceAll(text, searchValue, replaceValue) {
  return text.split(searchValue).join(replaceValue);
}

function replaceIgnoreSpaces(text, searchValue, replaceValue) {
  // 공백을 무시하고 치환 (한국어 텍스트에 유용)
  const searchPattern = searchValue.split('').join('\\s*');
  const regex = new RegExp(searchPattern, 'g');
  return text.replace(regex, replaceValue);
}

function findSimilarStrings(text, target) {
  const words = text.match(/[가-힣]+/g) || [];
  return words.filter(word => 
    word.length >= 2 && 
    (word.includes(target) || target.includes(word) || 
     levenshteinDistance(word, target) <= 1)
  ).slice(0, 5);
}

function levenshteinDistance(str1, str2) {
  const matrix = [];
  for (let i = 0; i <= str2.length; i++) {
    matrix[i] = [i];
  }
  for (let j = 0; j <= str1.length; j++) {
    matrix[0][j] = j;
  }
  for (let i = 1; i <= str2.length; i++) {
    for (let j = 1; j <= str1.length; j++) {
      if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1,
          matrix[i][j - 1] + 1,
          matrix[i - 1][j] + 1
        );
      }
    }
  }
  return matrix[str2.length][str1.length];
}

// 정규식 이스케이프 (기존)
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

// 서버 통신 (디버깅 강화)
async function postToLocalPseudonymize(prompt, id) {
  const payload = { prompt: String(prompt || ''), id: String(id || '') };
  
  console.log(`🌐🌐🌐 서버 요청 시작:`, { 
    prompt: prompt.substring(0, 50) + '...', 
    id,
    prompt_length: prompt.length 
  });
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30초 타임아웃
  
  try {
    const resp = await fetch('http://127.0.0.1:5000/pseudonymize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    const text = await resp.text();
    console.log(`🌐🌐🌐 서버 응답 수신:`, { 
      status: resp.status, 
      responseLength: text.length,
      response_preview: text.substring(0, 200) + '...'
    });
    
    if (!resp.ok) {
      throw new Error(`pseudonymize HTTP ${resp.status}: ${text.slice(0,200)}`);
    }

    let obj = {};
    try { 
      obj = JSON.parse(text); 
      console.log(`📊📊📊 서버 응답 파싱 성공:`, { 
        masked_prompt_length: (obj?.masked_prompt || '').length,
        reverse_map_keys: Object.keys(obj?.reverse_map || {}),
        reverse_map_size: Object.keys(obj?.reverse_map || {}).length,
        reverse_map_full: obj?.reverse_map,
        success: obj?.success
      });
    } catch (parseError) { 
      console.error(`❌ 서버 응답 파싱 실패:`, parseError);
      console.error(`원본 응답 텍스트:`, text);
      obj = {};
    }
    
    const result = {
      masked_prompt: obj?.masked_prompt || obj?.pseudonymized_text || payload.prompt,
      reverse_map: obj?.reverse_map || {},
      mapping: obj?.mapping || []
    };
    
    console.log(`🎯 최종 결과:`, result);
    return result;
    
  } catch (e) {
    clearTimeout(timeoutId);
    if (e.name === 'AbortError') {
      console.error(`⏰ 서버 요청 타임아웃 (30초)`);
      throw new Error('서버 요청 타임아웃');
    } else {
      console.error(`❌ 서버 통신 오류:`, e);
      throw e;
    }
  }
}

// 벤더별 어댑터 (기존 유지)
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