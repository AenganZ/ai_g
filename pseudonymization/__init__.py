# pseudonymization/__init__.py
"""
GenAI Pseudonymizer (AenganZ Enhanced) - 워크플로우 기반 가명화 모듈

워크플로우:
1. 프롬프트 가로채기 → 치환 맵 생성
2. PII 탐지 → 토큰으로 치환 ([PER_0], [ORG_0], [LOC_0] 등)
3. 토큰화된 프롬프트를 AI로 전송
4. AI 응답을 토큰에서 원본으로 복원
"""

# 핵심 함수들 (core.py)
from .core import (
    pseudonymize_text,
    pseudonymize_text_with_fake,  # 추가
    restore_original,
    workflow_process_ai_response,
    load_data_pools,
    get_data_pool_stats,
    assign_realistic_values,
    create_masked_text
)

# 데이터풀 (pools.py)
from .pools import (
    DataPools,
    get_pools,
    initialize_pools,
    reload_pools,
    COMPOUND_SURNAMES,
    SINGLE_SURNAMES,
    NAME_EXCLUDE_WORDS
)

# PII 탐지 (detection.py)
from .detection import (
    detect_pii_enhanced,
    detect_with_ner,
    detect_with_regex,
    detect_names_from_csv,
    detect_addresses_from_csv,
    merge_detections
)

# 가명화 치환 (replacement.py)
from .replacement import (
    ReplacementManager,
    WorkflowReplacementManager,  # 추가
    get_workflow_manager,  # 추가
    apply_replacements,
    apply_tokenization,  # 추가
    restore_text,
    restore_from_tokens,  # 추가
    create_detailed_mapping_report,  # 추가
    remove_duplicates
)

# NER 모델 (model.py)
from .model import (
    load_ner_model,
    is_ner_loaded,
    extract_entities_with_ner,
    get_ner_model
)

# 매니저 (manager.py)
from .manager import (
    PseudonymizationManager,
    get_manager,
    is_manager_ready,
    get_manager_status,
    pseudonymize_with_manager
)

# 버전 정보
__version__ = "4.0.0"
__title__ = "GenAI Pseudonymizer (AenganZ Enhanced)"
__description__ = "AI 서비스용 개인정보 가명화 시스템"
__author__ = "AenganZ Development Team"

# 공개 API
__all__ = [
    # 핵심 함수들
    'pseudonymize_text',
    'pseudonymize_text_with_fake',  # 추가
    'restore_original',
    'workflow_process_ai_response',
    'load_data_pools',
    'get_data_pool_stats',
    
    # 데이터풀
    'DataPools',
    'get_pools',
    'initialize_pools',
    'reload_pools',
    
    # PII 탐지
    'detect_pii_enhanced',
    'detect_with_ner',
    'detect_with_regex',
    'detect_names_from_csv',
    'detect_addresses_from_csv',
    
    # 가명화 치환
    'ReplacementManager',
    'WorkflowReplacementManager',  # 추가
    'get_workflow_manager',  # 추가
    'apply_replacements',
    'apply_tokenization',  # 추가
    'restore_text',
    'restore_from_tokens',  # 추가
    'create_detailed_mapping_report',  # 추가
    
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
    '__description__',
    '__author__'
]

def print_info():
    """정보 출력"""
    print(f"{__title__} v{__version__}")
    print(f"{__description__}")
    print(f"작성자: {__author__}")
    print()
    print("워크플로우:")
    print("  1. 프롬프트 가로채기 → 치환 맵 생성")
    print("  2. PII 탐지 → 토큰으로 치환")
    print("  3. 토큰화된 프롬프트를 AI로 전송")
    print("  4. AI 응답을 토큰에서 원본으로 복원")