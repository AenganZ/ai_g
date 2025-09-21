# app.py
"""
GenAI Pseudonymizer Server - 깔끔한 버전
Flask 서버 애플리케이션
"""

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pseudonymization.manager import get_manager
from utils.logging import append_json_to_file

# 설정
LOG_PATH = "pseudo-log.json"

# Flask 앱 생성
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)

# 매니저 인스턴스 (lazy loading)
manager = None

def get_initialized_manager():
    """매니저 초기화 및 반환"""
    global manager
    if manager is None:
        print("Initializing PseudonymizationManager...")
        manager = get_manager()
        print("PseudonymizationManager initialization completed!")
    return manager

@app.route("/", methods=["GET", "OPTIONS"])
def root():
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    mgr = get_initialized_manager()
    
    return jsonify({
        "message": "GenAI Pseudonymizer (Enhanced)", 
        "version": "3.0.0",
        "framework": "Flask",
        "detection_method": "NER + Regex + DataPools",
        "ready": mgr.initialized,
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
    
    mgr = get_initialized_manager()
    status = mgr.get_status()
    
    return jsonify({
        "status": "ok",
        "method": "enhanced_detection",
        "ready": mgr.initialized,
        "mode": status.get("mode", "unknown"),
        "uptime": status.get("uptime", 0),
        "timestamp": datetime.now().isoformat()
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
        data = request.get_json(force=True, silent=False)
    except Exception as e:
        response = jsonify(ok=False, error=f"invalid_json: {e}")
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 400
    
    # 필수 필드 확인
    if "prompt" not in data:
        response = jsonify(ok=False, error="missing_prompt")
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 400
    
    prompt = data["prompt"]
    request_id = data.get("request_id", f"debug_test_{int(datetime.now().timestamp() * 1000)}")
    
    # 로그 출력
    print("=" * 60)
    print(f"Pseudonymization request: {datetime.now().strftime('%H:%M:%S')}")
    print(f"ID: {request_id}")
    print(f"Original text: {prompt}")
    
    try:
        # 매니저를 통한 가명화
        mgr = get_initialized_manager()
        result = mgr.pseudonymize(prompt, log_id=request_id)
        
        # 응답 구성
        response_data = {
            "ok": True,
            "original_prompt": prompt,
            "masked_prompt": result.get("pseudonymized", result.get("masked_prompt", prompt)),
            "request_id": request_id,
            "processing_time": result.get("processing_time", "0.000s"),
            "detected_items": len(result.get("detection", {}).get("items", [])),
            "substitution_map": result.get("substitution_map", {}),
            "reverse_map": result.get("reverse_map", {})
        }
        
        print(f"Pseudonymization completed ({response_data['detected_items']} items detected)")
        print(f"Log saved to: {LOG_PATH}")
        print(f"Pseudonymization completed ({response_data['detected_items']} detected)")
        print(f"Substitution map: {response_data['substitution_map']}")
        print("=" * 60)
        
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        import traceback
        print(f"Pseudonymization error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        response = jsonify(
            ok=False, 
            error=f"pseudonymization_failed: {str(e)}",
            request_id=request_id
        )
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
        data = request.get_json(force=True)
        pseudonymized_text = data.get("pseudonymized_text", "")
        reverse_map = data.get("reverse_map", {})
        
        mgr = get_initialized_manager()
        from pseudonymization.core import restore_original
        restored = restore_original(pseudonymized_text, reverse_map)
        
        response = jsonify({
            "ok": True,
            "restored_text": restored
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        response = jsonify(ok=False, error=f"restore_failed: {str(e)}")
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
        if not os.path.exists(LOG_PATH):
            response = jsonify({"logs": []})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        
        logs = []
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line.strip()))
                    except:
                        continue
        
        # 최근 50개만 반환
        recent_logs = logs[-50:] if len(logs) > 50 else logs
        
        response = jsonify({"logs": recent_logs})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        response = jsonify({"logs": [], "error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

@app.route("/status", methods=["GET"])
def status():
    """매니저 상태 조회"""
    try:
        mgr = get_initialized_manager()
        status_data = mgr.get_status()
        
        response = jsonify({
            "ok": True,
            "status": status_data
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        response = jsonify(ok=False, error=str(e))
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

# 에러 핸들러
@app.errorhandler(404)
def not_found(error):
    response = jsonify(error="Not Found", message=f"Endpoint {request.path} not found")
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 404

@app.errorhandler(500)
def internal_error(error):
    response = jsonify(error="Internal Server Error", message=str(error))
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 500

if __name__ == "__main__":
    print("GenAI Pseudonymizer (Enhanced)")
    print("Framework: Flask (2.2+ compatible)")
    print("Detection: NER + Regex + DataPools")
    print("Pseudonymization: Clear fake data replacement")
    print("Restore: Bidirectional mapping")
    print("Server starting...")
    
    app.run(host="127.0.0.1", port=5000, debug=True)