# pseudonymization/core.py
"""
워크플로우 기반 핵심 가명화 통합 모듈
토큰 기반 가명화 → AI 처리 → 토큰 복원
"""

import time
from typing import Dict, Any, List
from .pools import initialize_pools, get_pools
from .detection import detect_pii_enhanced
from .replacement import get_workflow_manager, apply_tokenization, restore_from_tokens, create_detailed_mapping_report

# 워크플로우 핵심 함수 export
__all__ = [
    'pseudonymize_text',
    'restore_original', 
    'workflow_process_ai_response',
    'load_data_pools',
    'get_data_pool_stats',
    'assign_realistic_values',
    'create_masked_text'
]

def pseudonymize_text(text: str, detailed_report: bool = True) -> Dict[str, Any]:
    """
    워크플로우 기반 통합 가명화 함수
    
    Args:
        text: 원본 텍스트
        detailed_report: 상세 리포트 생성 여부
        
    Returns:
        dict: 가명화 결과 (토큰화된 텍스트 포함)
    """
    start_time = time.time()
    print(f"🚀 워크플로우 기반 가명화 시작: {text[:50]}...")
    
    # 데이터풀 확인 및 초기화
    pools = get_pools()
    if not pools._initialized:
        print("📦 데이터풀 초기화 중...")
        initialize_pools()
    
    # PII 탐지 (워크플로우 기반)
    print("🔍 PII 탐지 (워크플로우 기반)")
    detection = detect_pii_enhanced(text)
    
    if not detection['items']:
        processing_time = time.time() - start_time
        print(f"❌ PII 탐지되지 않음. 처리 시간: {processing_time:.3f}초")
        return {
            "original": text,
            "pseudonymized": text,
            "pseudonymized_text": text,
            "tokenized_text": text,  # 워크플로우용
            "masked_prompt": text,
            "detection": detection,
            "substitution_map": {},
            "reverse_map": {},
            "token_map": {},  # 워크플로우용
            "mapping_report": "PII가 탐지되지 않았습니다.",
            "processing_time": processing_time,
            "stats": {
                "detected_items": 0,
                "replaced_items": 0,
                "detection_time": processing_time,
                "replacement_time": 0,
                "total_time": processing_time,
                "items_by_type": {},
                "detection_stats": detection['stats']
            }
        }
    
    # 토큰 기반 치환 처리
    detection_time = time.time() - start_time
    replacement_start = time.time()
    
    manager = get_workflow_manager()
    token_map = detection['stats']['token_map']
    substitution_map, reverse_map = manager.create_substitution_map(detection['items'], token_map)
    
    # 텍스트 토큰화
    tokenized_text = apply_tokenization(text, substitution_map)
    
    replacement_time = time.time() - replacement_start
    total_time = time.time() - start_time
    
    # 상세 리포트 생성
    mapping_report = ""
    if detailed_report:
        mapping_report = create_detailed_mapping_report(substitution_map, reverse_map)
    
    print(f"📝 이전: {text}")
    print(f"🏷️ 토큰화: {tokenized_text}")
    print(f"⏱️ 처리 시간: 탐지 {detection_time:.3f}초, 토큰화 {replacement_time:.3f}초, 전체 {total_time:.3f}초")
    
    # 결과 반환
    result = {
        "original": text,
        "pseudonymized": tokenized_text,  # 토큰화된 텍스트
        "pseudonymized_text": tokenized_text,  # 호환성
        "tokenized_text": tokenized_text,  # 워크플로우용 (AI로 전송할 텍스트)
        "masked_prompt": tokenized_text,  # 호환성
        "detection": detection,
        "substitution_map": substitution_map,  # 원본 → 토큰
        "reverse_map": reverse_map,  # 토큰 → 원본
        "token_map": token_map,  # 워크플로우용
        "mapping_report": mapping_report,
        "processing_time": total_time,
        "stats": {
            "detected_items": len(detection['items']),
            "replaced_items": len(substitution_map),
            "detection_time": detection_time,
            "replacement_time": replacement_time,
            "total_time": total_time,
            "items_by_type": detection['stats']['items_by_type'],
            "detection_stats": detection['stats']['detection_stats']
        }
    }
    
    return result

def restore_original(tokenized_text: str, reverse_map: Dict[str, str]) -> str:
    """토큰화된 텍스트를 원본으로 복원 (워크플로우 4단계)"""
    print("🔄 워크플로우 4단계: AI 응답 복원")
    return restore_from_tokens(tokenized_text, reverse_map)

def workflow_process_ai_response(ai_response: str, reverse_map: Dict[str, str]) -> str:
    """워크플로우 4단계: AI 응답을 복원하여 최종 답변 생성"""
    
    print("🤖 AI 응답 수신 및 복원 시작")
    print(f"🤖 AI 응답 (토큰화됨): {ai_response[:100]}...")
    
    # AI 응답에서 토큰을 원본으로 복원
    restored_response = restore_from_tokens(ai_response, reverse_map)
    
    print(f"✅ 복원된 최종 답변: {restored_response[:100]}...")
    
    return restored_response

def load_data_pools(custom_data: Dict = None):
    """데이터풀 로드"""
    print("📦 데이터풀 로딩 중...")
    initialize_pools(custom_data)
    print("📦 데이터풀 로딩 완료")

def get_data_pool_stats() -> Dict[str, int]:
    """데이터풀 통계 정보"""
    pools = get_pools()
    return {
        "탐지_이름수": len(pools.real_names),
        "탐지_주소수": len(pools.real_addresses),
        "탐지_도로수": len(pools.road_names),
        "탐지_시군구수": len(pools.districts),
        "탐지_시도수": len(pools.provinces),
        "회사수": len(pools.companies)
    }

# 호환성을 위한 기존 함수들
def assign_realistic_values(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """호환성을 위한 함수"""
    manager = get_workflow_manager()
    
    # 간단한 토큰 맵 생성
    token_map = {}
    for i, item in enumerate(items):
        token_map[item['value']] = f"[ITEM_{i}]"
    
    substitution_map, _ = manager.create_substitution_map(items, token_map)
    return substitution_map

def create_masked_text(text: str, substitution_map: Dict[str, str]) -> str:
    """호환성을 위한 함수"""
    return apply_tokenization(text, substitution_map)