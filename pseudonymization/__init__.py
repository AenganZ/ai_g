# pseudonymization/__init__.py - 모듈화된 초기화
"""
GenAI Pseudonymizer (AenganZ Enhanced) - 모듈화된 가명화 시스템

주요 기능:
- 실제 가명 치환 (김가명, 이가명 등)
- 강화된 PII 탐지 (이메일, 전화번호, 이름, 주소, 나이)
- 스마트 주소 처리 (첫 번째 주소만 치환)
- 일반명사 필터링 (고객, 손님 등 제외)
- Flask 기반 서버 호환
"""

# ===== 핵심 함수들 (core.py) =====
from .core import (
    pseudonymize_text,
    pseudonymize_text_with_fake,
    restore_original,
    workflow_process_ai_response,
    load_data_pools,
    get_data_pool_stats,
    assign_realistic_values,
    create_masked_text
)

# ===== 데이터풀 (pools.py) =====
from .pools import (
    DataPools,
    get_pools,
    initialize_pools,
    reload_pools,
    COMPOUND_SURNAMES,
    SINGLE_SURNAMES,
    NAME_EXCLUDE_WORDS
)

# ===== PII 탐지 (detection.py) =====
from .detection import (
    detect_pii_enhanced,
    detect_with_ner,
    detect_with_regex,
    detect_names_from_csv,
    detect_addresses_from_csv,
    merge_detections,
    is_valid_name,
    detect_emails,
    detect_phones,
    detect_names_from_realname_list,
    detect_names_from_patterns,
    detect_addresses_smart,
    detect_ages
)

# ===== 매니저 (manager.py) =====
from .manager import (
    PseudonymizationManager,
    get_manager,
    is_manager_ready,
    get_manager_status,
    pseudonymize_with_manager
)

# ===== 버전 정보 =====
__version__ = "4.0.0"
__title__ = "GenAI Pseudonymizer (AenganZ Enhanced)"
__description__ = "AI 서비스용 개인정보 가명화 시스템 (모듈화된 버전)"
__author__ = "AenganZ Development Team"

# ===== 공개 API =====
__all__ = [
    # 핵심 함수들
    'pseudonymize_text',
    'pseudonymize_text_with_fake',
    'restore_original',
    'workflow_process_ai_response',
    'load_data_pools',
    'get_data_pool_stats',
    'assign_realistic_values',
    'create_masked_text',
    
    # 데이터풀
    'DataPools',
    'get_pools',
    'initialize_pools',
    'reload_pools',
    'COMPOUND_SURNAMES',
    'SINGLE_SURNAMES',
    'NAME_EXCLUDE_WORDS',
    
    # PII 탐지
    'detect_pii_enhanced',
    'detect_with_ner',
    'detect_with_regex',
    'detect_names_from_csv',
    'detect_addresses_from_csv',
    'merge_detections',
    'is_valid_name',
    'detect_emails',
    'detect_phones',
    'detect_names_from_realname_list',
    'detect_names_from_patterns',
    'detect_addresses_smart',
    'detect_ages',
    
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
    print("주요 기능:")
    print("  - 실제 가명 치환 (김가명, 이가명 등)")
    print("  - 강화된 PII 탐지 (이메일, 전화번호, 이름, 주소, 나이)")
    print("  - 스마트 주소 처리 (첫 번째 주소만 치환)")
    print("  - 일반명사 필터링 (고객, 손님 등 제외)")
    print("  - Flask 기반 서버 호환")
    print()
    print("사용법:")
    print("  from pseudonymization import pseudonymize_text_with_fake")
    print("  result = pseudonymize_text_with_fake('김철수 고객님')")
    print("  print(result['pseudonymized_text'])")