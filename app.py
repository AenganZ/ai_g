# app.py - 모듈화된 Flask 서버 (이모티콘 제거, 실제 가명 치환)
import os
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Any

from flask import Flask, request, jsonify
from flask_cors import CORS

# 모듈화된 pseudonymization 패키지 import (오류 시 종료)
from pseudonymization import (
    get_manager, 
    pseudonymize_text_with_fake,
    is_manager_ready,
    get_data_pool_stats,
    initialize_pools
)
print("Pseudonymization 모듈 로드 성공")

# ===== 설정 =====
LOG_FILE = "pseudo-log.json"
MAX_LOGS = 100

# ===== Flask 설정 =====
app = Flask(__name__)
CORS(app)

# ===== 전역 변수 =====
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
    global manager_initialized
    if not manager_initialized:
        try:
            print("가명화매니저 초기화 중...")
            initialize_pools()
            manager = get_manager()
            manager_initialized = True
            print("가명화매니저 초기화 완료")
        except Exception as e:
            print(f"매니저 초기화 실패: {e}")
            return jsonify({"error": f"매니저 초기화 실패: {e}"}), 500
    
    try:
        stats = get_data_pool_stats()
    except Exception as e:
        stats = {"error": f"통계 정보 로드 실패: {e}"}
    
    return jsonify({
        "service": "GenAI Pseudonymizer (AenganZ Enhanced)",
        "version": "4.0.0",
        "status": "running",
        "manager_ready": manager_initialized,
        "features": {
            "modular_design": True,
            "real_names_mode": True,
            "enhanced_filtering": True,
            "email_detection": True,
            "smart_address": True,
            "ner_model": "KPF/KPF-bert-ner"
        },
        "stats": stats
    })

@app.route("/pseudonymize", methods=["POST", "OPTIONS"])
def pseudonymize():
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    try:
        data = request.get_json()
        if not data or "prompt" not in data:
            response = jsonify({"error": "prompt 필드가 필요합니다"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        text = data["prompt"]
        request_id = data.get("id", f"req_{int(time.time())}")
        
        start_time = time.time()
        
        print(f"가명화 요청: {datetime.now().strftime('%H:%M:%S')}")
        print(f"ID: {request_id}")
        print(f"원본 텍스트: {text}")
        
        if not manager_initialized:
            # 매니저 초기화 시도
            try:
                print("가명화매니저 초기화 중...")
                initialize_pools()
                manager = get_manager()
                globals()["manager_initialized"] = True
                print("가명화매니저 초기화 완료")
            except Exception as e:
                print(f"매니저 초기화 실패: {e}")
                response = jsonify({"error": f"매니저 초기화 실패: {e}"})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 500
        
        print("가명화 모드로 처리 중...")
        
        # 비동기 가명화 처리 (asyncio.run 사용)
        result = asyncio.run(pseudonymize_text_with_fake(text))
        
        pseudonymized_text = result.get("pseudonymized_text", text)
        detected_items = result.get("detected_items", 0)
        detection_details = result.get("detection", {})
        
        processing_time = time.time() - start_time
        
        print(f"이전: {text}")
        print(f"가명화: {pseudonymized_text}")
        print(f"처리 시간: {processing_time:.3f}초")
        print(f"완료 ({detected_items}개 항목 탐지)")
        print("=" * 60)
        
        # 로그 저장 (브라우저 익스텐션 호환 형식)
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remote_addr": request.remote_addr,
            "path": "/pseudonymize",
            "input": {
                "id": request_id,
                "prompt": text
            },
            "output": {
                "pseudonymized_text": pseudonymized_text,
                "detection": detection_details,
                "processing_time": processing_time
            },
            "items": detection_details.get("items", []),
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "type": "pseudonymize",
            "request_id": request_id,
            "original_text": text,
            "detected_items": detected_items,
            "mode": "modular"
        }
        add_log(log_entry)
        
        response_data = {
            "pseudonymized_text": pseudonymized_text,
            "detection": detection_details,
            "processing_time": processing_time,
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "mode": "modular",
            # 브라우저 익스텐션 호환을 위한 추가 필드들
            "mapping": [
                {
                    "original": item.get("value", ""),
                    "type": item.get("type", ""),
                    "source": item.get("source", "")
                }
                for item in detection_details.get("items", [])
            ],
            "id": request_id,
            "detected_count": detected_items
        }
        
        response = jsonify(response_data)
        # 브라우저 익스텐션 호환을 위한 강화된 CORS 헤더
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        response = jsonify({
            "error": f"처리 중 오류 발생: {str(e)}",
            "success": False,
            "timestamp": datetime.now().isoformat()
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/restore", methods=["POST", "OPTIONS"])
def restore():
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    try:
        data = request.get_json()
        pseudonymized_text = data.get('pseudonymized_text', '')
        reverse_map = data.get('reverse_map', {})
        
        if not pseudonymized_text or not reverse_map:
            response = jsonify({"error": "pseudonymized_text와 reverse_map 필드가 필요합니다"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        start_time = time.time()
        
        # 간단한 복원 (역방향 치환)
        restored_text = pseudonymized_text
        for fake, original in reverse_map.items():
            restored_text = restored_text.replace(fake, original)
        
        processing_time = time.time() - start_time
        
        response_data = {
            "restored_text": restored_text,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        response = jsonify({
            "error": f"복원 처리 중 오류 발생: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
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

@app.route("/health", methods=["GET"])
def health():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "manager_ready": manager_initialized,
        "version": "4.0.0"
    }
    
    response = jsonify(health_status)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == "__main__":
    print("GenAI Pseudonymizer (AenganZ Enhanced) 서버 시작")
    print("가명화 모드: 김가명, 이가명 등 실제 가명 사용")
    print("전화번호: 010-0000-0000부터 1씩 증가")
    print("주소: 시/도만 표시")
    print("이메일: user001@example.com 형태")
    print("NER 모델: KPF/KPF-bert-ner")
    print("서버 시작 중...")
    
    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("서버 종료")
    except Exception as e:
        print(f"서버 시작 실패: {e}")
        import traceback
        traceback.print_exc()