# Manager
from typing import Dict, Any, Optional
from .model import load_model
from .core import pseudonymize_text

class PseudonymizationManager:
    """가명화 처리를 위한 중앙 관리 클래스"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self._initialized = False
    
    def initialize(self) -> None:
        """모델을 초기화합니다"""
        if self._initialized:
            print("⚠️  모델이 이미 초기화되어 있습니다.")
            return
            
        print("🤖 Qwen 모델 로딩 중...")
        self.model, self.tokenizer, self.device = load_model()
        self._initialized = True
        print(f"✅ 모델 로딩 완료! Device: {self.device}")
    
    def is_initialized(self) -> bool:
        """모델 초기화 상태를 확인합니다"""
        return self._initialized
    
    def pseudonymize(self, text: str) -> Dict[str, Any]:
        """텍스트를 가명화합니다
        
        Args:
            text: 가명화할 원본 텍스트
            
        Returns:
            Dict containing:
                - masked_prompt: 가명화된 텍스트
                - detection: 탐지된 개인정보 정보
                
        Raises:
            RuntimeError: 모델이 초기화되지 않은 경우
        """
        if not self._initialized:
            raise RuntimeError("모델이 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        
        return pseudonymize_text(text, self.model, self.tokenizer, self.device)
    
    def get_device_info(self) -> Dict[str, Any]:
        """현재 사용 중인 디바이스 정보를 반환합니다"""
        if not self._initialized:
            return {"status": "not_initialized"}
        
        import torch
        gpu_info = {}
        
        if self.device == "cuda" and torch.cuda.is_available():
            gpu_info = {
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB",
                "gpu_memory_allocated": f"{torch.cuda.memory_allocated(0) / 1e9:.1f}GB",
                "gpu_memory_cached": f"{torch.cuda.memory_reserved(0) / 1e9:.1f}GB"
            }
        
        return {
            "status": "initialized",
            "device": self.device,
            "gpu_info": gpu_info
        }

# singleton instance
_manager_instance: Optional[PseudonymizationManager] = None

def get_manager() -> PseudonymizationManager:
    """전역 PseudonymizationManager 인스턴스를 반환합니다"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = PseudonymizationManager()
    return _manager_instance
