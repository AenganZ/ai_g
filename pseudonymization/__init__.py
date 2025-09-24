# pseudonymization/__init__.py - 강화된 복원 함수 포함 버전
"""
GenAI Pseudonymizer (AenganZ Enhanced) - 강화된 역복호화 버전

주요 기능:
- 강화된 조사 처리 (님, 씨, 이, 가, 을, 를 등)
- 1:1 매핑 전략으로 정확한 복원
- 존칭 보존 처리
- 실제 가명 치환 (김가명, 이가명 등)
- 스마트 주소 처리 (개별 매핑)
- 일반명사 필터링 (고객, 손님 등 제외)
"""

# 핵심 함수들 (core.py)
from .core import (
    pseudonymize_text,
    pseudonymize_text_with_fake,
    restore_original,
    restore_original_enhanced,  # ⭐ 새로 추가
    workflow_process_ai_response,
    get_data_pool_stats,
    create_enhanced_substitution_map,  # ⭐ 새로 추가
    apply_enhanced_substitutions  # ⭐ 새로 추가
)

# 데이터풀 (pools.py)
from .pools import (
    get_pools,
    initialize_pools,
    NAME_EXCLUDE_WORDS
)

# PII 탐지 (normalizers.py에서 통합)
from .normalizers import (
    detect_pii_all,
    detect_emails,
    detect_phones,
    detect_names,
    detect_addresses,
    detect_ages,
    smart_clean_korean_text,  # ⭐ 새로 추가
    is_valid_korean_name,  # ⭐ 새로 추가
    # 호환성 함수들
    detect_pii_enhanced,
    detect_with_ner,
    detect_with_regex,
    detect_names_from_csv,
    detect_addresses_from_csv,
    merge_detections
)

# 매니저 (manager.py)
from .manager import (
    get_manager,
    is_manager_ready,
    get_manager_status
)

# 버전 정보 (업데이트)
__version__ = "4.2.0"  # 강화된 역복호화 버전
__title__ = "GenAI Pseudonymizer (AenganZ Enhanced) - Enhanced Reverse Decryption"
__description__ = "AI 서비스용 개인정보 가명화 시스템 (강화된 역복호화 버전)"
__author__ = "AenganZ Development Team"

# 확장된 공개 API
__all__ = [
    # 핵심 함수들 (강화됨)
    'pseudonymize_text',
    'pseudonymize_text_with_fake',
    'restore_original',
    'restore_original_enhanced',  # ⭐ 새로 추가
    'workflow_process_ai_response',
    'get_data_pool_stats',
    'create_enhanced_substitution_map',  # ⭐ 새로 추가
    'apply_enhanced_substitutions',  # ⭐ 새로 추가
    
    # 데이터풀
    'get_pools',
    'initialize_pools',
    'NAME_EXCLUDE_WORDS',
    
    # PII 탐지 (강화됨)
    'detect_pii_all',
    'detect_emails',
    'detect_phones', 
    'detect_names',
    'detect_addresses',
    'detect_ages',
    'smart_clean_korean_text',  # ⭐ 새로 추가
    'is_valid_korean_name',  # ⭐ 새로 추가
    'detect_pii_enhanced',  # 호환성
    'detect_with_ner',      # 호환성
    'detect_with_regex',    # 호환성
    'detect_names_from_csv', # 호환성
    'detect_addresses_from_csv', # 호환성
    'merge_detections',     # 호환성
    
    # 매니저
    'get_manager',
    'is_manager_ready',
    'get_manager_status',
    
    # 메타데이터
    '__version__',
    '__title__',
    '__description__',
    '__author__'
]

def print_info():
    """정보 출력 (업데이트)"""
    print(f"{__title__} v{__version__}")
    print(f"{__description__}")
    print(f"작성자: {__author__}")
    print()
    print("⭐ 강화된 역복호화 기능:")
    print("  - 한국어 조사 인식 및 처리 (님, 씨, 이, 가, 을, 를 등)")
    print("  - 1:1 매핑 전략으로 정확한 복원")
    print("  - 존칭 보존 처리")
    print("  - 문맥적 패턴 매칭")
    print()
    print("주요 기능:")
    print("  - 실제 가명 치환 (김가명, 이가명 등)")
    print("  - 강화된 PII 탐지 (이메일, 전화번호, 이름, 주소, 나이)")
    print("  - 스마트 주소 처리 (개별 매핑)")
    print("  - 일반명사 필터링 (고객, 손님 등 제외)")
    print("  - Flask 기반 서버 호환")
    print("  - 브라우저 확장 프로그램 호환")
    print()
    print("사용법:")
    print("  from pseudonymization import pseudonymize_text_with_fake, restore_original_enhanced")
    print("  result = pseudonymize_text_with_fake('김철수님이 부산에서 살고 있습니다')")
    print("  restored = restore_original_enhanced(ai_response, result['reverse_map'])")
    print()
    print("역복호화 테스트:")
    print("  입력: '김철수님이 부산 해운대구에서 살고 있습니다'")
    print("  가명화: '김가명님이 서울 강남구에서 살고 있습니다'")
    print("  AI응답: '김가명님께서 서울 강남구에 거주하시는군요'")
    print("  복원: '김철수님께서 부산 해운대구에 거주하시는군요'")

def test_enhanced_restoration():
    """강화된 복원 기능 테스트"""
    print("🧪 강화된 복원 기능 테스트 시작...")
    
    # 테스트 데이터
    test_cases = [
        {
            "name": "이름 + 존칭",
            "original": "김철수님이 문의했습니다",
            "fake_map": {"김가명": "김철수"},
            "ai_response": "김가명님의 문의를 확인했습니다",
            "expected": "김철수님의 문의를 확인했습니다"
        },
        {
            "name": "주소 개별 매핑",
            "original": "부산 해운대구에서 살고 있습니다",
            "fake_map": {"서울": "부산", "강남구": "해운대구"},
            "ai_response": "서울 강남구는 좋은 곳이네요",
            "expected": "부산 해운대구는 좋은 곳이네요"
        },
        {
            "name": "전화번호",
            "original": "010-1234-5678로 연락주세요",
            "fake_map": {"010-0000-0001": "010-1234-5678"},
            "ai_response": "010-0000-0001로 연락드리겠습니다",
            "expected": "010-1234-5678로 연락드리겠습니다"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n테스트 {i}: {test_case['name']}")
        print(f"  AI 응답: {test_case['ai_response']}")
        
        try:
            restored = restore_original_enhanced(test_case['ai_response'], test_case['fake_map'])
            print(f"  복원 결과: {restored}")
            print(f"  예상 결과: {test_case['expected']}")
            
            if restored == test_case['expected']:
                print(f"  ✅ 성공")
            else:
                print(f"  ❌ 실패")
        except Exception as e:
            print(f"  💥 오류: {e}")
    
    print("\n🧪 테스트 완료")

# 모듈 로드 시 정보 출력 (선택적)
if __name__ == "__main__":
    print_info()
    test_enhanced_restoration()