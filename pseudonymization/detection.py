# pseudonymization/detection.py
"""
워크플로우 기반 PII 탐지 모듈 (주소/이메일 탐지 개선)
- 전국 시/구 완전 탐지
- 첫 번째 주소만 치환
- 이메일 탐지 강화
"""

import re
import asyncio
from typing import List, Dict, Any, Set
from .pools import get_pools, NAME_EXCLUDE_WORDS

def detect_with_regex_fast(text: str) -> List[Dict[str, Any]]:
    """1차: 규칙/정규식 고속 패스 (핵심 패턴만)"""
    
    print("1차: 규칙/정규식 고속 패스")
    
    items = []
    
    # 이메일 (더 관대한 패턴들)
    email_patterns = [
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # 기본 패턴
        r'\b\w+@\w+\.\w+\b',  # 단순 패턴
        r'[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # 경계 없는 패턴
    ]
    
    found_emails = set()  # 중복 제거용
    for pattern in email_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            email = match.group().lower()
            if email not in found_emails and '@' in email and '.' in email:
                # 유효한 이메일인지 추가 검증
                if len(email.split('@')) == 2:
                    local, domain = email.split('@')
                    if local and domain and '.' in domain:
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
                "confidence": 0.95,
                "source": "정규식-주민등록번호"
            })
            print(f"주민등록번호 탐지: '{match.group()}'")
    
    print(f"규칙/정규식 탐지 완료: {len(items)}개")
    return items

def detect_names_with_realname_list(text: str) -> List[Dict[str, Any]]:
    """실명 목록 기반 이름 탐지 (제외 단어 적용)"""
    
    print("실명 목록 기반 이름 탐지")
    
    pools = get_pools()
    items = []
    
    # 실명 목록에서 탐지
    for name in pools.real_names:
        # 제외 단어 체크
        if name in NAME_EXCLUDE_WORDS:
            print(f"실명 목록 제외 단어 무시: '{name}'")
            continue
            
        # 텍스트에서 해당 이름 찾기
        for match in re.finditer(re.escape(name), text):
            # 앞뒤 문자 확인 (단어 경계)
            start_pos = match.start()
            end_pos = match.end()
            
            # 단어 경계 확인
            if start_pos > 0 and text[start_pos-1].isalpha():
                continue
            if end_pos < len(text) and text[end_pos].isalpha():
                continue
                
            items.append({
                "type": "이름",
                "value": name,
                "start": start_pos,
                "end": end_pos,
                "confidence": 0.95,
                "source": "실명목록"
            })
            print(f"실명 탐지: '{name}'")
    
    print(f"실명 목록 탐지 완료: {len(items)}개")
    return items

def detect_names_with_patterns(text: str, detected_names: Set[str]) -> List[Dict[str, Any]]:
    """패턴 기반 이름 탐지 (중복 방지, 엄격한 필터링)"""
    
    print("패턴 기반 이름 탐지")
    
    items = []
    
    def should_exclude_pattern(name: str) -> bool:
        """패턴 기반 제외 여부 판단"""
        
        # 제외 단어 리스트 체크
        if name in NAME_EXCLUDE_WORDS:
            print(f"제외 단어 무시: '{name}'")
            return True
        
        # 이미 탐지된 이름 제외
        if name in detected_names:
            return True
        
        # 문법 패턴 체크 (조사, 어미 등)
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
    """전국 주소 완전 탐지 (모든 주소 탐지, 첫 번째만 선택)"""
    
    print("전국 주소 완전 탐지 (모든 주소 찾기)")
    
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
            
            address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '소재', '예약', '지역']
            
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
            
            address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '소재', '예약', '지역']
            
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
    
    # 중복 제거 및 첫 번째 주소만 선택
    if all_addresses:
        # 위치별로 정렬 (가장 먼저 나오는 것)
        all_addresses.sort(key=lambda x: x['start'])
        
        print(f"전체 주소 탐지 완료: {len(all_addresses)}개")
        
        # 첫 번째 주소만 반환
        first_address = all_addresses[0]
        print(f"선택된 주소: '{first_address['value']}'")
        
        return [first_address]
    
    print("전체 주소 탐지 완료: 0개")
    return []

async def detect_with_ner_async(text: str, timeout: float = 0.08) -> List[Dict[str, Any]]:
    """2차: NER 보강 (비동기, 타임아웃)"""
    
    print(f"2차: NER 보강 (타임아웃: {timeout*1000:.0f}ms)")
    
    try:
        from .model import get_ner_model, is_ner_loaded
        
        if not is_ner_loaded():
            print("NER 모델이 로드되지 않음")
            return []
        
        model = get_ner_model()
        
        # 타임아웃 적용
        task = asyncio.create_task(asyncio.to_thread(model.extract_entities, text))
        ner_results = await asyncio.wait_for(task, timeout=timeout)
        
        items = []
        for result in ner_results:
            items.append({
                "type": result.get('type', '기타'),
                "value": result.get('value', ''),
                "start": result.get('start', 0),
                "end": result.get('end', 0),
                "confidence": result.get('confidence', 0.5),
                "source": f"NER-{result.get('model', 'unknown')}"
            })
        
        print(f"NER ({model.model_name}) 탐지: {len(items)}개 항목")
        return items
        
    except asyncio.TimeoutError:
        print(f"NER 타임아웃 ({timeout*1000:.0f}ms 초과)")
        return []
    except Exception as e:
        print(f"NER 처리 오류: {e}")
        return []
    
    finally:
        print(f"2차 NER 보강 완료: {len(items) if 'items' in locals() else 0}개 탐지")

def detect_with_ner(text: str) -> List[Dict[str, Any]]:
    """NER 모델 기반 PII 탐지 (동기 버전)"""
    
    try:
        from .model import get_ner_model, is_ner_loaded
        
        if not is_ner_loaded():
            return []
        
        model = get_ner_model()
        ner_results = model.extract_entities(text)
        
        items = []
        for result in ner_results:
            items.append({
                "type": result.get('type', '기타'),
                "value": result.get('value', ''),
                "start": result.get('start', 0),
                "end": result.get('end', 0),
                "confidence": result.get('confidence', 0.5),
                "source": f"NER-{result.get('model', 'unknown')}"
            })
        
        return items
        
    except Exception as e:
        print(f"NER 처리 오류: {e}")
        return []

def detect_with_regex(text: str) -> List[Dict[str, Any]]:
    """정규식 기반 PII 탐지 (호환성 함수)"""
    return detect_with_regex_fast(text)

def detect_names_from_csv(text: str) -> List[Dict[str, Any]]:
    """CSV 기반 이름 탐지 (호환성 함수)"""
    return detect_names_with_realname_list(text)

def detect_addresses_from_csv(text: str) -> List[Dict[str, Any]]:
    """CSV 기반 주소 탐지 (호환성 함수)"""
    return detect_addresses_comprehensive(text)

def merge_detections(regex_items: List[Dict], ner_items: List[Dict]) -> List[Dict]:
    """탐지 결과 병합 (호환성 함수)"""
    return merge_detections_with_priority(regex_items, ner_items)

def merge_detections_with_priority(regex_items: List[Dict], ner_items: List[Dict]) -> List[Dict]:
    """탐지 결과 병합 (규칙 우선, 겹치는 항목 제거)"""
    
    print("탐지 결과 병합 (규칙 우선)")
    
    merged = regex_items.copy()
    
    def is_overlapping(item1: Dict, item2: Dict) -> bool:
        """두 항목이 겹치는지 확인"""
        start1, end1 = item1['start'], item1['end']
        start2, end2 = item2['start'], item2['end']
        return not (end1 <= start2 or start1 >= end2)
    
    # NER 결과 중 겹치지 않는 것만 추가
    for ner_item in ner_items:
        overlapping = False
        for regex_item in regex_items:
            if is_overlapping(ner_item, regex_item):
                overlapping = True
                break
        
        if not overlapping:
            merged.append(ner_item)
    
    print(f"병합 완료: 규칙 {len(regex_items)}개 + NER {len(ner_items)}개 → {len(merged)}개")
    return merged

def assign_tokens(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """치환 토큰 할당"""
    
    print("치환 토큰 할당")
    
    token_map = {}
    type_counters = {}
    
    for item in items:
        pii_type = item['type']
        value = item['value']
        
        # 이미 할당된 값이면 스킵
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
        elif pii_type == "주소":
            token = f"[LOC_{type_counters[pii_type]}]"
        elif pii_type == "이메일":
            token = f"[EMAIL_{type_counters[pii_type]}]"
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
    
    # 전국 주소 완전 탐지 (첫 번째만 선택)
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
    
    return {
        'items': merged_items,
        'token_map': token_map,
        'total_detected': len(merged_items)
    }