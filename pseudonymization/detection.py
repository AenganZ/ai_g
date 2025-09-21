# pseudonymization/detection.py
"""
PII 탐지 모듈 - 깔끔한 버전
NER 간소화 + Regex 중심
"""

import re
from typing import List, Dict, Any, Set
from .pools import get_pools, NAME_EXCLUDE_WORDS

# 정규식 패턴
EMAIL_PATTERN = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
PHONE_PATTERN = re.compile(
    r'(?:010|011|016|017|018|019|02|031|032|033|041|042|043|044|051|052|053|054|055|061|062|063|064)'
    r'[-.\s]?\d{3,4}[-.\s]?\d{4}'
)
NAME_PATTERN = re.compile(r'([가-힣]{2,4})(님|씨|군|양|이|가|을|를|에게|께서|께|는|은)?')
AGE_PATTERN = re.compile(r'(\d{1,3})\s*(?:세|살)')
RRN_PATTERN = re.compile(r'\d{6}[-\s]?\d{7}')
CARD_PATTERN = re.compile(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}')

def detect_with_ner_simple(text: str) -> List[Dict[str, Any]]:
    """NER 모델 1차 스크리닝 - 가능성 있는 영역 찾기"""
    items = []
    
    try:
        from .model import extract_entities_with_ner, is_ner_loaded
        
        if is_ner_loaded():
            print("NER primary screening (low threshold)")
            
            ner_items = extract_entities_with_ner(text)
            
            # NER 결과를 1차 스크리닝으로 사용 (낮은 임계값)
            for item in ner_items:
                if item['confidence'] > 0.3:  # 낮은 임계값으로 변경
                    item['confidence'] = 0.6  # 중간 신뢰도로 조정
                    item['source'] = 'NER-Screen'
                    items.append(item)
            
            print(f"NER screening: {len(items)} potential areas found")
            
            # NER가 탐지한 영역 주변의 한국어 패턴도 추가 검색
            korean_name_hints = []
            for match in re.finditer(r'([가-힣]{2,4})', text):
                name_candidate = match.group(1)
                # 매우 기본적인 필터링만 수행
                if (len(name_candidate) >= 2 and 
                    name_candidate not in ['있습니다', '합니다', '입니다', '했습니다']):
                    korean_name_hints.append({
                        "type": "이름",
                        "value": name_candidate,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.4,  # 낮은 신뢰도
                        "source": "NER-Hint"
                    })
            
            items.extend(korean_name_hints)
            print(f"Korean name hints: {len(korean_name_hints)} candidates")
            
        else:
            print("NER model not used (Regex-focused mode)")
            
    except Exception as e:
        print(f"NER screening failed (continuing): {e}")
    
    return items

def detect_with_regex_enhanced(text: str, pools) -> List[Dict[str, Any]]:
    """강화된 정규식 탐지 - 실질적 PII 탐지 담당"""
    items = []
    
    print("Enhanced Regex detection (main engine)")
    
    # 이메일 탐지
    for match in EMAIL_PATTERN.finditer(text):
        items.append({
            "type": "이메일",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex-Email"
        })
        print(f"Email detected: '{match.group()}'")
    
    # 전화번호 탐지
    for match in PHONE_PATTERN.finditer(text):
        items.append({
            "type": "전화번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex-Phone"
        })
        print(f"Phone detected: '{match.group()}'")
    
    # 나이 탐지
    for match in AGE_PATTERN.finditer(text):
        age_value = match.group(1)
        age_num = int(age_value)
        if 1 <= age_num <= 120:
            items.append({
                "type": "나이",
                "value": age_value,
                "start": match.start(),
                "end": match.start() + len(age_value),
                "confidence": 0.95,
                "source": "Regex-Age"
            })
            print(f"Age detected: '{age_value}'")
    
    # 주민등록번호 탐지
    for match in RRN_PATTERN.finditer(text):
        items.append({
            "type": "주민등록번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex-RRN"
        })
        print(f"RRN detected: '{match.group()}'")
    
    # 신용카드 탐지
    for match in CARD_PATTERN.finditer(text):
        items.append({
            "type": "신용카드",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.95,
            "source": "Regex-Card"
        })
        print(f"Card detected: '{match.group()}'")
    
    return items

def detect_names_with_pools(text: str, pools) -> List[Dict[str, Any]]:
    """데이터풀 기반 정확한 이름 탐지"""
    items = []
    
    if not pools.real_names:
        return items
    
    print(f"Pool-based name detection ({len(pools.real_names):,} names)")
    
    josa_pattern = re.compile(r'(님|씨|군|양|이|가|을|를|에게|에서|한테|께서|께|는|은)$')
    
    detected_count = 0
    sorted_names = sorted(pools.real_names, key=len, reverse=True)
    
    for name in sorted_names:
        if name in text:
            if not is_valid_korean_name(name):
                continue
            
            start = 0
            while True:
                pos = text.find(name, start)
                if pos == -1:
                    break
                
                before_ok = pos == 0 or not text[pos-1].isalnum()
                after_pos = pos + len(name)
                after_ok = after_pos >= len(text) or not text[after_pos].isalnum()
                
                if after_pos < len(text):
                    rest_text = text[after_pos:]
                    if josa_pattern.match(rest_text):
                        after_ok = True
                
                if before_ok and after_ok:
                    items.append({
                        "type": "이름",
                        "value": name,
                        "start": pos,
                        "end": pos + len(name),
                        "confidence": 0.95,
                        "source": "Pool-Names"
                    })
                    detected_count += 1
                    print(f"Name detected: '{name}'")
                
                start = pos + 1
    
    print(f"Total names detected: {detected_count}")
    return items

def detect_addresses_with_pools(text: str, pools) -> List[Dict[str, Any]]:
    """데이터풀 기반 주소 탐지"""
    items = []
    
    print("Pool-based address detection")
    
    # 시/도 탐지
    for province in pools.provinces:
        if province in text:
            for match in re.finditer(re.escape(province), text):
                items.append({
                    "type": "주소",
                    "value": province,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "source": "Pool-Province"
                })
                print(f"Province detected: '{province}'")
    
    # 시/군/구 탐지
    for district in pools.districts:
        if district in text and len(district) >= 2:
            for match in re.finditer(re.escape(district), text):
                items.append({
                    "type": "주소",
                    "value": district,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                    "source": "Pool-District"
                })
                print(f"District detected: '{district}'")
    
    # 도로명 탐지
    for road in pools.road_names:
        if road in text and len(road) >= 3:
            for match in re.finditer(re.escape(road), text):
                items.append({
                    "type": "주소",
                    "value": road,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                    "source": "Pool-Road"
                })
                print(f"Road detected: '{road}'")
    
    return items

def is_valid_korean_name(name: str) -> bool:
    """한국 이름 유효성 검사"""
    if not name or len(name.strip()) == 0:
        return False
    
    name = name.strip()
    
    if not (2 <= len(name) <= 4):
        return False
    
    if name in NAME_EXCLUDE_WORDS:
        return False
    
    if not all(ord('가') <= ord(char) <= ord('힣') for char in name):
        return False
    
    if re.search(r'[0-9a-zA-Z!@#$%^&*()_+=\[\]{}|\\:";\'<>?,./]', name):
        return False
    
    if len(set(name)) == 1 and len(name) > 2:
        return False
    
    return True

def merge_detections_smart(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """스마트 중복 제거 (Regex > Pool > NER)"""
    if not items:
        return []
    
    print("Smart duplicate removal (Regex > Pool > NER)")
    
    priority_map = {
        'Regex-Email': 0,
        'Regex-Phone': 0,
        'Regex-Age': 0,
        'Regex-RRN': 0,
        'Regex-Card': 0,
        'Pool-Names': 1,
        'Pool-Province': 1,
        'Pool-District': 1,
        'Pool-Road': 1,
        'NER-Hint': 2
    }
    
    items.sort(key=lambda x: (x['start'], priority_map.get(x['source'], 3)))
    
    unique_items = []
    seen_values = set()
    
    for item in items:
        value_key = (item['type'], item['value'])
        if value_key in seen_values:
            continue
        
        overlap = False
        for existing in unique_items[:]:
            if item['start'] < existing['end'] and item['end'] > existing['start']:
                if abs(item['start'] - existing['start']) <= 2:
                    item_priority = priority_map.get(item['source'], 3)
                    existing_priority = priority_map.get(existing['source'], 3)
                    
                    if item_priority < existing_priority:
                        unique_items.remove(existing)
                        unique_items.append(item)
                        seen_values.discard((existing['type'], existing['value']))
                        seen_values.add(value_key)
                    overlap = True
                    break
        
        if not overlap:
            unique_items.append(item)
            seen_values.add(value_key)
    
    unique_items.sort(key=lambda x: x['start'])
    return unique_items

def detect_pii_enhanced(text: str) -> Dict[str, Any]:
    """강화된 PII 탐지 - NER 간소화 + Regex 중심"""
    items = []
    pools = get_pools()
    
    print(f"PII analysis (Regex-focused): {text[:50]}...")
    
    # NER 간소화 (힌트만)
    ner_items = detect_with_ner_simple(text)
    items.extend(ner_items)
    
    # Regex 강화 탐지 (메인 엔진)
    regex_items = detect_with_regex_enhanced(text, pools)
    items.extend(regex_items)
    
    # 데이터풀 이름 탐지
    name_items = detect_names_with_pools(text, pools)
    items.extend(name_items)
    
    # 데이터풀 주소 탐지
    address_items = detect_addresses_with_pools(text, pools)
    items.extend(address_items)
    
    # 스마트 중복 제거
    unique_items = merge_detections_smart(items)
    
    result = {
        "contains_pii": len(unique_items) > 0,
        "items": unique_items,
        "stats": {
            "ner_hints": len(ner_items),
            "regex_main": len(regex_items),
            "pool_names": len(name_items),
            "pool_addresses": len(address_items),
            "total": len(unique_items)
        }
    }
    
    print(f"Final detection result: {len(unique_items)} items")
    for idx, item in enumerate(unique_items, 1):
        print(f"#{idx} {item['type']}: '{item['value']}' (confidence: {item['confidence']:.2f}, source: {item['source']})")
    
    return result

# 호환성 함수들
def detect_with_ner(text: str) -> List[Dict[str, Any]]:
    return detect_with_ner_simple(text)

def detect_with_regex(text: str, pools) -> List[Dict[str, Any]]:
    return detect_with_regex_enhanced(text, pools)

def detect_names_from_csv(text: str, detection_data=None):
    pools = get_pools()
    return detect_names_with_pools(text, pools)

def detect_addresses_from_csv(text: str, detection_data=None):
    pools = get_pools()
    return detect_addresses_with_pools(text, pools)

def merge_detections(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return merge_detections_smart(items)