# core 
from typing import List, Tuple, Dict, Any
from .model import call_qwen_detect_pii
from .pools import pick_token

# PII 타입 정의
PII_TYPES = ["이름", "전화번호", "주소", "나이", "이메일"]

def replace_many(text: str, replacements: List[Tuple[str, str]]) -> str:
    """여러 문자열을 동시에 치환 (긴 것부터)"""
    out = text
    for orig, repl in sorted(replacements, key=lambda x: len(x[0]) if x[0] else 0, reverse=True):
        if not orig:
            continue
        out = out.replace(orig, repl)
    return out

def build_masked_prompt(original: str, items: List[Dict[str, Any]]) -> str:
    """Qwen 탐지 items를 기반으로 original을 토큰으로 가명화"""
    if not items:
        return original
    
    # 각 item에 token 채우기
    for it in items:
        token_type = it.get("type")
        it["token"] = pick_token(token_type) if token_type in PII_TYPES else "MASKED"

    text = original
    # 타입별로 매핑하여 치환
    replacements = []
    for it in items:
        val = it.get("value", "")
        tok = it.get("token", "MASKED")
        if val and tok:
            replacements.append((val, tok))
    
    # 치환 실행
    text = replace_many(text, replacements)
    return text

def pseudonymize_text(original_prompt: str, model, tokenizer, device) -> Dict[str, Any]:
    """텍스트를 가명화하는 메인 함수"""
    # Qwen 모델로 PII 탐지
    detection = call_qwen_detect_pii(original_prompt, model, tokenizer, device)
    
    # 토큰 기반 가명화
    items = detection.get("items", [])
    masked_prompt = build_masked_prompt(original_prompt, items)
    
    # detection.items에 token이 들어가도록 이미 build_masked_prompt에서 채움
    detection["items"] = items
    detection["contains_pii"] = bool(items)
    
    return {
        "masked_prompt": masked_prompt,
        "detection": detection
    }
