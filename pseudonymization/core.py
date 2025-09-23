# pseudonymization/core.py - normalizers.py만 사용하도록 수정
import re
import time
import random
import asyncio
from typing import Dict, List, Any, Tuple

from .normalizers import detect_pii_all  # detection.py 대신 normalizers.py 사용
from .pools import get_pools, get_data_pool_stats

def create_fake_substitution_map(items: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """실제 가명으로 대체 맵 생성 (주소 순서 수정 및 중복 제거)"""
    pools = get_pools()
    substitution_map = {}
    reverse_map = {}
    
    print(f"🔧 대체 맵 생성 시작: {len(items)}개 항목")
    
    # ⭐ 먼저 중복 제거 (같은 값이 여러 번 탐지되는 경우)
    seen_values = set()
    unique_items = []
    for item in items:
        key = (item["type"], item["value"])
        if key not in seen_values:
            unique_items.append(item)
            seen_values.add(key)
        else:
            print(f"🔄 중복 제거: {item['type']} '{item['value']}'")
    
    print(f"🧹 중복 제거 후: {len(unique_items)}개 항목")
    
    # 주소와 비주소 분리
    address_items = [item for item in unique_items if item["type"] == "주소"]
    non_address_items = [item for item in unique_items if item["type"] != "주소"]
    
    # ⭐ 주소 처리 로직 (순서 수정)
    if address_items:
        print(f"📍 주소 항목 {len(address_items)}개 처리 중...")
        
        # 주소 값들을 원본 텍스트 출현 순서대로 정렬
        address_values = [item["value"] for item in address_items]
        
        # 원본 텍스트에서의 출현 순서를 찾기 위해 start 위치 기준으로 정렬
        address_items_sorted = sorted(address_items, key=lambda x: x.get("start", 0))
        ordered_address_values = [item["value"] for item in address_items_sorted]
        
        print(f"🏠 탐지된 주소들 (순서대로): {ordered_address_values}")
        
        # ⭐ 올바른 순서로 완전한 원본 주소 구성
        full_original_address = " ".join(ordered_address_values)
        
        # 가명 주소 선택
        fake_address = pools.get_fake_address()
        
        print(f"🏠 원본 전체 주소 (올바른 순서): '{full_original_address}'")
        print(f"🏠 가명 주소: '{fake_address}'")
        
        # 모든 주소 부분을 같은 가명으로 치환
        for addr_value in ordered_address_values:
            if addr_value and addr_value not in substitution_map:
                substitution_map[addr_value] = fake_address
                print(f"🔄 주소 치환: '{addr_value}' → '{fake_address}'")
        
        # ⭐ reverse_map은 가명 → 올바른 순서의 완전한 원본 주소
        reverse_map[fake_address] = full_original_address
        print(f"🔑 주소 복원 매핑: '{fake_address}' → '{full_original_address}'")
    
    # 나머지 항목들 처리
    for item in non_address_items:
        original = item["value"]
        
        if original in substitution_map:
            print(f"🔄 이미 처리됨: {item['type']} '{original}'")
            continue
        
        fake_value = None
        
        if item["type"] == "이름":
            fake_value = pools.get_fake_name()
            
        elif item["type"] == "나이":
            try:
                age = int(original)
                min_age = max(20, age - 5)
                max_age = min(80, age + 5)
                
                if min_age >= max_age:
                    fake_value = str(age)
                else:
                    fake_value = str(random.randint(min_age, max_age))
            except (ValueError, TypeError):
                print(f"❌ 나이 치환 실패 (원본 유지): '{original}'")
                continue
                
        elif item["type"] == "이메일":
            fake_value = pools.get_fake_email()
            
        elif item["type"] == "전화번호":
            fake_value = pools.get_fake_phone()
        
        if fake_value and fake_value != original:
            substitution_map[original] = fake_value
            reverse_map[fake_value] = original
            print(f"🔄 {item['type']} 매핑: '{original}' → '{fake_value}' (복원: '{fake_value}' → '{original}')")
    
    print(f"✅ 대체 맵 생성 완료:")
    print(f"  - substitution_map: {len(substitution_map)}개")
    print(f"  - reverse_map: {len(reverse_map)}개")
    
    print(f"📤 최종 복원 매핑 (검증):")
    for fake, original in reverse_map.items():
        print(f"  '{fake}' → '{original}'")
    
    return substitution_map, reverse_map

def apply_smart_substitutions(text: str, substitution_map: Dict[str, str]) -> str:
    """스마트 대체 적용 (간소화된 버전)"""
    result = text
    
    print(f"🔄 치환 시작: '{text}'")
    
    # 긴 문자열부터 대체 (부분 매칭 방지)
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, replacement in sorted_items:
        if original in result:
            old_result = result
            result = result.replace(original, replacement)
            if old_result != result:
                print(f"🔄 치환 완료: '{original}' → '{replacement}'")
    
    print(f"✅ 치환 완료: '{result}'")
    return result

async def pseudonymize_text_with_fake(text: str) -> Dict[str, Any]:
    """실제 가명을 사용한 가명화 (주소 순서 수정)"""
    start_time = time.time()
    
    print(f"\n=== 🔐 가명화 시작 ===")
    print(f"📝 원본 텍스트: '{text}'")
    
    # 1. normalizers.py로 PII 탐지
    detection_start = time.time()
    items = await detect_pii_all(text)
    detection_time = time.time() - detection_start
    
    print(f"🔍 탐지 완료: {len(items)}개 항목 ({detection_time:.3f}초)")
    for i, item in enumerate(items):
        start_pos = item.get('start', 'N/A')
        end_pos = item.get('end', 'N/A')
        print(f"  {i+1}. {item['type']}: '{item['value']}' (출처: {item['source']}, 위치: {start_pos}-{end_pos})")
    
    # 2. 대체 맵 생성 (수정된 주소 처리)
    substitution_start = time.time()
    substitution_map, reverse_map = create_fake_substitution_map(items)
    
    # 3. 가명화 적용
    pseudonymized_text = apply_smart_substitutions(text, substitution_map)
    substitution_time = time.time() - substitution_start
    
    total_time = time.time() - start_time
    
    print(f"📊 최종 결과:")
    print(f"  📝 원본: '{text}'")
    print(f"  🎭 가명화: '{pseudonymized_text}'")
    print(f"  🔑 복원 맵: {reverse_map}")
    print(f"  ⏱️ 처리시간: {total_time:.3f}초")
    print(f"=== 🔐 가명화 완료 ===\n")
    
    return {
        "pseudonymized_text": pseudonymized_text,
        "original_text": text,
        "substitution_map": substitution_map,
        "reverse_map": reverse_map,  # ⭐ 수정된 순서의 reverse_map
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
    """원본 복원 (강화된 버전)"""
    print(f"🔄 복원 시작:")
    print(f"  📝 가명화 텍스트: '{pseudonymized_text}'")
    print(f"  🔑 복원 맵: {reverse_map}")
    
    result = pseudonymized_text
    
    # 긴 문자열부터 복원 (부분 매칭 방지)
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    replacement_count = 0
    for fake, original in sorted_items:
        if fake in result:
            old_result = result
            result = result.replace(fake, original)
            if old_result != result:
                replacement_count += 1
                print(f"  🔄 복원: '{fake}' → '{original}'")
    
    print(f"✅ 복원 완료: {replacement_count}개 항목 복원")
    print(f"  📝 복원된 텍스트: '{result}'")
    
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