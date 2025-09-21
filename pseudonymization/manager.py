# pseudonymization/manager.py
"""
가명화 매니저 - 수정된 버전
전체 가명화 프로세스 관리 + 한글 로그
"""

import time
import json
import os
from typing import Dict, Any, Optional, List
from .core import pseudonymize_text as core_pseudonymize_text
from .model import load_ner_model, is_ner_loaded
from .pools import get_pools, initialize_pools

class PseudonymizationManager:
    """가명화 프로세스 전체 관리"""
    
    def __init__(self, enable_ner: bool = True):
        self.ner_enabled = enable_ner
        self.pools_initialized = False
        self.ner_model_loaded = False
        
        # 통계
        self.stats = {
            "successful_requests": 0,
            "failed_requests": 0,
            "total_pii_detected": 0,
            "processing_times": [],
            "avg_detection_time": 0,
            "avg_replacement_time": 0,
            "ner_mode_requests": 0
        }
        
        print("가명화매니저 초기화 중...")
        self._initialize()
    
    def _initialize(self):
        """매니저 초기화"""
        try:
            # 데이터풀 초기화
            if not self.pools_initialized:
                print("데이터풀 로딩 중...")
                initialize_pools()
                self.pools_initialized = True
                print("데이터풀 로딩 성공")
            
            # NER 모델 로딩 (백그라운드)
            if self.ner_enabled and not self.ner_model_loaded:
                print("NER 간소화 모드 활성화")
                try:
                    load_ner_model()
                    if is_ner_loaded():
                        self.ner_model_loaded = True
                        print("NER 모델 로딩 성공")
                    else:
                        print("NER 모델 로딩 실패 (정규식 모드로 대체)")
                except Exception as e:
                    print(f"NER 모델 로딩 실패: {e}")
                    self.ner_model_loaded = False
            
            print("가명화매니저 초기화 완료!")
            
        except Exception as e:
            print(f"매니저 초기화 실패: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """매니저 상태 정보"""
        return {
            "initialized": self.pools_initialized,
            "ner_enabled": self.ner_enabled,
            "ner_loaded": self.ner_model_loaded,
            "stats": self.stats.copy()
        }
    
    def pseudonymize(self, text: str, log_id: Optional[str] = None, detailed_report: bool = False) -> Dict[str, Any]:
        """텍스트 가명화 (통합 인터페이스)"""
        if not text or not text.strip():
            return {
                'pseudonymized_text': text,
                'original_text': text,
                'detection': {'contains_pii': False, 'items': []},
                'substitution_map': {},
                'reverse_map': {},
                'processing_time': 0,
                'stats': {'items_by_type': {}, 'detection_stats': {}, 'total_items': 0}
            }
        
        try:
            start_time = time.time()
            
            if log_id:
                print("============================================================")
                print(f"가명화 요청: {time.strftime('%H:%M:%S')}")
                print(f"ID: {log_id}")
                print(f"원본 텍스트: {text}")
                
            print(f"가명화 시작: {text[:50]}...")
            print("PII 탐지 (NER 간소화 + 정규식 중심)")
            
            # 핵심 가명화 실행
            result = core_pseudonymize_text(text, detailed_report=detailed_report)
            
            # 통계 업데이트
            processing_time = time.time() - start_time
            self.stats["successful_requests"] += 1
            self.stats["total_pii_detected"] += len(result['detection']['items'])
            self.stats["processing_times"].append(processing_time)
            
            if self.ner_enabled:
                self.stats["ner_mode_requests"] += 1
            
            # 세부 시간 통계
            if 'detection_time' in result['stats']:
                if self.stats["avg_detection_time"] == 0:
                    self.stats["avg_detection_time"] = result['stats']['detection_time']
                else:
                    self.stats["avg_detection_time"] = (self.stats["avg_detection_time"] + result['stats']['detection_time']) / 2
            
            if 'replacement_time' in result['stats']:
                if self.stats["avg_replacement_time"] == 0:
                    self.stats["avg_replacement_time"] = result['stats']['replacement_time']
                else:
                    self.stats["avg_replacement_time"] = (self.stats["avg_replacement_time"] + result['stats']['replacement_time']) / 2
            
            print(f"가명화 완료 ({len(result['detection']['items'])}개 항목 탐지)")
            
            # 로그 저장
            if log_id:
                self._save_log(log_id, text, result)
            
            return result
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            print(f"가명화 실패: {e}")
            raise
    
    def _save_log(self, log_id: str, original_text: str, result: Dict[str, Any]):
        """로그 저장"""
        try:
            import json
            log_entry = {
                "id": log_id,
                "timestamp": time.time(),
                "original_length": len(original_text),
                "detected_items": len(result['detection']['items']),
                "processing_time": result['processing_time'],
                "items_by_type": result['stats']['items_by_type'],
                "detection_stats": result['stats']['detection_stats'],
                "ner_enabled": self.ner_enabled
            }
            
            with open("pseudo-log.json", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            print("로그 저장됨: pseudo-log.json")
            
        except Exception as e:
            print(f"로그 저장 실패: {e}")

# 전역 매니저 인스턴스
_global_manager = None

def get_manager(enable_ner: bool = True) -> PseudonymizationManager:
    """매니저 싱글톤 인스턴스"""
    global _global_manager
    if _global_manager is None:
        _global_manager = PseudonymizationManager(enable_ner=enable_ner)
    return _global_manager

def is_manager_ready() -> bool:
    """매니저 준비 상태 확인"""
    global _global_manager
    if _global_manager is None:
        return False
    return _global_manager.pools_initialized

def get_manager_status() -> Dict[str, Any]:
    """매니저 상태 정보"""
    global _global_manager
    if _global_manager is None:
        return {"initialized": False}
    return _global_manager.get_status()

def pseudonymize_with_manager(text: str, log_id: Optional[str] = None, detailed_report: bool = False) -> Dict[str, Any]:
    """매니저를 통한 가명화"""
    manager = get_manager()
    return manager.pseudonymize(text, log_id=log_id, detailed_report=detailed_report)