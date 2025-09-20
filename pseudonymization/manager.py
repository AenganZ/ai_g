# pseudonymization/manager.py - AenganZ 통합 매니저
import threading
import time
from typing import Dict, Any

from .core import pseudonymize_text, load_data_pools, get_data_pool_stats
from .model import load_ner_model, is_ner_loaded

class PseudonymizationManager:
    """가명화 매니저 클래스 (AenganZ 방식)"""
    
    def __init__(self):
        self.initialized = False
        self.initialization_lock = threading.Lock()
        self.data_pools_loaded = False
        self.ner_model_loading = False
        
    def initialize(self):
        """매니저 초기화"""
        with self.initialization_lock:
            if self.initialized:
                return
                
            print("🔄 PseudonymizationManager 초기화 중...")
            
            try:
                # 1. 데이터풀 로드 (동기적으로)
                load_data_pools()
                self.data_pools_loaded = True
                print("✅ 데이터풀 로드 완료")
                
                # 2. NER 모델 백그라운드 로드 시작
                self._start_ner_model_loading()
                
                self.initialized = True
                print("✅ PseudonymizationManager 초기화 완료!")
                
            except Exception as e:
                print(f"❌ 매니저 초기화 실패: {e}")
                raise
    
    def _start_ner_model_loading(self):
        """NER 모델 백그라운드 로딩 시작"""
        if not self.ner_model_loading:
            self.ner_model_loading = True
            threading.Thread(
                target=self._load_ner_model_background, 
                daemon=True,
                name="NER-Model-Loader"
            ).start()
    
    def _load_ner_model_background(self):
        """백그라운드에서 NER 모델 로드"""
        try:
            print("🤖 백그라운드에서 NER 모델 로딩 시작...")
            success = load_ner_model()
            
            if success:
                print("✅ NER 모델 백그라운드 로딩 완료!")
            else:
                print("⚠️ NER 모델 로딩 실패 (기본 모드로 계속)")
                
        except Exception as e:
            print(f"❌ NER 모델 백그라운드 로딩 오류: {e}")
        finally:
            self.ner_model_loading = False
    
    def pseudonymize(self, prompt: str) -> Dict[str, Any]:
        """프롬프트 가명화"""
        # 매니저가 초기화되지 않았으면 초기화
        if not self.initialized:
            self.initialize()
        
        # 데이터풀이 로드되지 않았으면 오류
        if not self.data_pools_loaded:
            raise RuntimeError("데이터풀이 로드되지 않았습니다. 초기화를 다시 시도하세요.")
        
        # 가명화 실행
        return pseudonymize_text(prompt)
    
    def is_ready(self) -> bool:
        """매니저 준비 상태 확인"""
        return self.initialized and self.data_pools_loaded
    
    def get_status(self) -> Dict[str, Any]:
        """매니저 상태 정보 반환"""
        return {
            "initialized": self.initialized,
            "data_pools_loaded": self.data_pools_loaded,
            "ner_model_loaded": is_ner_loaded(),
            "ner_model_loading": self.ner_model_loading,
            "data_pool_stats": get_data_pool_stats() if self.data_pools_loaded else {}
        }
    
    def reload_data_pools(self):
        """데이터풀 다시 로드"""
        print("🔄 데이터풀 재로딩...")
        
        try:
            load_data_pools()
            self.data_pools_loaded = True
            print("✅ 데이터풀 재로딩 완료")
        except Exception as e:
            print(f"❌ 데이터풀 재로딩 실패: {e}")
            self.data_pools_loaded = False
            raise
    
    def force_load_ner_model(self):
        """NER 모델 강제 로드"""
        if self.ner_model_loading:
            print("⚠️ NER 모델이 이미 로딩 중입니다.")
            return False
        
        print("🤖 NER 모델 강제 로딩...")
        
        try:
            success = load_ner_model()
            if success:
                print("✅ NER 모델 강제 로딩 완료")
            return success
        except Exception as e:
            print(f"❌ NER 모델 강제 로딩 실패: {e}")
            return False

# 전역 매니저 인스턴스
_manager_instance = None
_manager_lock = threading.Lock()

def get_manager() -> PseudonymizationManager:
    """매니저 싱글톤 인스턴스 반환"""
    global _manager_instance
    
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = PseudonymizationManager()
                
                # 백그라운드에서 초기화 시작
                def background_init():
                    try:
                        _manager_instance.initialize()
                    except Exception as e:
                        print(f"❌ 백그라운드 초기화 실패: {e}")
                
                threading.Thread(
                    target=background_init, 
                    daemon=True,
                    name="Manager-Initializer"
                ).start()
    
    return _manager_instance

# 편의 함수들
def is_manager_ready() -> bool:
    """매니저 준비 상태 확인"""
    manager = get_manager()
    return manager.is_ready()

def get_manager_status() -> Dict[str, Any]:
    """매니저 상태 정보 반환"""
    manager = get_manager()
    return manager.get_status()

def pseudonymize_with_manager(prompt: str) -> Dict[str, Any]:
    """매니저를 통한 가명화"""
    manager = get_manager()
    return manager.pseudonymize(prompt)