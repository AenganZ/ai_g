# app.py - Flask 2.2+ 호환 AenganZ 통합 버전
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
CORS(app)

# 매니저 인스턴스 (lazy loading)
manager = None

def get_initialized_manager():
    """매니저 초기화 및 반환 (Flask 2.2+ 호환)"""
    global manager
    if manager is None:
        print("🚀 PseudonymizationManager 초기화 중...")
        manager = get_manager()
        print("✅ PseudonymizationManager 초기화 완료!")
    return manager

@app.route("/", methods=["GET", "OPTIONS"])
def root():
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    # 매니저 초기화 (첫 요청 시)
    mgr = get_initialized_manager()
    
    return jsonify({
        "message": "GenAI Pseudonymizer (AenganZ Enhanced)", 
        "version": "2.0.0",
        "framework": "Flask",
        "detection_method": "NER + Regex + DataPools",
        "ready": mgr.is_ready(),
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
    
    # 매니저 초기화 (첫 요청 시)
    mgr = get_initialized_manager()
    
    return jsonify({
        "status": "ok",
        "method": "enhanced_detection",
        "ready": mgr.is_ready(),
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
        # 매니저 초기화 및 가명화 처리
        mgr = get_initialized_manager()
        result = mgr.pseudonymize(original_prompt)
        
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
        append_json_to_file(LOG_PATH, log_entry)

        print(f"✅ 가명화 완료 ({len(detection.get('items', []))}개 탐지)")
        print(f"🔄 대체 맵: {substitution_map}")
        print("="*60)

        # 응답 생성 (AenganZ 포맷 + 확장 호환성)
        response_data = {
            "ok": True,
            "original_prompt": original_prompt,        # 사용자가 보는 원본
            "masked_prompt": masked_prompt,            # LLM이 받는 마스킹된 버전
            "detection": detection,
            "substitution_map": substitution_map,      # 원본 → 가명 매핑
            "reverse_map": reverse_map,                # 가명 → 원본 매핑 (복원용)
            "mapping": detection.get("items", [])      # 기존 확장 호환성
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
            "masked_prompt": original_prompt,  # 오류 시 원본 반환
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
    # CORS preflight 요청 처리
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

    # 로그 파일 반환
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        
        # JSON 유효성 검사
        json.loads(raw)
        
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
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump({"logs": []}, f, ensure_ascii=False)
        
        response = jsonify({"success": True, "message": "Logs cleared"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({"success": False, "error": str(e)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

# 에러 핸들러
@app.errorhandler(404)
def not_found(error):
    response = jsonify({"error": "Not found"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 404

@app.errorhandler(500)
def internal_error(error):
    response = jsonify({"error": "Internal server error"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 500

if __name__ == "__main__":
    print("🎭 GenAI Pseudonymizer (AenganZ Enhanced)")
    print("🔧 프레임워크: Flask (2.2+ 호환)")
    print("🧠 탐지 방식: NER + 정규식 + 데이터풀")
    print("📛 가명화: 실제 데이터 대체")
    print("🔄 복원: 양방향 매핑")
    print("🌐 서버 시작 중...")
    
    # 개발 서버 실행
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