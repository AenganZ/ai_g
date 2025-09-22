# pseudonymization/core.py - normalizers.py만 사용하도록 수정
import re
import time
import random
import asyncio
from typing import Dict, List, Any, Tuple

from .normalizers import detect_pii_all  # detection.py 대신 normalizers.py 사용
from .pools import get_pools, get_data_pool_stats

def create_fake_substitution_map(items: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """실제 가명으로 대체 맵 생성"""
    pools = get_pools()
    substitution_map = {}
    reverse_map = {}
    
    # 주소 항목들을 먼저 처리
    address_items = [item for item in items if item["type"] == "주소"]
    non_address_items = [item for item in items if item["type"] != "주소"]
    
    # 주소 스마트 처리: 첫 번째 주소만 가명 주소로 치환
    if address_items:
        main_address = address_items[0]
        original = main_address["value"]
        fake_address = pools.get_fake_address()
        
        substitution_map[original] = fake_address
        reverse_map[fake_address] = original
        print(f"주소 치환: '{original}' → '{fake_address}'")
    
    # 나머지 항목들 처리
    for item in non_address_items:
        original = item["value"]
        
        if original in substitution_map:
            continue
        
        if item["type"] == "이름":
            fake_name = pools.get_fake_name()
            substitution_map[original] = fake_name
            reverse_map[fake_name] = original
            print(f"이름 치환: '{original}' → '{fake_name}'")
            
        elif item["type"] == "나이":
            try:
                age = int(original)
                min_age = max(20, age - 5)
                max_age = min(80, age + 5)
                
                if min_age >= max_age:
                    fake_age = age
                else:
                    fake_age = random.randint(min_age, max_age)
                
                fake_age_str = str(fake_age)
                substitution_map[original] = fake_age_str
                reverse_map[fake_age_str] = original
                print(f"나이 치환: '{original}' → '{fake_age_str}'")
            except (ValueError, TypeError):
                print(f"나이 치환 실패 (원본 유지): '{original}'")
                
        elif item["type"] == "이메일":
            fake_email = pools.get_fake_email()
            substitution_map[original] = fake_email
            reverse_map[fake_email] = original
            print(f"이메일 치환: '{original}' → '{fake_email}'")
            
        elif item["type"] == "전화번호":
            fake_phone = pools.get_fake_phone()
            substitution_map[original] = fake_phone
            reverse_map[fake_phone] = original
            print(f"전화번호 치환: '{original}' → '{fake_phone}'")
    
    return substitution_map, reverse_map

def apply_smart_substitutions(text: str, substitution_map: Dict[str, str]) -> str:
    """스마트 대체 적용"""
    result = text
    
    # 긴 문자열부터 대체
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, replacement in sorted_items:
        # 주소의 경우 연속된 구문을 모두 치환
        if original in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]:
            address_patterns = [
                rf'{re.escape(original)}(?:시|도)?\s+[가-힣\s\d,-]+(?:구|군|동|읍|면|로|가|번지|층|호)\s*\d*',
                rf'{re.escape(original)}(?:시|도)?\s+[가-힣]+(?:구|군)\s+[가-힣\s\d,-]+(?:동|로|가|번지)',
                rf'{re.escape(original)}(?:시|도)?\s+[가-힣]+(?:구|군)',
                rf'{re.escape(original)}(?:시|도)',
                rf'{re.escape(original)}'
            ]
            
            for pattern in address_patterns:
                old_result = result
                result = re.sub(pattern, replacement, result)
                if old_result != result:
                    print(f"주소 패턴 치환: '{pattern}' → '{replacement}'")
                    break
        else:
            result = result.replace(original, replacement)
    
    return result

async def pseudonymize_text_with_fake(text: str) -> Dict[str, Any]:
    """실제 가명을 사용한 가명화 (normalizers.py 전용)"""
    start_time = time.time()
    
    print(f"\n=== normalizers.py 기반 가명화 시작 ===")
    
    # 1. normalizers.py로 PII 탐지
    detection_start = time.time()
    items = await detect_pii_all(text)
    detection_time = time.time() - detection_start
    
    print(f"탐지 완료: {len(items)}개 항목")
    for item in items:
        print(f"  - {item['type']}: '{item['value']}' (출처: {item['source']})")
    
    # 2. 대체 맵 생성
    substitution_map, reverse_map = create_fake_substitution_map(items)
    
    # 3. 가명화 적용
    substitution_start = time.time()
    pseudonymized_text = apply_smart_substitutions(text, substitution_map)
    substitution_time = time.time() - substitution_start
    
    total_time = time.time() - start_time
    
    print(f"\n치환 결과:")
    print(f"  원본: {text}")
    print(f"  가명화: {pseudonymized_text}")
    print(f"  처리시간: {total_time:.3f}초")
    print("=== 가명화 완료 ===\n")
    
    return {
        "pseudonymized_text": pseudonymized_text,
        "original_text": text,
        "substitution_map": substitution_map,
        "reverse_map": reverse_map,
        "detected_items": len(items),
        "detection": {
            "items": [
                {
                    "type": item["type"], 
                    "value": item["value"], 
                    "source": item["source"],
                    "confidence": item.get("confidence", 0.8)
                } 
                for item in items
            ],
            "count": len(items),
            "contains_pii": len(items) > 0
        },
        "processing_time": total_time,
        "timings": {
            "detection": detection_time,
            "substitution": substitution_time,
            "total": total_time
        },
        "success": True,
        # 브라우저 익스텐션 호환을 위한 추가 필드
        "mapping": [
            {
                "type": item["type"],
                "value": item["value"],
                "token": substitution_map.get(item["value"], item["value"]),
                "original": item["value"],
                "source": item["source"],
                "confidence": item.get("confidence", 0.8)
            }
            for item in items
        ],
        "masked_prompt": pseudonymized_text
    }

def pseudonymize_text(text: str) -> Dict[str, Any]:
    """표준 가명화 함수 (동기 버전)"""
    return asyncio.run(pseudonymize_text_with_fake(text))

def restore_original(pseudonymized_text: str, reverse_map: Dict[str, str]) -> str:
    """원본 복원"""
    result = pseudonymized_text
    
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake, original in sorted_items:
        result = result.replace(fake, original)
    
    return result

def workflow_process_ai_response(ai_response: str, reverse_map: Dict[str, str]) -> str:
    """AI 응답 복원"""
    return restore_original(ai_response, reverse_map)

def load_data_pools():
    """데이터풀 로드"""
    from .pools import initialize_pools
    initialize_pools()
    return get_data_pool_stats()

def assign_realistic_values(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """현실적인 가명 할당"""
    substitution_map, _ = create_fake_substitution_map(items)
    return substitution_map

def create_masked_text(text: str, items: List[Dict[str, Any]]) -> str:
    """마스킹된 텍스트 생성"""
    substitution_map, _ = create_fake_substitution_map(items)
    return apply_smart_substitutions(text, substitution_map)