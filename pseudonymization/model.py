# Qwen model
import os
import json
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List, Dict, Any, Optional
from .normalizers import normalize_entities
from ..utils.parsers import extract_first_json

# 설정
MODEL_ID = os.getenv("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")

# 시스템 프롬프트
SYSTEM_PROMPT = """한국어 개인정보 추출기입니다. JSON으로만 응답하세요.
추출 대상: 이름, 나이, 전화번호, 이메일, 주소
출력 형식: {"entities": [{"name": "홍길동", "age": "25", "phone": "010-1234-5678", "email": "user@example.com", "address": "서울시"}]}
규칙:
- 이름: 한글 2-4자만
- 나이: 숫자만 ("25세" → "25")
- 전화번호: 010/011/016/017/018/019 시작
- 이메일: @포함된 주소
- 주소: 첫 번째 "시"까지만
- 없으면 null
- 추측 금지, 명확한 정보만"""

def pick_device_and_dtype():
    """최적의 디바이스와 데이터 타입을 선택"""
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    if torch.backends.mps.is_available():  # Apple Silicon
        return "mps", torch.float16
    return "cpu", torch.float32

def load_model():
    """Qwen 모델과 토크나이저를 로드"""
    device, torch_dtype = pick_device_and_dtype()
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    # 패딩 토큰 설정 (attention mask 경고 해결)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.unk_token if tokenizer.unk_token else "<|endoftext|>"
    # 패딩 토큰 ID 설정
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.unk_token_id if tokenizer.unk_token_id else tokenizer.eos_token_id

    # GPU 최적화된 모델 로딩
    if device == "cuda":
        torch.cuda.empty_cache()
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=torch_dtype,
            device_map="auto",
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )
    elif device == "mps":  # Apple Silicon
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=torch_dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        ).to(device)
    else:  # CPU
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype=torch_dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        ).to(device)
        torch.set_num_threads(4)

    model.eval()
    # GPU에서 추가 최적화 (torch.compile은 모델 로딩 후 적용)
    if device == "cuda" and hasattr(torch, 'compile'):
        try:
            model = torch.compile(model, mode="reduce-overhead")
        except Exception:
            pass
    
    return model, tokenizer, device

def generate_qwen_response(original_prompt: str, model, tokenizer, device) -> str:
    """Qwen 모델로 PII 추출 응답 생성 (순수 모델 추론)"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"[입력]\n{original_prompt}"}
    ]
    input_ids = tokenizer.apply_chat_template(
        messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
    ).to(device)

    # Attention mask 생성 (경고 해결)
    attention_mask = torch.ones_like(input_ids).to(device)

    with torch.no_grad():
        generation_kwargs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "max_new_tokens": 400,
            "temperature": 0.1,
            "top_p": 0.8,
            "do_sample": True,
            "eos_token_id": tokenizer.eos_token_id,
            "pad_token_id": tokenizer.pad_token_id,
            "use_cache": True,
        }
        if device == "cuda":
            generation_kwargs.update({
                "num_beams": 1,
                "repetition_penalty": 1.1,
                "length_penalty": 1.0,
            })
        out = model.generate(**generation_kwargs)
        return tokenizer.decode(out[0][input_ids.shape[-1]:], skip_special_tokens=True)

def call_qwen_detect_pii(original_prompt: str, model, tokenizer, device):
    """Qwen 모델을 사용하여 PII 탐지 (메인 인터페이스)"""
    try:
        # 1. 모델 추론
        decoded = generate_qwen_response(original_prompt, model, tokenizer, device)
        
        # 2. JSON 파싱
        parsed = extract_first_json(decoded.strip())
        if not parsed:
            return {"contains_pii": False, "items": [], "_error": "no_json_found"}

        entities_raw = parsed.get("entities", [])
        if not isinstance(entities_raw, list):
            entities_raw = []

        # 3. 정규화
        entities_norm = normalize_entities(entities_raw)

        # 4. 기존 형식으로 변환
        items = []
        for ent in entities_norm:
            for field_name, field_type in [("name", "이름"), ("age", "나이"),
                                           ("phone", "전화번호"), ("email", "이메일"),
                                           ("address", "주소")]:
                val = ent.get(field_name)
                if val:
                    items.append({
                        "type": field_type,
                        "value": val,
                        "start": 0,
                        "end": 0
                    })
        return {
            "contains_pii": bool(items),
            "items": items
        }
    except Exception as e:
        return {"contains_pii": False, "items": [], "_error": f"exception: {e}"}
