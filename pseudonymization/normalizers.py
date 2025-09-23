# pseudonymization/normalizers.py - 탐지 + 정규화 통합 모듈 (조사 처리 강화)
import re
import asyncio
from typing import Optional, Dict, List, Any

# 정규식 패턴들
EMAIL_RX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
AGE_RX = re.compile(r"\b(\d{1,3})\s*(?:세|살)?\b")
PHONE_NUM_ONLY = re.compile(r"\D+")
PHONE_PATTERN = re.compile(r'010[-\s]?\d{4}[-\s]?\d{4}')

# ⭐ 개선된 이름 탐지 패턴 (조사 처리 강화)
NAME_PATTERNS = [
    re.compile(r'이름은\s*([가-힣]{2,4})(님|씨)?(?![가-힣])'),
    re.compile(r'저는\s*([가-힣]{2,4})(님|씨)?(?![가-힣])'),
    re.compile(r'([가-힣]{2,4})(님|씨)?\s*입니다'),
    re.compile(r'([가-힣]{2,4})(이에요|예요|이야|야)'),
    re.compile(r'([가-힣]{2,4})(님|씨)(?![가-힣])'),
    re.compile(r'안녕하세요,?\s*(?:저는\s*)?([가-힣]{2,4})(님|씨)?'),
    re.compile(r'([가-힣]{2,4})(님|씨)?\s*고'),
    re.compile(r'([가-힣]{2,4})(님|씨)?\s*라고\s*합니다'),
    re.compile(r'([가-힣]{2,4})(님|씨)?\s*고객'),
    re.compile(r'([가-힣]{2,4})(님|씨)?\s*회원'),
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

def smart_clean_korean_text(text: str, preserve_context: bool = True) -> str:
    """스마트 한국어 텍스트 정리 (컨텍스트 보존)"""
    if not text:
        return text
    
    cleaned = text.strip()
    
    # ⭐ preserve_context=True이면 조사를 유지
    if preserve_context:
        return cleaned
    
    # 조사 패턴 (끝에 오는 조사들)
    particles = ['이', '가', '을', '를', '은', '는', '의', '와', '과', '에', '에게', '에서', '로', '으로']
    # 존칭은 보존 (님, 씨는 제거하지 않음)
    
    # 끝에 있는 조사들만 제거 (존칭은 보존)
    for particle in sorted(particles, key=len, reverse=True):
        if cleaned.endswith(particle) and len(cleaned) > len(particle) + 1:  # 최소 2글자는 남겨야 함
            without_particle = cleaned[:-len(particle)]
            if len(without_particle) >= 2:
                cleaned = without_particle
                break
    
    return cleaned

def is_valid_korean_name(name: str, include_honorifics: bool = True) -> bool:
    """한국어 이름 유효성 검증 (존칭 포함 옵션)"""
    pools = get_pools()
    
    if not name or len(name) < 2 or len(name) > 5:  # 존칭 포함하면 최대 5글자
        return False
    
    # 존칭 분리
    base_name = name
    has_honorific = False
    
    if include_honorifics:
        if name.endswith('님') or name.endswith('씨'):
            base_name = name[:-1]
            has_honorific = True
    
    if len(base_name) < 2 or len(base_name) > 4:
        return False
    
    # 한글만 허용
    if not all('\uac00' <= char <= '\ud7af' for char in base_name):
        return False
    
    # 숫자 포함 제외
    if any(char.isdigit() for char in base_name):
        return False
    
    # 제외 단어들
    if base_name in pools.name_exclude_words:
        return False
    
    # 확장된 일반명사 목록
    common_nouns = {
        "고객", "손님", "회원", "선생", "교수", "의사", "직원", "학생",
        "친구", "선배", "후배", "동료", "가족", "부모", "자녀", "형제",
        "자매", "사람", "분들", "여러분", "모든", "모두", "전부", "일부",
        "담당자", "책임자", "관리자", "운영자", "개발자", "설계자", "기획자",
        "상담원", "안내원", "접수원", "대리", "과장", "부장", "팀장", "실장",
        "차장", "이사", "상무", "전무", "사장", "대표", "회장", "의장",
        "이번", "다음", "저번", "처음", "마지막", "첫째", "둘째", "셋째",
        "오늘", "어제", "내일", "지금", "나중", "앞서", "이후", "이전",
        "그분", "이분", "저분", "누군가", "아무나", "모든", "각자", "서로",
        "혼자", "함께", "같이", "따로", "별도", "개별", "공동", "전체"
    }
    
    if base_name in common_nouns:
        return False
    
    # 지역명 제외
    all_regions = set(pools.provinces + pools.cities + pools.roads)
    if base_name in all_regions:
        return False
    
    # 한국어 성씨 확인 (선택적 강화)
    common_surnames = {
        "김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", 
        "서", "신", "권", "황", "안", "송", "전", "홍", "고", "문", "양", "손"
    }
    
    # 2글자 이름인데 성씨로 시작하지 않으면 의심스러움
    if len(base_name) == 2 and base_name[0] not in common_surnames:
        if base_name not in pools.real_names:
            return False
    
    return True

# ===== PII 탐지 함수들 (강화됨) =====

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
    """전화번호 탐지 (정확도 개선)"""
    items = []
    seen_phones = set()
    
    for match in PHONE_PATTERN.finditer(text):
        phone = match.group()
        normalized_phone = phone.replace(' ', '').replace('-', '')
        
        if len(normalized_phone) == 11 and normalized_phone.startswith('010'):
            formatted_phone = f"{normalized_phone[:3]}-{normalized_phone[3:7]}-{normalized_phone[7:]}"
            
            if formatted_phone not in seen_phones:
                seen_phones.add(formatted_phone)
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
    seen_ages = set()
    
    for match in AGE_RX.finditer(text):
        age_str = match.group(1)
        
        if age_str in seen_ages:
            continue
        
        try:
            age = int(age_str)
            if 1 <= age <= 120 and len(age_str) <= 2:
                start_pos = max(0, match.start() - 10)
                end_pos = min(len(text), match.end() + 10)
                context = text[start_pos:end_pos]
                
                age_keywords = ['세', '살', '나이', '연령', '만', '년생', '올해']
                if any(keyword in context for keyword in age_keywords):
                    seen_ages.add(age_str)
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
    """이름 탐지 (존칭 포함 강화)"""
    items = []
    detected_names = set()
    
    print(f"🔍 강화된 이름 탐지 시작: '{text}'")
    
    # 1. 패턴 기반 탐지 (존칭 포함)
    for i, pattern in enumerate(NAME_PATTERNS):
        for match in pattern.finditer(text):
            # 그룹 1: 이름, 그룹 2: 존칭 (옵션)
            base_name = match.group(1)
            honorific = match.group(2) if match.lastindex > 1 and match.group(2) else ""
            full_name = base_name + (honorific or "")
            
            print(f"  패턴 {i+1}: '{base_name}' + '{honorific}' = '{full_name}'")
            
            # ⭐ 기본 이름으로 유효성 검사
            if not is_valid_korean_name(base_name, include_honorifics=False):
                print(f"    ❌ 유효하지 않은 기본 이름: '{base_name}'")
                continue
            
            # ⭐ 존칭이 있는 경우 전체 이름도 검사
            if honorific and not is_valid_korean_name(full_name, include_honorifics=True):
                print(f"    ❌ 유효하지 않은 전체 이름: '{full_name}'")
                continue
            
            # 중복 제거 (기본 이름 기준)
            if base_name in detected_names:
                print(f"    🔄 중복 제거: '{base_name}'")
                continue
            
            # ⭐ 존칭이 있는 경우 전체 이름을 저장, 없으면 기본 이름만
            final_name = full_name if honorific else base_name
            
            items.append({
                "type": "이름",
                "value": final_name,
                "start": match.start(1),
                "end": match.end(),
                "confidence": 0.85,
                "source": "normalizers-이름패턴",
                "has_honorific": bool(honorific),
                "base_name": base_name,
                "honorific": honorific
            })
            detected_names.add(base_name)  # 기본 이름으로 중복 체크
            print(f"    ✅ 이름 탐지: '{final_name}' (기본: '{base_name}', 존칭: '{honorific}')")
    
    # 2. 실명 목록 기반 탐지 (존칭 포함)
    pools = get_pools()
    for real_name in pools.real_names:
        if real_name in detected_names:
            continue
        
        # 기본 이름 매칭
        for match in re.finditer(re.escape(real_name), text):
            # 앞뒤 문맥 확인하여 존칭 포함 여부 판단
            start_pos = match.start()
            end_pos = match.end()
            
            # 뒤에 존칭이 있는지 확인
            if end_pos < len(text) and text[end_pos:end_pos+1] in ['님', '씨']:
                full_name = real_name + text[end_pos]
                end_pos += 1
                has_honorific = True
            else:
                full_name = real_name
                has_honorific = False
            
            items.append({
                "type": "이름",
                "value": full_name,
                "start": start_pos,
                "end": end_pos,
                "confidence": 0.90,
                "source": "normalizers-실명목록",
                "has_honorific": has_honorific,
                "base_name": real_name,
                "honorific": text[end_pos-1] if has_honorific else ""
            })
            detected_names.add(real_name)
            print(f"  ✅ 실명 목록: '{full_name}' (기본: '{real_name}')")
    
    print(f"🔍 강화된 이름 탐지 완료: {len(items)}개")
    return items

def detect_addresses(text: str) -> List[Dict[str, Any]]:
    """주소 탐지 (조사 처리 강화)"""
    items = []
    pools = get_pools()
    all_addresses = []
    
    print(f"🏠 주소 탐지 시작: '{text}'")
    
    # 1. 복합 주소 패턴 (조사 포함 버전)
    for province in pools.provinces:
        complex_patterns = [
            rf'{re.escape(province)}(?:시|도)?\s+[가-힣]+(?:구|군|시)(?:에서|에|로|으로)?',
            rf'{re.escape(province)}\s+[가-힣]+(?:구|군)(?:에서|에|로|으로)?',
        ]
        
        for pattern in complex_patterns:
            for match in re.finditer(pattern, text):
                full_match = match.group()
                
                # ⭐ 조사는 분리하되 컨텍스트는 보존
                clean_match = re.sub(r'(에서|에|로|으로)$', '', full_match).strip()
                
                print(f"  복합 패턴: '{full_match}' → 정리: '{clean_match}'")
                
                all_addresses.append({
                    "province": province,
                    "value": clean_match,
                    "original_match": full_match,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "priority": 1,
                    "has_particle": full_match != clean_match
                })
    
    # 2. 단일 주소 패턴
    if not all_addresses:
        for province in pools.provinces:
            pattern = rf'{re.escape(province)}(?:시|도)?(?:에서|에|로|으로)?'
            for match in re.finditer(pattern, text):
                full_match = match.group()
                clean_match = re.sub(r'(에서|에|로|으로)$', '', full_match).strip()
                
                print(f"  단일 패턴: '{full_match}' → 정리: '{clean_match}'")
                
                start_pos = max(0, match.start() - 15)
                end_pos = min(len(text), match.end() + 15)
                context = text[start_pos:end_pos]
                
                address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '예약', '지역']
                if any(keyword in context for keyword in address_keywords):
                    all_addresses.append({
                        "province": province,
                        "value": clean_match,
                        "original_match": full_match,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.80,
                        "priority": 2,
                        "has_particle": full_match != clean_match
                    })
    
    # 3. ⭐ 각 주소를 개별적으로 반환 (1:1 매핑을 위해)
    all_addresses.sort(key=lambda x: (x["priority"], x["start"]))
    for addr in all_addresses:
        items.append({
            "type": "주소",
            "value": addr["value"],  # 정리된 주소
            "start": addr["start"],
            "end": addr["end"],
            "confidence": addr["confidence"],
            "source": "normalizers-주소",
            "original_match": addr["original_match"],
            "has_particle": addr["has_particle"]
        })
        print(f"  ✅ 주소: '{addr['value']}' (원본: '{addr['original_match']}')")
    
    print(f"🏠 주소 탐지 완료: {len(items)}개")
    return items

def detect_with_ner_supplement(text: str, existing_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """NER 모델 보완 탐지 (존칭 처리 강화)"""
    if not NER_AVAILABLE:
        return []
    
    try:
        existing_values = set()
        for item in existing_items:
            # 기본 이름과 존칭 포함 이름 모두 기록
            base_value = item.get("base_name", item["value"])
            existing_values.add(base_value)
            existing_values.add(item["value"])
        
        ner_entities = extract_entities_with_ner(text)
        
        supplementary_items = []
        for entity in ner_entities:
            entity_type = entity.get('type', '')
            raw_value = entity.get('value', '')
            confidence = entity.get('confidence', 0.0)
            
            # ⭐ 스마트 정리 (컨텍스트 보존)
            clean_value = smart_clean_korean_text(raw_value, preserve_context=True)
            
            if clean_value in existing_values or not clean_value:
                continue
            
            if confidence > 0.9:
                if entity_type == "이름":
                    if not is_valid_korean_name(clean_value, include_honorifics=True):
                        continue
                    if not all('\uac00' <= char <= '\ud7af' or char in '씨님' for char in clean_value):
                        continue
                
                # 존칭 분리
                base_name = clean_value
                honorific = ""
                if clean_value.endswith('님') or clean_value.endswith('씨'):
                    base_name = clean_value[:-1]
                    honorific = clean_value[-1]
                
                supplementary_items.append({
                    "type": entity_type,
                    "value": clean_value,
                    "start": entity.get('start', 0),
                    "end": entity.get('start', 0) + len(clean_value),
                    "confidence": confidence,
                    "source": f"NER-보완",
                    "has_honorific": bool(honorific),
                    "base_name": base_name,
                    "honorific": honorific
                })
        
        return supplementary_items
        
    except Exception as e:
        print(f"NER 보완 탐지 오류: {e}")
        return []

async def detect_pii_all(text: str) -> List[Dict[str, Any]]:
    """통합 PII 탐지 함수 (강화된 조사 처리)"""
    print(f"\n🔍 === 강화된 PII 탐지 시작 ===")
    print(f"📝 입력: '{text}'")
    
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
    
    # 3단계: ⭐ 중복 제거 (기본 이름 기준)
    seen_items = set()
    final_items = []
    
    for item in all_items:
        # 이름의 경우 기본 이름으로 중복 체크
        if item["type"] == "이름":
            base_name = item.get("base_name", item["value"])
            key = (item["type"], base_name)
        else:
            key = (item["type"], item["value"])
        
        if key not in seen_items:
            final_items.append(item)
            seen_items.add(key)
            print(f"✅ 최종 항목: {item['type']} '{item['value']}'")
        else:
            print(f"🔄 중복 제거: {item['type']} '{item['value']}'")
    
    print(f"🔍 === 강화된 PII 탐지 완료: {len(final_items)}개 ===\n")
    return final_items

# ===== 기존 정규화 함수들 (유지) =====

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
    if raw.startswith("+82"):
        digits = to_digits(raw)
        if digits.startswith("8210"):
            digits = "0" + digits[2:]
        elif digits.startswith("82"):
            digits = "0" + digits[2:]
    else:
        digits = to_digits(raw)

    if digits.startswith("010") and len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if digits[:3] in {"011","016","017","018","019"}:
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        if len(digits) == 11:
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"

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
    """이름에서 공백 정리 (존칭 보존)"""
    if not val:
        return None
    return smart_clean_korean_text(re.sub(r"\s+", " ", val).strip(), preserve_context=True)

def norm_address(val: Optional[str]) -> Optional[str]:
    """주소를 정리하여 정규화 (조사만 제거)"""
    if not val:
        return None
    cleaned = re.sub(r"\s+", " ", val).strip()
    # 끝의 조사만 제거
    cleaned = re.sub(r'(에서|에|로|으로)$', '', cleaned).strip()
    return cleaned

def cross_check(entity: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """엔티티 간 교차 검증"""
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

# 호환성 함수들
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
        # 이름의 경우 기본 이름으로 중복 체크
        if item.get("type") == "이름":
            base_name = item.get("base_name", item["value"])
            key = (item["type"], base_name)
        else:
            key = (item["type"], item["value"])
        
        if key not in seen:
            unique.append(item)
            seen.add(key)
    
    return unique