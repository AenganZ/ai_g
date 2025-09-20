# Parsers for json
import json
import re
from typing import Optional, Dict, Any

def extract_first_json(s: str) -> Optional[Dict[str, Any]]:
    """문자열에서 첫 번째 유효한 JSON 객체 추출"""
    # 1. 완전한 JSON 블록 찾기 (중첩 괄호 고려)
    json_start = -1
    brace_count = 0
    for i, char in enumerate(s):
        if char == '{':
            if json_start == -1:
                json_start = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if json_start != -1 and brace_count == 0:
                json_candidate = s[json_start:i+1]
                try:
                    parsed = json.loads(json_candidate)
                    return parsed
                except json.JSONDecodeError:
                    json_start = -1
                    continue

    # 2. 정규식으로 JSON 블록 찾기
    json_pattern = re.compile(r'\{[^{}]*"entities"[^{}]*\[[^\]]*\][^{}]*\}', re.DOTALL)
    matches = json_pattern.findall(s)
    for match in matches:
        try:
            parsed = json.loads(match)
            return parsed
        except json.JSONDecodeError:
            continue

    # 3. entities 키워드 기반 검색
    entities_idx = s.find('"entities"')
    if entities_idx >= 0:
        start = s.rfind("{", 0, entities_idx)
        if start >= 0:
            brace_count = 0
            for i in range(start, len(s)):
                if s[i] == '{':
                    brace_count += 1
                elif s[i] == '}':
                    brace_count -= 1
                if brace_count == 0:
                    json_candidate = s[start:i+1]
                    try:
                        parsed = json.loads(json_candidate)
                        return parsed
                    except json.JSONDecodeError:
                        break

    # 4. 마지막 시도: 가장 간단한 매치
    simple_patterns = [
        r'\{"entities":\s*\[[^\]]*\]\}',
        r'\{[^}]*"entities"[^}]*\}',
    ]
    for pattern in simple_patterns:
        matches = re.findall(pattern, s, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match)
                return parsed
            except json.JSONDecodeError:
                continue

    return None