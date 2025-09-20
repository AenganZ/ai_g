from flask import Flask, request, jsonify
from flask_cors import CORS  # CORS 추가
import os
from datetime import datetime
from pseudonymization import get_manager
from utils.logging import append_json_to_file

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# CORS 설정 (Chrome 확장과의 통신을 위해)
CORS(app, origins=["*"], methods=["GET", "POST", "OPTIONS"])

# 설정
LOG_PATH = os.getenv("PSEUDO_LOG_PATH", "./pseudo-log.txt")
MAX_INPUT_LENGTH = 4000  # 더 긴 텍스트 처리

# singleton instance
manager = get_manager()

# Request logging
@app.before_request
def log_request_info():
    print(f"\n🌐 HTTP 요청 수신:")
    print(f" 📍 URL: {request.url}")
    print(f" 🔧 메서드: {request.method}")
    print(f" 🏠 Origin: {request.headers.get('Origin', 'None')}")
    print(f" 📦 Content-Type: {request.headers.get('Content-Type', 'None')}")
    if request.method == "POST":
        try:
            if request.is_json:
                data = request.get_json()
                print(f" 📝 Body: {data}")
            else:
                print(f" 📝 Raw Body: {request.get_data()}")
        except Exception as e:
            print(f" ❌ Body 파싱 실패: {e}")
    print("="*50)

@app.route("/", methods=["GET"])
def root():
    return jsonify(
        message="GenAI Pseudonymizer Server is running!",
        endpoints={
            "health": "/health",
            "pseudonymize": "/pseudonymize (POST)",
            "prompt_logs": "/prompt_logs",
            "test": "/test (POST)"
        }
    )

@app.route("/test", methods=["POST", "OPTIONS"])
def test_endpoint():
    """디버깅용 테스트 엔드포인트"""
    if request.method == "OPTIONS":
        # CORS preflight 요청 처리
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    try:
        data = request.get_json()
        return jsonify(ok=True, received_data=data, message="테스트 성공!")
    except Exception as e:
        return jsonify(ok=False, error=str(e))

@app.route("/pseudonymize", methods=["POST", "OPTIONS"])
def pseudonymize():
    # CORS preflight 요청 처리
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

    # 확장에서 {"prompt":"","id":""} 전송
    try:
        data = request.get_json(force=True, silent=False)
    except Exception as e:
        return jsonify(ok=False, error=f"invalid_json: {e}"), 400

    if not isinstance(data, dict):
        return jsonify(ok=False, error="payload_must_be_object"), 400

    original_prompt = data.get("prompt", "")
    req_id = data.get("id", "")

    # 가명화 처리
    result = manager.pseudonymize(original_prompt)
    masked_prompt = result["masked_prompt"]
    detection = result["detection"]

    out = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "remote_addr": request.remote_addr,
        "path": request.path,
        "input": {
            "id": req_id,
            "prompt": original_prompt
        },
        "detection": detection
    }
    append_json_to_file(LOG_PATH, out)

    # 확장으로 가명화 프롬프트 반환
    response = jsonify(ok=True, masked_prompt=masked_prompt, detection=detection)
    return response

@app.route("/prompt_logs", methods=["GET", "OPTIONS"])
def prompt_logs():
    # CORS preflight 요청 처리
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response

    # 파일 그대로 반환 (유효 JSON 보장)
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        import json
        json.loads(raw)  # JSON 유효성 검사
        response = app.response_class(
            response=raw,
            status=200,
            mimetype="application/json; charset=utf-8"
        )
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except FileNotFoundError:
        import json
        empty = {"logs": []}
        response = app.response_class(
            response=json.dumps(empty, ensure_ascii=False),
            status=200,
            mimetype="application/json; charset=utf-8"
        )
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception:
        import json
        safe = {"logs": []}
        response = app.response_class(
            response=json.dumps(safe, ensure_ascii=False),
            status=200,
            mimetype="application/json; charset=utf-8"
        )
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

@app.route("/health", methods=["GET"])
def health():
    device_info = manager.get_device_info()
    return jsonify(
        status="ok",
        model=os.getenv("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct"),
        device_info=device_info,
        log_path=os.path.abspath(LOG_PATH)
    )

# 에러 핸들러 추가
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
    manager.initialize()
    app.run(host="127.0.0.1", port=5000, debug=False)