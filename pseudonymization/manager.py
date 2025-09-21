# pseudonymization/manager.py
"""
가명화 통합 관리자
전체 시스템 초기화 및 상태 관리
"""

import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime

from .core import pseudonymize_text, restore_original, get_data_pool_stats
from .pools import initialize_pools, reload_pools, get_pools
from .model import load_ner_model, is_ner_loaded, get_ner_model
from .replacement import ReplacementManager

class PseudonymizationManager:
    """가명화 통합 관리자 클래스"""
    
    def __init__(self):
        self.initialized = False
        self.initialization_lock = threading.Lock()
        self.data_pools_loaded = False
        self.ner_model_loading = False
        self.start_time = None
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_pii_detected": 0,
            "processing_times": []
        }
        self.replacement_manager = None
    
    def initialize(self, auto_load_ner: bool = True):
        """매니저 초기화"""
        with self.initialization_lock:
            if self.initialized:
                return True
            
            print("🔄 PseudonymizationManager 초기화 중...")
            self.start_time = datetime.now()
            
            try:
                # 1. 데이터풀 초기화
                print("📂 데이터풀 초기화...")
                initialize_pools()
                self.data_pools_loaded = True
                print("✅ 데이터풀 초기화 완료")
                
                # 2. ReplacementManager 초기화
                self.replacement_manager = ReplacementManager()
                print("✅ ReplacementManager 초기화 완료")
                
                # 3. NER 모델 로드 (옵션)
                if auto_load_ner:
                    try:
                        self._start_ner_model_loading()
                    except Exception as e:
                        print(f"⚠️ NER 모델 초기화 스킵: {e}")
                
                self.initialized = True
                print("✅ PseudonymizationManager 초기화 완료!")
                return True
                
            except Exception as e:
                print(f"❌ 매니저 초기화 실패: {e}")
                self.initialized = False
                return False
    
    def _start_ner_model_loading(self):
        """NER 모델 백그라운드 로딩 시작"""
        try:
            # NER 모델 로드 시도 (에러 처리 강화)
            from .model import is_ner_loaded
            
            if not self.ner_model_loading and not is_ner_loaded():
                self.ner_model_loading = True
                threading.Thread(
                    target=self._load_ner_model_background,
                    daemon=True,
                    name="NER-Model-Loader"
                ).start()
                print("🤖 NER 모델 백그라운드 로딩 시작...")
        except Exception as e:
            print(f"⚠️ NER 모델 로딩 스킵: {e}")
            self.ner_model_loading = False
    
    def _load_ner_model_background(self):
        """백그라운드에서 NER 모델 로드"""
        try:
            start_time = time.time()
            success = load_ner_model()
            
            elapsed = time.time() - start_time
            
            if success:
                print(f"✅ NER 모델 백그라운드 로딩 완료! ({elapsed:.1f}초)")
            else:
                print(f"⚠️ NER 모델 로딩 실패 ({elapsed:.1f}초)")
                
        except Exception as e:
            print(f"❌ NER 모델 백그라운드 로딩 오류: {e}")
        finally:
            self.ner_model_loading = False
    
    def pseudonymize(self, prompt: str, request_id: str = None) -> Dict[str, Any]:
        """프롬프트 가명화"""
        # 초기화 확인
        if not self.initialized:
            if not self.initialize():
                raise RuntimeError("매니저 초기화 실패")
        
        # 통계 업데이트
        self.stats["total_requests"] += 1
        start_time = time.time()
        
        try:
            # 가명화 실행
            result = pseudonymize_text(prompt)
            
            # 통계 업데이트
            elapsed = time.time() - start_time
            self.stats["successful_requests"] += 1
            self.stats["total_pii_detected"] += len(result['detection']['items'])
            self.stats["processing_times"].append(elapsed)
            
            # 최대 100개만 유지 (메모리 관리)
            if len(self.stats["processing_times"]) > 100:
                self.stats["processing_times"] = self.stats["processing_times"][-100:]
            
            # 요청 ID 추가
            if request_id:
                result["request_id"] = request_id
            
            # 처리 시간 추가
            result["processing_time"] = f"{elapsed:.3f}s"
            
            # 호환성을 위해 masked_prompt 확인
            if "masked_prompt" not in result and "pseudonymized" in result:
                result["masked_prompt"] = result["pseudonymized"]
            
            return result
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            print(f"❌ 가명화 실패: {e}")
            raise
    
    def restore(self, pseudonymized_text: str, reverse_map: Dict[str, str]) -> str:
        """가명화된 텍스트 복원"""
        return restore_original(pseudonymized_text, reverse_map)
    
    def is_ready(self) -> bool:
        """매니저 준비 상태 확인"""
        return self.initialized and self.data_pools_loaded
    
    def get_status(self) -> Dict[str, Any]:
        """매니저 상태 정보 반환"""
        uptime = None
        if self.start_time:
            uptime = str(datetime.now() - self.start_time).split('.')[0]
        
        avg_processing_time = None
        if self.stats["processing_times"]:
            avg_processing_time = sum(self.stats["processing_times"]) / len(self.stats["processing_times"])
        
        # NER 모델 상태 확인 (에러 처리)
        ner_loaded = False
        try:
            from .model import is_ner_loaded
            ner_loaded = is_ner_loaded()
        except:
            pass
        
        return {
            "initialized": self.initialized,
            "uptime": uptime,
            "data_pools": {
                "loaded": self.data_pools_loaded,
                "stats": get_data_pool_stats() if self.data_pools_loaded else {}
            },
            "ner_model": {
                "loaded": ner_loaded,
                "loading": self.ner_model_loading
            },
            "statistics": {
                "total_requests": self.stats["total_requests"],
                "successful_requests": self.stats["successful_requests"],
                "failed_requests": self.stats["failed_requests"],
                "success_rate": f"{(self.stats['successful_requests'] / max(1, self.stats['total_requests']) * 100):.1f}%",
                "total_pii_detected": self.stats["total_pii_detected"],
                "avg_processing_time": f"{avg_processing_time:.3f}s" if avg_processing_time else None
            }
        }
    
    def reload_data_pools(self):
        """데이터풀 재로드"""
        print("🔄 데이터풀 재로딩...")
        
        try:
            reload_pools()
            self.data_pools_loaded = True
            
            # ReplacementManager도 새로 초기화
            self.replacement_manager = ReplacementManager()
            
            print("✅ 데이터풀 재로딩 완료")
        except Exception as e:
            print(f"❌ 데이터풀 재로딩 실패: {e}")
            self.data_pools_loaded = False
            raise
    
    def force_load_ner_model(self):
        """NER 모델 강제 로드 (동기)"""
        if self.ner_model_loading:
            print("⚠️ NER 모델이 이미 로딩 중입니다.")
            return False
        
        try:
            from .model import is_ner_loaded, load_ner_model
            
            if is_ner_loaded():
                print("ℹ️ NER 모델이 이미 로드되어 있습니다.")
                return True
            
            print("🤖 NER 모델 강제 로드 시작...")
            success = load_ner_model()
            
            if success:
                print("✅ NER 모델 강제 로드 완료!")
            else:
                print("❌ NER 모델 강제 로드 실패")
            
            return success
            
        except Exception as e:
            print(f"❌ NER 모델 로드 실패: {e}")
            return False
    
    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_pii_detected": 0,
            "processing_times": []
        }
        print("📊 통계가 초기화되었습니다.")

# ==================== 전역 인스턴스 ====================
_manager_instance = None

def get_manager() -> PseudonymizationManager:
    """매니저 싱글톤 인스턴스 반환"""
    global _manager_instance
    
    if _manager_instance is None:
        _manager_instance = PseudonymizationManager()
        _manager_instance.initialize()
    
    return _manager_instance

def is_manager_ready() -> bool:
    """매니저 준비 상태 확인"""
    manager = get_manager()
    return manager.is_ready()

def get_manager_status() -> Dict[str, Any]:
    """매니저 상태 정보 반환"""
    manager = get_manager()
    return manager.get_status()

def pseudonymize_with_manager(prompt: str, request_id: str = None) -> Dict[str, Any]:
    """매니저를 통한 가명화"""
    manager = get_manager()
    return manager.pseudonymize(prompt, request_id)

# ==================== 테스트 ====================
if __name__ == "__main__":
    print("📊 가명화 매니저 테스트")
    print("=" * 60)
    
    # 매니저 초기화
    manager = get_manager()
    
    # 상태 확인
    print("\n📈 초기 상태:")
    status = manager.get_status()
    for key, value in status.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for k, v in value.items():
                print(f"      {k}: {v}")
        else:
            print(f"   {key}: {value}")
    
    # 테스트 실행
    test_texts = [
        "김철수 고객님, 010-1234-5678로 연락드리겠습니다.",
        "남궁민수님이 서울시 강남구에 계십니다.",
        "황보석준 과장님의 이메일은 test@example.com입니다."
    ]
    
    print("\n🧪 가명화 테스트:")
    for i, text in enumerate(test_texts, 1):
        print(f"\n테스트 {i}: {text}")
        result = manager.pseudonymize(text, f"test_{i}")
        print(f"   가명화: {result['pseudonymized']}")
        print(f"   처리시간: {result['processing_time']}")
        print(f"   PII 개수: {len(result['detection']['items'])}")
    
    # 최종 상태
    print("\n📈 최종 상태:")
    status = manager.get_status()
    stats = status['statistics']
    print(f"   총 요청: {stats['total_requests']}")
    print(f"   성공률: {stats['success_rate']}")
    print(f"   총 PII 탐지: {stats['total_pii_detected']}")
    print(f"   평균 처리시간: {stats['avg_processing_time']}")