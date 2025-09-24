# pseudonymization/manager.py - 모듈화된 매니저
import time
from typing import Dict, Any, Optional

from .core import pseudonymize_text_with_fake, get_data_pool_stats
from .pools import initialize_pools, get_pools

class PseudonymizationManager:
    """가명화 매니저 클래스"""
    
    def __init__(self):
        self.initialized = False
        self.pools = None
        self.stats = {}
        
    def initialize(self):
        """매니저 초기화"""
        try:
            print("가명화매니저 초기화 중...")
            initialize_pools()
            self.pools = get_pools()
            self.stats = get_data_pool_stats()
            self.initialized = True
            print("가명화매니저 초기화 완료")
            return True
        except Exception as e:
            print(f"매니저 초기화 실패: {e}")
            return False
    
    def is_ready(self) -> bool:
        """매니저 준비 상태 확인"""
        return self.initialized and self.pools is not None
    
    def get_status(self) -> Dict[str, Any]:
        """매니저 상태 반환"""
        return {
            "initialized": self.initialized,
            "ready": self.is_ready(),
            "stats": self.stats,
            "timestamp": time.time()
        }
    
    async def pseudonymize(self, text: str) -> Dict[str, Any]:
        """가명화 실행"""
        if not self.is_ready():
            raise RuntimeError("매니저가 초기화되지 않았습니다")
        
        return await pseudonymize_text_with_fake(text)
    
    def reset_counters(self):
        """카운터 리셋"""
        if self.pools:
            self.pools.reset_counters()
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        if self.pools:
            return get_data_pool_stats()
        return {}

# 전역 매니저 인스턴스
_manager: Optional[PseudonymizationManager] = None

def get_manager() -> PseudonymizationManager:
    """매니저 인스턴스 반환"""
    global _manager
    if _manager is None:
        _manager = PseudonymizationManager()
        _manager.initialize()
    return _manager

def is_manager_ready() -> bool:
    """매니저 준비 상태 확인"""
    try:
        manager = get_manager()
        return manager.is_ready()
    except:
        return False

def get_manager_status() -> Dict[str, Any]:
    """매니저 상태 반환"""
    try:
        manager = get_manager()
        return manager.get_status()
    except Exception as e:
        return {
            "initialized": False,
            "ready": False,
            "error": str(e),
            "timestamp": time.time()
        }

async def pseudonymize_with_manager(text: str) -> Dict[str, Any]:
    """매니저를 통한 가명화"""
    manager = get_manager()
    return await manager.pseudonymize(text)