# pseudonymization/detection.py
"""
워크플로우 기반 PII 탐지 모듈
1차: 규칙/정규식 고속 패스
2차: NER 보강 (비동기, 타임아웃, 높은 임계치)
치환 토큰: [PER_0], [ORG_0], [LOC_0] 등
"""

import re
import asyncio
import time
from typing import List, Dict, Any, Set

# 정규식 패턴 (1차 고속 패스)
EMAIL_PATTERN = re.compile(r'\S+@\S+\.\S+')
PHONE_PATTERN = re.compile(
    r'(?:010|011|016|017|018|019|02|031|032|033|041|042|043|044|051|052|053|054|055|061|062|063|064)'
    r'[-.\s]?\d{3,4}[-.\s]?\d{4}'
)
AGE_PATTERN = re.compile(r'(\d{1,3})\s*(?:세|살)')
RRN_PATTERN = re.compile(r'\d{6}[-\s]?\d{7}')
CARD_PATTERN = re.compile(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}')
ACCOUNT_PATTERN = re.compile(r'\d{10,16}')  # 계좌번호

# 특별 처리가 필요한 지역
SPECIAL_CITIES = {
    '대구': 'city',  # 대구는 시이지만 "구"로 끝남
    '대전': 'city',
    '부산': 'city',
    '서울': 'city',
    '인천': 'city',
    '광주': 'city',
    '울산': 'city'
}

def detect_with_regex_fast(text: str) -> List[Dict[str, Any]]:
    """1차: 규칙/정규식 고속 패스"""
    items = []
    
    print("🚀 1차: 규칙/정규식 고속 패스")
    
    # 이메일 탐지
    for match in EMAIL_PATTERN.finditer(text):
        items.append({
            "type": "이메일",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "규칙-이메일"
        })
        print(f"📧 이메일 탐지: '{match.group()}'")
    
    # 전화번호 탐지
    for match in PHONE_PATTERN.finditer(text):
        items.append({
            "type": "전화번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "규칙-전화번호"
        })
        print(f"📞 전화번호 탐지: '{match.group()}'")
    
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
                "confidence": 1.0,
                "source": "규칙-나이"
            })
            print(f"🎂 나이 탐지: '{age_value}'")
    
    # 주민등록번호 탐지
    for match in RRN_PATTERN.finditer(text):
        items.append({
            "type": "주민등록번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "규칙-주민등록번호"
        })
        print(f"🆔 주민등록번호 탐지: '{match.group()}'")
    
    # 신용카드 탐지
    for match in CARD_PATTERN.finditer(text):
        items.append({
            "type": "신용카드",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "규칙-신용카드"
        })
        print(f"💳 신용카드 탐지: '{match.group()}'")
    
    print(f"🚀 1차 고속 패스 완료: {len(items)}개 탐지")
    return items

def detect_names_with_realname_list(text: str) -> List[Dict[str, Any]]:
    """실명 목록 기반 이름 탐지"""
    items = []
    
    print("👤 실명 목록 기반 이름 탐지")
    
    # 일반적인 한국어 이름 목록 (확장)
    common_korean_names = [
        '김철수', '이영희', '박민수', '최영수', '정민준', '강서윤', '조지우', '윤서현',
        '장하은', '임예은', '한지민', '오윤서', '서하윤', '신채원', '권지원', '황수빈',
        '안다은', '송예린', '류시은', '전소은', '홍길동', '김영희', '이철수', '박영수',
        '최민수', '정영희', '강철수', '조영수', '윤민수', '장영희', '임철수', '한영수',
        '김민준', '이서준', '박도윤', '최예준', '정시우', '강주원', '조하준', '윤지호',
        '장준서', '임건우', '한현우', '오우진', '서선우', '신연우', '권정우', '황성민',
        '김가영', '이나영', '박수영', '최지영', '정민영', '강유영', '조소영', '윤은영'
    ]
    
    # 실명 목록에서 직접 찾기
    for name in common_korean_names:
        if name in text:
            start_pos = text.find(name)
            items.append({
                "type": "이름",
                "value": name,
                "start": start_pos,
                "end": start_pos + len(name),
                "confidence": 0.95,
                "source": "실명목록"
            })
            print(f"👤 실명 탐지: '{name}'")
    
    return items

def detect_names_with_patterns(text: str, exclude_detected: Set[str]) -> List[Dict[str, Any]]:
    """패턴 기반 이름 탐지"""
    items = []
    
    print("🔍 패턴 기반 이름 탐지")
    
    # 이름 패턴들 (높은 신뢰도)
    name_patterns = [
        r'([가-힣]{2,4})님(?!\w)',          # 이영희님
        r'([가-힣]{2,4})씨(?!\w)',          # 홍길동씨  
        r'이름은\s*([가-힣]{2,4})(?!\w)',   # 이름은 홍길동
        r'저는\s*([가-힣]{2,4})(?!\w)',     # 저는 홍길동
        r'([가-힣]{2,4})이고(?!\w)',        # 홍길동이고
    ]
    
    # 제외할 단어 (확장)
    exclude_words = {
        '고객', '회원', '사용자', '관리자', '직원', '담당자', '선생', '교수',
        '부장', '과장', '대리', '팀장', '사장', '대표', '예약', '확인', '문의',
        '연락', '주세', '있습니다', '했습니다', '합니다', '입니다'
    }
    
    for pattern in name_patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            
            # 이미 탐지된 이름이거나 제외 단어면 스킵
            if name in exclude_detected or name in exclude_words:
                continue
                
            # 기본 유효성 검사
            if (len(name) >= 2 and 
                all(ord('가') <= ord(char) <= ord('힣') for char in name)):
                
                items.append({
                    "type": "이름",
                    "value": name,
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.85,
                    "source": "패턴-이름"
                })
                print(f"👤 패턴 이름 탐지: '{name}'")
                exclude_detected.add(name)
    
    return items

def detect_addresses_smart(text: str) -> List[Dict[str, Any]]:
    """스마트 주소 탐지 (중복 방지)"""
    items = []
    
    print("🏠 스마트 주소 탐지")
    
    # 주요 도시 (특별 처리 포함)
    cities = list(SPECIAL_CITIES.keys()) + ['세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
    
    # 주요 구
    districts = [
        '강남구', '서초구', '송파구', '강동구', '마포구', '용산구', '종로구', '중구',
        '강서구', '양천구', '구로구', '금천구', '영등포구', '동작구', '관악구',
        '해운대구', '부산진구', '동래구', '수영구', '남구', '북구', '수원시', '성남시'
    ]
    
    detected_locations = []
    
    # 시/도 탐지
    for city in cities:
        if city in text:
            for match in re.finditer(re.escape(city), text):
                detected_locations.append({
                    "type": "주소",
                    "value": city,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                    "source": "패턴-주소",
                    "location_type": "city"
                })
                print(f"🏙️ 도시 탐지: '{city}'")
    
    # 구 탐지 (대구 등 특별 처리)
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