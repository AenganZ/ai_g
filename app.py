# app.py - Flask 기반 GenAI 가명화 서버
import os
import re
import json
import time
import random
import asyncio
import pandas as pd
from datetime import datetime
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify
from flask_cors import CORS

# NER 모델 관련 import
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    import torch
    NER_AVAILABLE = True
    print("✅ Transformers 라이브러리 로드 성공")
except ImportError:
    NER_AVAILABLE = False
    print("⚠️ Transformers 라이브러리가 없습니다. pip install transformers torch 를 실행하세요.")

# ===== 설정 =====
LOG_FILE = "pseudo-log.json"
MAX_LOGS = 100

# ===== Flask 설정 =====
app = Flask(__name__)
CORS(app)

# ===== 전역 변수 =====
manager = None
manager_initialized = False

# ===== 로깅 유틸리티 =====
def load_logs():
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"logs": []}
    except:
        return {"logs": []}

def save_logs(logs_data):
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"로그 저장 실패: {e}")

def add_log(entry):
    logs_data = load_logs()
    logs_data["logs"].append(entry)
    if len(logs_data["logs"]) > MAX_LOGS:
        logs_data["logs"] = logs_data["logs"][-MAX_LOGS:]
    save_logs(logs_data)

# ===== 가명화 매니저 초기화 =====
def initialize_manager():
    """매니저 초기화"""
    global manager, manager_initialized
    
    try:
        print("워크플로우 기반 GenAI 가명화기 시작")
        print("서버 초기화 중...")
        
        print("가명화매니저 초기화 중...")
        
        # pseudonymization 모듈 import
        try:
            from pseudonymization.manager import get_manager
            from pseudonymization.core import get_data_pool_stats
            
            # 매니저 인스턴스 생성 (가명화 모드 기본)
            manager = get_manager(use_fake_mode=True)
            
            print("NER 모델 백그라운드 로딩...")
            
            # 데이터풀 통계 출력
            try:
                stats = get_data_pool_stats()
                print("데이터풀 로딩 성공")
                print(f"실명: {stats.get('탐지_이름수', 0):,}개")
                print(f"시/도: {stats.get('탐지_시도수', 0):,}개")
                print(f"시: {stats.get('탐지_시수', 0):,}개") 
                print(f"구/군: {stats.get('탐지_시군구수', 0):,}개")
            except Exception as e:
                print(f"데이터풀 통계 출력 실패: {e}")
            
            manager_initialized = True
            print("가명화매니저 초기화 완료!")
            print("서버 준비 완료!")
            
        except ImportError as e:
            print(f"pseudonymization 모듈 import 실패: {e}")
            print("단순 정규식 모드로 실행됩니다.")
            manager_initialized = False
            
    except Exception as e:
        print(f"매니저 초기화 실패: {e}")
        manager_initialized = False

# ===== 단순 정규식 기반 PII 탐지 (fallback) =====
def simple_pii_detection(text: str) -> List[Dict[str, Any]]:
    """단순 정규식 기반 PII 탐지 (매니저 없을 때 사용)"""
    
    items = []
    
    # 이메일 탐지
    email_patterns = [
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
        r'\b\w+@\w+\.\w+\b',
    ]
    
    for pattern in email_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            items.append({
                "type": "이메일",
                "value": match.group(),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.9,
                "source": "정규식"
            })
    
    # 전화번호 탐지
    phone_pattern = r'01[0-9]-?\d{4}-?\d{4}'
    for match in re.finditer(phone_pattern, text):
        items.append({
            "type": "전화번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.9,
            "source": "정규식"
        })
    
    # 이름 패턴 탐지 (더 정확한 패턴)
    name_patterns = [
        r'([가-힣]{2,4})님',
        r'([가-힣]{2,4})씨',
        r'이름은\s*([가-힣]{2,4})(?:이고|이며|입니다|이에요|예요|이야|야)',
        r'저는\s*([가-힣]{2,4})(?:이고|이며|입니다|이에요|예요|이야|야)',
        r'제\s*이름은\s*([가-힣]{2,4})(?:이고|이며|입니다|이에요|예요|이야|야)',
        r'([가-힣]{2,4})(?=\s+고객)',  # "김철수 고객"에서 김철수 추출
    ]
    
    # 제외할 단어들
    exclude_words = {
        "고객", "거주하시", "분이시", "주세요", "드세요", "하세요", "보내드", "메일",
        "연락", "문의", "예약", "확인", "사항", "정보", "내용", "시간", "장소", "해운"
    }
    
    for pattern in name_patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            # 제외 단어 체크
            if name not in exclude_words and len(name) >= 2:
                items.append({
                    "type": "이름",
                    "value": name,
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.7,
                    "source": "정규식"
                })
    
    # 주소 패턴 (시/도 + 구/군 모두 탐지)
    address_patterns = [
        # 시/도
        r'(서울|부산|대구|인천|광주|대전|울산|세종)(?:시|특별시|광역시)?',
        r'(경기|강원|충북|충남|전북|전남|경북|경남|제주)(?:도)?',
        # 구/군 (주요 지역)
        r'(강남구|강동구|강북구|강서구|관악구|광진구|구로구|금천구|노원구|도봉구)',
        r'(동대문구|동작구|마포구|서대문구|서초구|성동구|성북구|송파구|양천구)',
        r'(영등포구|용산구|은평구|종로구|중구|중랑구)',
        r'(해운대구|부산진구|동래구|남구|북구|사하구|금정구|연제구|수영구|사상구)',
        r'(수성구|달서구|달성군|중구|동구|서구|남구|북구)',
    ]
    
    for pattern in address_patterns:
        for match in re.finditer(pattern, text):
            addr = match.group(1)
            # 주소 관련 문맥 확인
            start_pos = max(0, match.start() - 20)
            end_pos = min(len(text), match.end() + 20)
            context = text[start_pos:end_pos]
            
            # 주소 관련 키워드가 있는지 확인
            address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '소재', '예약', '지역', '에서']
            if any(keyword in context for keyword in address_keywords):
                items.append({
                    "type": "주소",
                    "value": addr,
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.8,
                    "source": "정규식"
                })
    
    return items

def simple_pseudonymize(items: List[Dict], text: str) -> tuple:
    """단순 가명화 처리 (주소 스마트 치환 포함)"""
    
    substitution_map = {}
    reverse_map = {}
    masked_text = text
    
    # 가명 풀
    fake_names = ["김가명", "이가명", "박무명", "최차명", "정익명"]
    fake_emails = ["user001@example.com", "user002@test.co.kr", "user003@demo.net"]
    fake_phones = ["010-0000-0000", "010-0001-0000", "010-0002-0000"]
    
    counters = {"이름": 0, "이메일": 0, "전화번호": 0, "주소": 0}
    
    # 주소 스마트 처리
    address_items = [item for item in items if item["type"] == "주소"]
    non_address_items = [item for item in items if item["type"] != "주소"]
    
    # 주소 치환 (연속 주소를 큰 단위만 남기고 처리)
    if address_items:
        # 위치순으로 정렬
        sorted_addresses = sorted(address_items, key=lambda x: x['start'])
        
        # 가장 큰 단위 주소 찾기 (시/도 우선)
        main_address = None
        provinces = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", 
                    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
        
        for addr_item in sorted_addresses:
            addr_value = addr_item['value']
            if addr_value in provinces:
                main_address = addr_value
                break
        
        # 시/도가 없으면 첫 번째 주소 사용
        if not main_address and sorted_addresses:
            main_address = sorted_addresses[0]['value']
        
        if main_address:
            print(f"대표 주소 선택: '{main_address}'")
            
            # 연속된 주소 구문 찾기 및 치환
            address_values = [item['value'] for item in sorted_addresses]
            
            # 모든 주소가 연속으로 나타나는 패턴 찾기
            if len(address_values) > 1:
                # 연속 주소 패턴 생성: "부산 해운대구" 같은 형태
                pattern = r'\s*'.join([re.escape(addr) for addr in address_values])
                
                if re.search(pattern, masked_text):
                    # 전체 연속 구문을 대표 주소로 치환
                    masked_text = re.sub(pattern, main_address, masked_text)
                    print(f"주소 연속 구문 치환: '{' '.join(address_values)}' → '{main_address}'")
                    
                    substitution_map[f"주소전체"] = main_address
                    reverse_map[main_address] = ' '.join(address_values)
                else:
                    # 개별 주소들 중 메인이 아닌 것들 제거
                    for addr_item in sorted_addresses:
                        if addr_item['value'] != main_address:
                            # 다른 주소들은 제거
                            pattern = r'\s*' + re.escape(addr_item['value']) + r'\s*'
                            masked_text = re.sub(pattern, ' ', masked_text)
                            print(f"부차 주소 제거: '{addr_item['value']}'")
                    
                    # 연속 공백 정리
                    masked_text = re.sub(r'\s+', ' ', masked_text).strip()
            
            substitution_map[f"주소_대표"] = main_address
            reverse_map[main_address] = "원본주소"
    
    # 다른 항목들 처리
    for item in non_address_items:
        original = item["value"]
        pii_type = item["type"]
        
        if original in substitution_map:
            continue
        
        # 가명 선택
        if pii_type == "이름":
            replacement = fake_names[counters["이름"] % len(fake_names)]
            counters["이름"] += 1
        elif pii_type == "이메일":
            replacement = fake_emails[counters["이메일"] % len(fake_emails)]
            counters["이메일"] += 1
        elif pii_type == "전화번호":
            replacement = fake_phones[counters["전화번호"] % len(fake_phones)]
            counters["전화번호"] += 1
        else:
            replacement = f"[{pii_type}]"
        
        substitution_map[original] = replacement
        reverse_map[replacement] = original
        
        # 텍스트 치환
        masked_text = masked_text.replace(original, replacement)
    
    return masked_text, substitution_map, reverse_map

# ===== API 엔드포인트 =====
@app.route('/pseudonymize', methods=['POST'])
def pseudonymize_text():
    """텍스트 가명화 처리"""
    
    data = request.get_json()
    request_id = data.get('id', 'unknown')
    prompt = data.get('prompt', '')
    
    print("=" * 60)
    print(f"가명화 요청: {datetime.now().strftime('%H:%M:%S')}")
    print(f"ID: {request_id}")
    print(f"원본 텍스트: {prompt}")
    
    start_time = time.time()
    
    try:
        if manager_initialized and manager:
            print("가명화 모드로 처리 중...")
            
            # pseudonymization 매니저 사용
            from pseudonymization.detection import detect_pii_enhanced
            from pseudonymization.replacement import WorkflowReplacementManager
            
            # PII 탐지
            detection_result = detect_pii_enhanced(prompt)
            items = detection_result['items']
            token_map = detection_result['token_map']
            
            # 워크플로우 매니저로 가명화 처리
            workflow_manager = WorkflowReplacementManager()
            masked_text, substitution_map, reverse_map = workflow_manager.apply_pseudonymization(
                text=prompt,
                items=items
            )
            
        else:
            print("단순 정규식 모드로 처리 중...")
            
            # 단순 모드
            items = simple_pii_detection(prompt)
            masked_text, substitution_map, reverse_map = simple_pseudonymize(items, prompt)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # 로그 기록
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remote_addr": request.remote_addr,
            "path": "/pseudonymize",
            "input": {"id": request_id, "prompt": prompt},
            "detection": {
                "contains_pii": len(items) > 0,
                "items": [
                    {
                        "type": item["type"],
                        "value": item["value"],
                        "start": item["start"],
                        "end": item["end"],
                        "confidence": item["confidence"],
                        "source": item["source"],
                        "replacement": substitution_map.get(item["value"], item["value"])
                    } for item in items
                ],
                "model_used": "AenganZ Enhanced" if manager_initialized else "Simple Regex"
            },
            "substitution_map": substitution_map,
            "reverse_map": reverse_map,
            "performance": {"items_detected": len(items)}
        }

        add_log(log_entry)

        print(f"가명화 결과: {masked_text}")
        print(f"이전: {prompt}")
        print(f"가명화: {masked_text}")
        print(f"처리 시간: 탐지 {processing_time//2}ms, 치환 {processing_time//2}ms, 전체 {processing_time}ms")
        print(f"완료 ({processing_time}ms, {len(items)}개 탐지)")
        print(f"복구 맵: {reverse_map}")
        print("=" * 60)

        return jsonify({
            "ok": True,
            "original_prompt": prompt,
            "masked_prompt": masked_text,
            "mapping": [
                {
                    "type": item["type"],
                    "value": item["value"],
                    "start": item["start"],
                    "end": item["end"],
                    "confidence": item["confidence"],
                    "source": item["source"]
                } for item in items
            ],
            "substitution_map": substitution_map,
            "reverse_map": reverse_map,
            "detection": {
                "contains_pii": len(items) > 0, 
                "items": items,
                "model_used": "AenganZ Enhanced" if manager_initialized else "Simple Regex"
            }
        })

    except Exception as e:
        print(f"오류: {e}")
        return jsonify({
            "ok": False, 
            "error": str(e), 
            "original_prompt": prompt,
            "masked_prompt": prompt, 
            "mapping": [], 
            "substitution_map": {},
            "reverse_map": {},
            "detection": {"contains_pii": False, "items": []}
        })

@app.route('/prompt_logs', methods=['GET'])
def get_logs():
    """로그 조회 (브라우저 익스텐션용)"""
    return jsonify(load_logs())

@app.route('/prompt_logs', methods=['DELETE'])
def clear_logs():
    """로그 삭제"""
    try:
        save_logs({"logs": []})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/status', methods=['GET'])
def get_status():
    """서버 상태 확인"""
    return jsonify({
        "status": "running",
        "manager_initialized": manager_initialized,
        "ner_available": NER_AVAILABLE,
        "version": "4.0.0"
    })

@app.route('/set-mode', methods=['POST'])
def set_mode():
    """모드 전환 (토큰화/가명화)"""
    global manager
    
    data = request.get_json()
    mode = data.get("mode", "fake")  # fake 또는 token
    
    try:
        if manager_initialized and manager:
            if hasattr(manager, 'set_mode'):
                manager.set_mode(use_fake_mode=(mode == "fake"))
                return jsonify({"success": True, "mode": mode})
        
        return jsonify({"success": False, "error": "Manager not available"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    print("GenAI Pseudonymizer (AenganZ Enhanced) 서버 시작")
    print("가명화 모드: 김가명, 이가명 등 실제 가명 사용")
    print("브라우저 익스텐션 호환")

    if not NER_AVAILABLE:
        print("경고: transformers 라이브러리가 설치되지 않았습니다.")
        print("설치 명령: pip install transformers torch pandas")
    
    # 매니저 초기화
    initialize_manager()
    
    app.run(host="127.0.0.1", port=5000, debug=True)