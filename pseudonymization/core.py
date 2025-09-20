# pseudonymization/core.py - 수정된 주소 패턴 (문법 오류 수정)
import os
import re
import random
from typing import List, Dict, Any, Optional

# ===== 개선된 정규식 패턴 =====
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'010[-\s]?\d{4}[-\s]?\d{4}')
AGE_PATTERN = re.compile(r'\b(\d{1,2})\s*(?:세|살)\b')

# 🔧 **안전한 이름 패턴** - 위험한 패턴 제거, 확실한 것만 사용
NAME_PATTERNS = [
    # 안전하고 확실한 패턴들만 사용
    re.compile(r'이름은\s*([가-힣]{2,4})'),
    re.compile(r'저는\s*([가-힣]{2,4})'),
    re.compile(r'안녕하세요,?\s*(?:저는\s*)?([가-힣]{2,4})'),
    re.compile(r'([가-힣]{2,4})\s*입니다'),
    re.compile(r'([가-힣]{2,4})라고\s*합니다'),
    re.compile(r'([가-힣]{2,4})라고\s*해요'),
    re.compile(r'([가-힣]{2,4})(?:님|씨)'),
    
    # 🚫 위험한 패턴들 제거: "이고", "이며" 등은 오탐 가능성 높음
    # 대신 정규식보다는 NER 모델에 의존하거나 더 명확한 패턴만 사용
]

# 🔧 **수정된 주소 패턴** - 정확한 주소만 탐지
ADDRESS_PATTERNS = [
    # 1. 완전한 주소 형태: "서울시 강남구", "부산 해운대구"
    re.compile(r'([가-힣]+(?:특별시|광역시|특별자치시|특별자치도|시|도))\s+([가-힣]+(?:구|군))'),
    
    # 2. 구/군 + 동/로: "강남구 테헤란로", "중구 명동"  
    re.compile(r'([가-힣]+(?:구|군))\s+([가-힣]+(?:동|로|가))'),
    
    # 3. 시/도만 (명확한 지역명): "서울", "부산", "대구", "대전", "광주", "울산", "인천"
    re.compile(r'\b(서울|부산|대구|대전|광주|울산|인천|세종|제주)(?=\s|$|에|에서|의|으로|로)'),
    
    # 4. 구/군만 (명확한 지역명): "강남구", "해운대구", "중구" 
    re.compile(r'\b([가-힣]{2,4}(?:구|군))(?=\s|$|에|에서|의|으로|로)'),
    
    # 5. 도로명 주소: "테헤란로", "명동길"
    re.compile(r'([가-힣]{2,10}(?:로|길|대로|로길))'),
]

# 🚫 **주소가 아닌 단어들 제외** (정확한 제외 리스트)
ADDRESS_EXCLUDE_WORDS = {
    # 동사/형용사
    '거주하시', '거주하는', '살고있는', '살고', '있는', '계시는', '위치한', '자리한',
    '분이시', '하시는', '되시는', '이시는', '으시는', '하신', '이신', '으신',
    
    # 지시어/수식어  
    '그분의', '이분의', '저분의', '우리의', '제가', '내가', '당신의',
    '어디에', '여기에', '저기에', '그곳에', '이곳에',
    
    # 일반 명사 (지역명과 유사한 것들)
    '중요', '중심', '중앙', '동쪽', '서쪽', '남쪽', '북쪽', '근처', '주변', '일대',
    '지역은', '동네는', '근처는', '쪽은', '방면은', '곳은', '데는',
    
    # 기타 오탐 가능 단어들
    '문구', '상구', '하구', '입구', '출구', '통로', '도로', '길로', '경로'
}

# ===== 데이터풀 저장소 =====
name_pool = []
full_name_pool = []
fake_name_pool = []
email_pool = []
phone_pool = []
address_pool = []
company_pool = []

def load_data_pools():
    """모든 데이터풀 초기화"""
    global name_pool, full_name_pool, fake_name_pool
    global email_pool, phone_pool, address_pool, company_pool
    
    print("📂 데이터풀 로딩 중...")
    
    # 이름풀 로드
    try:
        if os.path.exists('name.csv'):
            import pandas as pd
            df = pd.read_csv('name.csv', encoding='utf-8')
            name_pool = df['이름'].tolist()[:1000]
            print(f"✅ name.csv에서 {len(name_pool)}개 이름 로드")
        else:
            name_pool = ['민준', '서준', '지우', '서현']
    except Exception as e:
        print(f"❌ 이름풀 로드 실패: {e}")
        name_pool = ['민준', '서준', '지우', '서현']
    
    # 한국 성씨
    surnames = [
        '김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
        '한', '오', '서', '신', '권', '황', '안', '송', '류', '전'
    ]
    
    # 성+이름 조합 생성
    full_name_pool = []
    for surname in surnames:
        for name in name_pool[:50]:  # 메모리 절약
            full_name_pool.append(surname + name)
    
    # 가명 이름 풀 생성
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
            road_names = df['도로명'].dropna().unique().tolist()[:100]
            
            # 기존 주소에 도로명 추가
            for base in address_pool[:5]:
                for road in road_names[:10]:
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
    """강화된 PII 탐지 (개선된 주소 탐지)"""
    items = []
    
    print(f"🔍 PII 분석: {text[:50]}...")
    
    # 1. NER 모델 사용 (사용 가능한 경우)
    try:
        from .model import extract_entities_with_ner, is_ner_loaded
        
        if is_ner_loaded():
            print("🤖 NER 모델로 개체명 추출 중...")
            ner_items = extract_entities_with_ner(text)
            items.extend(ner_items)
            print(f"   NER 결과: {len(ner_items)}개 탐지")
    except Exception as e:
        print(f"⚠️ NER 모델 사용 실패: {e}")
    
    # 2. 정규식 기반 탐지
    print("🔎 정규식 패턴으로 추가 탐지 중...")
    
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
    print("👤 이름 패턴 분석 중...")
    for pattern in NAME_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            if len(name) >= 2 and len(name) <= 4:
                # 🔧 후처리: 조사 제거 ("홍길동이" → "홍길동")
                clean_name = re.sub(r'[이가을를에서]$', '', name)
                if len(clean_name) >= 2:  # 조사 제거 후에도 2글자 이상이어야 함
                    items.append({
                        "type": "이름",
                        "value": clean_name,  # 정리된 이름 사용
                        "start": match.start(1),
                        "end": match.start(1) + len(clean_name),  # 정리된 길이로 조정
                        "confidence": 0.75,
                        "source": "Pattern"
                    })
                    print(f"   ✅ 이름 탐지: '{name}' → '{clean_name}' (조사 제거)")
                else:
                    print(f"   ❌ 제외: '{name}' (조사 제거 후 너무 짧음)")
            else:
                print(f"   ❌ 제외: '{name}' (길이 부적절: {len(name)})")
    
    # 🔧 **개선된 주소 패턴 탐지**
    print("🏠 주소 패턴 분석 중...")
    for i, pattern in enumerate(ADDRESS_PATTERNS):
        for match in pattern.finditer(text):
            address_text = match.group().strip()
            
            # 제외 단어 필터링
            if address_text in ADDRESS_EXCLUDE_WORDS:
                print(f"   ❌ 제외됨: '{address_text}' (제외 목록에 포함)")
                continue
            
            # 길이 검증 (너무 짧거나 긴 것 제외)
            if len(address_text) < 2 or len(address_text) > 20:
                print(f"   ❌ 제외됨: '{address_text}' (길이 부적절: {len(address_text)})")
                continue
            
            # 숫자만 있는 것 제외
            if address_text.isdigit():
                print(f"   ❌ 제외됨: '{address_text}' (숫자만 포함)")
                continue
            
            # 한글이 포함되어 있는지 확인
            if not re.search(r'[가-힣]', address_text):
                print(f"   ❌ 제외됨: '{address_text}' (한글 미포함)")
                continue
            
            print(f"   ✅ 주소 탐지: '{address_text}' (패턴 {i+1})")
            items.append({
                "type": "주소",
                "value": address_text,
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.85,  # 정규식 주소는 높은 신뢰도
                "source": f"Regex-Pattern{i+1}"
            })
    
    # 3. 데이터풀 기반 탐지 (전체 이름 풀 확인)
    print("📋 데이터풀 기반 탐지 중...")
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
    
    # 4. 중복 제거 및 우선순위 정렬
    print("🧹 중복 제거 및 정렬 중...")
    unique_items = []
    seen = set()
    
    # NER 결과를 우선순위로 정렬 (NER > Regex > Pattern)
    priority_order = {'NER': 0, 'Regex': 1, 'Pattern': 2, 'FullNamePool': 3}
    items.sort(key=lambda x: (x['start'], priority_order.get(x['source'].split('-')[0], 4)))
    
    for item in items:
        # 위치 기반 중복 체크 (겹치는 범위 제거)
        overlap = False
        for existing in unique_items:
            if (item['start'] < existing['end'] and item['end'] > existing['start']):
                # 겹치는 경우 더 긴 것 또는 신뢰도 높은 것 선택
                if (item['end'] - item['start']) > (existing['end'] - existing['start']):
                    unique_items.remove(existing)
                    break
                else:
                    overlap = True
                    break
        
        if not overlap:
            unique_items.append(item)
    
    # 최종 결과 정렬 (위치 순)
    unique_items.sort(key=lambda x: x['start'])
    
    print(f"🎯 최종 탐지 결과: {len(unique_items)}개")
    for item in unique_items:
        print(f"   - {item['type']}: '{item['value']}' (신뢰도: {item['confidence']:.2f}, 출처: {item['source']})")
    
    return unique_items

def assign_realistic_values(items: List[Dict[str, Any]]) -> Dict[str, str]:
    """실제 데이터풀에서 대체값 할당 (주소 간소화)"""
    substitution_map = {}
    
    # 🔧 주소 아이템들을 먼저 그룹화
    address_items = [item for item in items if item['type'] == '주소']
    non_address_items = [item for item in items if item['type'] != '주소']
    
    # 🏠 **주소 간소화**: 여러 주소를 하나의 간단한 지역명으로 통합
    if address_items:
        print(f"🏠 주소 간소화: {len(address_items)}개 → 1개 지역명")
        
        # 간단한 지역명 풀 (시/도 단위)
        simple_regions = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
        chosen_region = random.choice(simple_regions)
        
        print(f"   선택된 지역: {chosen_region}")
        
        # 모든 주소를 같은 지역명으로 대체
        for item in address_items:
            substitution_map[item['value']] = chosen_region
            item['replacement'] = chosen_region
            print(f"   주소 간소화: '{item['value']}' → '{chosen_region}'")
    
    # 주소가 아닌 다른 아이템들 처리
    for item in non_address_items:
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
        elif pii_type == "회사":
            replacement = random.choice(company_pool) if company_pool else "테스트회사"
        elif pii_type == "나이":
            replacement = str(random.randint(20, 65))
        else:
            replacement = f"[{pii_type.upper()}_MASKED]"
        
        substitution_map[original_value] = replacement
        item['replacement'] = replacement
        
        print(f"   할당: {original_value} → {replacement}")
    
    return substitution_map

def create_masked_text(original_text: str, items: List[Dict[str, Any]]) -> str:
    """마스킹된 텍스트 생성 (개선된 중복 제거)"""
    replacements = [(item['value'], item.get('replacement', 'MASKED')) 
                   for item in items if item['value']]
    
    # 긴 것부터 치환 (부분 매칭 방지)
    replacements.sort(key=lambda x: len(x[0]), reverse=True)
    
    masked_text = original_text
    for original, replacement in replacements:
        masked_text = masked_text.replace(original, replacement)
    
    # 🔧 **개선된 중복 제거**: 연속된 같은 대체값들 제거
    print(f"🔧 치환 후: {masked_text}")
    
    # 모든 대체값들 수집
    replacement_values = set(item.get('replacement', '') for item in items if item.get('replacement'))
    
    # 각 대체값에 대해 중복 제거
    for replacement_value in replacement_values:
        if len(replacement_value) < 2:  # 너무 짧은 것 제외
            continue
            
        # 연속된 같은 대체값 패턴 찾기
        pattern = re.escape(replacement_value)
        
        # "인천 인천", "인천  인천", "인천, 인천" 등 처리
        duplicate_pattern = f'({pattern})(\\s*,?\\s*{pattern})+'
        
        def replace_duplicates(match):
            return match.group(1)  # 첫 번째 것만 남기기
        
        before = masked_text
        masked_text = re.sub(duplicate_pattern, replace_duplicates, masked_text)
        
        if before != masked_text:
            print(f"   🔧 중복 제거: '{replacement_value}' 연속 발생 → 1개로 통합")
    
    # 추가 정리: 연속된 공백, 쉼표 정리
    masked_text = re.sub(r'\s*,\s*,', ',', masked_text)  # 연속 쉼표 제거
    masked_text = re.sub(r'\s+', ' ', masked_text)       # 연속 공백 제거
    masked_text = masked_text.strip()
    
    print(f"🔧 최종 정리: {masked_text}")
    
    return masked_text

def pseudonymize_text(original_prompt: str) -> Dict[str, Any]:
    """메인 가명화 함수 (undefined 오류 해결)"""
    try:
        # PII 탐지
        items = detect_pii_enhanced(original_prompt)
        
        # 실제 데이터풀에서 대체값 할당 (주소 합치기 포함)
        substitution_map = assign_realistic_values(items)
        
        # 복구용 맵 생성 (가명 → 원본)
        reverse_map = {v: k for k, v in substitution_map.items()}
        
        # 마스킹된 텍스트 생성
        masked_prompt = create_masked_text(original_prompt, items)
        
        # 🔧 detection에 replacement 정보 포함 (undefined 해결)
        for item in items:
            if 'replacement' not in item:
                # 혹시 누락된 경우를 위한 fallback
                item['replacement'] = substitution_map.get(item['value'], 'MASKED')
        
        detection = {
            "contains_pii": len(items) > 0,
            "items": items,  # 이제 각 item에 replacement 정보 포함
            "model_used": "Enhanced NER + Improved Regex + NamePool + FullNamePool"
        }
        
        print(f"🎯 최종 결과:")
        print(f"   원본: {original_prompt}")
        print(f"   가명: {masked_prompt}")
        print(f"   탐지: {len(items)}개 항목")
        for i, item in enumerate(items, 1):
            print(f"   #{i} {item['type']}: '{item['value']}' → '{item.get('replacement', 'MASKED')}'")
        
        return {
            "masked_prompt": masked_prompt,
            "detection": detection,
            "substitution_map": substitution_map,
            "reverse_map": reverse_map,
            "performance": {
                "items_detected": len(items)
            }
        }
    
    except Exception as e:
        print(f"❌ 가명화 처리 오류: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "masked_prompt": original_prompt,
            "detection": {"contains_pii": False, "items": []},
            "substitution_map": {},
            "reverse_map": {},
            "performance": {"items_detected": 0}
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