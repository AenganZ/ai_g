# app.py - 모듈화된 완전 버전 (AenganZ Enhanced) - 가명화 모드 기본
import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS

# 가명화 모듈 import
from pseudonymization.manager import get_manager, is_manager_ready, get_manager_status
from pseudonymization.core import get_data_pool_stats  # 수정: pools.py → core.py
from pseudonymization.core import workflow_process_ai_response
from pseudonymization import __version__, __title__, __description__

# 설정
LOG_FILE = "pseudo-log.json"
MAX_LOGS = 100

# Flask 설정
app = Flask(__name__)
CORS(app)

# 전역 변수
manager = None
manager_initialized = False

# 로깅 유틸리티
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

def initialize_manager():
    """매니저 초기화"""
    global manager, manager_initialized
    
    try:
        print("워크플로우 기반 GenAI 가명화기 (AenganZ Enhanced)")
        print("가명화: 김가명, 이가명 형태 (기본모드)")
        print("전화번호: 010-0000-0000부터 1씩 증가")
        print("주소: 시/도만 표시")
        print("서버 시작 중...")
        
        print("가명화매니저 초기화 중...")
        
        # 매니저 인스턴스 생성 (가명화 모드 기본)
        manager = get_manager(use_fake_mode=True)
        
        print("NER 모델 백그라운드 로딩...")
        
        # 데이터풀 통계 출력
        try:
            stats = get_data_pool_stats()
            print("데이터풀 로딩 성공")
            print(f"실명: {stats.get('탐지_이름수', 0):,}개")
            print(f"주소: {stats.get('탐지_주소수', 0):,}개") 
            print(f"시군구: {stats.get('탐지_시군구수', 0):,}개")
            print(f"시도: {stats.get('탐지_시도수', 0):,}개")
        except Exception as e:
            print(f"데이터풀 통계 출력 실패: {e}")
        
        manager_initialized = True
        print("가명화매니저 초기화 완료!")
        print("서버 준비 완료!")
        
    except Exception as e:
        print(f"매니저 초기화 실패: {e}")
        manager_initialized = False

# 백그라운드에서 매니저 초기화
def start_background_initialization():
    """백그라운드에서 매니저 초기화"""
    def init_worker():
        initialize_manager()
    
    init_thread = threading.Thread(target=init_worker, daemon=True)
    init_thread.start()

# API 엔드포인트

@app.route('/health', methods=['GET', 'OPTIONS'])
def health_check():
    """서버 상태 확인"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
        
    global manager_initialized
    
    return jsonify({
        "status": "ready" if manager_initialized else "initializing",
        "manager_ready": manager_initialized,
        "timestamp": datetime.now().isoformat(),
        "version": __version__
    })

@app.route('/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    """데이터풀 통계"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
        
    try:
        stats = get_data_pool_stats()
        return jsonify({
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "error": f"통계 조회 실패: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/pseudonymize', methods=['POST', 'OPTIONS'])
def pseudonymize():
    """기존 호환성을 위한 가명화 엔드포인트"""
    # CORS preflight 요청 처리
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    global manager, manager_initialized
    
    if not manager_initialized or not manager:
        return jsonify({
            "error": "Manager not ready",
            "message": "가명화 매니저가 초기화되지 않았습니다."
        }), 503
    
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "요청에 'prompt' 필드가 필요합니다"}), 400
        
        text = data['prompt']
        detailed_report = data.get('detailed_report', False)
        request_id = data.get("id", f"pseudo_{int(time.time() * 1000)}_{hash(text) % 100000}")
        
        print("============================================================")
        print(f"가명화 요청: {time.strftime('%H:%M:%S')}")
        print(f"ID: {request_id}")
        print(f"원본 텍스트: {text}")
        
        start_time = time.time()
        
        # 가명화 실행
        result = manager.pseudonymize(text, detailed_report=detailed_report)
        
        processing_time = time.time() - start_time
        
        print(f"가명화 완료 ({result.get('stats', {}).get('detected_items', 0)}개 항목 탐지)")
        print("============================================================")
        
        # 로그 엔트리 준비
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "pseudonymize",
            "request_id": request_id,
            "original_text": text,
            "pseudonymized_text": result.get("pseudonymized", ""),
            "processing_time": processing_time,
            "detected_items": result.get("stats", {}).get("detected_items", 0),
            "success": True
        }
        
        # 로그 저장
        append_json_to_file(LOG_FILE, log_entry)
        
        # 원래 형식의 응답 반환
        return jsonify({
            "pseudonymized_text": result.get("pseudonymized", ""),
            "original_text": text,
            "detection": result.get("detection", {}),
            "substitution_map": result.get("substitution_map", {}),
            "reverse_map": result.get("reverse_map", {}),
            "processing_time": processing_time,
            "stats": result.get("stats", {}),
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_msg = str(e)
        print(f"가명화 처리 오류: {error_msg}")
        
        # 오류 로그
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "pseudonymize_error",
            "request_id": data.get('id', '') if 'data' in locals() else '',
            "original_text": data.get('prompt', '') if 'data' in locals() else '',
            "error": error_msg,
            "success": False
        }
        append_json_to_file(LOG_FILE, log_entry)
        
        return jsonify({
            "error": f"가명화 처리 중 오류 발생: {error_msg}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/restore', methods=['POST', 'OPTIONS'])
def restore():
    """복원 엔드포인트"""
    # CORS preflight 요청 처리
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
        
    try:
        data = request.get_json()
        if not data or 'pseudonymized_text' not in data or 'reverse_map' not in data:
            return jsonify({"error": "pseudonymized_text와 reverse_map 필드가 필요합니다"}), 400
        
        pseudonymized_text = data['pseudonymized_text']
        reverse_map = data['reverse_map']
        
        start_time = time.time()
        
        # 복원 실행
        from pseudonymization.core import restore_original
        restored_text = restore_original(pseudonymized_text, reverse_map)
        
        processing_time = time.time() - start_time
        
        return jsonify({
            "restored_text": restored_text,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "error": f"복원 처리 중 오류 발생: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/logs', methods=['GET', 'OPTIONS'])
def get_logs():
    """로그 조회"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
        
    try:
        limit = request.args.get('limit', 50, type=int)
        if not os.path.exists(LOG_FILE):
            return jsonify({
                "logs": [],
                "total": 0
            })
        
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logs = data.get("logs", [])
        total = len(logs)
        
        # 최신순으로 정렬하고 제한
        logs = logs[-limit:] if limit > 0 else logs
        logs.reverse()
        
        return jsonify({
            "logs": logs,
            "total": total,
            "returned": len(logs)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"로그 조회 중 오류: {str(e)}"
        }), 500

@app.route('/', methods=['GET'])
def index():
    """기본 페이지"""
    status = "ready" if manager_initialized else "initializing"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>GenAI 가명화기</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
            .status {{ padding: 10px 20px; border-radius: 5px; margin: 20px 0; text-align: center; font-weight: bold; }}
            .ready {{ background: #d4edda; color: #155724; }}
            .initializing {{ background: #fff3cd; color: #856404; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>GenAI 가명화기 (AenganZ Enhanced)</h1>
            <p>버전: {__version__}</p>
            
            <div class="status {'ready' if status == 'ready' else 'initializing'}">
                {'서버 준비 완료' if status == 'ready' else '초기화 중...'}
            </div>
            
            <h2>API 엔드포인트</h2>
            <ul>
                <li><strong>POST /pseudonymize</strong> - 가명화 (prompt 필드 사용)</li>
                <li><strong>POST /restore</strong> - 복원</li>
                <li><strong>GET /health</strong> - 상태 확인</li>
                <li><strong>GET /stats</strong> - 통계</li>
                <li><strong>GET /logs</strong> - 로그</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    return html

# 서버 시작
if __name__ == '__main__':
    print("GenAI 가명화기 (AenganZ Enhanced) 시작")
    print("=" * 50)
    
    # 백그라운드에서 매니저 초기화 시작
    start_background_initialization()
    
    print("Flask 서버 시작 (http://localhost:5000)")
    
    # Flask 서버 시작
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n서버 종료")
    except Exception as e:
        print(f"서버 시작 실패: {e}")