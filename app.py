# app.py - 파일 기반 역복호화 API 추가
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

def build_reverse_map_from_detection(detection_items):
    """detection items에서 reverse_map 생성"""
    reverse_map = {}
    for item in detection_items:
        token = item.get("token", "")
        original = item.get("value", "")
        if token and original and token != original:
            reverse_map[token] = original
    return reverse_map

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
        "service": "GenAI Pseudonymizer (파일 기반 역복호화)",
        "version": "4.1.0",
        "status": "running",
        "manager_ready": manager_initialized,
        "features": {
            "file_based_restore": True,
            "real_names_mode": True,
            "enhanced_filtering": True,
            "email_detection": True,
            "smart_address": True,
            "ner_model": "KPF/KPF-bert-ner",
            "persistent_reverse_mapping": True
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
        
        debug_log(f"⭐ 파일 기반 가명화 요청 시작 [{request_id}]", {
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
        debug_log(f"🚀 pseudonymize_text_with_fake 호출 시작 [{request_id}]")
        result = asyncio.run(pseudonymize_text_with_fake(text))
        debug_log(f"🚀 pseudonymize_text_with_fake 호출 완료 [{request_id}]")
        
        pseudonymized_text = result.get("pseudonymized_text", text)
        detected_items = result.get("detected_items", 0)
        detection_details = result.get("detection", {})
        mapping = result.get("mapping", [])
        reverse_map = result.get("reverse_map", {})
        
        processing_time = time.time() - start_time
        
        debug_log(f"✅ 가명화 처리 완료 [{request_id}]", {
            "original_text": text[:50] + "..." if len(text) > 50 else text,
            "pseudonymized_text": pseudonymized_text[:50] + "..." if len(pseudonymized_text) > 50 else pseudonymized_text,
            "detected_items": detected_items,
            "reverse_map": reverse_map,
            "reverse_map_size": len(reverse_map),
            "processing_time": processing_time
        })
        
        # ⭐ 파일 기반 저장을 위한 로그 엔트리
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remote_addr": request.remote_addr,
            "path": "/pseudonymize", 
            "request_id": request_id,  # ⭐ 핵심: request_id 저장
            "input": {
                "id": request_id,
                "prompt": text
            },
            "output": {
                "pseudonymized_text": pseudonymized_text,
                "detection": detection_details,
                "processing_time": processing_time,
                "reverse_map": reverse_map  # ⭐ reverse_map도 저장
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
            "original_text": text,
            "detected_items": detected_items,
            "mode": "file_based_restore",
            "total_processing_time": time.time() - request_start_time
        }
        add_log(log_entry)
        
        # ⭐ 브라우저 익스텐션 호환 응답 형식 + 파일 기반
        response_data = {
            "pseudonymized_text": pseudonymized_text,
            "masked_prompt": pseudonymized_text,
            "detection": detection_details,
            "processing_time": processing_time,
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "mode": "file_based_restore",
            "mapping": mapping,
            "reverse_map": reverse_map,  # ⭐ reverse_map 제공 (호환성)
            "request_id": request_id,    # ⭐ request_id 제공 (파일 기반용)
            "detected_count": detected_items
        }
        
        debug_log(f"📤 응답 전송 [{request_id}]", {
            "response_size": len(json.dumps(response_data, ensure_ascii=False)),
            "reverse_map_confirmed": bool(reverse_map),
            "request_id_confirmed": bool(request_id),
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

@app.route("/get_reverse_map", methods=["POST", "OPTIONS"])
def get_reverse_map():
    """⭐ 새로운 API: request_id로 reverse_map 조회"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    try:
        data = request.get_json()
        request_id = data.get("request_id", "")
        
        if not request_id:
            response = jsonify({"error": "request_id가 필요합니다", "reverse_map": {}})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        debug_log(f"🔍 reverse_map 조회 요청", {"request_id": request_id})
        
        # 로그 파일에서 해당 request_id 찾기
        logs_data = load_logs()
        logs = logs_data.get("logs", [])
        
        # 최근 로그부터 역순으로 검색
        for log_entry in reversed(logs):
            if log_entry.get("request_id") == request_id:
                reverse_map = log_entry.get("output", {}).get("reverse_map", {})
                detection_items = log_entry.get("detection", {}).get("items", [])
                
                # reverse_map이 없으면 detection items에서 생성
                if not reverse_map and detection_items:
                    reverse_map = build_reverse_map_from_detection(detection_items)
                
                debug_log(f"✅ reverse_map 찾음", {
                    "request_id": request_id,
                    "reverse_map": reverse_map,
                    "map_size": len(reverse_map)
                })
                
                response_data = {
                    "success": True,
                    "request_id": request_id,
                    "reverse_map": reverse_map,
                    "found": True,
                    "timestamp": datetime.now().isoformat()
                }
                
                response = jsonify(response_data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response
        
        # 찾지 못한 경우 - 최근 로그 사용 (fallback)
        if logs:
            latest_log = logs[-1]
            reverse_map = latest_log.get("output", {}).get("reverse_map", {})
            detection_items = latest_log.get("detection", {}).get("items", [])
            
            if not reverse_map and detection_items:
                reverse_map = build_reverse_map_from_detection(detection_items)
            
            debug_log(f"⚠️ request_id 못 찾음, 최근 로그 사용", {
                "requested_id": request_id,
                "latest_id": latest_log.get("request_id", "unknown"),
                "reverse_map": reverse_map
            })
            
            response_data = {
                "success": True,
                "request_id": request_id,
                "reverse_map": reverse_map,
                "found": False,
                "used_latest": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            response_data = {
                "success": False,
                "request_id": request_id,
                "reverse_map": {},
                "found": False,
                "error": "로그가 없습니다",
                "timestamp": datetime.now().isoformat()
            }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        debug_error("reverse_map 조회 중 오류", e)
        response = jsonify({
            "success": False,
            "reverse_map": {},
            "error": f"reverse_map 조회 오류: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/restore_text", methods=["POST", "OPTIONS"])
def restore_text():
    """⭐ 새로운 API: 텍스트 복원 (서버에서 처리)"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    try:
        data = request.get_json()
        ai_response_text = data.get('ai_response_text', '')
        request_id = data.get('request_id', '')
        
        debug_log("📝 텍스트 복원 요청", {
            "request_id": request_id,
            "text_length": len(ai_response_text),
            "text_preview": ai_response_text[:100] + "..." if len(ai_response_text) > 100 else ai_response_text
        })
        
        if not ai_response_text:
            response = jsonify({"error": "ai_response_text가 필요합니다", "restored_text": ""})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 400
        
        # request_id로 reverse_map 찾기
        logs_data = load_logs()
        logs = logs_data.get("logs", [])
        reverse_map = {}
        
        for log_entry in reversed(logs):
            if log_entry.get("request_id") == request_id:
                reverse_map = log_entry.get("output", {}).get("reverse_map", {})
                detection_items = log_entry.get("detection", {}).get("items", [])
                
                if not reverse_map and detection_items:
                    reverse_map = build_reverse_map_from_detection(detection_items)
                break
        
        # reverse_map이 없으면 최근 로그 사용
        if not reverse_map and logs:
            latest_log = logs[-1]
            reverse_map = latest_log.get("output", {}).get("reverse_map", {})
            detection_items = latest_log.get("detection", {}).get("items", [])
            
            if not reverse_map and detection_items:
                reverse_map = build_reverse_map_from_detection(detection_items)
        
        debug_log("🔑 복원용 reverse_map", {
            "reverse_map": reverse_map,
            "map_size": len(reverse_map)
        })
        
        # 서버에서 텍스트 복원
        restored_text = ai_response_text
        restoration_count = 0
        restoration_details = []
        
        # 길이 순으로 정렬 (긴 것부터)
        sorted_mappings = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        for fake_value, original_value in sorted_mappings:
            if fake_value and original_value and fake_value in restored_text:
                count_before = restored_text.count(fake_value)
                if count_before > 0:
                    restored_text = restored_text.replace(fake_value, original_value)
                    restoration_count += count_before
                    restoration_details.append({
                        "fake": fake_value,
                        "original": original_value,
                        "count": count_before
                    })
                    debug_log(f"🔄 복원 완료", {
                        "fake": fake_value,
                        "original": original_value,
                        "count": count_before
                    })
        
        debug_log("✅ 텍스트 복원 완료", {
            "total_restorations": restoration_count,
            "restoration_details": restoration_details,
            "restored_preview": restored_text[:100] + "..." if len(restored_text) > 100 else restored_text
        })
        
        response_data = {
            "success": True,
            "restored_text": restored_text,
            "restoration_count": restoration_count,
            "restoration_details": restoration_details,
            "reverse_map_used": reverse_map,
            "timestamp": datetime.now().isoformat()
        }
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        debug_error("텍스트 복원 중 오류", e)
        response = jsonify({
            "success": False,
            "restored_text": ai_response_text,
            "error": f"텍스트 복원 오류: {str(e)}",
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
        "version": "4.1.0",
        "file_based_restore": True,
        "persistent_reverse_mapping": True
    }
    
    response = jsonify(health_status)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

if __name__ == "__main__":
    print("🚀 GenAI Pseudonymizer (파일 기반 역복호화) 서버 시작")
    print("📝 가명화 모드: 김가명, 이가명 등 실제 가명 사용")
    print("📞 전화번호: 010-0000-0000부터 1씩 증가")
    print("🏠 주소: 시/도만 표시")
    print("📧 이메일: user001@example.com 형태")
    print("🤖 NER 모델: KPF/KPF-bert-ner")
    print("💾 파일 기반 역복호화: pseudo-log.json 활용")
    print("🔄 새로운 API: /get_reverse_map, /restore_text")
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