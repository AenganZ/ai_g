# pseudonymization/__init__.py
"""
GenAI Pseudonymizer (Future-Enhanced) - 가명화 모듈

구조화된 모듈로 재설계된 가명화 시스템
- pools.py: 데이터풀 관리
- detection.py: PII 탐지
- replacement.py: 가명화 치환
- core.py: 통합 인터페이스
- model.py: NER 모델
- manager.py: 전체 관리
"""

# 핵심 함수들 (core.py)
from .core import (
    pseudonymize_text,
    restore_original,
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
    apply_replacements,
    restore_text,
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

# 매니저 (manager.py)
from .manager import (
    PseudonymizationManager,
    get_manager,
    is_manager_ready,
    get_manager_status,
    pseudonymize_with_manager
)

# 버전 정보
__version__ = "3.0.0"
__title__ = "GenAI Pseudonymizer (Future-Enhanced)"
__description__ = "구조화된 AI 서비스용 개인정보 가명화 시스템"
__author__ = "Future Development Team"

# 공개 API
__all__ = [
    # 핵심 함수들
    'pseudonymize_text',
    'restore_original',
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
    'apply_replacements',
    'restore_text',
    
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

# 모듈 로드 시 정보 출력
def _print_module_info():
    """모듈 정보 출력"""
    import os
    if os.getenv('DEBUG') == '1' or os.getenv('FLASK_DEBUG') == 'True':
        print(f"📦 {__title__} v{__version__}")
        print(f"   {__description__}")
        print(f"   작성자: {__author__}")
        print(f"   모듈 구조:")
        print(f"      📂 pools.py - 데이터풀 관리")
        print(f"      🔍 detection.py - PII 탐지")
        print(f"      🔄 replacement.py - 가명화 치환")
        print(f"      🎯 core.py - 통합 인터페이스")
        print(f"      🤖 model.py - NER 모델")
        print(f"      📊 manager.py - 전체 관리")

# 자동 초기화 (옵션)
def auto_initialize():
    """자동 초기화"""
    try:
        # 데이터풀 초기화
        initialize_pools()
        
        # NER 모델 백그라운드 로드 시작
        import threading
        threading.Thread(
            target=load_ner_model,
            daemon=True,
            name="NER-AutoLoader"
        ).start()
        
        print("✅ 가명화 모듈 자동 초기화 완료")
    except Exception as e:
        print(f"⚠️ 자동 초기화 실패: {e}")

# 개발 모드에서 정보 출력
try:
    _print_module_info()
    # 자동 초기화 (필요시 주석 해제)
    # auto_initialize()
except:
    pass