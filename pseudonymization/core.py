# pseudonymization/core.py - 모듈화된 핵심 기능 (실제 가명 치환)
import re
import time
import random
import asyncio
from typing import Dict, List, Any, Tuple

from .detection import detect_pii_enhanced
from .pools import get_pools, get_data_pool_stats

def create_fake_substitution_map(items: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """실제 가명으로 대체 맵 생성"""
    pools = get_pools()
    substitution_map = {}
    reverse_map = {}
    
    for item in items:
        original = item["value"]
        
        if original in substitution_map:
            continue
        
        if item["type"] == "이름":
            fake_name = pools.get_fake_name()
            substitution_map[original] = fake_name
            reverse_map[fake_name] = original
            
        elif item["type"] == "나이":
            age = int(original)
            fake_age = random.randint(max(20, age-10), min(80, age+10))
            fake_age_str = str(fake_age)
            substitution_map[original] = fake_age_str
            reverse_map[fake_age_str] = original
            
        elif item["type"] == "이메일":
            fake_email = pools.get_fake_email()
            substitution_map[original] = fake_email
            reverse_map[fake_email] = original
            
        elif item["type"] == "전화번호":
            fake_phone = pools.get_fake_phone()
            substitution_map[original] = fake_phone
            reverse_map[fake_phone] = original
            
        elif item["type"] == "주소":
            # 주소는 시/도 단위로만
            fake_address = pools.get_fake_address()
            substitution_map[original] = fake_address
            reverse_map[fake_address] = original
    
    return substitution_map, reverse_map

def apply_smart_substitutions(text: str, substitution_map: Dict[str, str]) -> str:
    """스마트 대체 적용 (강화된 주소 치환)"""
    result = text
    
    # 긴 문자열부터 대체 (겹치는 문제 방지)
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, replacement in sorted_items:
        # 주소의 경우 스마트 치환
        if original in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]:
            # 모든 가능한 주소 패턴들을 대체
            address_patterns = [
                # 1. 가장 복잡한 패턴부터
                rf'{re.escape(original)}(?:시|도)?\s+[가-힣\s\d,-]+(?:구|군|동|읍|면|로|가|번지|층|호)\s*\d*',
                rf'{re.escape(original)}(?:시|도)?\s+[가-힣]+(?:구|군)\s+[가-힣\s\d,-]+(?:동|로|가|번지)',
                rf'{re.escape(original)}(?:시|도)?\s+[가-힣]+(?:구|군)\s+[가-힣]+(?:동|로|가)',
                rf'{re.escape(original)}(?:시|도)?\s+[가-힣]+(?:구|군)',
                # 2. 기본 패턴
                rf'{re.escape(original)}(?:시|도)',
                rf'{re.escape(original)}'
            ]
            
            # 각 패턴을 순서대로 적용
            for pattern in address_patterns:
                def replace_address_func(match):
                    return replacement  # 간단한 지역명으로만 치환
                
                result = re.sub(pattern, replace_address_func, result)
        else:
            # 일반적인 치환
            result = result.replace(original, replacement)
    
    return result

async def pseudonymize_text_with_fake(text: str) -> Dict[str, Any]:
    """실제 가명을 사용한 가명화 (메인 함수)"""
    start_time = time.time()
    
    print(f"가명화 시작: {text[:50]}...")
    
    # 1. PII 탐지
    detection_start = time.time()
    items = await detect_pii_enhanced(text)
    detection_time = time.time() - detection_start
    
    # 2. 대체 맵 생성
    substitution_map, reverse_map = create_fake_substitution_map(items)
    
    # 3. 가명화 적용
    substitution_start = time.time()
    pseudonymized_text = apply_smart_substitutions(text, substitution_map)
    substitution_time = time.time() - substitution_start
    
    total_time = time.time() - start_time
    
    print(f"이전: {text}")
    print(f"가명화: {pseudonymized_text}")
    print(f"처리 시간: 탐지 {detection_time:.3f}초, 치환 {substitution_time:.3f}초, 전체 {total_time:.3f}초")
    print(f"완료 ({len(items)}개 항목 탐지)")
    
    return {
        "pseudonymized_text": pseudonymized_text,
        "original_text": text,
        "substitution_map": substitution_map,
        "reverse_map": reverse_map,
        "detected_items": len(items),
        "detection": {
            "items": [{"type": item["type"], "value": item["value"], "source": item["source"]} for item in items],
            "count": len(items)
        },
        "processing_time": total_time,
        "timings": {
            "detection": detection_time,
            "substitution": substitution_time,
            "total": total_time
        },
        "success": True
    }

def pseudonymize_text(text: str) -> Dict[str, Any]:
    """표준 가명화 함수 (동기 버전)"""
    return asyncio.run(pseudonymize_text_with_fake(text))

def restore_original(pseudonymized_text: str, reverse_map: Dict[str, str]) -> str:
    """원본 복원"""
    result = pseudonymized_text
    
    # 긴 문자열부터 복원
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake, original in sorted_items:
        result = result.replace(fake, original)
    
    return result

def workflow_process_ai_response(ai_response: str, reverse_map: Dict[str, str]) -> str:
    """AI 응답 복원 (워크플로우 모드)"""
    return restore_original(ai_response, reverse_map)

def load_data_pools():
    """데이터풀 로드 (호환성)"""
    from .pools import initialize_pools
    initialize_pools()
    return get_data_pool_stats()

def assign_realistic_values(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """현실적인 가명 할당 (호환성)"""
    substitution_map, _ = create_fake_substitution_map(items)
    return substitution_map

def create_masked_text(text: str, items: List[Dict[str, Any]]) -> str:
    """마스킹된 텍스트 생성 (호환성)"""
    substitution_map, _ = create_fake_substitution_map(items)
    return apply_smart_substitutions(text, substitution_map)