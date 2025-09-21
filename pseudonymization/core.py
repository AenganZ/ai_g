# pseudonymization/core.py
"""
핵심 가명화 통합 모듈
pools, detection, replacement 모듈을 활용한 통합 인터페이스
"""

from typing import Dict, Any
from .pools import initialize_pools, get_pools
from .detection import detect_pii_enhanced
from .replacement import ReplacementManager, apply_replacements, restore_text

# 전역 ReplacementManager
_replacement_manager = None

def get_replacement_manager() -> ReplacementManager:
    """ReplacementManager 싱글톤 인스턴스"""
    global _replacement_manager
    if _replacement_manager is None:
        _replacement_manager = ReplacementManager()
    return _replacement_manager

def pseudonymize_text(text: str) -> Dict[str, Any]:
    """
    통합 가명화 함수
    
    Args:
        text: 원본 텍스트
        
    Returns:
        dict: {
            "original": 원본 텍스트,
            "pseudonymized": 가명화된 텍스트,
            "masked_prompt": 가명화된 텍스트 (호환성),
            "detection": PII 탐지 결과,
            "substitution_map": 원본→가명 매핑,
            "reverse_map": 가명→원본 매핑
        }
    """
    print(f"🔍 가명화 시작: {text[:50]}...")
    
    # 1. PII 탐지
    detection = detect_pii_enhanced(text)
    
    if not detection['items']:
        print("ℹ️ PII가 탐지되지 않았습니다.")
        return {
            "original": text,
            "pseudonymized": text,
            "masked_prompt": text,  # 호환성을 위해 추가
            "detection": detection,
            "substitution_map": {},
            "reverse_map": {}
        }
    
    # 2. 치환값 할당
    manager = get_replacement_manager()
    substitution_map, reverse_map = manager.assign_replacements(detection['items'])
    
    # 3. 텍스트 치환
    pseudonymized = apply_replacements(text, substitution_map)
    
    print(f"🔧 치환 전: {text}")
    print(f"🔧 치환 후: {pseudonymized}")
    
    # 4. 결과 반환 (masked_prompt 키 추가)
    result = {
        "original": text,
        "pseudonymized": pseudonymized,
        "masked_prompt": pseudonymized,  # 호환성을 위해 추가
        "detection": detection,
        "substitution_map": substitution_map,
        "reverse_map": reverse_map
    }
    
    print(f"✅ 가명화 완료: {len(detection['items'])}개 PII 처리")
    
    return result

def restore_original(pseudonymized_text: str, reverse_map: Dict[str, str]) -> str:
    """
    가명화된 텍스트를 원본으로 복원
    
    Args:
        pseudonymized_text: 가명화된 텍스트
        reverse_map: 가명→원본 매핑
        
    Returns:
        str: 복원된 원본 텍스트
    """
    return restore_text(pseudonymized_text, reverse_map)

def load_data_pools(custom_data: Dict = None):
    """데이터풀 로드"""
    initialize_pools(custom_data)

def get_data_pool_stats() -> Dict[str, int]:
    """데이터풀 통계"""
    pools = get_pools()
    return {
        "names": len(pools.names),
        "fake_names": len(pools.fake_names),
        "emails": len(pools.emails),
        "phones": len(pools.phones),
        "addresses": len(pools.addresses),
        "companies": len(pools.companies)
    }

# 호환성을 위한 함수들
def assign_realistic_values(items):
    """기존 코드 호환성을 위한 함수"""
    manager = get_replacement_manager()
    return manager.assign_replacements(items)

def create_masked_text(text, items, substitution_map):
    """기존 코드 호환성을 위한 함수"""
    return apply_replacements(text, substitution_map)

# ==================== 테스트 ====================
if __name__ == "__main__":
    print("🎭 통합 가명화 코어 모듈 테스트")
    print("=" * 60)
    
    # 데이터풀 초기화
    load_data_pools()
    
    # 테스트 케이스들
    test_cases = [
        "김철수 고객님, 부산 해운대구 예약이 확인되었습니다. 문의사항은 010-9876-5432로 연락 주세요.",
        "안녕하세요, 제 이름은 홍길동이고 연락처는 010-1234-5678입니다. 서울 강남구에 살고 있습니다.",
        "남궁민수님의 이메일은 test@example.com이고, 삼성전자에서 근무하십니다.",
        "황보석준 과장님이 대전시 서구에 계십니다. 02-1234-5678로 연락 가능합니다.",
        "제갈공명 선생님은 45세이고, 주민번호는 781225-1234567입니다."
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n📝 테스트 케이스 {i}")
        print("=" * 60)
        
        # 가명화
        result = pseudonymize_text(test_text)
        
        print(f"\n🎯 최종 결과:")
        print(f"   원본: {result['original']}")
        print(f"   가명: {result['pseudonymized']}")
        print(f"   탐지: {len(result['detection']['items'])}개 항목")
        
        for idx, item in enumerate(result['detection']['items'], 1):
            original_value = item['value']
            pseudo_value = result['substitution_map'].get(original_value, original_value)
            print(f"   #{idx} {item['type']}: '{original_value}' → '{pseudo_value}'")
        
        # 복원 테스트
        restored = restore_original(result['pseudonymized'], result['reverse_map'])
        print(f"\n🔄 복원 테스트:")
        print(f"   복원: {restored}")
        print(f"   일치: {restored == result['original']}")