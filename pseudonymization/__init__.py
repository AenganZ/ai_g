# pseudonymization/__init__.py
"""
GenAI Pseudonymizer (AenganZ Enhanced) - 워크플로우 기반 가명화 모듈

워크플로우:
1. 프롬프트 가로채기 → 치환 맵 생성
2. PII 탐지 → 토큰으로 치환 ([PER_0], [ORG_0], [LOC_0] 등)
3. 토큰화된 프롬프트를 AI로 전송
4. AI 응답을 토큰에서 원본으로 복원

- pools.py: 데이터풀 관리
- detection.py: 워크플로우 기반 PII 탐지 (1차 정규식 + 2차 NER)
- replacement.py: 토큰 기반 치환
- core.py: 워크플로우 통합 인터페이스
- model.py: NER 모델 (2차 보강용)
- manager.py: 전체 관리
"""

# 핵심 함수들 (core.py)
from .core import (
    pseudonymize_text,
    restore_original,
    workflow_process_ai_response,  # 워크플로우 4단계
    load_data_pools,
    get_data_pool_stats,
    # 호환성
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

# PII 탐지 (detection.py) - 워크플로우 기반
from .detection import (
    detect_pii_enhanced,
    detect_with_ner,
    detect_with_ner_simple,
    detect_with_regex,
    detect_names_from_csv,
    detect_addresses_from_csv,
    merge_detections,
    assign_tokens  # 워크플로우용
)

# 가명화 치환 (replacement.py) - 토큰 기반
from .replacement import (
    ReplacementManager,
    WorkflowReplacementManager,  # 워크플로우용
    apply_replacements,
    apply_tokenization,  # 워크플로우용
    restore_text,
    restore_from_tokens,  # 워크플로우용
    remove_duplicates
)

# NER 모델 (model.py)
from .model import (
    load_ner_model,
    is_ner_loaded,
    extract_entities_with_ner,
    get_ner_model,
    WorkingNERModel
)

# 매니저 (manager.py) - 워크플로우 기반
from .manager import (
    PseudonymizationManager,
    get_manager,
    is_manager_ready,
    get_manager_status,
    pseudonymize_with_manager
)

# 버전 정보
__version__ = "4.0.0"
__title__ = "GenAI Pseudonymizer (AenganZ Enhanced - 워크플로우)"
__description__ = "워크플로우 기반 AI 서비스용 개인정보 가명화 시스템"
__author__ = "AenganZ Development Team"

# 공개 API
__all__ = [
    # 핵심 함수들
    'pseudonymize_text',
    'restore_original',
    'workflow_process_ai_response',  # 워크플로우 4단계
    'load_data_pools',
    'get_data_pool_stats',
    
    # 데이터풀
    'DataPools',
    'get_pools',
    'initialize_pools',
    'reload_pools',
    
    # PII 탐지 (워크플로우)
    'detect_pii_enhanced',
    'detect_with_ner',
    'detect_with_ner_simple',
    'detect_with_regex',
    'detect_names_from_csv',
    'detect_addresses_from_csv',
    'assign_tokens',  # 워크플로우용
    
    # 가명화 치환 (토큰 기반)
    'ReplacementManager',
    'WorkflowReplacementManager',
    'apply_replacements',
    'apply_tokenization',  # 워크플로우용
    'restore_text',
    'restore_from_tokens',  # 워크플로우용
    
    # NER 모델
    'load_ner_model',
    'is_ner_loaded',
    'extract_entities_with_ner',
    'get_ner_model',
    
    # 매니저 (워크플로우)
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

def print_workflow_info():
    """워크플로우 정보 출력"""
    print(f"{__title__} v{__version__}")
    print(f"{__description__}")
    print(f"작성자: {__author__}")
    print()
    print("워크플로우:")
    print("  1. 프롬프트 가로채기 → 치환 맵 생성")
    print("  2. PII 탐지 → 토큰으로 치환 ([PER_0], [ORG_0], [LOC_0] 등)")  
    print("  3. 토큰화된 프롬프트를 AI로 전송")
    print("  4. AI 응답을 토큰에서 원본으로 복원")
    print()
    print("모듈 구조:")
    print("  detection.py - 워크플로우 기반 PII 탐지 (1차 정규식 + 2차 NER)")
    print("  replacement.py - 토큰 기반 치환")
    print("  core.py - 워크플로우 통합 인터페이스")
    print("  manager.py - 전체 관리")

# 호환성을 위한 함수명
def print_info():
    """호환성을 위한 함수"""
    print_workflow_info()