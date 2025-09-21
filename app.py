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
from pseudonymization.pools import get_data_pool_stats
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
    """매니저 초기화 (가명화 모드 기본)"""
    global manager, manager_initialized
    
    try:
        print("🚀 워크플로우 기반 GenAI 가명화기 (AenganZ Enhanced)")
        print("🔧 프레임워크: Flask (모듈 버전)")
        print("🧠 탐지 방식: 1차 정규식 + 2차 NER 보강")
        print("🎭 가명화: 김가명, 이가명 형태 (기본모드)")
        print("📞 전화번호: 010-0000-0000부터 1씩 증가")
        print("🏠 주소: 시/도만 표시")
        print("🔄 복원: 양방향 매핑")
        print("🌐 서버 시작 중...")
        
        print("가명화매니저 초기화 중...")
        
        # 데이터풀 로딩
        print("데이터풀 로딩 중...")
        
        # 매니저 인스턴스 생성 (가명화 모드 기본)
        manager = get_manager(use_fake_mode=True)  # 가명화 모드 기본 설정
        
        # NER 모델 2차 보강 활성화
        print("🤖 NER 2차 보강 모드 활성화")
        print("🤖 NER 백그라운드 로딩 (타임아웃 제한)")
        
        # 데이터풀 통계 출력
        try:
            stats = get_data_pool_stats()
            print("데이터풀 로딩 성공")
            print(f"실명: {stats.get('탐지_이름수', 0):,}개")
            print(f"주소: {stats.get('탐지_주소수', 0):,}개") 
            print(f"시군구: {stats.get('탐지_시군구수', 0):,}개")
            print(f"시도: {stats.get('탐지_시도수', 0):,}개")
            print(f"가명 이름: {stats.get('가명_이름수', 0):,}개")
            print(f"가명 전화: {stats.get('가명_전화수', 0):,}개")
            print(f"가명 주소: {stats.get('가명_주소수', 0):,}개")
        except Exception as e:
            print(f"데이터풀 통계 출력 실패: {e}")
        
        manager_initialized = True
        print("🎭 가명화매니저 초기화 완료! (가명화 모드)")
        print("📝 예시: '홍길동' → '김가명', '010-1234-5678' → '010-0000-0000', '서울 강남구' → '서울시'")
        
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
        stats = get_data_pool_stats()
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
        "pseudonymization_mode": "가명화 (김가명, 이가명 형태)",
        "phone_format": "010-0000-0000부터 1씩 증가",
        "address_format": "시/도만 표시",
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
        "mode": "가명화_기본",
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
        
        # 모드 설정 (요청에서 지정 가능, 기본은 가명화)
        mode = data.get("mode", "fake")  # "fake" 또는 "token"
        
        # 빈 텍스트 처리
        if not text.strip():
            return jsonify({
                "pseudonymized_text": text,
                "fake_text": text,
                "tokenized_text": text,
                "original_text": text,
                "detection": {"contains_pii": False, "items": []},
                "substitution_map": {},
                "reverse_map": {},
                "fake_substitution_map": {},
                "fake_reverse_map": {},
                "token_map": {},
                "processing_time": 0,
                "processing_mode": mode,
                "workflow_ready": False
            })
        
        print("============================================================")
        print(f"가명화 요청: {time.strftime('%H:%M:%S')}")
        print(f"ID: {request_id}")
        print(f"모드: {'가명화' if mode == 'fake' else '토큰화'}")
        print(f"원본 텍스트: {text}")
        
        # 가명화 실행
        result = manager.pseudonymize(
            text=text, 
            detailed_report=True,
            force_mode=mode
        )
        
        print(f"가명화 완료 ({result['stats']['detected_items']}개 항목 탐지)")
        
        # 응답 형식 맞춤
        response_data = {
            "pseudonymized_text": result.get("fake_text", result.get("pseudonymized_text", text)),  # 가명화된 텍스트 (기본)
            "fake_text": result.get("fake_text", text),  # 가명화된 텍스트
            "tokenized_text": result.get("tokenized_text", text),  # 토큰화된 텍스트 (워크플로우용)
            "original_text": text,  # 원본 텍스트
            "detection": result.get("detection", {"contains_pii": False, "items": []}),
            "substitution_map": result.get("substitution_map", {}),  # 원본 → 토큰
            "reverse_map": result.get("reverse_map", {}),  # 토큰 → 원본
            "fake_substitution_map": result.get("fake_substitution_map", {}),  # 원본 → 가명
            "fake_reverse_map": result.get("fake_reverse_map", {}),  # 가명 → 원본
            "token_map": result.get("token_map", {}),  # 워크플로우용
            "mapping_report": result.get("mapping_report", ""),  # 토큰 매핑 리포트
            "fake_mapping_report": result.get("fake_mapping_report", ""),  # 가명화 매핑 리포트
            "processing_time": result.get("processing_time", 0),
            "processing_mode": result.get("processing_mode", mode),
            "workflow_ready": True,
            "stats": result.get("stats", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        # 로그 저장
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "original_text": text,
                "pseudonymized_text": response_data["pseudonymized_text"],
                "fake_text": response_data["fake_text"],
                "tokenized_text": response_data["tokenized_text"],
                "mode": mode,
                "detected_items": len(result.get("detection", {}).get("items", [])),
                "processing_time": response_data["processing_time"],
                "stats": response_data["stats"]
            }
            
            append_json_to_file(LOG_FILE, log_entry)
            print(f"📝 로그 저장됨: {LOG_FILE}")
            
        except Exception as e:
            print(f"로그 저장 실패: {e}")
        
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"가명화 처리 중 오류 발생: {str(e)}"
        print(f"가명화 실패: {error_msg}")
        
        # 에러 로그 저장
        try:
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "error": error_msg,
                "original_text": text,
                "type": "error"
            }
            append_json_to_file(LOG_FILE, error_log)
        except:
            pass
        
        import traceback
        traceback.print_exc()
        
        return jsonify({"error": error_msg}), 500

@app.route("/restore", methods=["POST", "OPTIONS"])
def restore():
    """워크플로우 4단계: AI 응답 복원"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "요청 데이터가 필요합니다"}), 400
        
        ai_response = data.get("ai_response", "")
        reverse_map = data.get("reverse_map", {})
        fake_reverse_map = data.get("fake_reverse_map", {})
        mode = data.get("mode", "fake")  # "fake" 또는 "token"
        
        if not ai_response:
            return jsonify({"error": "ai_response 필드가 필요합니다"}), 400
        
        print("🔄 워크플로우 4단계: AI 응답 복원 시작")
        print(f"모드: {'가명화 복원' if mode == 'fake' else '토큰 복원'}")
        print(f"AI 응답: {ai_response[:100]}...")
        
        if mode == "fake" and fake_reverse_map:
            # 가명화 복원
            from pseudonymization.replacement import get_workflow_manager
            manager_instance = get_workflow_manager()
            manager_instance.fake_reverse_map = fake_reverse_map
            restored_response = manager_instance.restore_from_fake(ai_response)
        else:
            # 토큰 복원 (기본)
            restored_response = workflow_process_ai_response(ai_response, reverse_map)
        
        print(f"✅ 복원 완료: {restored_response[:100]}...")
        
        return jsonify({
            "restored_response": restored_response,
            "original_ai_response": ai_response,
            "restoration_mode": mode,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        error_msg = f"복원 처리 중 오류 발생: {str(e)}"
        print(f"복원 실패: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return jsonify({"error": error_msg}), 500

@app.route("/stats", methods=["GET", "OPTIONS"])
def stats():
    """통계 정보"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    try:
        if manager and hasattr(manager, 'get_stats'):
            manager_stats = manager.get_stats()
        else:
            manager_stats = {"error": "매니저가 초기화되지 않았습니다"}
        
        pool_stats = get_data_pool_stats()
        
        return jsonify({
            "manager_stats": manager_stats,
            "pool_stats": pool_stats,
            "system_info": {
                "version": __version__,
                "title": __title__,
                "description": __description__,
                "manager_initialized": manager_initialized,
                "default_mode": "가명화 (김가명, 이가명 형태)"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": f"통계 조회 실패: {str(e)}"}), 500

@app.route("/set-mode", methods=["POST", "OPTIONS"])
def set_mode():
    """가명화 모드 변경"""
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', '*')
        return response
    
    try:
        data = request.get_json()
        if not data or "mode" not in data:
            return jsonify({"error": "mode 필드가 필요합니다 ('fake' 또는 'token')"}), 400
        
        mode = data["mode"]
        if mode not in ["fake", "token"]:
            return jsonify({"error": "mode는 'fake' 또는 'token'이어야 합니다"}), 400
        
        if manager and hasattr(manager, 'set_fake_mode'):
            manager.set_fake_mode(mode == "fake")
            
        mode_str = "가명화 (김가명, 이가명 형태)" if mode == "fake" else "토큰화 ([PER_0], [LOC_0] 형태)"
        print(f"🔧 처리 모드 변경: {mode_str}")
        
        return jsonify({
            "message": f"모드가 {mode_str}로 변경되었습니다",
            "current_mode": mode,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": f"모드 변경 실패: {str(e)}"}), 500

# ===== 서버 실행 =====
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 GenAI 가명화기 (AenganZ Enhanced) v4.0.0")
    print("🎭 가명화 모드 기본 설정")
    print("=" * 60)
    
    # 서버 시작 전 초기화
    initialize_manager()
    
    print("🌐 서버 시작...")
    print("📋 API 엔드포인트:")
    print("   GET  /           : 서버 정보")
    print("   GET  /health     : 상태 확인")
    print("   POST /pseudonymize : 가명화 처리")
    print("   POST /restore    : AI 응답 복원")
    print("   GET  /stats      : 통계 정보")
    print("   POST /set-mode   : 모드 변경")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=5000, debug=False)