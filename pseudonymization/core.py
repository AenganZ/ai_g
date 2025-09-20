# pseudonymization/core.py - AenganZ PII 탐지 로직
import os
import re
import random
from typing import List, Dict, Any, Optional

# ===== 정규식 패턴 (AenganZ 방식) =====
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'010[-\s]?\d{4}[-\s]?\d{4}')
AGE_PATTERN = re.compile(r'\b(\d{1,2})\s*(?:세|살)\b')

# 강화된 이름 패턴 (AenganZ 방식)
NAME_PATTERNS = [
    re.compile(r'이름은\s*([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})\s*입니다'),
    re.compile(r'저는\s*([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})(?:이에요|예요|이야|야)'),
    re.compile(r'([가-힣]{2,4})(?:입니다|이다)'),
    re.compile(r'안녕하세요,?\s*(?:저는\s*)?([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})이고'),
    re.compile(r'([가-힣]{2,4})이며'),
    re.compile(r'([가-힣]{2,4})라고\s*합니다'),
    re.compile(r'([가-힣]{2,4})라고\s*해요'),
    re.compile(r'([가-힣]{2,4})(?:님|씨)'),
]

# 주소 패턴 (AenganZ 방식)
ADDRESS_PATTERNS = [
    re.compile(r'[가-힣]+(?:시|도|구|군)\s+[가-힣\s\d,-]+(?:동|로|가|번지|층|호)'),
    re.compile(r'[가-힣]+(?:시|도|구|군)'),
]

# ===== 데이터풀 저장소 =====
name_pool = []
full_name_pool = []
fake_name_pool = []
email_pool = []
phone_pool = []
address_pool = []
company_pool = []

def load_data_pools():
    """모든 데이터풀 초기화 (AenganZ 방식)"""
    global name_pool, full_name_pool, fake_name_pool
    global email_pool, phone_pool, address_pool, company_pool
    
    print("📂 데이터풀 로딩 중...")
    
    # 이름풀 로드 (name.csv가 있으면 사용)
    try:
        if os.path.exists('name.csv'):
            import pandas as pd
            df = pd.read_csv('name.csv', encoding='utf-8')
            name_pool = df['이름'].tolist()[:1000]  # 최대 1000개
            print(f"✅ name.csv에서 {len(name_pool)}개 이름 로드")
        else:
            # 기본 이름풀
            name_pool = [
                '민준', '서준', '도윤', '예준', '시우', '주원', '하준', '지호',
                '지후', '준우', '현우', '준서', '도현', '지훈', '건우', '우진',
                '서윤', '지우', '서현', '하은', '예은', '윤서', '지민', '채원'
            ]
            print(f"✅ 기본 이름풀 사용: {len(name_pool)}개")
    except Exception as e:
        print(f"❌ 이름풀 로드 실패: {e}")
        name_pool = ['민준', '서준', '지우', '서현']
    
    # 한국 성씨
    surnames = [
        '김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
        '한', '오', '서', '신', '권', '황', '안', '송', '류', '전'
    ]
    
    # 성+이름 조합 생성 (AenganZ 방식)
    full_name_pool = []
    for surname in surnames:
        for name in name_pool[:50]:  # 메모리 절약
            full_name_pool.append(surname + name)
    
    # 가명 이름 풀 생성 (AenganZ 방식)
    fake_words = ['가명', '익명', '무명', '차명', '별명', '테스트', '샘플', '더미']
    fake_name_pool = [surname + fake_word for surname in surnames for fake_word in fake_words]
    
    # 이메일풀 생성
    email_domains = ['gmail.com', 'naver.com', 'daum.net', 'kakao.com']
    email_prefixes = ['user', 'test', 'hello', 'work', 'info', 'office']
    email_pool = []
    for i in range(100):
        prefix = random.choice(email_prefixes) + str(i + 1000)
        domain = random.choice(email_domains)
        email_pool.append(f"{prefix}@{domain}")
    
    # 전화번호풀 생성
    phone_pool = [f"010-{i//100:04d}-{i%100:04d}" for i in range(1000, 2000)]
    
    # 주소풀 생성
    address_pool = [
        '서울시 강남구', '서울시 서초구', '서울시 송파구', '서울시 강동구',
        '서울시 마포구', '서울시 용산구', '부산시 해운대구', '부산시 부산진구',
        '대구시 중구', '대구시 동구', '인천시 남동구', '인천시 부평구',
        '경기도 수원시', '경기도 성남시', '대전시 서구', '광주시 서구'
    ]
    
    # 도로명 풀 로드 (있는 경우)
    try:
        if os.path.exists('address_road.csv'):
            import pandas as pd
            df = pd.read_csv('address_road.csv', encoding='utf-8')
            road_names = df['도로명'].dropna().unique().tolist()[:100]  # 상위 100개
            
            # 기존 주소에 도로명 추가
            for base in address_pool[:5]:  # 상위 5개 지역만
                for road in road_names[:10]:  # 상위 10개 도로명
                    address_pool.append(f"{base} {road}")
            print(f"✅ address_road.csv에서 {len(road_names)}개 도로명 로드")
    except Exception as e:
        print(f"⚠️ 도로명 로드 실패: {e}")
    
    # 회사풀 생성
    company_pool = [
        '삼성전자', 'LG전자', 'SK하이닉스', '현대자동차', 'KIA', '포스코',
        '넷마블', '카카오', '네이버', '쿠팡', '배달의민족', '토스'
    ]
    
    print(f"✅ 데이터풀 로드 완료")
    print(f"   📛 이름: {len(name_pool)}개")
    print(f"   👤 성+이름: {len(full_name_pool)}개")
    print(f"   🎭 가명이름: {len(fake_name_pool)}개")
    print(f"   🏠 주소: {len(address_pool)}개")

def detect_pii_enhanced(text: str) -> List[Dict[str, Any]]:
    """강화된 PII 탐지 (AenganZ 방식)"""
    items = []
    
    print(f"🔍 PII 분석: {text[:50]}...")
    
    # 1. NER 모델 사용 (사용 가능한 경우)
    try:
        from .model import extract_entities_with_ner, is_ner_loaded
        
        if is_ner_loaded():
            ner_items = extract_entities_with_ner(text)
            items.extend(ner_items)
            print(f"🤖 NER 탐지: {len(ner_items)}개")
    except Exception as e:
        print(f"⚠️ NER 모델 사용 실패: {e}")
    
    # 2. 정규식 기반 탐지 (AenganZ 방식)
    # 이메일
    for match in EMAIL_PATTERN.finditer(text):
        items.append({
            "type": "이메일",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex"
        })
    
    # 전화번호
    for match in PHONE_PATTERN.finditer(text):
        items.append({
            "type": "전화번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex"
        })
    
    # 나이
    for match in AGE_PATTERN.finditer(text):
        items.append({
            "type": "나이",
            "value": match.group(1),
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.9,
            "source": "Regex"
        })
    
    # 이름 패턴
    for pattern in NAME_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            if len(name) >= 2 and len(name) <= 4:
                items.append({
                    "type": "이름",
                    "value": name,
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.75,
                    "source": "Pattern"
                })
    
    # 주소 패턴
    for pattern in ADDRESS_PATTERNS:
        for match in pattern.finditer(text):
            items.append({
                "type": "주소",
                "value": match.group(),
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.9,
                "source": "Regex"
            })
    
    # 3. 데이터풀 기반 탐지 (성+이름 조합)
    if full_name_pool:
        for full_name in full_name_pool[:500]:  # 성능을 위해 제한
            if full_name in text:
                start_idx = text.find(full_name)
                items.append({
                    "type": "이름",
                    "value": full_name,
                    "start": start_idx,
                    "end": start_idx + len(full_name),
                    "confidence": 0.8,
                    "source": "FullNamePool"
                })
    
    # 중복 제거 및 정렬
    unique_items = []
    seen = set()
    for item in sorted(items, key=lambda x: x['start']):
        key = (item['type'], item['value'], item['start'])
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    
    print(f"✅ 총 {len(unique_items)}개 PII 탐지됨")
    return unique_items

def assign_realistic_values(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """실제 데이터풀에서 대체값 할당 (AenganZ 방식)"""
    substitution_map = {}
    
    for item in items:
        pii_type = item['type']
        original_value = item['value']
        
        if original_value in substitution_map:
            continue
        
        if pii_type == "이름":
            replacement = random.choice(fake_name_pool) if fake_name_pool else "김가명"
        elif pii_type == "이메일":
            replacement = random.choice(email_pool) if email_pool else "test@example.com"
        elif pii_type == "전화번호":
            replacement = random.choice(phone_pool) if phone_pool else "010-0000-0000"
        elif pii_type == "주소":
            replacement = random.choice(address_pool) if address_pool else "서울시 강남구"
        elif pii_type == "회사":
            replacement = random.choice(company_pool) if company_pool else "테스트회사"
        elif pii_type == "나이":
            replacement = str(random.randint(20, 65))
        else:
            replacement = f"[{pii_type.upper()}_MASKED]"
        
        substitution_map[original_value] = replacement
        item['replacement'] = replacement
    
    return substitution_map

def create_masked_text(original_text: str, items: List[Dict[str, Any]]) -> str:
    """마스킹된 텍스트 생성 (AenganZ 방식)"""
    replacements = [(item['value'], item.get('replacement', 'MASKED')) 
                   for item in items if item['value']]
    
    # 긴 것부터 치환 (부분 매칭 방지)
    replacements.sort(key=lambda x: len(x[0]), reverse=True)
    
    masked_text = original_text
    for original, replacement in replacements:
        masked_text = masked_text.replace(original, replacement)
    
    return masked_text

def pseudonymize_text(original_prompt: str) -> Dict[str, Any]:
    """메인 가명화 함수 (AenganZ 방식)"""
    try:
        # PII 탐지
        items = detect_pii_enhanced(original_prompt)
        
        # 실제 데이터풀에서 대체값 할당
        substitution_map = assign_realistic_values(items)
        
        # 복구용 맵 생성 (가명 → 원본)
        reverse_map = {v: k for k, v in substitution_map.items()}
        
        # 마스킹된 텍스트 생성
        masked_prompt = create_masked_text(original_prompt, items)
        
        detection = {
            "contains_pii": len(items) > 0,
            "items": items,
            "model_used": "NER + Regex + NamePool + FullNamePool"
        }
        
        return {
            "masked_prompt": masked_prompt,
            "detection": detection,
            "substitution_map": substitution_map,
            "reverse_map": reverse_map
        }
    
    except Exception as e:
        print(f"❌ 가명화 처리 오류: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "masked_prompt": original_prompt,
            "detection": {"contains_pii": False, "items": []},
            "substitution_map": {},
            "reverse_map": {}
        }

def get_data_pool_stats() -> Dict[str, int]:
    """데이터풀 통계 반환"""
    return {
        "names": len(name_pool),
        "full_names": len(full_name_pool),
        "fake_names": len(fake_name_pool),
        "emails": len(email_pool),
        "phones": len(phone_pool),
        "addresses": len(address_pool),
        "companies": len(company_pool)
    }