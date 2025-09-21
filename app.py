# app.py - FastAPI 기반 (브라우저 익스텐션 호환)
import os
import json
import time
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 가명화 모듈 import
from pseudonymization.manager import get_manager, is_manager_ready, get_manager_status
from pseudonymization.core import get_data_pool_stats, workflow_process_ai_response
from pseudonymization import __version__, __title__, __description__

# 설정
LOG_FILE = "pseudo-log.json"
MAX_LOGS = 100

# FastAPI 설정
app = FastAPI(title="GenAI Pseudonymizer", version=__version__, description=__description__)
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# 전역 변수
manager = None
manager_initialized = False

# Pydantic 모델들
class PseudoRequest(BaseModel):
    prompt: str
    id: Optional[str] = ""

class PseudoItem(BaseModel):
    type: str
    value: str
    start: int
    end: int
    replacement: str
    confidence: float
    source: str

class PseudoResponse(BaseModel):
    ok: bool
    original_prompt: str  # 사용자가 보는 원본
    masked_prompt: str    # LLM이 받는 가명화된 버전
    mapping: List[PseudoItem]
    substitution_map: Dict[str, str]
    reverse_map: Dict[str, str]  # 복구용 맵 (가명 → 원본)
    detection: Dict[str, Any]

# 로그 관리 함수들
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

# 매니저 초기화
async def initialize_manager():
    """매니저 초기화"""
    global manager, manager_initialized
    
    try:
        print("워크플로우 기반 GenAI 가명화기 (AenganZ Enhanced)")
        print("가명화: 김가명, 이가명 형태 (기본모드)")
        print("전화번호: 010-0000-0000부터 1씩 증가")
        print("주소: 시/도만 표시")
        print("이메일: user001@example.com 형태")
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
            print(f"시/도: {stats.get('탐지_시도수', 0):,}개")
            print(f"시: {stats.get('탐지_시수', 0):,}개") 
            print(f"구/군: {stats.get('탐지_시군구수', 0):,}개")
        except Exception as e:
            print(f"데이터풀 통계 출력 실패: {e}")
        
        manager_initialized = True
        print("가명화매니저 초기화 완료!")
        print("서버 준비 완료!")
        
    except Exception as e:
        print(f"매니저 초기화 실패: {e}")
        manager_initialized = False

# 서버 시작시 초기화
@app.on_event("startup")
async def startup_event():
    # 백그라운드에서 매니저 초기화
    executor = ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, lambda: asyncio.run(initialize_manager()))

# API 엔드포인트들
@app.get("/")
def root():
    return {
        "message": "GenAI Pseudonymizer (FastAPI - 브라우저 익스텐션 호환)", 
        "version": __version__,
        "framework": "FastAPI",
        "manager_loaded": manager_initialized,
        "data_pools": {
            "전국_시도수": len(get_manager().pools.provinces) if manager_initialized else 0,
            "전국_시수": len(get_manager().pools.cities) if manager_initialized else 0,
            "전국_구군수": len(get_manager().pools.districts) if manager_initialized else 0,
        } if manager_initialized else {}
    }

@app.get("/health")
def health():
    return {
        "status": "ready" if manager_initialized else "initializing", 
        "method": "enhanced_address_detection", 
        "manager_ready": manager_initialized,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stats")
def get_stats():
    """데이터풀 통계"""
    try:
        stats = get_data_pool_stats()
        return {
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": f"통계 조회 실패: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/pseudonymize")
async def pseudonymize(request: PseudoRequest):
    """가명화 처리 (브라우저 익스텐션 호환)"""
    global manager, manager_initialized
    
    if not manager_initialized or not manager:
        return {
            "ok": False,
            "error": "Manager not ready",
            "original_prompt": request.prompt,
            "masked_prompt": request.prompt,
            "mapping": [],
            "substitution_map": {},
            "reverse_map": {},
            "detection": {"contains_pii": False, "items": []}
        }
    
    start_time = time.time()
    
    print(f"\n" + "="*60)
    print(f"가명화 요청: {datetime.now().strftime('%H:%M:%S')}")
    print(f"ID: {request.id}")
    print(f"원문: {request.prompt}")
    
    try:
        # 가명화 실행
        result = manager.pseudonymize(request.prompt, detailed_report=True)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # 로그 엔트리 생성 (기존 FastAPI 형식 유지)
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "remote_addr": "127.0.0.1",  # FastAPI에서는 실제 IP 얻기 복잡함
            "path": "/pseudonymize",
            "input": {"id": request.id, "prompt": request.prompt},
            "detection": {
                "contains_pii": len(result.get('detection', {}).get('items', [])) > 0, 
                "items": [
                    {
                        "type": item.get('type', ''),
                        "value": item.get('value', ''),
                        "start": item.get('start', 0),
                        "end": item.get('end', 0),
                        "confidence": item.get('confidence', 0.0),
                        "source": item.get('source', ''),
                        "replacement": result.get('substitution_map', {}).get(item.get('value', ''), '')
                    } for item in result.get('detection', {}).get('items', [])
                ],
                "model_used": "NER + Regex + NamePool + AddressPool"
            },
            "substitution_map": result.get('substitution_map', {}),
            "reverse_map": result.get('reverse_map', {}),
            "performance": {"total_time_ms": processing_time, "items_detected": len(result.get('detection', {}).get('items', []))}
        }
        
        add_log(log_entry)
        
        print(f"완료 ({processing_time}ms, {len(result.get('detection', {}).get('items', []))}개 탐지)")
        print(f"복구 맵: {result.get('reverse_map', {})}")
        print("="*60)
        
        # FastAPI 응답 형식으로 변환
        detection_items = result.get('detection', {}).get('items', [])
        mapping = []
        for item in detection_items:
            if item.get('value') in result.get('substitution_map', {}):
                mapping.append(PseudoItem(
                    type=item.get('type', ''),
                    value=item.get('value', ''),
                    start=item.get('start', 0),
                    end=item.get('end', 0),
                    replacement=result.get('substitution_map', {}).get(item.get('value', ''), ''),
                    confidence=item.get('confidence', 0.0),
                    source=item.get('source', '')
                ))
        
        return PseudoResponse(
            ok=True,
            original_prompt=request.prompt,    # 사용자가 보는 원본
            masked_prompt=result.get('pseudonymized_text', request.prompt),  # LLM이 받는 가명화된 버전
            mapping=mapping,
            substitution_map=result.get('substitution_map', {}),
            reverse_map=result.get('reverse_map', {}),   # 복구용 맵
            detection={
                "contains_pii": len(detection_items) > 0, 
                "items": detection_items,
                "model_used": "NER + Regex + NamePool + AddressPool"
            }
        )
        
    except Exception as e:
        print(f"오류: {e}")
        return {
            "ok": False, 
            "error": str(e), 
            "original_prompt": request.prompt,
            "masked_prompt": request.prompt, 
            "mapping": [], 
            "substitution_map": {},
            "reverse_map": {},
            "detection": {"contains_pii": False, "items": []}
        }

@app.post("/restore")
async def restore(request: dict):
    """가명화 복원"""
    try:
        pseudonymized_text = request.get('pseudonymized_text', '')
        reverse_map = request.get('reverse_map', {})
        
        if not pseudonymized_text or not reverse_map:
            return {
                "error": "pseudonymized_text와 reverse_map 필드가 필요합니다"
            }
        
        start_time = time.time()
        
        # 복원 실행
        restored_text = workflow_process_ai_response(pseudonymized_text, reverse_map)
        
        processing_time = time.time() - start_time
        
        return {
            "restored_text": restored_text,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": f"복원 처리 중 오류 발생: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/prompt_logs")
def get_logs():
    """로그 조회 (브라우저 익스텐션 호환)"""
    return load_logs()

@app.delete("/prompt_logs")
def clear_logs():
    """로그 삭제 (브라우저 익스텐션 호환)"""
    try:
        save_logs({"logs": []})
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/logs")
def get_logs_alternative():
    """로그 조회 (대안 엔드포인트)"""
    try:
        logs_data = load_logs()
        logs = logs_data.get("logs", [])
        
        # 최신순으로 정렬
        logs.reverse()
        
        return {
            "logs": logs,
            "total": len(logs),
            "returned": len(logs)
        }
        
    except Exception as e:
        return {
            "error": f"로그 조회 중 오류: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    print("GenAI 가명화기 (FastAPI - 브라우저 익스텐션 호환)")
    print("전국 시/구 데이터 완전 지원")
    print("이메일 탐지 강화")
    print("주소 중복 처리 (첫 번째만 치환)")
    print("가명화: 김가명, 이가명 등 명백한 가명 사용")
    print("브라우저 익스텐션과 호환됩니다")
    
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")