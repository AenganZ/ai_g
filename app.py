# app.py - 모듈화된 완전 버전 (AenganZ Enhanced)
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
from pseudonymization.pools import get_pool_stats
from pseudonymization.core import workflow_process_ai_response  # 워크플로우 4단계
from pseudonymization import __version__, __title__, __description__

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
        print("🚀 워크플로우 기반 GenAI 가명화기 (AenganZ Enhanced)")
        print("🔧 프레임워크: Flask (모듈 버전)")
        print("🧠 탐지 방식: 1차 정규식 + 2차 NER 보강")
        print("🏷️ 가명화: 토큰 기반 치환")
        print("🔄 복원: 양방향 매핑")
        print("🌐 서버 시작 중...")
        
        print("가명화매니저 초기화 중...")
        print("가명화매니저 초기화 중...")
        
        # 데이터풀 로딩
        print("데이터풀 로딩 중...")
        
        # 매니저 인스턴스 생성
        manager = get_manager(enable_ner=True)
        
        # NER 모델 2차 보강 활성화
        print("🤖 NER 2차 보강 모드 활성화")
        print("🤖 NER 백그라운드 로딩 (타임아웃 제한)")
        
        # 데이터풀 통계 출력
        try:
            stats = get_pool_stats()
            print("데이터풀 로딩 성공")
            print(f"탐지 이름: {stats.get('detection_names', 0):,}개")
            print(f"탐지 도로: {stats.get('detection_roads', 0):,}개")
            print(f"탐지 시군구: {stats.get('detection_districts', 0):,}개")
            print(f"탐지 시도: {stats.get('detection_provinces', 0):,}개")
            print(f"회사: {stats.get('companies', 0):,}개")
        except Exception as e:
            print(f"데이터풀 통계 출력 실패: {e}")
        
        manager_initialized = True
        print("가명화매니저 초기화 완료!")
        
        return True
        
    except Exception as e:
        print(f"매니저 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        manager_initialized = False
        return False

# ===== Flask 라우트 =====
@app.route("/", methods=["GET", "OPTIONS"])
def root():
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
        stats = get_pool_stats()
        manager_status = get_manager_status()
    except:
        stats = {}
        manager_status = {"initialized": manager_initialized}
    
    return jsonify({
        "message": __title__, 
        "version": __version__,
        "description": __description__,
        "framework": "Flask (모듈 버전)",
        "detection_method": "1차 정규식 + 2차 NER 보강 (워크플로우)",
        "manager_status": manager_status,
        "data_pools": stats,
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
        "ready": is_manager_ready(),
        "manager_initialized": manager_initialized,
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
        request_id = data.get("id", f"pseudo_{int(time.time() * 1000)}_{hash(text) % 100000}")
        
        # 빈 텍스트 처리
        if not text.strip():
            return jsonify({
                "pseudonymized_text": text,
                "tokenized_text": text,  # 워크플로우용
                "original_text": text,
                "detection": {"contains_pii": False, "items": []},
                "substitution_map": {},
                "reverse_map": {},
                "token_map": {},  # 워크플로우용
                "processing_time": 0,
                "workflow_ready": False
            })
        
        # 가명화 실행
        result = manager.pseudonymize(
            text=text, 
            log_id=request_id, 
            detailed_report=True
        )
        
        # 응답 형식 맞춤 (워크플로우용)
        response_data = {
            "pseudonymized_text": result.get("tokenized_text", result.get("pseudonymized_text", text)),  # 토큰화된 텍스트
            "tokenized_text": result.get("tokenized_text", text),  # 워크플로우 3단계용 (AI로 전송할 텍스트)
            "original_text": text,  # 원본 텍스트
            "detection": result.get("detection", {"contains_pii": False, "items": []}),
            "substitution_map": result.get("substitution_map", {}),  # 원본 → 토큰
            "reverse_map": result.get("reverse_map", {}),  # 토큰 → 원본 (복원용)
            "token_map": result.get("token_map", {}),  # 워크플로우용
            "processing_time": result.get("processing_time", 0),
            "stats": result.get("stats", {}),
            "mapping_report": result.get("mapping_report", ""),
            "workflow_ready": True  # 워크플로우 준비 완료
        }
        
        # 로그 저장
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remote_addr": request.remote_addr,
            "path": request.path,
            "input": {"id": request_id, "prompt": text},
            **response_data
        }
        
        append_json_to_file(LOG_FILE, log_entry)
        
        # CORS 헤더 추가
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_msg = f"가명화 처리 중 오류 발생: {str(e)}"
        print(f"오류: {error_msg}")
        import traceback
        traceback.print_exc()
        
        response = jsonify({"error": error_msg})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/status", methods=["GET"])
def status():
    """시스템 상태 정보"""
    try:
        manager_status = get_manager_status()
        pool_stats = get_pool_stats()
        
        response = jsonify({
            "system": "정상",
            "manager": manager_status,
            "pools": pool_stats,
            "timestamp": datetime.now().isoformat()
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        response = jsonify({"error": f"상태 조회 실패: {e}"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/restore", methods=["POST", "OPTIONS"])
def restore_ai_response():
    """워크플로우 4단계: AI 응답 복원"""
    # CORS preflight 요청 처리
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    try:
        # 요청 데이터 파싱
        data = request.get_json()
        if not data or "ai_response" not in data or "reverse_map" not in data:
            return jsonify({"error": "요청에 'ai_response'와 'reverse_map' 필드가 필요합니다"}), 400
        
        ai_response = data["ai_response"]
        reverse_map = data["reverse_map"]
        
        # AI 응답 복원
        restored_response = manager.process_ai_response(ai_response, reverse_map)
        
        # 응답 데이터
        response_data = {
            "ai_response_tokenized": ai_response,  # 토큰화된 AI 응답
            "ai_response_restored": restored_response,  # 복원된 최종 답변
            "restoration_successful": True
        }
        
        # CORS 헤더 추가
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        error_msg = f"AI 응답 복원 중 오류 발생: {str(e)}"
        print(f"❌ {error_msg}")
        
        response = jsonify({"error": error_msg})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route("/prompt_logs", methods=["GET"])
def get_logs():
    """로그 조회"""
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
    """로그 삭제"""
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
    print("🎭 GenAI 가명화기 (AenganZ Enhanced - 모듈 버전)")
    print("🔧 프레임워크: Flask (모듈화)")
    print("🧠 탐지 방식: 패턴 + 정규식 + 실명목록")
    print("📛 가명화: 명확한 가명 대체")
    print("🔄 복원: 양방향 매핑")
    print("🌐 서버 시작 중...")
    
    # 초기화
    initialize_manager()
    
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