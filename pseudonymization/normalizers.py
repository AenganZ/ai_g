# Normalizers module
import re
from typing import Optional, Dict

# 정규식 패턴들
EMAIL_RX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
AGE_RX = re.compile(r"\b(\d{1,3})\s*(?:세|살)?\b")
PHONE_NUM_ONLY = re.compile(r"\D+")

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
