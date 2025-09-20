# pseudonymization/__init__.py - 모듈 초기화
"""
GenAI Pseudonymizer (AenganZ Enhanced) - 가명화 모듈

이 모듈은 AenganZ의 강력한 PII 탐지 기능을 모듈화된 구조로 제공합니다.

주요 기능:
- NER 모델 + 정규식 + 데이터풀 기반 PII 탐지
- 실제 데이터 기반 자연스러운 가명화
- 양방향 매핑을 통한 완벽한 응답 복원
"""

# 핵심 함수들
from .core import (
    pseudonymize_text,
    detect_pii_enhanced,
    assign_realistic_values,
    create_masked_text,
    load_data_pools,
    get_data_pool_stats
)

# NER 모델
from .model import (
    load_ner_model,
    is_ner_loaded,
    extract_entities_with_ner,
    get_ner_model
)

# 매니저
from .manager import (
    PseudonymizationManager,
    get_manager,
    is_manager_ready,
    get_manager_status,
    pseudonymize_with_manager
)

# 버전 정보
__version__ = "2.0.0"
__title__ = "GenAI Pseudonymizer (AenganZ Enhanced)"
__description__ = "AI 서비스용 개인정보 가명화 시스템"

# 공개 API
__all__ = [
    # 핵심 함수들
    'pseudonymize_text',
    'detect_pii_enhanced', 
    'assign_realistic_values',
    'create_masked_text',
    'load_data_pools',
    'get_data_pool_stats',
    
    # NER 모델
    'load_ner_model',
    'is_ner_loaded',
    'extract_entities_with_ner',
    'get_ner_model',
    
    # 매니저
    'PseudonymizationManager',
    'get_manager',
    'is_manager_ready',
    'get_manager_status',
    'pseudonymize_with_manager',
    
    # 메타데이터
    '__version__',
    '__title__',
    '__description__'
]

# 모듈 로드 시 정보 출력
def _print_module_info():
    """모듈 정보 출력 (개발 모드에서만)"""
    import os
    if os.getenv('FLASK_DEBUG') == 'True' or os.getenv('DEBUG') == '1':
        print(f"📦 {__title__} v{__version__} 로드됨")
        print(f"   {__description__}")

# 개발 모드에서만 정보 출력
try:
    _print_module_info()
except:
    pass  # 오류 시 무시