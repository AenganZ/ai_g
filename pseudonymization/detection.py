# pseudonymization/detection.py
"""
워크플로우 기반 PII 탐지 모듈 (강화된 버전)
1차: 규칙/정규식 고속 패스
2차: NER 보강 (타임아웃 80ms)
"""

import re
import asyncio
from typing import List, Dict, Any
from .pools import get_pools

def detect_with_regex_fast(text: str) -> List[Dict[str, Any]]:
    """1차: 규칙/정규식 고속 패스 (핵심 패턴만)"""
    
    print("1차: 규칙/정규식 고속 패스")
    
    items = []
    
    # 이메일 (더 관대한 패턴)
    email_patterns = [
        r'\b[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # 기본적인 패턴 (더 관대함)
        r'\b\w+@\w+\.\w+\b',  # 매우 단순한 패턴
    ]
    
    found_emails = set()  # 중복 제거용
    for pattern in email_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            email = match.group().lower()
            if email not in found_emails and '@' in email and '.' in email:
                found_emails.add(email)
                items.append({
                    "type": "이메일",
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "source": "정규식-이메일"
                })
                print(f"이메일 탐지: '{match.group()}'")
    
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
            print(f"전화번호 탐지: '{match.group()}'")
    
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
            print(f"주민등록번호 탐지: '{match.group()}'")
    
    print(f"규칙/정규식 탐지 완료: {len(items)}개")
    
    return items

def detect_names_with_realname_list(text: str) -> List[Dict[str, Any]]:
    """실명 목록 기반 이름 탐지 (제외 단어 강화)"""
    
    print("실명 목록 기반 이름 탐지")
    
    items = []
    pools = get_pools()
    
    # 제외 단어 체크 함수
    def should_exclude(name: str) -> bool:
        # NAME_EXCLUDE_WORDS에 있는 단어들
        if name in pools.name_exclude_words:
            print(f"제외 단어 무시: '{name}'")
            return True
        
        # 지역명들
        if name in pools.provinces or name in pools.cities or name in pools.districts:
            print(f"지역명 무시: '{name}'")
            return True
        
        # 문법 요소들 (어미, 조사 등)
        grammar_endings = ['은', '는', '이', '가', '을', '를', '에', '에서', '으로', '로', '고', '며', '이고', '하고']
        if any(name.endswith(ending) for ending in grammar_endings):
            print(f"문법 요소 무시: '{name}'")
            return True
        
        # 1-2글자면서 확실하지 않은 것들
        if len(name) <= 2 and name not in ['김', '이', '박', '최', '정', '홍길동', '김철수', '이영희']:
            if not name in pools.single_surnames and not name in ['민준', '서준', '지우', '서현']:
                print(f"불확실한 단어 무시: '{name}'")
                return True
        
        return False
    
    # 실명 목록에서 탐지
    for name in pools.real_names:
        if should_exclude(name):
            continue
            
        # 텍스트에서 해당 이름 찾기
        for match in re.finditer(re.escape(name), text):
            items.append({
                "type": "이름",
                "value": name,
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.95,
                "source": "실명목록"
            })
            print(f"실명 탐지: '{name}'")
    
    print(f"실명 목록 탐지 완료: {len(items)}개")
    return items

def detect_names_with_patterns(text: str, existing_names: set = None) -> List[Dict[str, Any]]:
    """패턴 기반 이름 탐지 (중복 제거, 강화된 필터링)"""
    
    print("패턴 기반 이름 탐지")
    
    if existing_names is None:
        existing_names = set()
    
    items = []
    pools = get_pools()
    
    # 강화된 제외 함수
    def should_exclude_pattern(name: str) -> bool:
        # 이미 탐지된 이름
        if name in existing_names:
            return True
        
        # NAME_EXCLUDE_WORDS에 있는 단어들
        if name in pools.name_exclude_words:
            print(f"제외 단어 무시: '{name}'")
            return True
        
        # 지역명들  
        if name in pools.provinces or name in pools.cities or name in pools.districts:
            print(f"지역명 무시: '{name}'")
            return True
        
        # 문법 요소 확인
        grammar_patterns = [
            r'.*은$', r'.*는$', r'.*이$', r'.*가$', r'.*을$', r'.*를$', 
            r'.*에$', r'.*에서$', r'.*으로$', r'.*로$', r'.*고$', r'.*며$', 
            r'.*이고$', r'.*하고$', r'.*죠$', r'.*요$', r'.*다$', r'.*습니다$'
        ]
        
        for pattern in grammar_patterns:
            if re.match(pattern, name):
                print(f"문법 패턴 무시: '{name}'")
                return True
        
        # 동사/형용사 어간
        if any(name.endswith(ending) for ending in ['하시', '드리', '보내', '받으', '주세', '갔으', '왔으', '했으']):
            print(f"동사 어간 무시: '{name}'")
            return True
        
        # 숫자 포함
        if any(char.isdigit() for char in name):
            print(f"숫자 포함 무시: '{name}'")
            return True
        
        # 너무 짧거나 긴 것들
        if len(name) < 2 or len(name) > 4:
            print(f"길이 부적절 무시: '{name}'")
            return True
        
        return False
    
    # 한국 이름 패턴들
    name_patterns = [
        r'(?:안녕하세요,?\s*(?:저는\s*)?|제\s*이름은\s*)([가-힣]{2,4})(?:입니다|이에요|예요|님|씨|이고|라고)',
        r'([가-힣]{2,4})(?:님|씨)(?:\s|,|\.)',
        r'([가-힣]{2,4})(?:이고|이며|라고)\s',
        r'([가-힣]{2,4})(?:의|가)\s',
    ]
    
    for pattern in name_patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            
            if should_exclude_pattern(name):
                continue
            
            items.append({
                "type": "이름",
                "value": name,
                "start": match.start(1),
                "end": match.end(1),
                "confidence": 0.8,
                "source": "패턴-이름"
            })
            print(f"패턴 이름 탐지: '{name}'")
    
    print(f"패턴 이름 탐지 완료: {len(items)}개")
    return items

def detect_addresses_comprehensive(text: str) -> List[Dict[str, Any]]:
    """전국 주소 탐지 (첫 번째 주소만 반환)"""
    
    print("전국 주소 탐지 (첫 번째만)")
    
    pools = get_pools()
    
    # 모든 가능한 주소 요소 찾기
    all_addresses = []
    
    # 1. 시/도 탐지
    for province in pools.provinces:
        for match in re.finditer(re.escape(province), text):
            # 주변 문맥 확인 (주소 관련 단어와 함께 있는지)
            start_pos = max(0, match.start() - 20)
            end_pos = min(len(text), match.end() + 20)
            context = text[start_pos:end_pos]
            
            # 주소 관련 단어들
            address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '소재', '예약', '지역', '동', '구', '시', '도']
            
            if any(keyword in context for keyword in address_keywords):
                all_addresses.append({
                    "type": "주소",
                    "value": province,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                    "source": "패턴-주소",
                    "priority": 1  # 시/도가 가장 우선순위
                })
                print(f"시/도 탐지: '{province}' (위치: {match.start()})")
    
    # 2. 시 탐지
    for city in pools.cities:
        for match in re.finditer(re.escape(city), text):
            start_pos = max(0, match.start() - 20)
            end_pos = min(len(text), match.end() + 20)
            context = text[start_pos:end_pos]
            
            address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '소재', '예약', '지역', '동', '구']
            
            if any(keyword in context for keyword in address_keywords):
                all_addresses.append({
                    "type": "주소",
                    "value": city,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.85,
                    "source": "패턴-주소",
                    "priority": 2  # 시가 두 번째 우선순위
                })
                print(f"시 탐지: '{city}' (위치: {match.start()})")
    
    # 3. 구/군 탐지
    for district in pools.districts:
        for match in re.finditer(re.escape(district), text):
            start_pos = max(0, match.start() - 20)
            end_pos = min(len(text), match.end() + 20)
            context = text[start_pos:end_pos]
            
            address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '소재', '예약', '지역', '동', '태평동']
            
            if any(keyword in context for keyword in address_keywords):
                all_addresses.append({
                    "type": "주소",
                    "value": district,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.8,
                    "source": "패턴-주소",
                    "priority": 3  # 구/군이 세 번째 우선순위
                })
                print(f"구/군 탐지: '{district}' (위치: {match.start()})")
    
    # 첫 번째 주소만 선택 (위치 순으로 정렬 후 첫 번째)
    if all_addresses:
        # 위치 순으로 정렬 (start 기준)
        all_addresses.sort(key=lambda x: x["start"])
        first_address = all_addresses[0]
        
        # priority와 관련 없이 첫 번째만 반환
        del first_address["priority"]
        
        print(f"첫 번째 주소 선택: '{first_address['value']}' (나머지 {len(all_addresses)-1}개 무시)")
        return [first_address]
    
    print("주소 탐지 없음")
    return []

async def detect_with_ner_async(text: str, timeout: float = 0.08) -> List[Dict[str, Any]]:
    """2차: NER 보강 (비동기, 타임아웃)"""
    
    print(f"2차: NER 보강 (타임아웃: {int(timeout*1000)}ms)")
    
    try:
        from .model import extract_entities_with_ner, is_ner_loaded
        
        if not is_ner_loaded():
            print("NER 모델이 로드되지 않음")
            return []
        
        # 타임아웃 적용하여 NER 실행
        ner_task = asyncio.create_task(asyncio.to_thread(extract_entities_with_ner, text))
        ner_entities = await asyncio.wait_for(ner_task, timeout=timeout)
        
        items = []
        for entity in ner_entities:
            if entity['confidence'] >= 0.85:  # 높은 임계치
                items.append({
                    "type": entity['label'],
                    "value": entity['text'],
                    "start": entity['start'],
                    "end": entity['end'],
                    "confidence": entity['confidence'],
                    "source": "NER"
                })
        
        print(f"NER (koelectra-base-v3-naver-ner) 탐지: {len(items)}개 항목")
        
    except asyncio.TimeoutError:
        print(f"NER 타임아웃 ({int(timeout*1000)}ms)")
        items = []
    except Exception as e:
        print(f"NER 실행 실패: {e}")
        items = []
    
    print(f"2차 NER 보강 완료: {len(items)}개 탐지")
    return items

def merge_detections_with_priority(items1: List[Dict[str, Any]], items2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """탐지 결과 병합 (규칙 우선, 위치 기반 중복 제거)"""
    
    print("탐지 결과 병합 (규칙 우선)")
    
    all_items = items1 + items2
    
    # 위치 기반 중복 제거
    unique_items = []
    used_positions = set()
    
    # 규칙 기반 항목을 우선 처리
    for item in items1:
        position_key = (item["start"], item["end"])
        if position_key not in used_positions:
            unique_items.append(item)
            used_positions.add(position_key)
    
    # NER 항목 중 겹치지 않는 것만 추가
    for item in items2:
        position_key = (item["start"], item["end"])
        if position_key not in used_positions:
            # 겹치는 범위 확인
            overlaps = False
            for used_start, used_end in used_positions:
                if not (item["end"] <= used_start or item["start"] >= used_end):
                    overlaps = True
                    break
            
            if not overlaps:
                unique_items.append(item)
                used_positions.add(position_key)
    
    print(f"병합 완료: 규칙 {len(items1)}개 + NER {len(items2)}개 → {len(unique_items)}개")
    return unique_items

def assign_tokens(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """치환 토큰 할당"""
    
    print("치환 토큰 할당")
    
    token_map = {}
    type_counters = {}
    
    for item in items:
        pii_type = item['type']
        value = item['value']
        
        # 이미 할당된 경우 건너뛰기
        if value in token_map:
            continue
        
        # 타입별 카운터 초기화
        if pii_type not in type_counters:
            type_counters[pii_type] = 0
        
        # 토큰 생성
        if pii_type == "이름":
            token = f"[PER_{type_counters[pii_type]}]"
        elif pii_type == "전화번호":
            token = f"[PHONE_{type_counters[pii_type]}]"
        elif pii_type == "이메일":
            token = f"[EMAIL_{type_counters[pii_type]}]"
        elif pii_type == "주소":
            token = f"[LOC_{type_counters[pii_type]}]"
        elif pii_type == "주민등록번호":
            token = f"[SSN_{type_counters[pii_type]}]"
        else:
            token = f"[{pii_type.upper()}_{type_counters[pii_type]}]"
        
        token_map[value] = token
        type_counters[pii_type] += 1
        
        print(f"{value} → {token}")
    
    print(f"토큰 할당 완료: {len(token_map)}개")
    return token_map

def detect_pii_enhanced(text: str) -> Dict[str, Any]:
    """워크플로우 기반 통합 PII 탐지"""
    
    print("=" * 60)
    print("워크플로우 기반 PII 탐지 시작")
    print("=" * 60)
    
    # 1차: 규칙/정규식 고속 패스
    regex_items = detect_with_regex_fast(text)
    
    # 실명 목록 기반 이름 탐지 (제외 단어 강화)
    realname_items = detect_names_with_realname_list(text)
    regex_items.extend(realname_items)
    
    # 패턴 기반 이름 탐지 (중복 방지, 엄격한 필터링)
    detected_names = {item['value'] for item in realname_items}
    pattern_items = detect_names_with_patterns(text, detected_names)
    regex_items.extend(pattern_items)
    
    # 전국 주소 완전 탐지 
    address_items = detect_addresses_comprehensive(text)
    regex_items.extend(address_items)
    
    # 2차: NER 보강 (비동기, 타임아웃)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ner_items = loop.run_until_complete(detect_with_ner_async(text, timeout=0.08))
        loop.close()
    except Exception as e:
        print(f"NER 비동기 실행 실패: {e}")
        ner_items = []
    
    # 탐지 결과 병합 (규칙 우선)
    merged_items = merge_detections_with_priority(regex_items, ner_items)
    
    # 치환 토큰 할당
    token_map = assign_tokens(merged_items)
    
    print("=" * 60)
    print(f"최종 탐지 결과: {len(merged_items)}개")
    for i, item in enumerate(merged_items, 1):
        token = token_map.get(item['value'], '???')
        print(f"#{i} {item['type']}: '{item['value']}' → {token} (신뢰도: {item['confidence']:.2f}, 출처: {item['source']})")
    print("=" * 60)
    
    # 통계 생성
    stats = {
        "detection_time": 0,  # 호출하는 곳에서 설정
        "items_by_type": {},
        "detection_stats": {
            "regex_items": len(regex_items) - len(address_items),
            "ner_items": len(ner_items),
            "total_items": len(merged_items)
        },
        "token_map": token_map
    }
    
    # 타입별 통계
    for item in merged_items:
        pii_type = item['type']
        if pii_type not in stats['items_by_type']:
            stats['items_by_type'][pii_type] = 0
        stats['items_by_type'][pii_type] += 1
    
    return {
        "items": merged_items,
        "stats": stats
    }

# 기존 호환성 함수들
def detect_with_ner(text: str) -> List[Dict[str, Any]]:
    """NER 탐지 (호환성)"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(detect_with_ner_async(text))
        loop.close()
        return result
    except:
        return []

def detect_with_regex(text: str) -> List[Dict[str, Any]]:
    """정규식 탐지 (호환성)"""
    return detect_with_regex_fast(text)

def detect_names_from_csv(text: str) -> List[Dict[str, Any]]:
    """CSV 이름 탐지 (호환성)"""
    return detect_names_with_realname_list(text)

def detect_addresses_from_csv(text: str) -> List[Dict[str, Any]]:
    """CSV 주소 탐지 (호환성)"""
    return detect_addresses_comprehensive(text)

def merge_detections(items1: List[Dict[str, Any]], items2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """탐지 결과 병합 (호환성)"""
    return merge_detections_with_priority(items1, items2)