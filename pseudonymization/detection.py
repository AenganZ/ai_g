# pseudonymization/detection.py
"""
워크플로우 기반 PII 탐지 모듈 (강화된 버전)
1차: 규칙/정규식 고속 패스 (90ms 내외)
2차: NER 보강 (타임아웃 80ms, 높은 임계치)
"""

import re
import asyncio
from typing import List, Dict, Any
from .pools import get_pools

def detect_with_regex_fast(text: str) -> List[Dict[str, Any]]:
    """1차: 규칙/정규식 고속 패스 (핵심 패턴만)"""
    
    print("🚀 1차: 규칙/정규식 고속 패스")
    
    items = []
    
    # 이메일 (고신뢰도)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    for match in re.finditer(email_pattern, text):
        items.append({
            "type": "이메일",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.95,
            "source": "정규식-이메일"
        })
        print(f"📧 이메일 탐지: '{match.group()}'")
    
    # 전화번호 (한국식)
    phone_patterns = [
        r'01[0-9]-\d{4}-\d{4}',  # 010-1234-5678
        r'01[0-9]\d{4}\d{4}',     # 01012345678
        r'\d{2,3}-\d{3,4}-\d{4}', # 02-123-4567, 031-1234-5678
    ]
    
    for pattern in phone_patterns:
        for match in re.finditer(pattern, text):
            items.append({
                "type": "전화번호",
                "value": match.group(),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.9,
                "source": "정규식-전화번호"
            })
            print(f"📞 전화번호 탐지: '{match.group()}'")
    
    # 주민등록번호 (부분 마스킹 포함)
    rrn_patterns = [
        r'\d{6}-[1-4]\d{6}',  # 123456-1234567
        r'\d{6}-[1-4]\*{6}',  # 123456-1******
    ]
    
    for pattern in rrn_patterns:
        for match in re.finditer(pattern, text):
            items.append({
                "type": "주민등록번호",
                "value": match.group(),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.98,
                "source": "정규식-주민등록번호"
            })
            print(f"🆔 주민등록번호 탐지: '{match.group()}'")
    
    # 신용카드 번호
    card_pattern = r'\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}'
    for match in re.finditer(card_pattern, text):
        # 간단한 검증 (연속된 같은 숫자 제외)
        card_num = re.sub(r'[- ]', '', match.group())
        if not all(digit == card_num[0] for digit in card_num):
            items.append({
                "type": "신용카드",
                "value": match.group(),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.85,
                "source": "정규식-신용카드"
            })
            print(f"💳 신용카드 탐지: '{match.group()}'")
    
    print(f"🚀 규칙/정규식 탐지 완료: {len(items)}개")
    
    return items

def detect_names_with_realname_list(text: str) -> List[Dict[str, Any]]:
    """실명 목록 기반 이름 탐지"""
    
    print("👤 실명 목록 기반 이름 탐지")
    
    items = []
    pools = get_pools()
    
    # 실명 목록에서 탐지
    for name in pools.real_names:
        if len(name) >= 2:  # 2글자 이상
            for match in re.finditer(re.escape(name), text):
                items.append({
                    "type": "이름",
                    "value": name,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "source": "실명목록"
                })
                print(f"👤 실명 탐지: '{name}'")
    
    print(f"👤 실명 목록 탐지 완료: {len(items)}개")
    
    return items

def detect_names_with_patterns(text: str, exclude_names: set = None) -> List[Dict[str, Any]]:
    """패턴 기반 이름 탐지 (중복 방지)"""
    
    print("🔍 패턴 기반 이름 탐지")
    
    items = []
    exclude_names = exclude_names or set()
    pools = get_pools()
    
    # 한국어 이름 패턴: [성씨][이름] (2-4글자)
    korean_name_pattern = r'[가-힣]{2,4}(?=\s|님|씨|은|는|이|가|을|를|에게|께서|와|과|의|로|으로|$|[^\가-힣])'
    
    for match in re.finditer(korean_name_pattern, text):
        name = match.group()
        
        # 이미 탐지된 이름 제외
        if name in exclude_names:
            continue
        
        # 제외 단어 확인
        if name in pools.name_exclude_words:
            print(f"🚫 제외 단어 무시: '{name}'")
            continue
        
        # 성씨 패턴 확인
        if name[0] in pools.compound_surnames or name[0] in pools.single_surnames:
            items.append({
                "type": "이름",
                "value": name,
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.8,
                "source": "패턴-이름"
            })
            print(f"🔍 패턴 이름 탐지: '{name}'")
    
    print(f"🔍 패턴 이름 탐지 완료: {len(items)}개")
    
    return items

def detect_addresses_smart(text: str) -> List[Dict[str, Any]]:
    """스마트 주소 탐지 (첫 번째 주소만 선택)"""
    
    print("🏠 스마트 주소 탐지")
    
    items = []
    pools = get_pools()
    detected_locations = []
    
    # 시/도 탐지
    provinces = pools.provinces
    for province in provinces:
        if province in text:
            for match in re.finditer(re.escape(province), text):
                detected_locations.append({
                    "type": "주소",
                    "value": province,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                    "source": "패턴-주소",
                    "location_type": "province"
                })
                print(f"🗺️ 시/도 탐지: '{province}'")
    
    # 도시 탐지
    cities = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]
    for city in cities:
        if city in text:
            for match in re.finditer(re.escape(city), text):
                detected_locations.append({
                    "type": "주소",
                    "value": city,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.85,
                    "source": "패턴-주소",
                    "location_type": "city"
                })
                print(f"🏙️ 도시 탐지: '{city}'")
    
    # 구 탐지 (대구 등 특별 처리)
    districts = pools.districts
    for district in districts:
        if district in text:
            # "대구"가 포함된 경우 특별 처리
            if "대구" in district and district != "대구":
                continue  # "대구"는 시이므로 구로 처리하지 않음
                
            for match in re.finditer(re.escape(district), text):
                detected_locations.append({
                    "type": "주소", 
                    "value": district,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.8,
                    "source": "패턴-주소",
                    "location_type": "district"
                })
                print(f"🏘️ 구 탐지: '{district}'")
    
    # 중복 제거: 겹치는 위치의 주소들 중 첫 번째만 선택
    if detected_locations:
        # 시작 위치로 정렬
        detected_locations.sort(key=lambda x: x['start'])
        
        # 첫 번째 주소만 선택
        first_location = detected_locations[0]
        items.append(first_location)
        
        print(f"🏠 주소 중복 제거: {len(detected_locations)}개 → 1개")
        print(f"🏠 선택된 주소: '{first_location['value']}'")
    
    return items

async def detect_with_ner_async(text: str, timeout: float = 0.1) -> List[Dict[str, Any]]:
    """2차: NER 보강 (비동기, 타임아웃, 높은 임계치)"""
    items = []
    
    try:
        print(f"🤖 2차: NER 보강 (타임아웃: {timeout*1000:.0f}ms)")
        
        # 타임아웃과 함께 NER 실행
        async def run_ner():
            try:
                from .model import extract_entities_with_ner, is_ner_loaded
                
                if is_ner_loaded():
                    ner_items = extract_entities_with_ner(text)
                    
                    # 높은 임계치 적용 (0.9 이상)
                    high_confidence_items = []
                    for item in ner_items:
                        if item['confidence'] > 0.9:
                            item['source'] = 'NER-고신뢰도'
                            high_confidence_items.append(item)
                            print(f"🤖 NER 고신뢰도 탐지: {item['type']} = '{item['value']}' (신뢰도: {item['confidence']:.3f})")
                    
                    return high_confidence_items
                else:
                    print("🤖 NER 모델 로드되지 않음")
                    return []
                    
            except Exception as e:
                print(f"🤖 NER 실행 오류: {e}")
                return []
        
        # 타임아웃과 함께 실행
        items = await asyncio.wait_for(run_ner(), timeout=timeout)
        print(f"🤖 2차 NER 보강 완료: {len(items)}개 탐지")
        
    except asyncio.TimeoutError:
        print(f"🤖 NER 타임아웃 ({timeout*1000:.0f}ms) - 규칙 기반 결과 사용")
    except Exception as e:
        print(f"🤖 NER 보강 실패: {e}")
    
    return items

def merge_detections_with_priority(regex_items: List[Dict[str, Any]], 
                                  ner_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """탐지 결과 병합 (규칙 우선, 스팬 충돌 해결)"""
    
    print("🔄 탐지 결과 병합 (규칙 우선)")
    
    # 규칙 기반 결과가 우선
    merged_items = regex_items.copy()
    
    # NER 결과 추가 (겹치지 않는 것만)
    for ner_item in ner_items:
        overlapped = False
        
        for regex_item in regex_items:
            # 스팬 충돌 확인
            if (ner_item['start'] < regex_item['end'] and 
                ner_item['end'] > regex_item['start']):
                overlapped = True
                print(f"🔄 스팬 충돌 무시: NER '{ner_item['value']}' vs 규칙 '{regex_item['value']}'")
                break
        
        if not overlapped:
            merged_items.append(ner_item)
            print(f"🔄 NER 결과 추가: '{ner_item['value']}'")
    
    # 시작 위치로 정렬
    merged_items.sort(key=lambda x: x['start'])
    
    print(f"🔄 병합 완료: 규칙 {len(regex_items)}개 + NER {len(ner_items)}개 → {len(merged_items)}개")
    
    return merged_items

def assign_tokens(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """치환 토큰 할당 ([PER_0], [ORG_0], [LOC_0] 등)"""
    
    print("🏷️ 치환 토큰 할당")
    
    # 타입별 카운터
    type_counters = {}
    token_map = {}
    
    # 타입별 토큰 접두사
    type_prefixes = {
        '이름': 'PER',
        '회사': 'ORG', 
        '주소': 'LOC',
        '이메일': 'EMAIL',
        '전화번호': 'PHONE',
        '나이': 'AGE',
        '주민등록번호': 'RRN',
        '신용카드': 'CARD',
        '계좌번호': 'ACCT'
    }
    
    for item in items:
        pii_type = item['type']
        pii_value = item['value']
        
        # 타입별 카운터 증가
        if pii_type not in type_counters:
            type_counters[pii_type] = 0
        
        # 토큰 생성
        prefix = type_prefixes.get(pii_type, 'MISC')
        token = f"[{prefix}_{type_counters[pii_type]}]"
        
        token_map[pii_value] = token
        type_counters[pii_type] += 1
        
        print(f"🏷️ {pii_value} → {token}")
    
    print(f"🏷️ 토큰 할당 완료: {len(token_map)}개")
    
    return token_map

def detect_pii_enhanced(text: str) -> Dict[str, Any]:
    """워크플로우 기반 강화된 PII 탐지"""
    
    print("=" * 60)
    print("🔍 워크플로우 기반 PII 탐지 시작")
    print("=" * 60)
    
    # 1차: 규칙/정규식 고속 패스
    regex_items = detect_with_regex_fast(text)
    
    # 실명 목록 탐지
    realname_items = detect_names_with_realname_list(text)
    regex_items.extend(realname_items)
    
    # 패턴 기반 이름 탐지 (중복 방지)
    detected_names = {item['value'] for item in realname_items}
    pattern_items = detect_names_with_patterns(text, detected_names)
    regex_items.extend(pattern_items)
    
    # 스마트 주소 탐지
    address_items = detect_addresses_smart(text)
    regex_items.extend(address_items)
    
    # 2차: NER 보강 (비동기, 타임아웃)
    try:
        # 비동기 NER 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ner_items = loop.run_until_complete(detect_with_ner_async(text, timeout=0.08))
        loop.close()
    except Exception as e:
        print(f"🤖 NER 비동기 실행 실패: {e}")
        ner_items = []
    
    # 탐지 결과 병합 (규칙 우선)
    merged_items = merge_detections_with_priority(regex_items, ner_items)
    
    # 치환 토큰 할당
    token_map = assign_tokens(merged_items)
    
    print("=" * 60)
    print(f"🎯 최종 탐지 결과: {len(merged_items)}개")
    for i, item in enumerate(merged_items, 1):
        token = token_map.get(item['value'], '???')
        print(f"#{i} {item['type']}: '{item['value']}' → {token} (신뢰도: {item['confidence']:.2f}, 출처: {item['source']})")
    print("=" * 60)
    
    # 통계 생성
    stats = {
        'items_by_type': {},
        'detection_stats': {},
        'total_items': len(merged_items),
        'token_map': token_map
    }
    
    for item in merged_items:
        item_type = item['type']
        source = item['source']
        
        if item_type not in stats['items_by_type']:
            stats['items_by_type'][item_type] = 0
        stats['items_by_type'][item_type] += 1
        
        if source not in stats['detection_stats']:
            stats['detection_stats'][source] = 0
        stats['detection_stats'][source] += 1
    
    return {
        'contains_pii': len(merged_items) > 0,
        'items': merged_items,
        'stats': stats,
        'token_map': token_map
    }

# 호환성 함수들
def detect_with_ner(text: str) -> List[Dict[str, Any]]:
    """호환성을 위한 함수"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(detect_with_ner_async(text))
        loop.close()
        return result
    except:
        return []

def detect_with_ner_simple(text: str) -> List[Dict[str, Any]]:
    """간소화된 NER 탐지 (누락된 함수 추가)"""
    print("🤖 간소화된 NER 탐지")
    
    # 기본적으로 동기적 NER 탐지 시도
    try:
        from .model import extract_entities_with_ner, is_ner_loaded
        
        if is_ner_loaded():
            entities = extract_entities_with_ner(text)
            print(f"🤖 NER 간소 탐지 완료: {len(entities)}개")
            return entities
        else:
            print("🤖 NER 모델 로드되지 않음 - 빈 결과 반환")
            return []
            
    except Exception as e:
        print(f"🤖 NER 간소 탐지 실패: {e}")
        return []

def detect_with_regex(text: str, pools=None) -> List[Dict[str, Any]]:
    """호환성을 위한 함수"""
    return detect_with_regex_fast(text)

def detect_names_from_csv(text: str, pools=None) -> List[Dict[str, Any]]:
    """호환성을 위한 함수"""
    return detect_names_with_realname_list(text)

def detect_addresses_from_csv(text: str, pools=None) -> List[Dict[str, Any]]:
    """호환성을 위한 함수"""
    return detect_addresses_smart(text)

def merge_detections(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """호환성을 위한 함수"""
    return items  # 이미 병합됨

# 워크플로우 핵심 함수 export
__all__ = [
    'detect_pii_enhanced',
    'detect_with_ner',
    'detect_with_ner_simple', 
    'detect_with_regex',
    'detect_names_from_csv',
    'detect_addresses_from_csv',
    'merge_detections',
    'assign_tokens'  # 워크플로우용
]