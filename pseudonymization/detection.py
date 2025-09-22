# pseudonymization/detection.py - 모듈화된 PII 탐지 (고객 등 일반명사 제외)
import re
import asyncio
from typing import List, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor

from .pools import get_pools

# ===== 정규식 패턴 =====
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'010[-\s]?\d{4}[-\s]?\d{4}')
AGE_PATTERN = re.compile(r'\b(\d{1,2})\s*(?:세|살)\b')

# 강화된 이름 패턴 (일반명사 제외, 호칭 추가)
NAME_PATTERNS = [
    re.compile(r'이름은\s*([가-힣]{2,4})'),
    re.compile(r'저는\s*([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})\s*입니다'),
    re.compile(r'([가-힣]{2,4})(?:이에요|예요|이야|야)'),
    re.compile(r'([가-힣]{2,4})(?:입니다|이다)'),
    re.compile(r'안녕하세요,?\s*(?:저는\s*)?([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})이고'),
    re.compile(r'([가-힣]{2,4})이며'),
    re.compile(r'([가-힣]{2,4})라고\s*합니다'),
    re.compile(r'([가-힣]{2,4})라고\s*해요'),
    # 호칭 패턴 추가 (아, 야, 이 등)
    re.compile(r'([가-힣]{2,4})(?:아|야|이)\s'),
    # "님"이나 "씨" 패턴에서 일반 명사 제외
    re.compile(r'(?<!고객|손님|회원|선생|교수|의사|직원|학생|선배|후배|동료|친구)([가-힣]{2,4})(?:님|씨)'),
]

def is_valid_name(name: str) -> bool:
    """유효한 이름인지 검증 (강화된 필터링)"""
    pools = get_pools()
    
    if not name or len(name) < 2 or len(name) > 4:
        return False
    
    if name in pools.name_exclude_words:
        print(f"제외 단어 무시: '{name}'")
        return False
    
    # 숫자나 특수문자 포함시 제외
    if any(char.isdigit() or not char.isalpha() for char in name):
        return False
    
    # 일반 명사들 추가 체크
    common_nouns = {
        "고객", "손님", "회원", "선생", "교수", "의사", "직원", "학생",
        "친구", "선배", "후배", "동료", "가족", "부모", "자녀", "형제",
        "자매", "사람", "분들", "여러분", "모든", "모두", "전부", "일부",
        "관리", "담당", "책임", "업무", "근무", "출근", "퇴근", "회사",
        "조직", "팀원", "부서", "센터", "지점", "본사", "지사"
    }
    
    if name in common_nouns:
        print(f"일반 명사 무시: '{name}'")
        return False
    
    # 문법 패턴 제외
    grammar_patterns = [
        r'.*은$', r'.*는$', r'.*이$', r'.*가$', r'.*을$', r'.*를$',
        r'.*에$', r'.*에서$', r'.*으로$', r'.*로$', r'.*죠$', r'.*요$',
        r'.*며$', r'.*고$', r'.*다$', r'.*니다$'
    ]
    
    for pattern in grammar_patterns:
        if re.match(pattern, name):
            print(f"문법 패턴 무시: '{name}'")
            return False
    
    return True

def detect_emails(text: str) -> List[Dict[str, Any]]:
    """이메일 탐지"""
    items = []
    print("이메일 패턴 검사 중...")
    
    for match in EMAIL_PATTERN.finditer(text):
        email = match.group()
        items.append({
            "type": "이메일",
            "value": email,
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.95,
            "source": "정규식-이메일"
        })
        print(f"이메일 탐지: '{email}'")
    
    return items

def detect_phones(text: str) -> List[Dict[str, Any]]:
    """전화번호 탐지"""
    items = []
    print("전화번호 패턴 검사 중...")
    
    for match in PHONE_PATTERN.finditer(text):
        phone = match.group()
        items.append({
            "type": "전화번호",
            "value": phone,
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.90,
            "source": "정규식-전화번호"
        })
        print(f"전화번호 탐지: '{phone}'")
    
    return items

def detect_names_from_realname_list(text: str) -> List[Dict[str, Any]]:
    """실명 목록 기반 이름 탐지 (강화된 필터링)"""
    items = []
    pools = get_pools()
    
    print("실명 목록 기반 이름 탐지")
    
    for name in pools.real_names:
        if not is_valid_name(name):
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
    
    return items

def detect_names_from_patterns(text: str, existing_names: Set[str] = None) -> List[Dict[str, Any]]:
    """패턴 기반 이름 탐지 (중복 제거, 강화된 필터링)"""
    items = []
    
    if existing_names is None:
        existing_names = set()
    
    print("패턴 기반 이름 탐지")
    
    for pattern in NAME_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            
            if not is_valid_name(name) or name in existing_names:
                continue
            
            items.append({
                "type": "이름",
                "value": name,
                "start": match.start(1),
                "end": match.end(1),
                "confidence": 0.80,
                "source": "패턴-이름"
            })
            print(f"패턴 이름 탐지: '{name}'")
            existing_names.add(name)
    
    return items

def detect_addresses_smart(text: str) -> List[Dict[str, Any]]:
    """스마트 주소 탐지 (CSV 데이터 활용, 첫 번째 주소만)"""
    items = []
    pools = get_pools()
    
    print("스마트 주소 탐지 (CSV 데이터 활용)")
    all_addresses = []
    
    # 1. 복합 주소 패턴 탐지 (가장 우선순위)
    # "대전시 중구 태평동 87", "서울시 강남구 테헤란로" 등
    for province in pools.provinces:
        for city in pools.cities:
            # 시/도 + 시/구/군 + 동/로/가 패턴
            complex_patterns = [
                rf'{re.escape(province)}(?:시|도)?\s+{re.escape(city)}(?:시|구|군)\s+[가-힣\d\s,-]+(?:동|로|가|번지|층|호)',
                rf'{re.escape(province)}(?:시|도)?\s+{re.escape(city)}(?:구|군)',
                rf'{re.escape(province)}(?:시|도)\s+{re.escape(city)}(?:구|군)'
            ]
            
            for pattern in complex_patterns:
                for match in re.finditer(pattern, text):
                    all_addresses.append({
                        "type": "주소",
                        "value": province,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.98,
                        "source": "패턴-복합주소",
                        "priority": 1,
                        "full_match": match.group()
                    })
                    print(f"복합 주소 탐지: '{province}' (전체: {match.group()})")
    
    # 2. 도로명 포함 주소 패턴
    for province in pools.provinces:
        for road in pools.roads[:100]:  # 성능을 위해 상위 100개만 사용
            road_patterns = [
                rf'{re.escape(province)}(?:시|도)?\s+[가-힣]+(?:구|군)?\s+{re.escape(road)}(?:로|길)',
                rf'{re.escape(province)}(?:시|도)?\s+{re.escape(road)}(?:로|길)'
            ]
            
            for pattern in road_patterns:
                for match in re.finditer(pattern, text):
                    all_addresses.append({
                        "type": "주소",
                        "value": province,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.95,
                        "source": "패턴-도로명주소",
                        "priority": 2,
                        "full_match": match.group()
                    })
                    print(f"도로명 주소 탐지: '{province}' (전체: {match.group()})")
    
    # 3. 시/도 + 구/군 기본 패턴
    for province in pools.provinces:
        # 시/도 + 구/군 패턴
        basic_pattern = rf'{re.escape(province)}(?:시|도)?\s+[가-힣]+(?:구|군)'
        
        for match in re.finditer(basic_pattern, text):
            all_addresses.append({
                "type": "주소",
                "value": province,
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.90,
                "source": "패턴-기본주소",
                "priority": 3,
                "full_match": match.group()
            })
            print(f"기본 주소 탐지: '{province}' (전체: {match.group()})")
    
    # 4. 키워드 기반 탐지 (기존 방식, 낮은 우선순위)
    for province in pools.provinces:
        for match in re.finditer(re.escape(province), text):
            # 주변 문맥 확인
            start_pos = max(0, match.start() - 20)
            end_pos = min(len(text), match.end() + 20)
            context = text[start_pos:end_pos]
            
            # 주소 관련 단어들
            address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '소재', '예약', '지역', '출신', '본적', '와', '가']
            
            if any(keyword in context for keyword in address_keywords):
                all_addresses.append({
                    "type": "주소",
                    "value": province,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.85,
                    "source": "패턴-키워드주소",
                    "priority": 4,
                    "full_match": match.group()
                })
                print(f"키워드 주소 탐지: '{province}'")
    
    # 첫 번째 주소만 선택 (우선순위와 위치 기준)
    if all_addresses:
        # 우선순위와 시작 위치 기준 정렬
        all_addresses.sort(key=lambda x: (x["priority"], x["start"]))
        selected_address = all_addresses[0]
        
        # 중복 제거를 위해 동일한 province는 하나만
        unique_address = {
            "type": selected_address["type"],
            "value": selected_address["value"],
            "start": selected_address["start"],
            "end": selected_address["end"],
            "confidence": selected_address["confidence"],
            "source": selected_address["source"]
        }
        
        items.append(unique_address)
        print(f"최종 선택된 주소: '{selected_address['value']}' (출처: {selected_address['source']})")
    
    return items

def detect_ages(text: str) -> List[Dict[str, Any]]:
    """나이 탐지"""
    items = []
    print("나이 패턴 검사 중...")
    
    for match in AGE_PATTERN.finditer(text):
        age = match.group(1)
        if 1 <= int(age) <= 120:
            items.append({
                "type": "나이",
                "value": age,
                "start": match.start(),
                "end": match.end(),
                "confidence": 1.0,
                "source": "정규식-나이"
            })
            print(f"나이 탐지: '{age}'")
    
    return items

async def detect_pii_enhanced(text: str) -> List[Dict[str, Any]]:
    """강화된 PII 탐지 (통합)"""
    items = []
    
    print(f"강화된 PII 분석: {text}")
    
    # 1. 이메일 탐지
    items.extend(detect_emails(text))
    
    # 2. 전화번호 탐지
    items.extend(detect_phones(text))
    
    # 3. 실명 목록 기반 이름 탐지
    name_items = detect_names_from_realname_list(text)
    items.extend(name_items)
    
    # 4. 패턴 기반 이름 탐지 (중복 제거)
    existing_names = {item["value"] for item in name_items}
    items.extend(detect_names_from_patterns(text, existing_names))
    
    # 5. 스마트 주소 탐지
    items.extend(detect_addresses_smart(text))
    
    # 6. 나이 탐지
    items.extend(detect_ages(text))
    
    print(f"탐지 완료: {len(items)}개 항목")
    return items

# ===== 호환성 함수들 =====
def detect_with_ner(text: str) -> List[Dict[str, Any]]:
    """NER 모델을 사용한 탐지 (호환성)"""
    # 현재는 정규식 기반만 사용
    return asyncio.run(detect_pii_enhanced(text))

def detect_with_regex(text: str) -> List[Dict[str, Any]]:
    """정규식을 사용한 탐지 (호환성)"""
    return asyncio.run(detect_pii_enhanced(text))

def detect_names_from_csv(text: str) -> List[Dict[str, Any]]:
    """CSV에서 이름 탐지 (호환성)"""
    return detect_names_from_realname_list(text)

def detect_addresses_from_csv(text: str) -> List[Dict[str, Any]]:
    """CSV에서 주소 탐지 (호환성)"""
    return detect_addresses_smart(text)

def merge_detections(*detection_lists) -> List[Dict[str, Any]]:
    """탐지 결과 병합 (호환성)"""
    merged = []
    for detection_list in detection_lists:
        if detection_list:
            merged.extend(detection_list)
    
    # 중복 제거 (위치 기준)
    seen_positions = set()
    unique_items = []
    
    for item in merged:
        position = (item["start"], item["end"])
        if position not in seen_positions:
            unique_items.append(item)
            seen_positions.add(position)
    
    return unique_items