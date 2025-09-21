# pseudonymization/manager.py
"""
가명화 매니저 클래스
"""

import time
from typing import Dict, Any, Optional, List
from .pools import initialize_pools, get_pools
from .core import pseudonymize_text as core_pseudonymize_text, pseudonymize_text_with_fake  # 수정된 import
from .model import load_ner_model, is_ner_loaded

class PseudonymizationManager:
    """가명화 관리자 클래스"""
    
    def __init__(self, use_fake_mode: bool = True):
        self.use_fake_mode = use_fake_mode
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'token_mode_requests': 0,
            'fake_mode_requests': 0,
            'avg_detection_time': 0,
            'avg_replacement_time': 0,
            'total_pii_detected': 0,
            'processing_times': []
        }
        self._initialize()
    
    def _initialize(self):
        """매니저 초기화"""
        try:
            # 데이터풀 초기화
            print("데이터풀 초기화 중...")
            initialize_pools()
            
            # NER 모델 백그라운드 로딩
            print("NER 모델 백그라운드 로딩...")
            load_ner_model()
            
            print("매니저 초기화 완료")
            
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
                print("가명화 모드로 처리 중...")
            else:
                self.stats['token_mode_requests'] += 1
                print("토큰화 모드로 처리 중...")
            
            # 가명화 처리
            start_time = time.time()
            
            # 통합된 함수 사용
            result = core_pseudonymize_text(text, detailed_report, use_fake=use_fake)
            
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
            
            return result
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            print(f"가명화 실패: {e}")
            raise e
    
    def get_status(self) -> Dict[str, Any]:
        """매니저 상태 반환"""
        pools = get_pools()
        return {
            "initialized": pools._initialized,
            "ner_loaded": is_ner_loaded(),
            "use_fake_mode": self.use_fake_mode,
            "stats": self.stats.copy(),
            "data_pool_sizes": {
                "real_names": len(pools.real_names),
                "real_addresses": len(pools.real_addresses),
                "provinces": len(pools.provinces),
                "districts": len(pools.districts)
            }
        }
    
    def set_mode(self, use_fake_mode: bool):
        """모드 변경"""
        old_mode = self.use_fake_mode
        self.use_fake_mode = use_fake_mode
        print(f"모드 변경: {'가명화' if old_mode else '토큰화'} → {'가명화' if use_fake_mode else '토큰화'}")

# 전역 매니저 인스턴스
_manager_instance: Optional[PseudonymizationManager] = None

def get_manager(use_fake_mode: bool = True) -> PseudonymizationManager:
    """매니저 싱글톤 인스턴스 반환"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PseudonymizationManager(use_fake_mode)
    return _manager_instance

def is_manager_ready() -> bool:
    """매니저 준비 상태 확인"""
    global _manager_instance
    if _manager_instance is None:
        return False
    return get_pools()._initialized

def get_manager_status() -> Dict[str, Any]:
    """매니저 상태 정보"""
    if _manager_instance is None:
        return {"initialized": False, "error": "Manager not created"}
    return _manager_instance.get_status()

def pseudonymize_with_manager(text: str, detailed_report: bool = True) -> Dict[str, Any]:
    """매니저를 통한 가명화"""
    manager = get_manager()
    return manager.pseudonymize(text, detailed_report)