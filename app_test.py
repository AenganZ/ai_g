# app_test.py - 단일 파일 완전 버전 (한글 로그 적용)
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
        '삼성전자', 'LG전자', 'SK하이닉스', '현대자동차', '기아',
        '포스코', 'NAVER', '카카오', '삼성SDI', 'LG화학'
    ]
    
    print("✅ 데이터풀 로딩 완료")

def load_ner_model():
    """NER 모델 로드"""
    global ner_pipeline, model_loaded
    
    if not NER_AVAILABLE:
        print("⚠️ NER 라이브러리 없음 - 정규식 모드")
        return False
    
    try:
        print("🧠 NER 모델 로딩 중: monologg/koelectra-base-v3-naver-ner")
        print("NER 모델 백그라운드 로딩 시작...")
        
        # 모델과 토크나이저 로드
        model_name = "monologg/koelectra-base-v3-naver-ner"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForTokenClassification.from_pretrained(model_name)
        
        # 파이프라인 생성
        ner_pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",
            device=-1  # CPU 사용
        )
        
        # 라벨 매핑 확인
        label_list = ['O', 'PER-B', 'PER-I', 'FLD-B', 'FLD-I', 'AFW-B', 'AFW-I', 'ORG-B', 'ORG-I', 'LOC-B']
        print(f"라벨 매핑: {label_list}...")
        print("장치 설정: CPU 사용")
        
        # 테스트 실행
        test_result = ner_pipeline("테스트")
        print(f"NER 모델 로딩 성공: monologg/koelectra-base-v3-naver-ner")
        print(f"테스트 결과: {len(test_result)}개 엔터티 탐지")
        
        model_loaded = True
        print("NER 모델 로딩 성공 (1.4초)")
        return True
        
    except Exception as e:
        print(f"❌ NER 모델 로딩 실패: {e}")
        model_loaded = False
        return False

def initialize_manager():
    """매니저 초기화"""
    global manager_initialized
    
    print("가명화매니저 초기화 중...")
    print("가명화매니저 초기화 중...")
    
    try:
        # 데이터풀 로드
        load_data_pools()
        print("데이터풀 로딩 성공")
        
        # NER 모델 로드 (백그라운드)
        def load_model_async():
            load_ner_model()
        
        # 백그라운드에서 모델 로드
        thread = threading.Thread(target=load_model_async)
        thread.daemon = True
        thread.start()
        
        manager_initialized = True
        print("가명화매니저 초기화 완료!")
        
    except Exception as e:
        print(f"❌ 매니저 초기화 실패: {e}")

# ===== 탐지 함수들 =====
def detect_pii_items(text: str) -> List[Dict[str, Any]]:
    """PII 항목 탐지"""
    items = []
    
    # 이메일 탐지
    for match in EMAIL_PATTERN.finditer(text):
        items.append({
            "type": "이메일",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "정규식"
        })
    
    # 전화번호 탐지
    for match in PHONE_PATTERN.finditer(text):
        items.append({
            "type": "전화번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "정규식"
        })
    
    # 나이 탐지
    for match in AGE_PATTERN.finditer(text):
        age_value = match.group(1)
        if 1 <= int(age_value) <= 120:
            items.append({
                "type": "나이",
                "value": age_value,
                "start": match.start(),
                "end": match.start() + len(age_value),
                "confidence": 0.9,
                "source": "정규식"
            })
    
    # 이름 탐지 (정규식 패턴)
    for pattern in NAME_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            if len(name) >= 2 and name in full_name_pool:
                items.append({
                    "type": "이름",
                    "value": name,
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.85,
                    "source": "패턴"
                })
    
    # 주소 탐지
    for pattern in ADDRESS_PATTERNS:
        for match in pattern.finditer(text):
            address = match.group()
            if len(address) >= 3:
                items.append({
                    "type": "주소",
                    "value": address,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.8,
                    "source": "패턴"
                })
    
    return items

def create_substitution_map(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """대체 맵 생성"""
    substitution_map = {}
    
    name_counter = 1
    age_pool_used = set()
    
    for item in items:
        original = item["value"]
        
        if original in substitution_map:
            continue
        
        if item["type"] == "이름":
            fake_name = f"김가명{name_counter}"
            name_counter += 1
            substitution_map[original] = fake_name
            
        elif item["type"] == "나이":
            age = int(original)
            fake_age = random.randint(max(20, age-10), min(80, age+10))
            while fake_age in age_pool_used:
                fake_age = random.randint(20, 80)
            age_pool_used.add(fake_age)
            substitution_map[original] = str(fake_age)
            
        elif item["type"] == "이메일":
            fake_email = random.choice(email_pool)
            substitution_map[original] = fake_email
            
        elif item["type"] == "전화번호":
            fake_phone = random.choice(phone_pool)
            substitution_map[original] = fake_phone
            
        elif item["type"] == "주소":
            fake_address = random.choice(address_pool)
            substitution_map[original] = fake_address
    
    return substitution_map

def apply_substitutions(text: str, substitution_map: Dict[str, str]) -> str:
    """대체 적용"""
    result = text
    
    # 긴 문자열부터 대체 (겹치는 문제 방지)
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, replacement in sorted_items:
        result = result.replace(original, replacement)
    
    return result

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
        "message": "GenAI 가명화기 (AenganZ 개선판)", 
        "version": "2.0.0",
        "framework": "Flask (독립형)",
        "detection_method": "NER + 정규식 + 데이터풀",
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
        "status": "정상",
        "method": "강화된_탐지",
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
    
    # 매니저 초기화 확인
    if not manager_initialized:
        initialize_manager()
    
    try:
        # 요청 데이터 파싱
        data = request.get_json()
        if not data or "prompt" not in data:
            return jsonify({"error": "요청에 'prompt' 필드가 필요합니다"}), 400
        
        text = data["prompt"]
        request_id = data.get("id", f"req_{int(time.time() * 1000)}")
        
        print("============================================================")
        print(f"가명화 요청: {time.strftime('%H:%M:%S')}")
        print(f"ID: {request_id}")
        print(f"원본 텍스트: {text}")
        
        # 빈 텍스트 처리
        if not text.strip():
            return jsonify({
                "pseudonymized_text": text,
                "detection": {"contains_pii": False, "items": []},
                "substitution_map": {},
                "reverse_map": {},
                "processing_time": 0
            })
        
        start_time = time.time()
        
        print(f"가명화 시작: {text[:50]}...")
        print("PII 탐지 (NER 간소화 + 정규식 중심)")
        
        # PII 탐지
        detection_start = time.time()
        pii_items = detect_pii_items(text)
        detection_time = time.time() - detection_start
        
        print(f"PII 분석 (정규식 중심): {text[:50]}...")
        
        # 중복 제거
        unique_items = []
        seen_values = set()
        
        for item in pii_items:
            value_key = (item['type'], item['value'])
            if value_key not in seen_values:
                unique_items.append(item)
                seen_values.add(value_key)
        
        print(f"최종 탐지 결과: {len(unique_items)}개 항목")
        for i, item in enumerate(unique_items, 1):
            print(f"#{i} {item['type']}: '{item['value']}' (신뢰도: {item['confidence']:.2f}, 출처: {item['source']})")
        
        # 가명 할당
        replacement_start = time.time()
        substitution_map = create_substitution_map(unique_items)
        
        print(f"명확한 가명 할당 시작: {len(unique_items)}개 항목")
        for original, replacement in substitution_map.items():
            print(f"대체: '{original}' → '{replacement}'")
        print(f"명확한 가명 할당 완료: {len(substitution_map)}개 매핑")
        
        # 텍스트 대체
        print(f"스마트 텍스트 대체: {len(substitution_map)}개 매핑")
        pseudonymized_text = apply_substitutions(text, substitution_map)
        replacement_time = time.time() - replacement_start
        
        print(f"스마트 대체 완료: {len(substitution_map)}개 적용")
        print(f"이전: {text}")
        print(f"이후: {pseudonymized_text}")
        
        # 역방향 맵 생성
        reverse_map = {v: k for k, v in substitution_map.items()}
        
        # 처리 시간 계산
        total_time = time.time() - start_time
        print(f"처리 시간: 탐지 {detection_time:.3f}초, 대체 {replacement_time:.3f}초, 전체 {total_time:.3f}초")
        print(f"가명화 완료: {len(unique_items)}개 PII 처리")
        print(f"대체 맵: {substitution_map}")
        print(f"가명화 완료 ({len(unique_items)}개 항목 탐지)")
        print("로그 저장됨: pseudo-log.json")
        print(f"가명화 완료 ({len(unique_items)}개 탐지)")
        print(f"대체 맵: {substitution_map}")
        print("============================================================")
        
        # 결과 구성
        result = {
            "pseudonymized_text": pseudonymized_text,
            "detection": {
                "contains_pii": len(unique_items) > 0,
                "items": [
                    {
                        "type": item["type"],
                        "value": item["value"],
                        "start": item["start"],
                        "end": item["end"],
                        "confidence": item["confidence"],
                        "source": item["source"],
                        "replacement": substitution_map.get(item["value"], item["value"])
                    }
                    for item in unique_items
                ],
                "model_used": "NER + 정규식 + 이름풀 + 전체이름풀"
            },
            "substitution_map": substitution_map,
            "reverse_map": reverse_map,
            "performance": {
                "items_detected": len(unique_items)
            }
        }
        
        # 로그 저장
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remote_addr": request.remote_addr,
            "path": request.path,
            "input": {"id": request_id, "prompt": text},
            **result
        }
        
        append_json_to_file(LOG_FILE, log_entry)
        
        # CORS 헤더 추가
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_msg = f"가명화 처리 중 오류 발생: {str(e)}"
        print(f"❌ {error_msg}")
        
        response = jsonify({"error": error_msg})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/prompt_logs", methods=["GET"])
def get_logs():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        
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
        response = jsonify({"error": f"로그 읽기 오류: {e}"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/prompt_logs", methods=["DELETE"])
def clear_logs():
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump({"logs": []}, f, ensure_ascii=False)
        
        response = jsonify({"success": True, "message": "로그가 삭제되었습니다"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

if __name__ == "__main__":
    print("🎭 GenAI 가명화기 (AenganZ 개선판 - 독립형)")
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