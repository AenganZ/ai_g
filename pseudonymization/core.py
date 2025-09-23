# pseudonymization/core.py - Import 수정 버전
import re
import time
import random
import asyncio
from typing import Dict, List, Any, Tuple

# ⭐ relative import를 absolute import로 변경
try:
    from .normalizers import detect_pii_all
    from .pools import get_pools, get_data_pool_stats
except ImportError:
    # 직접 실행 시 절대 import 사용
    from pseudonymization.normalizers import detect_pii_all
    from pseudonymization.pools import get_pools, get_data_pool_stats

def create_enhanced_substitution_map(items: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """강화된 가명 대체 맵 생성 (존칭 처리 개선)"""
    pools = get_pools()
    substitution_map = {}
    reverse_map = {}
    
    print(f"🔧 존칭 처리 개선된 대체 맵 생성 시작: {len(items)}개 항목")
    
    # 중복 제거
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
    
    # 타입별로 분류
    address_items = [item for item in unique_items if item["type"] == "주소"]
    name_items = [item for item in unique_items if item["type"] == "이름"]  
    other_items = [item for item in unique_items if item["type"] not in ["주소", "이름"]]
    
    # ⭐ 1. 개선된 주소 처리 (각 부분을 개별 매핑)
    if address_items:
        print(f"📍 주소 항목 {len(address_items)}개 개별 처리...")
        
        for addr_item in address_items:
            original = addr_item["value"]
            
            if original in substitution_map:
                print(f"🔄 이미 처리된 주소: '{original}'")
                continue
            
            fake_address = pools.get_fake_address()
            while fake_address in reverse_map:
                fake_address = pools.get_fake_address()
            
            substitution_map[original] = fake_address
            reverse_map[fake_address] = original
            
            print(f"🏠 개별 주소 매핑: '{original}' → '{fake_address}'")
    
    # ⭐ 2. 존칭 처리 개선된 이름 처리
    if name_items:
        print(f"👤 이름 항목 {len(name_items)}개 존칭 처리 개선...")
        
        for name_item in name_items:
            full_name = name_item["value"]  # 예: "이영희님"
            
            if full_name in substitution_map:
                print(f"🔄 이미 처리된 이름: '{full_name}'")
                continue
            
            # ⭐ 존칭 분리
            base_name = full_name
            honorific = ""
            
            if full_name.endswith('님'):
                base_name = full_name[:-1]
                honorific = '님'
            elif full_name.endswith('씨'):
                base_name = full_name[:-1] 
                honorific = '씨'
            
            print(f"👤 이름 분석: '{full_name}' = '{base_name}' + '{honorific}'")
            
            # 기본 이름에 대한 가명 생성
            fake_base_name = pools.get_fake_name()
            
            # ⭐ 기본 이름과 존칭 포함 이름 모두 매핑
            substitution_map[base_name] = fake_base_name
            reverse_map[fake_base_name] = base_name
            
            if honorific:
                fake_full_name = fake_base_name + honorific
                substitution_map[full_name] = fake_full_name
                reverse_map[fake_full_name] = full_name
                print(f"👤 존칭 포함 매핑: '{full_name}' → '{fake_full_name}'")
            
            print(f"👤 기본 이름 매핑: '{base_name}' → '{fake_base_name}'")
    
    # ⭐ 3. 기타 항목들 처리
    for item in other_items:
        original = item["value"]
        
        if original in substitution_map:
            print(f"🔄 이미 처리됨: {item['type']} '{original}'")
            continue
        
        fake_value = None
        
        if item["type"] == "나이":
            try:
                age = int(original)
                min_age = max(20, age - 5)
                max_age = min(80, age + 5)
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
            print(f"🔄 {item['type']} 매핑: '{original}' → '{fake_value}'")
    
    print(f"✅ 존칭 처리 개선된 대체 맵 생성 완료:")
    print(f"  - substitution_map: {len(substitution_map)}개")
    print(f"  - reverse_map: {len(reverse_map)}개")
    
    print(f"📤 최종 복원 매핑 (검증):")
    for fake, original in reverse_map.items():
        print(f"  '{fake}' → '{original}'")
    
    return substitution_map, reverse_map

def apply_enhanced_substitutions(text: str, substitution_map: Dict[str, str]) -> str:
    """강화된 대체 적용 (긴 문자열 우선)"""
    result = text
    
    print(f"🔄 강화된 치환 시작: '{text}'")
    
    # ⭐ 길이 순으로 정렬 (긴 것부터 먼저 치환)
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    substitution_count = 0
    
    for original, replacement in sorted_items:
        if original in result:
            old_result = result
            result = result.replace(original, replacement)
            
            if old_result != result:
                substitution_count += 1
                print(f"🔄 치환 완료: '{original}' → '{replacement}'")
    
    print(f"✅ 치환 완료: {substitution_count}개 항목 치환됨")
    print(f"📝 최종 결과: '{result}'")
    return result

async def pseudonymize_text_with_fake(text: str) -> Dict[str, Any]:
    """실제 가명을 사용한 가명화 (존칭 처리 개선)"""
    start_time = time.time()
    
    print(f"\n=== 🔐 존칭 처리 개선된 가명화 시작 ===")
    print(f"📝 원본 텍스트: '{text}'")
    
    # 1. PII 탐지
    detection_start = time.time()
    items = await detect_pii_all(text)
    detection_time = time.time() - detection_start
    
    print(f"🔍 탐지 완료: {len(items)}개 항목 ({detection_time:.3f}초)")
    for i, item in enumerate(items):
        start_pos = item.get('start', 'N/A')
        end_pos = item.get('end', 'N/A')
        print(f"  {i+1}. {item['type']}: '{item['value']}' (출처: {item['source']}, 위치: {start_pos}-{end_pos})")
    
    # 2. 존칭 처리 개선된 대체 맵 생성
    substitution_start = time.time()
    substitution_map, reverse_map = create_enhanced_substitution_map(items)
    
    # 3. 가명화 적용
    pseudonymized_text = apply_enhanced_substitutions(text, substitution_map)
    substitution_time = time.time() - substitution_start
    
    # 4. reverse_map 검증
    print(f"🔍 reverse_map 최종 검증:")
    validated_reverse_map = {}
    for fake, original in reverse_map.items():
        if fake in pseudonymized_text:
            validated_reverse_map[fake] = original
            print(f"  ✅ 유효한 매핑: '{fake}' → '{original}'")
        else:
            print(f"  ⚠️ 미사용 매핑 (제외): '{fake}' → '{original}'")
    
    total_time = time.time() - start_time
    
    print(f"📊 최종 결과:")
    print(f"  📝 원본: '{text}'")
    print(f"  🎭 가명화: '{pseudonymized_text}'")
    print(f"  🔑 검증된 복원 맵: {validated_reverse_map}")
    print(f"  ⏱️ 처리시간: {total_time:.3f}초")
    print(f"=== 🔐 존칭 처리 개선된 가명화 완료 ===\n")
    
    return {
        "pseudonymized_text": pseudonymized_text,
        "original_text": text,
        "substitution_map": substitution_map,
        "reverse_map": validated_reverse_map,
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

def restore_original_enhanced(pseudonymized_text: str, reverse_map: Dict[str, str]) -> str:
    """존칭 처리 개선된 원본 복원"""
    print(f"🔄 존칭 처리 개선된 복원 시작:")
    print(f"  📝 가명화 텍스트: '{pseudonymized_text}'")
    print(f"  🔑 복원 맵: {reverse_map}")
    
    result = pseudonymized_text
    
    # ⭐ 길이 순으로 정렬 (긴 것부터 복원)
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    replacement_count = 0
    replacement_details = []
    
    for fake, original in sorted_items:
        if fake in result:
            old_result = result
            result = result.replace(fake, original)
            
            if old_result != result:
                replacement_count += 1
                replacement_details.append({"fake": fake, "original": original})
                print(f"  🔄 복원: '{fake}' → '{original}'")
    
    print(f"✅ 존칭 처리 개선된 복원 완료: {replacement_count}개 항목 복원")
    print(f"  📝 복원된 텍스트: '{result}'")
    print(f"  📊 복원 상세: {replacement_details}")
    
    return result

# 호환성 함수들
restore_original = restore_original_enhanced

def workflow_process_ai_response(ai_response: str, reverse_map: Dict[str, str]) -> str:
    """AI 응답 복원"""
    return restore_original_enhanced(ai_response, reverse_map)

def load_data_pools():
    """데이터풀 로드"""
    try:
        from .pools import initialize_pools
    except ImportError:
        from pseudonymization.pools import initialize_pools
    initialize_pools()
    return get_data_pool_stats()

def assign_realistic_values(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """현실적인 가명 할당"""
    substitution_map, _ = create_enhanced_substitution_map(items)
    return substitution_map

def create_masked_text(text: str, items: List[Dict[str, Any]]) -> str:
    """마스킹된 텍스트 생성"""
    substitution_map, _ = create_enhanced_substitution_map(items)
    return apply_enhanced_substitutions(text, substitution_map)