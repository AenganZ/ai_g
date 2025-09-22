# pseudonymization/normalizers.py - 탐지 + 정규화 통합 모듈
import re
import asyncio
from typing import Optional, Dict, List, Any

# 정규식 패턴들
EMAIL_RX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
AGE_RX = re.compile(r"\b(\d{1,3})\s*(?:세|살)?\b")
PHONE_NUM_ONLY = re.compile(r"\D+")
PHONE_PATTERN = re.compile(r'010[-\s]?\d{4}[-\s]?\d{4}')

# 이름 탐지 패턴
NAME_PATTERNS = [
    re.compile(r'이름은\s*([가-힣]{2,4})'),
    re.compile(r'저는\s*([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})\s*입니다'),
    re.compile(r'([가-힣]{2,4})(?:이에요|예요|이야|야)'),
    re.compile(r'([가-힣]{2,4})(?:님|씨)(?![가-힣])'),
    re.compile(r'안녕하세요,?\s*(?:저는\s*)?([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})이고'),
    re.compile(r'([가-힣]{2,4})라고\s*합니다'),
    re.compile(r'([가-힣]{2,4})\s*고객'),
]

# NER 모델 import (선택적)
try:
    from .model import extract_entities_with_ner, is_ner_available, is_ner_loaded
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False

def get_pools():
    """pools.py에서 데이터풀 가져오기"""
    from .pools import get_pools
    return get_pools()

def is_valid_korean_name(name: str) -> bool:
    """한국어 이름 유효성 검증 (강화됨)"""
    pools = get_pools()
    
    if not name or len(name) < 2 or len(name) > 4:
        return False
    
    # '씨' 제거 후 검사
    clean_name = name.replace('씨', '').replace('님', '')
    if len(clean_name) < 2:
        return False
    
    # 한글만 허용
    if not all('\uac00' <= char <= '\ud7af' for char in name):
        return False
    
    # 숫자 포함 제외
    if any(char.isdigit() for char in name):
        return False
    
    # 제외 단어들
    if name in pools.name_exclude_words:
        return False
    
    # 확장된 일반명사 목록
    common_nouns = {
        "고객", "손님", "회원", "선생", "교수", "의사", "직원", "학생",
        "친구", "선배", "후배", "동료", "가족", "부모", "자녀", "형제",
        "자매", "사람", "분들", "여러분", "모든", "모두", "전부", "일부",
        # 업무 관련 일반명사 추가
        "담당자", "책임자", "관리자", "운영자", "개발자", "설계자", "기획자",
        "상담원", "안내원", "접수원", "대리", "과장", "부장", "팀장", "실장",
        "차장", "이사", "상무", "전무", "사장", "대표", "회장", "의장",
        # 시간/순서 관련
        "이번", "다음", "저번", "처음", "마지막", "첫째", "둘째", "셋째",
        "오늘", "어제", "내일", "지금", "나중", "앞서", "이후", "이전",
        # 기타 일반어
        "그분", "이분", "저분", "누군가", "아무나", "모든", "각자", "서로",
        "혼자", "함께", "같이", "따로", "별도", "개별", "공동", "전체"
    }
    
    if name in common_nouns or clean_name in common_nouns:
        return False
    
    # 지역명 제외
    all_regions = set(pools.provinces + pools.cities + pools.roads)
    if name in all_regions or clean_name in all_regions:
        return False
    
    # 한국어 성씨 확인 (선택적 강화)
    common_surnames = {
        "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", 
        "서", "신", "권", "황", "안", "송", "전", "홍", "고", "문", "양", "손"
    }
    
    # 2글자 이름인데 성씨로 시작하지 않으면 의심스러움 (완전 제외하지는 않음)
    if len(clean_name) == 2 and clean_name[0] not in common_surnames:
        # 하지만 실명 목록에 있으면 허용
        if clean_name not in pools.real_names:
            return False
    
    return True

# ===== PII 탐지 함수들 =====

def detect_emails(text: str) -> List[Dict[str, Any]]:
    """이메일 탐지"""
    items = []
    for match in EMAIL_RX.finditer(text):
        email = match.group()
        items.append({
            "type": "이메일",
            "value": email,
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.95,
            "source": "normalizers-이메일"
        })
    return items

def detect_phones(text: str) -> List[Dict[str, Any]]:
    """전화번호 탐지"""
    items = []
    for match in PHONE_PATTERN.finditer(text):
        phone = match.group()
        normalized_phone = phone.replace(' ', '').replace('-', '')
        if len(normalized_phone) == 11 and normalized_phone.startswith('010'):
            formatted_phone = f"{normalized_phone[:3]}-{normalized_phone[3:7]}-{normalized_phone[7:]}"
            items.append({
                "type": "전화번호",
                "value": formatted_phone,
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.95,
                "source": "normalizers-전화번호"
            })
    return items

def detect_ages(text: str) -> List[Dict[str, Any]]:
    """나이 탐지 (엄격한 검증)"""
    items = []
    for match in AGE_RX.finditer(text):
        age_str = match.group(1)
        
        try:
            age = int(age_str)
            if 1 <= age <= 120 and len(age_str) <= 2:
                start_pos = max(0, match.start() - 10)
                end_pos = min(len(text), match.end() + 10)
                context = text[start_pos:end_pos]
                
                age_keywords = ['세', '살', '나이', '연령', '만', '년생', '올해']
                if any(keyword in context for keyword in age_keywords):
                    items.append({
                        "type": "나이",
                        "value": age_str,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 1.0,
                        "source": "normalizers-나이"
                    })
        except ValueError:
            continue
    return items

def detect_names(text: str) -> List[Dict[str, Any]]:
    """이름 탐지 (중복 제거 강화)"""
    items = []
    detected_names = set()
    
    # 1. 패턴 기반 탐지
    for pattern in NAME_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            
            if not is_valid_korean_name(name):
                continue
            
            # 중복 제거: 기본 형태로 정규화
            clean_name = name.replace('씨', '').replace('님', '')
            
            # 이미 탐지된 이름의 변형인지 확인
            is_duplicate = False
            for existing in detected_names:
                existing_clean = existing.replace('씨', '').replace('님', '')
                # 같은 기본 이름이면 중복 처리
                if clean_name == existing_clean:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            items.append({
                "type": "이름",
                "value": name,
                "start": match.start(1),
                "end": match.end(1),
                "confidence": 0.85,
                "source": "normalizers-이름패턴"
            })
            detected_names.add(name)
    
    # 2. 실명 목록 기반 탐지 (중복 확인)
    pools = get_pools()
    for name in pools.real_names:
        if not is_valid_korean_name(name):
            continue
        
        # 이미 탐지된 이름과 중복 확인
        clean_name = name.replace('씨', '').replace('님', '')
        is_duplicate = False
        for existing in detected_names:
            existing_clean = existing.replace('씨', '').replace('님', '')
            if clean_name == existing_clean:
                is_duplicate = True
                break
        
        if is_duplicate:
            continue
        
        for match in re.finditer(re.escape(name), text):
            items.append({
                "type": "이름",
                "value": name,
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.90,
                "source": "normalizers-실명목록"
            })
            detected_names.add(name)
    
    return items

def detect_addresses(text: str) -> List[Dict[str, Any]]:
    """주소 탐지 (첫 번째 시/도만)"""
    items = []
    pools = get_pools()
    all_addresses = []
    
    # 1. 복합 주소 패턴
    for province in pools.provinces:
        complex_patterns = [
            rf'{re.escape(province)}(?:시|도)?\s+[가-힣]+(?:구|군|시)',
            rf'{re.escape(province)}\s+[가-힣]+(?:구|군)',
        ]
        
        for pattern in complex_patterns:
            for match in re.finditer(pattern, text):
                all_addresses.append({
                    "province": province,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "priority": 1,
                    "full_match": match.group()
                })
    
    # 2. 단일 주소 패턴
    if not all_addresses:
        for province in pools.provinces:
            for match in re.finditer(re.escape(province), text):
                start_pos = max(0, match.start() - 15)
                end_pos = min(len(text), match.end() + 15)
                context = text[start_pos:end_pos]
                
                address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '예약', '지역']
                if any(keyword in context for keyword in address_keywords):
                    all_addresses.append({
                        "province": province,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.80,
                        "priority": 2,
                        "full_match": match.group()
                    })
    
    # 3. 첫 번째 주소만 선택
    if all_addresses:
        all_addresses.sort(key=lambda x: (x["priority"], x["start"]))
        selected = all_addresses[0]
        
        items.append({
            "type": "주소",
            "value": selected["province"],
            "start": selected["start"],
            "end": selected["end"],
            "confidence": selected["confidence"],
            "source": "normalizers-주소"
        })
    
    return items

def detect_with_ner_supplement(text: str, existing_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """NER 모델 보완 탐지 (중복 제거 강화)"""
    if not NER_AVAILABLE:
        return []
    
    try:
        # 기존 탐지된 항목들 수집 (정규화된 형태로)
        existing_values = set()
        for item in existing_items:
            value = item["value"]
            # 이름의 경우 '씨', '님' 제거한 형태도 추가
            existing_values.add(value)
            if item["type"] == "이름":
                clean_value = value.replace('씨', '').replace('님', '')
                existing_values.add(clean_value)
        
        ner_entities = extract_entities_with_ner(text)
        
        supplementary_items = []
        for entity in ner_entities:
            entity_type = entity.get('type', '')
            entity_value = entity.get('value', '')
            confidence = entity.get('confidence', 0.0)
            
            # 정규화된 값으로 중복 확인
            clean_entity_value = entity_value.replace('씨', '').replace('님', '')
            
            # 이미 탐지된 항목과 중복 확인
            if entity_value in existing_values or clean_entity_value in existing_values:
                continue
            
            # 높은 신뢰도만 (NER 보완용이므로 엄격하게)
            if confidence > 0.9:
                # 이름의 경우 추가 검증
                if entity_type == "이름":
                    if not is_valid_korean_name(entity_value):
                        continue
                    # 영문자나 숫자가 포함된 경우 제외 (junseok124 같은 케이스)
                    if not all('\uac00' <= char <= '\ud7af' or char in '씨님' for char in entity_value):
                        continue
                
                supplementary_items.append({
                    "type": entity_type,
                    "value": entity_value,
                    "start": entity.get('start', 0),
                    "end": entity.get('end', 0),
                    "confidence": confidence,
                    "source": f"NER-보완"
                })
        
        return supplementary_items
        
    except Exception as e:
        return []

async def detect_pii_all(text: str) -> List[Dict[str, Any]]:
    """통합 PII 탐지 함수"""
    all_items = []
    
    # 1단계: normalizers 기반 주요 탐지
    all_items.extend(detect_emails(text))
    all_items.extend(detect_phones(text))
    all_items.extend(detect_names(text))
    all_items.extend(detect_addresses(text))
    all_items.extend(detect_ages(text))
    
    # 2단계: NER 보완 (선택적)
    if NER_AVAILABLE:
        ner_supplement = detect_with_ner_supplement(text, all_items)
        all_items.extend(ner_supplement)
    
    # 3단계: 중복 제거
    seen_values = set()
    final_items = []
    
    for item in all_items:
        key = (item["type"], item["value"])
        if key not in seen_values:
            final_items.append(item)
            seen_values.add(key)
    
    return final_items

# ===== 기존 정규화 함수들 =====

def normalize_entities(raw_entities: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    """엔터티 정규화"""
    out = []
    for e in raw_entities:
        ent = {
            "name": norm_name(e.get("name")) if isinstance(e.get("name"), str) else None,
            "age": norm_age(str(e.get("age"))) if e.get("age") is not None else None,
            "phone": norm_phone(e.get("phone")) if isinstance(e.get("phone"), str) else None,
            "email": norm_email(e.get("email")) if isinstance(e.get("email"), str) else None,
            "address": norm_address(e.get("address")) if isinstance(e.get("address"), str) else None
        }
        ent = cross_check(ent)
        out.append(ent)
    return out

def norm_age(val: Optional[str]) -> Optional[str]:
    """나이 값을 숫자만 추출하여 정규화"""
    if not val:
        return None
    m = AGE_RX.search(val)
    return m.group(1) if m else None

def to_digits(s: str) -> str:
    """문자열에서 숫자만 추출"""
    return PHONE_NUM_ONLY.sub("", s)

def norm_phone(val: Optional[str]) -> Optional[str]:
    """전화번호를 표준 형식으로 정규화"""
    if not val:
        return None
    raw = val.strip()
    # +82 10 xxxx xxxx -> 010...
    if raw.startswith("+82"):
        digits = to_digits(raw)
        if digits.startswith("8210"):
            digits = "0" + digits[2:]  # 8210 -> 010
        elif digits.startswith("82"):
            digits = "0" + digits[2:]
    else:
        digits = to_digits(raw)

    # Common Korean mobile formats
    if digits.startswith("010") and len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if digits[:3] in {"011","016","017","018","019"}:
        # 3-3/4-4 heuristic
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        if len(digits) == 11:
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

    # Fallback: tidy hyphens only
    tidy = re.sub(r"\s+", " ", raw).replace("–","-").replace("—","-")
    return tidy

def norm_email(val: Optional[str]) -> Optional[str]:
    """이메일 주소를 소문자로 정규화"""
    if not val:
        return None
    val = val.strip()
    if "@" not in val:
        return None
    return val.lower()

def norm_name(val: Optional[str]) -> Optional[str]:
    """이름에서 공백 정리"""
    if not val:
        return None
    return re.sub(r"\s+", " ", val).strip()

def norm_address(val: Optional[str]) -> Optional[str]:
    """주소를 '시'까지만 남기도록 정규화"""
    if not val:
        return None
    s = re.sub(r"\s+", " ", val).strip()
    # 주소를 '시'까지만 남기는 로직
    tokens = s.split()
    if not tokens:
        return None
    # 시-계열 접미 찾기
    city_suffixes = ["시", "특별시", "광역시", "특별자치시"]
    for i, token in enumerate(tokens):
        for suffix in city_suffixes:
            if token.endswith(suffix):
                # 도로 시작하는 경우 도+시까지
                if i > 0 and (tokens[i-1].endswith("도") or tokens[i-1].endswith("특별자치도")):
                    return " ".join(tokens[:i+1])
                else:
                    # 시로 바로 시작하는 경우
                    return token
    # 시가 없으면 군/구 찾기
    for i, token in enumerate(tokens):
        if token.endswith("군") or token.endswith("구"):
            if i > 0:
                return " ".join(tokens[:i+1])
            else:
                return token
    # 그것도 없으면 첫 토큰만
    return tokens[0] if tokens else None

def cross_check(entity: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """엔티티 간 교차 검증 (주소에 이메일이 포함된 경우 등)"""
    addr = entity.get("address")
    email = entity.get("email")
    if addr and "@" in addr:
        m = EMAIL_RX.search(addr)
        if m and not email:
            entity["email"] = m.group(0).lower()
            entity["address"] = None
        elif not m:
            entity["address"] = None
    return entity

def detect_pii_enhanced(text: str):
    return asyncio.run(detect_pii_all(text))

def detect_with_ner(text: str):
    return asyncio.run(detect_pii_all(text))

def detect_with_regex(text: str):
    return asyncio.run(detect_pii_all(text))

def detect_names_from_csv(text: str):
    return detect_names(text)

def detect_addresses_from_csv(text: str):
    return detect_addresses(text)

def merge_detections(*detection_lists):
    merged = []
    for detection_list in detection_lists:
        if detection_list:
            merged.extend(detection_list)
    
    seen = set()
    unique = []
    for item in merged:
        key = (item["type"], item["value"])
        if key not in seen:
            unique.append(item)
            seen.add(key)
    
    return unique