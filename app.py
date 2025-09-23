# app.py - 모듈화된 Flask 서버 (강화된 디버깅 버전)
import os
import json
import time
import asyncio
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

# 필요한 pseudonymization 함수들만 import
from pseudonymization import (
    get_manager, 
    pseudonymize_text_with_fake,
    get_data_pool_stats,
    initialize_pools
)
print("Pseudonymization 모듈 로드 성공")

# 설정
LOG_FILE = "pseudo-log.json"
MAX_LOGS = 100

# Flask 설정
app = Flask(__name__)
CORS(app)

# 전역 변수
manager_initialized = False

# 디버깅 헬퍼
def debug_log(message, data=None):
    print(f"🔧 [SERVER-DEBUG] {message}")
    if data:
        print(f"   데이터: {data}")

def debug_error(message, error=None):
    print(f"❌ [SERVER-ERROR] {message}")
    if error:
        print(f"   오류: {error}")

# 로깅 유틸리티
def load_logs():
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"logs": []}
    except Exception as e:
        debug_error("로그 로드 실패", e)
        return {"logs": []}

def save_logs(logs_data):
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        debug_error("로그 저장 실패", e)

def add_log(entry):
    logs_data = load_logs()
    logs_data["logs"].append(entry)
    if len(logs_data["logs"]) > MAX_LOGS:
        logs_data["logs"] = logs_data["logs"][-MAX_LOGS:]
    save_logs(logs_data)

# Flask 라우트
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
            debug_log("매니저 초기화 시작")
            initialize_pools()
            manager = get_manager()
            manager_initialized = True
            debug_log("매니저 초기화 완료")
        except Exception as e:
            debug_error("매니저 초기화 실패", e)
            return jsonify({"error": f"매니저 초기화 실패: {e}"}), 500
    
    try:
        stats = get_data_pool_stats()
        debug_log("통계 정보 로드 완료", stats)
    except Exception as e:
        debug_error("통계 정보 로드 실패", e)
        stats = {"error": f"통계 정보 로드 실패: {e}"}
    
    return jsonify({
        "service": "GenAI Pseudonymizer (AenganZ Enhanced)",
        "version": "4.0.1",
        "status": "running",
        "manager_ready": manager_initialized,
        "features": {
            "modular_design": True,
            "real_names_mode": True,
            "enhanced_filtering": True,
            "email_detection": True,
            "smart_address": True,
            "ner_model": "KPF/KPF-bert-ner",
            "reverse_restoration": True,
            "enhanced_debugging": True  # 강화된 디버깅 활성화
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
    
    request_start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or "prompt" not in data:
            debug_error("잘못된 요청 - prompt 필드 누락", data)
            response = jsonify({"error": "prompt 필드가 필요합니다"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        text = data["prompt"]
        request_id = data.get("id", f"req_{int(time.time())}")
        
        debug_log(f"가명화 요청 시작 [{request_id}]", {
            "prompt": text[:100] + "..." if len(text) > 100 else text,
            "prompt_length": len(text),
            "request_ip": request.remote_addr
        })
        
        start_time = time.time()
        
        if not manager_initialized:
            try:
                debug_log("매니저 즉시 초기화 시작")
                initialize_pools()
                manager = get_manager()
                globals()["manager_initialized"] = True
                debug_log("매니저 즉시 초기화 완료")
            except Exception as e:
                debug_error("매니저 초기화 실패", e)
                response = jsonify({"error": f"매니저 초기화 실패: {e}"})
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 500
        
        # 비동기 가명화 처리
        debug_log(f"pseudonymize_text_with_fake 호출 시작 [{request_id}]")
        result = asyncio.run(pseudonymize_text_with_fake(text))
        debug_log(f"pseudonymize_text_with_fake 호출 완료 [{request_id}]")
        
        pseudonymized_text = result.get("pseudonymized_text", text)
        detected_items = result.get("detected_items", 0)
        detection_details = result.get("detection", {})
        mapping = result.get("mapping", [])
        reverse_map = result.get("reverse_map", {})
        
        processing_time = time.time() - start_time
        
        debug_log(f"가명화 처리 완료 [{request_id}]", {
            "original_text": text[:50] + "..." if len(text) > 50 else text,
            "pseudonymized_text": pseudonymized_text[:50] + "..." if len(pseudonymized_text) > 50 else pseudonymized_text,
            "detected_items": detected_items,
            "reverse_map": reverse_map,
            "reverse_map_size": len(reverse_map),
            "processing_time": processing_time
        })
        
        # ⭐ reverse_map 검증 및 보장
        if detected_items > 0 and not reverse_map:
            debug_error(f"경고: PII가 탐지되었지만 reverse_map이 비어있음 [{request_id}]", {
                "detected_items": detected_items,
                "mapping": mapping[:3]  # 처음 3개만 로그
            })
            
            # mapping에서 reverse_map 재구성 시도
            reconstructed_reverse_map = {}
            for item in mapping:
                token = item.get("token", "")
                original = item.get("original", "")
                if token and original and token != original:
                    reconstructed_reverse_map[token] = original
            
            if reconstructed_reverse_map:
                reverse_map = reconstructed_reverse_map
                debug_log(f"reverse_map 재구성 완료 [{request_id}]", reverse_map)
            else:
                debug_error(f"reverse_map 재구성 실패 [{request_id}]")
        
        # 최종 검증
        debug_log(f"최종 응답 준비 [{request_id}]", {
            "pseudonymized_length": len(pseudonymized_text),
            "reverse_map_entries": len(reverse_map),
            "mapping_entries": len(mapping),
            "has_pii": detected_items > 0,
            "final_reverse_map": reverse_map
        })
        
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
                "processing_time": processing_time,
                "reverse_map": reverse_map
            },
            "detection": {
                "items": [
                    {
                        "type": item.get("type", ""),
                        "value": item.get("value", ""),
                        "token": item.get("token", ""),
                        "source": item.get("source", ""),
                        "start": 0,
                        "end": 0
                    }
                    for item in mapping
                ],
                "count": detected_items,
                "contains_pii": detected_items > 0
            },
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "type": "pseudonymize",
            "request_id": request_id,
            "original_text": text,
            "detected_items": detected_items,
            "mode": "modular_enhanced",
            "total_processing_time": time.time() - request_start_time
        }
        add_log(log_entry)
        
        # ⭐ 브라우저 익스텐션 호환 응답 형식
        response_data = {
            "pseudonymized_text": pseudonymized_text,
            "masked_prompt": pseudonymized_text,
            "detection": detection_details,
            "processing_time": processing_time,
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "mode": "modular_enhanced",
            "mapping": mapping,
            "reverse_map": reverse_map,  # ⭐ 핵심: reverse_map 보장
            "id": request_id,
            "detected_count": detected_items
        }
        
        debug_log(f"응답 전송 [{request_id}]", {
            "response_size": len(json.dumps(response_data, ensure_ascii=False)),
            "reverse_map_confirmed": bool(reverse_map),
            "total_time": time.time() - request_start_time
        })
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response
        
    except Exception as e:
        debug_error(f"가명화 처리 중 오류", e)
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
        
        debug_log("복원 요청 수신", {
            "pseudonymized_length": len(pseudonymized_text),
            "reverse_map": reverse_map,
            "reverse_map_size": len(reverse_map)
        })
        
        if not pseudonymized_text or not reverse_map:
            debug_error("복원 요청 오류 - 필수 필드 누락")
            response = jsonify({"error": "pseudonymized_text와 reverse_map 필드가 필요합니다"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        start_time = time.time()
        
        # ⭐ 강화된 복원 로직
        restored_text = pseudonymized_text
        sorted_reverse_mappings = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        replacement_count = 0
        replacement_details = []
        
        debug_log("복원 시작", {
            "mappings_to_process": len(sorted_reverse_mappings),
            "sorted_mappings": sorted_reverse_mappings
        })
        
        for fake, original in sorted_reverse_mappings:
            if fake and original and fake in restored_text:
                before_replace = restored_text
                restored_text = restored_text.replace(fake, original)
                if before_replace != restored_text:
                    replacement_count += 1
                    detail = {"fake": fake, "original": original}
                    replacement_details.append(detail)
                    debug_log(f"복원 성공", detail)
        
        processing_time = time.time() - start_time
        
        debug_log("복원 완료", {
            "total_replacements": replacement_count,
            "processing_time": processing_time,
            "original_length": len(pseudonymized_text),
            "restored_length": len(restored_text),
            "replacement_details": replacement_details
        })
        
        response_data = {
            "restored_text": restored_text,
            "processing_time": processing_time,
            "replacement_count": replacement_count,
            "replacement_details": replacement_details,
            "timestamp": datetime.now().isoformat()
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        debug_error("복원 처리 중 오류", e)
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
        debug_error("로그 읽기 오류", e)
        response = jsonify({"error": f"로그 읽기 오류: {e}"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/prompt_logs", methods=["DELETE"])
def clear_logs():
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump({"logs": []}, f, ensure_ascii=False)
        
        debug_log("로그 삭제 완료")
        response = jsonify({"success": True, "message": "로그가 삭제되었습니다"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        debug_error("로그 삭제 실패", e)
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/health", methods=["GET"])
def health():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "manager_ready": manager_initialized,
        "version": "4.0.1",
        "reverse_restoration": True,
        "enhanced_debugging": True
    }
    
    response = jsonify(health_status)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == "__main__":
    print("🚀 GenAI Pseudonymizer (AenganZ Enhanced) 서버 시작")
    print("📝 가명화 모드: 김가명, 이가명 등 실제 가명 사용")
    print("📞 전화번호: 010-0000-0000부터 1씩 증가")
    print("🏠 주소: 시/도만 표시")
    print("📧 이메일: user001@example.com 형태")
    print("🤖 NER 모델: KPF/KPF-bert-ner")
    print("🔄 역복호화 기능: 활성화")
    print("🔧 강화된 디버깅: 활성화")
    print("⚡ 서버 시작 중...")
    
    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("🛑 서버 종료")
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        import traceback
        traceback.print_exc()