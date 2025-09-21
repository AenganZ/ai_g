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
    
    print("1차: 규칙/정규식 고속 패스")
    
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
            print(f"신용카드 탐지: '{match.group()}'")
    
    print(f"규칙/정규식 탐지 완료: {len(items)}개")
    
    return items

def detect_names_with_realname_list(text: str) -> List[Dict[str, Any]]:
    """실명 목록 기반 이름 탐지 (제외 단어 체크 추가)"""
    
    print("실명 목록 기반 이름 탐지")
    
    items = []
    pools = get_pools()
    
    # 실명 목록에서 탐지
    for name in pools.real_names:
        if len(name) >= 2:  # 2글자 이상
            # 제외 단어 확인 (추가됨)
            if name in pools.name_exclude_words:
                print(f"실명 목록 제외 단어 무시: '{name}'")
                continue
            
            # 이름으로 보기 어려운 단어들 필터링 (추가됨)
            if _is_invalid_name(name):
                print(f"유효하지 않은 이름 무시: '{name}'")
                continue
            
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

def _is_invalid_name(name: str) -> bool:
    """이름으로 보기 어려운 단어인지 확인"""
    
    # 문법 요소들
    grammar_words = {
        '이름은', '이름이', '이고', '이며', '이다', '입니다', '했습니다', '있습니다',
        '했어요', '해요', '이에요', '예요', '이야', '야', '에서', '에게', '으로', '로',
        '그런', '그래', '이런', '저런', '같은', '다른', '새로운', '오래된'
    }
    
    # 지역명들 (이름이 아님)
    location_words = {
        '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
        '강남', '강북', '강서', '강동', '서초', '송파', '마포', '용산',
        '중구', '동구', '서구', '남구', '북구', '수원', '성남', '안양'
    }
    
    # 일반 명사들
    common_words = {
        '사람', '학생', '선생', '의사', '간호사', '회사', '학교', '병원',
        '음식', '요리', '책상', '의자', '컴퓨터', '핸드폰', '자동차', '집',
        '나무', '꽃', '물', '불', '바람', '하늘', '구름', '별'
    }
    
    # 숫자가 포함된 경우
    if any(char.isdigit() for char in name):
        return True
    
    # 특수문자가 포함된 경우
    if not name.replace(' ', '').isalpha():
        return True
    
    # 문법 요소, 지역명, 일반 명사 체크
    if name in grammar_words or name in location_words or name in common_words:
        return True
    
    # 1글자 성씨만 있는 경우 (성씨가 아닌 1글자는 제외)
    pools = get_pools()
    if len(name) == 1 and name not in pools.single_surnames:
        return True
    
    return False

def detect_names_with_patterns(text: str, exclude_names: set = None) -> List[Dict[str, Any]]:
    """패턴 기반 이름 탐지 (중복 방지, 엄격한 필터링)"""
    
    print("패턴 기반 이름 탐지")
    
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
            print(f"제외 단어 무시: '{name}'")
            continue
        
        # 이름으로 보기 어려운 단어들 필터링 (추가됨)
        if _is_invalid_name(name):
            print(f"유효하지 않은 패턴 무시: '{name}'")
            continue
        
        # 성씨 패턴 확인 (더 엄격하게)
        if len(name) >= 2 and (name[0] in pools.compound_surnames or name[0] in pools.single_surnames):
            # 성씨 + 이름 조합이 실제 이름처럼 보이는지 확인
            if _looks_like_real_name(name):
                items.append({
                    "type": "이름",
                    "value": name,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.8,
                    "source": "패턴-이름"
                })
                print(f"패턴 이름 탐지: '{name}'")
            else:
                print(f"실제 이름이 아닌 패턴 무시: '{name}'")
    
    print(f"패턴 이름 탐지 완료: {len(items)}개")
    
    return items

def _looks_like_real_name(name: str) -> bool:
    """실제 이름처럼 보이는지 확인 (더 엄격한 검사)"""
    
    # 너무 짧거나 긴 경우
    if len(name) < 2 or len(name) > 4:
        return False
    
    # 같은 글자 반복 (예: "가가", "나나나")
    if len(set(name)) == 1:
        return False
    
    # 지역명으로 끝나는 경우
    location_endings = ['시', '도', '구', '군', '동', '로', '가', '읍', '면', '리', '에', '에서', '으로', '로']
    for ending in location_endings:
        if name.endswith(ending):
            return False
    
    # 명사로 끝나는 경우들
    noun_endings = ['시장', '의원', '사장', '부장', '과장', '팀장', '회장', '사무소', '병원', '학교', '회사', '고객님', '선생님']
    for ending in noun_endings:
        if name.endswith(ending):
            return False
    
    # 동사/형용사 어미들
    verb_endings = ['하다', '되다', '있다', '없다', '좋다', '나쁘다', '크다', '작다', '하고', '하며', '하는', '되는']
    for ending in verb_endings:
        if name.endswith(ending[:2]):  # 어미의 처음 2글자로 체크
            return False
    
    # 문법 조사들
    particle_endings = ['은', '는', '이', '가', '을', '를', '의', '에', '로', '와', '과', '도', '만', '부터', '까지']
    for particle in particle_endings:
        if name.endswith(particle):
            return False
    
    # 지역 관련 단어들
    location_words = {
        '서울', '부산', '대구', '인천', '광주', '대전', '울산', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
        '강남구에', '강북구에', '서초구에', '송파구에', '마포구에', '중구에', '동구에', '서구에', '남구에', '북구에'
    }
    if name in location_words:
        return False
    
    # 숫자가 포함된 경우
    if any(char.isdigit() for char in name):
        return False
    
    # 특수문자가 포함된 경우
    if not name.replace(' ', '').isalpha():
        return False
    
    return True

def detect_addresses_smart(text: str) -> List[Dict[str, Any]]:
    """스마트 주소 탐지 (첫 번째 주소만 선택)"""
    
    print("스마트 주소 탐지")
    
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
                    "source": "패턴-주소"
                })
                print(f"시/도 탐지: '{province}'")
    
    # 구/군 탐지
    districts = pools.districts
    for district in districts:
        if district in text:
            for match in re.finditer(re.escape(district), text):
                detected_locations.append({
                    "type": "주소",
                    "value": district,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.85,
                    "source": "패턴-주소"
                })
                print(f"구 탐지: '{district}'")
    
    # 도시 탐지
    cities = pools.cities
    for city in cities:
        if city in text:
            for match in re.finditer(re.escape(city), text):
                detected_locations.append({
                    "type": "주소",
                    "value": city,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.85,
                    "source": "패턴-주소"
                })
                print(f"도시 탐지: '{city}'")
    
    # 중복 제거 및 정렬
    detected_locations.sort(key=lambda x: x["start"])
    
    # 중복 위치 제거
    unique_locations = []
    used_positions = set()
    
    for location in detected_locations:
        position_key = (location["start"], location["end"])
        if position_key not in used_positions:
            unique_locations.append(location)
            used_positions.add(position_key)
    
    print(f"주소 중복 제거: {len(detected_locations)}개 → {len(unique_locations)}개")
    
    # 첫 번째 주소만 선택
    if unique_locations:
        selected = unique_locations[0]
        items.append(selected)
        print(f"선택된 주소: '{selected['value']}'")
    
    return items

# NER 관련 함수들 (기존 유지)
async def detect_with_ner_async(text: str, timeout: float = 0.08) -> List[Dict[str, Any]]:
    """비동기 NER 탐지 (타임아웃 적용)"""
    
    print(f"2차: NER 보강 (타임아웃: {int(timeout*1000)}ms)")
    
    try:
        # 타임아웃 적용
        ner_task = asyncio.create_task(_run_ner_detection(text))
        ner_items = await asyncio.wait_for(ner_task, timeout=timeout)
        
        print(f"2차 NER 보강 완료: {len(ner_items)}개 탐지")
        return ner_items
        
    except asyncio.TimeoutError:
        print(f"NER 타임아웃 ({int(timeout*1000)}ms) - 정규식만 사용")
        return []
    except Exception as e:
        print(f"NER 실행 오류: {e}")
        return []

async def _run_ner_detection(text: str) -> List[Dict[str, Any]]:
    """NER 모델 실행"""
    from .model import get_ner_model, is_ner_loaded
    
    if not is_ner_loaded():
        return []
    
    try:
        ner_model = get_ner_model()
        entities = ner_model.extract_entities(text)
        
        # 높은 임계치 적용 (간소화 모드)
        filtered_entities = []
        for entity in entities:
            if entity.get('confidence', 0) >= 0.8:  # 높은 임계치
                filtered_entities.append({
                    "type": entity['type'],
                    "value": entity['value'],
                    "start": entity.get('start', 0),
                    "end": entity.get('end', 0),
                    "confidence": entity['confidence'],
                    "source": "NER"
                })
                print(f"NER 탐지: {entity['type']} = '{entity['value']}' (신뢰도: {entity['confidence']:.2f})")
        
        return filtered_entities
        
    except Exception as e:
        print(f"NER 모델 실행 실패: {e}")
        return []

def merge_detections_with_priority(regex_items: List[Dict[str, Any]], ner_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """탐지 결과 병합 (규칙 우선, 중복 제거)"""
    
    print("탐지 결과 병합 (규칙 우선)")
    
    # 위치 기반 중복 체크
    merged_items = []
    used_positions = set()
    
    # 1. 규칙/정규식 결과 먼저 추가 (우선순위 높음)
    for item in regex_items:
        start, end = item['start'], item['end']
        position_key = (start, end, item['value'])
        
        if position_key not in used_positions:
            merged_items.append(item)
            used_positions.add(position_key)
    
    # 2. NER 결과 추가 (중복되지 않은 것만)
    for item in ner_items:
        start, end = item['start'], item['end']
        position_key = (start, end, item['value'])
        
        # 겹치는 위치가 있는지 확인
        overlapping = False
        for used_start, used_end, used_value in used_positions:
            if not (end <= used_start or start >= used_end):  # 겹침 체크
                overlapping = True
                break
        
        if not overlapping:
            merged_items.append(item)
            used_positions.add(position_key)
    
    print(f"병합 완료: 규칙 {len(regex_items)}개 + NER {len(ner_items)}개 → {len(merged_items)}개")
    
    return merged_items

def assign_tokens(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """치환 토큰 할당 ([PER_0], [ORG_0], [LOC_0] 등)"""
    
    print("치환 토큰 할당")
    
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
        
        print(f"{pii_value} → {token}")
    
    print(f"토큰 할당 완료: {len(token_map)}개")
    
    return token_map

def detect_pii_enhanced(text: str) -> Dict[str, Any]:
    """워크플로우 기반 강화된 PII 탐지"""
    
    print("=" * 60)
    print("워크플로우 기반 PII 탐지 시작")
    print("=" * 60)
    
    # 1차: 규칙/정규식 고속 패스
    regex_items = detect_with_regex_fast(text)
    
    # 실명 목록 탐지 (제외 단어 체크 추가됨)
    realname_items = detect_names_with_realname_list(text)
    regex_items.extend(realname_items)
    
    # 패턴 기반 이름 탐지 (중복 방지, 엄격한 필터링)
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

def detect_with_ner_simple(text: str) -> List[Dict[str, Any]]:
    """간소화된 NER 탐지 (호환성)"""
    return detect_with_ner(text)

def detect_with_regex(text: str) -> List[Dict[str, Any]]:
    """정규식 탐지 (호환성)"""
    return detect_with_regex_fast(text)

def detect_names_from_csv(text: str) -> List[Dict[str, Any]]:
    """CSV 이름 탐지 (호환성)"""
    return detect_names_with_realname_list(text)

def detect_addresses_from_csv(text: str) -> List[Dict[str, Any]]:
    """CSV 주소 탐지 (호환성)"""
    return detect_addresses_smart(text)

def merge_detections(items1: List[Dict[str, Any]], items2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """탐지 결과 병합 (호환성)"""
    return merge_detections_with_priority(items1, items2)