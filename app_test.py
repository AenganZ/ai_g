# app_standalone.py - 단일 파일 완전 버전 (Windows 호환)
import os
import re
import json
import time
import random
import asyncio
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify
from flask_cors import CORS

# NER 모델 관련 import (선택적)
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    import torch
    import pandas as pd
    NER_AVAILABLE = True
    print("✅ Transformers 라이브러리 로드 성공")
except ImportError:
    NER_AVAILABLE = False
    print("⚠️ Transformers 라이브러리가 없습니다. 기본 탐지 모드로 실행됩니다.")

# ===== 설정 =====
LOG_FILE = "pseudo-log.json"
MAX_LOGS = 100

# ===== Flask 설정 =====
app = Flask(__name__)
CORS(app)

# ===== 전역 변수 =====
name_pool = []
full_name_pool = []
fake_name_pool = []
email_pool = []
phone_pool = []
address_pool = []
company_pool = []

ner_pipeline = None
model_loaded = False
manager_initialized = False

# ===== 로깅 유틸리티 =====
def append_json_to_file(path: str, new_entry: Dict[str, Any]) -> None:
    """JSON 엔트리를 로그 파일에 추가"""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"logs": []}
    except:
        data = {"logs": []}
    
    if "logs" not in data or not isinstance(data["logs"], list):
        data["logs"] = []
    
    data["logs"].append(new_entry)
    
    # 로그 개수 제한
    if len(data["logs"]) > MAX_LOGS:
        data["logs"] = data["logs"][-MAX_LOGS:]
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== 정규식 패턴 =====
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'010[-\s]?\d{4}[-\s]?\d{4}')
AGE_PATTERN = re.compile(r'\b(\d{1,2})\s*(?:세|살)\b')

# 강화된 이름 패턴
NAME_PATTERNS = [
    re.compile(r'이름은\s*([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})\s*입니다'),
    re.compile(r'저는\s*([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})(?:이에요|예요|이야|야)'),
    re.compile(r'([가-힣]{2,4})(?:입니다|이다)'),
    re.compile(r'안녕하세요,?\s*(?:저는\s*)?([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})이고'),
    re.compile(r'([가-힣]{2,4})이며'),
    re.compile(r'([가-힣]{2,4})라고\s*합니다'),
    re.compile(r'([가-힣]{2,4})라고\s*해요'),
    re.compile(r'([가-힣]{2,4})(?:님|씨)'),
]

# 주소 패턴
ADDRESS_PATTERNS = [
    re.compile(r'[가-힣]+(?:시|도|구|군)\s+[가-힣\s\d,-]+(?:동|로|가|번지|층|호)'),
    re.compile(r'[가-힣]+(?:시|도|구|군)'),
]

# ===== 데이터풀 로드 =====
def load_data_pools():
    """모든 데이터풀 초기화"""
    global name_pool, full_name_pool, fake_name_pool
    global email_pool, phone_pool, address_pool, company_pool
    
    print("📂 데이터풀 로딩 중...")
    
    # 이름풀 로드 (name.csv가 있으면 사용, 없으면 기본값)
    try:
        if os.path.exists('name.csv') and NER_AVAILABLE:
            import pandas as pd
            df = pd.read_csv('name.csv', encoding='utf-8')
            name_pool = df['이름'].tolist()[:1000]  # 최대 1000개
            print(f"✅ name.csv에서 {len(name_pool)}개 이름 로드")
        else:
            name_pool = [
                '민준', '서준', '도윤', '예준', '시우', '주원', '하준', '지호',
                '지후', '준우', '현우', '준서', '도현', '지훈', '건우', '우진',
                '서윤', '지우', '서현', '하은', '예은', '윤서', '지민', '채원'
            ]
            print(f"✅ 기본 이름풀 사용: {len(name_pool)}개")
    except Exception as e:
        print(f"❌ 이름풀 로드 실패: {e}")
        name_pool = ['민준', '서준', '지우', '서현']
    
    # 한국 성씨
    surnames = [
        '김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
        '한', '오', '서', '신', '권', '황', '안', '송', '류', '전'
    ]
    
    # 성+이름 조합 생성
    full_name_pool = []
    for surname in surnames:
        for name in name_pool[:50]:  # 메모리 절약
            full_name_pool.append(surname + name)
    
    # 가명 이름 풀 생성
    fake_words = ['가명', '익명', '무명', '차명', '별명', '테스트', '샘플', '더미']
    fake_name_pool = [surname + fake_word for surname in surnames for fake_word in fake_words]
    
    # 이메일풀
    email_domains = ['gmail.com', 'naver.com', 'daum.net', 'kakao.com']
    email_prefixes = ['user', 'test', 'hello', 'work', 'info', 'office']
    email_pool = []
    for i in range(100):
        prefix = random.choice(email_prefixes) + str(i + 1000)
        domain = random.choice(email_domains)
        email_pool.append(f"{prefix}@{domain}")
    
    # 전화번호풀
    phone_pool = [f"010-{i//100:04d}-{i%100:04d}" for i in range(1000, 2000)]
    
    # 주소풀
    address_pool = [
        '서울시 강남구', '서울시 서초구', '서울시 송파구', '서울시 강동구',
        '서울시 마포구', '서울시 용산구', '부산시 해운대구', '부산시 부산진구',
        '대구시 중구', '대구시 동구', '인천시 남동구', '인천시 부평구',
        '경기도 수원시', '경기도 성남시', '대전시 서구', '광주시 서구'
    ]
    
    # 회사풀
    company_pool = [
        '삼성전자', 'LG전자', 'SK하이닉스', '현대자동차', 'KIA', '포스코',
        '넷마블', '카카오', '네이버', '쿠팡', '배달의민족', '토스'
    ]
    
    print(f"✅ 데이터풀 로드 완료")
    print(f"   📛 이름: {len(name_pool)}개")
    print(f"   👤 성+이름: {len(full_name_pool)}개")
    print(f"   🎭 가명이름: {len(fake_name_pool)}개")

def load_ner_model():
    """NER 모델 로드 (백그라운드)"""
    global ner_pipeline, model_loaded
    
    if not NER_AVAILABLE:
        print("❌ NER 모델을 로드할 수 없습니다 - transformers 라이브러리가 필요합니다")
        return False
    
    try:
        print("🔄 NER 모델 로딩 중... (monologg/koelectra-base-v3-naver-ner)")
        
        model_name = "monologg/koelectra-base-v3-naver-ner"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        
        ner_pipeline = pipeline(
            "ner", 
            model=model, 
            tokenizer=tokenizer,
            aggregation_strategy="simple",
            device=0 if torch.cuda.is_available() else -1
        )
        
        model_loaded = True
        print("✅ NER 모델 로드 완료!")
        return True
        
    except Exception as e:
        print(f"❌ NER 모델 로드 실패: {e}")
        model_loaded = False
        return False

def map_ner_label_to_pii_type(label: str) -> Optional[str]:
    """NER 라벨을 PII 타입으로 매핑"""
    mapping = {
        'PER': '이름',
        'PERSON': '이름',
        'LOC': '주소',
        'LOCATION': '주소',
        'ORG': '회사',
        'ORGANIZATION': '회사'
    }
    return mapping.get(label)

def detect_pii_enhanced(text: str) -> List[Dict[str, Any]]:
    """강화된 PII 탐지 (동기 버전)"""
    items = []
    
    print(f"🔍 PII 분석: {text[:50]}...")
    
    # 1. NER 모델 사용 (사용 가능한 경우)
    if model_loaded and ner_pipeline:
        try:
            ner_results = ner_pipeline(text)
            
            for entity in ner_results:
                entity_type = entity['entity_group']
                entity_text = entity['word']
                confidence = entity['score']
                start = entity['start']
                end = entity['end']
                
                if confidence > 0.7:
                    pii_type = map_ner_label_to_pii_type(entity_type)
                    if pii_type:
                        items.append({
                            "type": pii_type,
                            "value": entity_text,
                            "start": start,
                            "end": end,
                            "confidence": confidence,
                            "source": "NER"
                        })
        except Exception as e:
            print(f"❌ NER 모델 실행 오류: {e}")
    
    # 2. 정규식 기반 탐지
    # 이메일
    for match in EMAIL_PATTERN.finditer(text):
        items.append({
            "type": "이메일",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex"
        })
    
    # 전화번호
    for match in PHONE_PATTERN.finditer(text):
        items.append({
            "type": "전화번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex"
        })
    
    # 나이
    for match in AGE_PATTERN.finditer(text):
        items.append({
            "type": "나이",
            "value": match.group(1),
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.9,
            "source": "Regex"
        })
    
    # 이름 패턴
    for pattern in NAME_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            if len(name) >= 2 and len(name) <= 4:
                items.append({
                    "type": "이름",
                    "value": name,
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.75,
                    "source": "Pattern"
                })
    
    # 주소 패턴
    for pattern in ADDRESS_PATTERNS:
        for match in pattern.finditer(text):
            items.append({
                "type": "주소",
                "value": match.group(),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.9,
                "source": "Regex"
            })
    
    # 3. 데이터풀 기반 탐지
    if full_name_pool:
        for full_name in full_name_pool[:500]:  # 성능을 위해 제한
            if full_name in text:
                start_idx = text.find(full_name)
                items.append({
                    "type": "이름",
                    "value": full_name,
                    "start": start_idx,
                    "end": start_idx + len(full_name),
                    "confidence": 0.8,
                    "source": "FullNamePool"
                })
    
    # 중복 제거
    unique_items = []
    seen = set()
    for item in sorted(items, key=lambda x: x['start']):
        key = (item['type'], item['value'], item['start'])
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    
    return unique_items

def assign_realistic_values(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """실제 데이터풀에서 대체값 할당"""
    substitution_map = {}
    
    for item in items:
        pii_type = item['type']
        original_value = item['value']
        
        if original_value in substitution_map:
            continue
        
        if pii_type == "이름":
            replacement = random.choice(fake_name_pool) if fake_name_pool else "김가명"
        elif pii_type == "이메일":
            replacement = random.choice(email_pool) if email_pool else "test@example.com"
        elif pii_type == "전화번호":
            replacement = random.choice(phone_pool) if phone_pool else "010-0000-0000"
        elif pii_type == "주소":
            replacement = random.choice(address_pool) if address_pool else "서울시 강남구"
        elif pii_type == "회사":
            replacement = random.choice(company_pool) if company_pool else "테스트회사"
        elif pii_type == "나이":
            replacement = str(random.randint(20, 65))
        else:
            replacement = f"[{pii_type.upper()}_MASKED]"
        
        substitution_map[original_value] = replacement
        item['replacement'] = replacement
    
    return substitution_map

def create_masked_text(original_text: str, items: List[Dict[str, Any]]) -> str:
    """마스킹된 텍스트 생성"""
    replacements = [(item['value'], item.get('replacement', 'MASKED')) 
                   for item in items if item['value']]
    
    # 긴 것부터 치환 (부분 매칭 방지)
    replacements.sort(key=lambda x: len(x[0]), reverse=True)
    
    masked_text = original_text
    for original, replacement in replacements:
        masked_text = masked_text.replace(original, replacement)
    
    return masked_text

def pseudonymize_text(original_prompt: str) -> Dict[str, Any]:
    """메인 가명화 함수"""
    try:
        items = detect_pii_enhanced(original_prompt)
        substitution_map = assign_realistic_values(items)
        reverse_map = {v: k for k, v in substitution_map.items()}
        masked_prompt = create_masked_text(original_prompt, items)
        
        detection = {
            "contains_pii": len(items) > 0,
            "items": items,
            "model_used": "NER + Regex + NamePool + FullNamePool" if model_loaded else "Regex + NamePool + FullNamePool"
        }
        
        return {
            "masked_prompt": masked_prompt,
            "detection": detection,
            "substitution_map": substitution_map,
            "reverse_map": reverse_map
        }
    
    except Exception as e:
        print(f"❌ 가명화 처리 오류: {e}")
        return {
            "masked_prompt": original_prompt,
            "detection": {"contains_pii": False, "items": []},
            "substitution_map": {},
            "reverse_map": {}
        }

def initialize_manager():
    """매니저 초기화"""
    global manager_initialized
    
    if manager_initialized:
        return
    
    print("🚀 PseudonymizationManager 초기화 중...")
    
    # 데이터풀 로드
    load_data_pools()
    
    # NER 모델 백그라운드 로드
    if NER_AVAILABLE:
        threading.Thread(target=load_ner_model, daemon=True).start()
    
    manager_initialized = True
    print("✅ PseudonymizationManager 초기화 완료!")

# ===== Flask 라우트 =====
@app.route("/", methods=["GET", "OPTIONS"])
def root():
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    # 매니저 초기화
    if not manager_initialized:
        initialize_manager()
    
    return jsonify({
        "message": "GenAI Pseudonymizer (AenganZ Enhanced)", 
        "version": "2.0.0",
        "framework": "Flask (Standalone)",
        "detection_method": "NER + Regex + DataPools",
        "ner_model_loaded": model_loaded,
        "data_pools": {
            "names": len(name_pool),
            "full_names": len(full_name_pool),
            "fake_names": len(fake_name_pool),
            "emails": len(email_pool)
        },
        "timestamp": datetime.now().isoformat()
    })

@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    return jsonify({
        "status": "ok",
        "method": "enhanced_detection",
        "ready": manager_initialized,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/pseudonymize", methods=["POST", "OPTIONS"])
def pseudonymize():
    # CORS preflight 요청 처리
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

    # 매니저 초기화
    if not manager_initialized:
        initialize_manager()

    # JSON 파싱
    try:
        data = request.get_json(force=True, silent=False)
    except Exception as e:
        response = jsonify(ok=False, error=f"invalid_json: {e}")
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 400

    if not isinstance(data, dict):
        response = jsonify(ok=False, error="payload_must_be_object")
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 400

    original_prompt = data.get("prompt", "")
    req_id = data.get("id", "")

    if not original_prompt.strip():
        response = jsonify(ok=False, error="empty_prompt")
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 400

    print(f"\n" + "="*60)
    print(f"🔍 가명화 요청: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🆔 ID: {req_id}")
    print(f"📄 원문: {original_prompt}")

    try:
        # 가명화 처리
        result = pseudonymize_text(original_prompt)
        
        masked_prompt = result["masked_prompt"]
        detection = result["detection"]
        substitution_map = result.get("substitution_map", {})
        reverse_map = result.get("reverse_map", {})

        # 로그 저장
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remote_addr": request.remote_addr,
            "path": request.path,
            "input": {
                "id": req_id,
                "prompt": original_prompt
            },
            "detection": detection,
            "substitution_map": substitution_map,
            "reverse_map": reverse_map,
            "performance": {
                "items_detected": len(detection.get("items", []))
            }
        }
        append_json_to_file(LOG_FILE, log_entry)

        print(f"✅ 가명화 완료 ({len(detection.get('items', []))}개 탐지)")
        print(f"🔄 대체 맵: {substitution_map}")
        print("="*60)

        # 응답 생성
        response_data = {
            "ok": True,
            "original_prompt": original_prompt,
            "masked_prompt": masked_prompt,
            "detection": detection,
            "substitution_map": substitution_map,
            "reverse_map": reverse_map,
            "mapping": detection.get("items", [])
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        print(f"❌ 가명화 오류: {e}")
        import traceback
        traceback.print_exc()
        
        error_response = {
            "ok": False,
            "error": str(e),
            "original_prompt": original_prompt,
            "masked_prompt": original_prompt,
            "detection": {"contains_pii": False, "items": []},
            "substitution_map": {},
            "reverse_map": {},
            "mapping": []
        }
        
        response = jsonify(error_response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/prompt_logs", methods=["GET", "OPTIONS"])
def prompt_logs():
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        json.loads(raw)  # 유효성 검사
        
        response = app.response_class(
            response=raw,
            status=200,
            mimetype="application/json; charset=utf-8"
        )
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except FileNotFoundError:
        empty = {"logs": []}
        response = app.response_class(
            response=json.dumps(empty, ensure_ascii=False),
            status=200,
            mimetype="application/json; charset=utf-8"
        )
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({"error": f"log_read_error: {e}"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/prompt_logs", methods=["DELETE"])
def clear_logs():
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump({"logs": []}, f, ensure_ascii=False)
        
        response = jsonify({"success": True, "message": "Logs cleared"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

if __name__ == "__main__":
    print("🎭 GenAI Pseudonymizer (AenganZ Enhanced - Standalone)")
    print("🔧 프레임워크: Flask (단일 파일 버전)")
    print("🧠 탐지 방식: NER + 정규식 + 데이터풀")
    print("📛 가명화: 실제 데이터 대체")
    print("🔄 복원: 양방향 매핑")
    print("🌐 서버 시작 중...")
    
    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 서버 종료")
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        import traceback
        traceback.print_exc()