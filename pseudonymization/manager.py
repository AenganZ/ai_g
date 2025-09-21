# pseudonymization/manager.py
"""
가명화 매니저 - 수정된 버전 (가명화 지원)
전체 가명화 프로세스 관리 + 한글 로그
"""

import time
import json
import os
from typing import Dict, Any, Optional, List
from .core import pseudonymize_text as core_pseudonymize_text, pseudonymize_text_with_fake
from .model import load_ner_model, is_ner_loaded
from .pools import get_pools, initialize_pools

class PseudonymizationManager:
    """가명화 프로세스 전체 관리 (가명화 모드 지원)"""
    
    def __init__(self, enable_ner: bool = True, use_fake_mode: bool = True):
        self.ner_enabled = enable_ner
        self.use_fake_mode = use_fake_mode  # True: 가명화, False: 토큰화
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
            "ner_mode_requests": 0,
            "fake_mode_requests": 0,
            "token_mode_requests": 0
        }
        
        print("가명화매니저 초기화 중...")
        print(f"가명화 모드: {'ON (김가명, 이가명 형태)' if use_fake_mode else 'OFF (토큰화)'}")
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
    
    def pseudonymize(self, text: str, detailed_report: bool = True, force_mode: str = None) -> Dict[str, Any]:
        """
        텍스트 가명화 처리
        
        Args:
            text: 원본 텍스트
            detailed_report: 상세 리포트 생성 여부
            force_mode: 강제 모드 ('fake' 또는 'token')
        """
        try:
            # 모드 결정
            if force_mode == 'fake':
                use_fake = True
            elif force_mode == 'token':
                use_fake = False
            else:
                use_fake = self.use_fake_mode
            
            # 통계 업데이트
            if use_fake:
                self.stats['fake_mode_requests'] += 1
            else:
                self.stats['token_mode_requests'] += 1
            
            # 가명화 처리
            start_time = time.time()
            
            if use_fake:
                print("🎭 가명화 모드로 처리 중...")
                result = pseudonymize_text_with_fake(text, detailed_report)
            else:
                print("🏷️ 토큰화 모드로 처리 중...")
                result = core_pseudonymize_text(text, detailed_report, use_fake=False)
            
            processing_time = time.time() - start_time
            
            # 통계 업데이트
            self.stats['successful_requests'] += 1
            self.stats['total_pii_detected'] += result['stats']['detected_items']
            self.stats['processing_times'].append(processing_time)
            
            # 평균 시간 계산
            if self.stats['processing_times']:
                avg_time = sum(self.stats['processing_times']) / len(self.stats['processing_times'])
                self.stats['avg_detection_time'] = avg_time
                self.stats['avg_replacement_time'] = avg_time
            
            # 결과에 모드 정보 추가
            result['processing_mode'] = 'fake' if use_fake else 'token'
            result['manager_stats'] = self.stats.copy()
            
            print(f"✅ 가명화 완료 ({result['stats']['detected_items']}개 항목 탐지)")
            
            return result
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            print(f"❌ 가명화 실패: {e}")
            raise
    
    def set_fake_mode(self, enabled: bool):
        """가명화 모드 설정"""
        self.use_fake_mode = enabled
        mode_str = "가명화 (김가명, 이가명)" if enabled else "토큰화 ([PER_0], [LOC_0])"
        print(f"🔧 처리 모드 변경: {mode_str}")
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        pools = get_pools()
        
        return {
            "매니저_통계": self.stats,
            "데이터풀_통계": {
                "실명수": len(pools.real_names),
                "주소수": len(pools.real_addresses) if hasattr(pools, 'real_addresses') else 0,
                "시도수": len(pools.provinces),
                "시군구수": len(pools.districts),
                "가명_이름수": len(pools.fake_names) if hasattr(pools, 'fake_names') else 0,
                "가명_전화수": len(pools.fake_phones) if hasattr(pools, 'fake_phones') else 0,
                "가명_주소수": len(pools.fake_addresses) if hasattr(pools, 'fake_addresses') else 0
            },
            "모델_상태": {
                "NER_로딩됨": self.ner_model_loaded,
                "데이터풀_초기화됨": self.pools_initialized
            },
            "처리_모드": {
                "현재_모드": "가명화" if self.use_fake_mode else "토큰화",
                "가명화_요청수": self.stats.get('fake_mode_requests', 0),
                "토큰화_요청수": self.stats.get('token_mode_requests', 0)
            }
        }
    
    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            "successful_requests": 0,
            "failed_requests": 0,
            "total_pii_detected": 0,
            "processing_times": [],
            "avg_detection_time": 0,
            "avg_replacement_time": 0,
            "ner_mode_requests": 0,
            "fake_mode_requests": 0,
            "token_mode_requests": 0
        }
        print("📊 통계 초기화 완료")

# 전역 매니저 인스턴스
_manager_instance = None

def get_manager(use_fake_mode: bool = True) -> PseudonymizationManager:
    """PseudonymizationManager 싱글톤 인스턴스"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PseudonymizationManager(use_fake_mode=use_fake_mode)
    return _manager_instance

def is_manager_ready() -> bool:
    """매니저 준비 상태 확인"""
    try:
        manager = get_manager()
        return manager.pools_initialized
    except:
        return False

def get_manager_status() -> Dict[str, Any]:
    """매니저 상태 정보"""
    try:
        if _manager_instance is None:
            return {"status": "초기화되지_않음"}
        
        manager = get_manager()
        return {
            "status": "준비됨" if manager.pools_initialized else "초기화중",
            "ner_enabled": manager.ner_enabled,
            "ner_loaded": manager.ner_model_loaded,
            "pools_initialized": manager.pools_initialized,
            "fake_mode": manager.use_fake_mode,
            "stats": manager.stats
        }
    except Exception as e:
        return {"status": "오류", "error": str(e)}

def pseudonymize_with_manager(text: str, use_fake: bool = True, detailed_report: bool = True) -> Dict[str, Any]:
    """매니저를 통한 가명화 처리"""
    manager = get_manager(use_fake_mode=use_fake)
    force_mode = 'fake' if use_fake else 'token'
    return manager.pseudonymize(text, detailed_report, force_mode=force_mode)