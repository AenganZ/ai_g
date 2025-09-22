# simple_detection.py - 단순 정규식 기반 PII 탐지 모듈 (fallback)
"""
pseudonymization 모듈이 로드되지 않을 때 사용하는 fallback 모드
normalizers.py의 정규식 활용
"""

import re
from typing import List, Dict, Any

# normalizers.py에서 정규식 패턴 import 시도
try:
    from pseudonymization.normalizers import EMAIL_RX, norm_phone, norm_email
    NORMALIZERS_AVAILABLE = True
except ImportError:
    # normalizers를 못 불러오면 자체 정규식 사용
    EMAIL_RX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
    NORMALIZERS_AVAILABLE = False

def simple_pii_detection(text: str) -> List[Dict[str, Any]]:
    """단순 정규식 기반 PII 탐지"""
    
    items = []
    
    # 이메일 탐지 (normalizers.py 활용)
    found_emails = set()
    for match in EMAIL_RX.finditer(text):
        email = match.group()
        if NORMALIZERS_AVAILABLE:
            email = norm_email(email)
        else:
            email = email.lower()
        
        if email and email not in found_emails:
            found_emails.add(email)
            items.append({
                "type": "이메일",
                "value": email,
                "start": match.start(),
                "end": match.end(),
                "confidence": 0.9,
                "source": "정규식"
            })
    
    # 전화번호 탐지
    phone_patterns = [
        r'01[0-9]-\d{4}-\d{4}',  # 010-1234-5678
        r'01[0-9]\d{4}\d{4}',     # 01012345678
        r'\d{2,3}-\d{3,4}-\d{4}', # 02-123-4567
    ]
    
    found_phones = set()
    for pattern in phone_patterns:
        for match in re.finditer(pattern, text):
            phone = match.group()
            if NORMALIZERS_AVAILABLE:
                phone = norm_phone(phone)
            
            if phone and phone not in found_phones:
                found_phones.add(phone)
                items.append({
                    "type": "전화번호",
                    "value": phone,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.9,
                    "source": "정규식"
                })
    
    # 이름 패턴 탐지 (더 정확한 패턴)
    name_patterns = [
        r'([가-힣]{2,4})님',
        r'([가-힣]{2,4})씨',
        r'이름은\s*([가-힣]{2,4})(?:이고|이며|입니다|이에요|예요|이야|야)',
        r'저는\s*([가-힣]{2,4})(?:이고|이며|입니다|이에요|예요|이야|야)',
        r'제\s*이름은\s*([가-힣]{2,4})(?:이고|이며|입니다|이에요|예요|이야|야)',
        r'([가-힣]{2,4})(?=\s+고객)',  # "김철수 고객"에서 김철수 추출
    ]
    
    # 제외할 단어들
    exclude_words = {
        "고객", "거주하시", "분이시", "주세요", "드세요", "하세요", "보내드", "메일",
        "연락", "문의", "예약", "확인", "사항", "정보", "내용", "시간", "장소", "해운"
    }
    
    for pattern in name_patterns:
        for match in re.finditer(pattern, text):
            name = match.group(1)
            # 제외 단어 체크
            if name not in exclude_words and len(name) >= 2:
                items.append({
                    "type": "이름",
                    "value": name,
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.7,
                    "source": "정규식"
                })
    
    # 주소 패턴 (시/도 + 구/군 모두 탐지)
    address_patterns = [
        # 시/도
        r'(서울|부산|대구|인천|광주|대전|울산|세종)(?:시|특별시|광역시)?',
        r'(경기|강원|충북|충남|전북|전남|경북|경남|제주)(?:도)?',
        # 구/군 (주요 지역)
        r'(강남구|강동구|강북구|강서구|관악구|광진구|구로구|금천구|노원구|도봉구)',
        r'(동대문구|동작구|마포구|서대문구|서초구|성동구|성북구|송파구|양천구)',
        r'(영등포구|용산구|은평구|종로구|중구|중랑구)',
        r'(해운대구|부산진구|동래구|남구|북구|사하구|금정구|연제구|수영구|사상구)',
        r'(수성구|달서구|달성군|중구|동구|서구|남구|북구)',
    ]
    
    for pattern in address_patterns:
        for match in re.finditer(pattern, text):
            addr = match.group(1)
            # 주소 관련 문맥 확인
            start_pos = max(0, match.start() - 20)
            end_pos = min(len(text), match.end() + 20)
            context = text[start_pos:end_pos]
            
            # 주소 관련 키워드가 있는지 확인
            address_keywords = ['거주', '살고', '있습니다', '위치', '주소', '소재', '예약', '지역', '에서']
            if any(keyword in context for keyword in address_keywords):
                items.append({
                    "type": "주소",
                    "value": addr,
                    "start": match.start(1),
                    "end": match.end(1),
                    "confidence": 0.8,
                    "source": "정규식"
                })
    
    return items

def simple_pseudonymize_smart(items: List[Dict], text: str) -> tuple:
    """단순 가명화 처리 (스마트 주소 치환 포함)"""
    
    substitution_map = {}
    reverse_map = {}
    masked_text = text
    
    # 가명 풀
    fake_names = ["김가명", "이가명", "박무명", "최차명", "정익명"]
    fake_emails = ["user001@example.com", "user002@test.co.kr", "user003@demo.net"]
    fake_phones = ["010-0000-0000", "010-0001-0000", "010-0002-0000"]
    
    counters = {"이름": 0, "이메일": 0, "전화번호": 0, "주소": 0}
    
    # 주소 스마트 처리
    address_items = [item for item in items if item["type"] == "주소"]
    non_address_items = [item for item in items if item["type"] != "주소"]
    
    # 주소 치환 (연속 주소를 큰 단위만 남기고 처리)
    if address_items:
        # 위치순으로 정렬
        sorted_addresses = sorted(address_items, key=lambda x: x['start'])
        
        # 가장 큰 단위 주소 찾기 (시/도 우선)
        main_address = None
        provinces = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", 
                    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
        
        for addr_item in sorted_addresses:
            addr_value = addr_item['value']
            if addr_value in provinces:
                main_address = addr_value
                break
        
        # 시/도가 없으면 첫 번째 주소 사용
        if not main_address and sorted_addresses:
            main_address = sorted_addresses[0]['value']
        
        if main_address:
            print(f"대표 주소 선택: '{main_address}'")
            
            # 중복 제거 (같은 값은 한 번만 처리)
            processed_addresses = set()
            
            # 연속된 주소 구문 찾기 및 치환
            address_values = []
            for item in sorted_addresses:
                if item['value'] not in processed_addresses:
                    address_values.append(item['value'])
                    processed_addresses.add(item['value'])
            
            # 연속 주소 패턴 처리
            if len(address_values) > 1:
                # 정확한 연속 패턴 찾기: "서울 강남구"
                pattern = r'\s+'.join([re.escape(addr) for addr in address_values])
                
                if re.search(pattern, masked_text):
                    # 전체 연속 구문을 대표 주소로 치환
                    masked_text = re.sub(pattern, main_address, masked_text)
                    print(f"주소 연속 구문 치환: '{' '.join(address_values)}' → '{main_address}'")
                else:
                    # 개별 주소들 처리 (메인이 아닌 것들만 제거)
                    for addr_value in address_values:
                        if addr_value != main_address:
                            # 단어 경계를 고려한 정확한 치환
                            pattern = r'\b' + re.escape(addr_value) + r'\b'
                            if re.search(pattern, masked_text):
                                masked_text = re.sub(pattern, '', masked_text)
                                print(f"부차 주소 제거: '{addr_value}'")
                    
                    # 연속 공백 정리
                    masked_text = re.sub(r'\s+', ' ', masked_text).strip()
            
            substitution_map[f"주소_대표"] = main_address
            reverse_map[main_address] = "원본주소"
    
    # 다른 항목들 처리
    for item in non_address_items:
        original = item["value"]
        pii_type = item["type"]
        
        if original in substitution_map:
            continue
        
        # 가명 선택
        if pii_type == "이름":
            replacement = fake_names[counters["이름"] % len(fake_names)]
            counters["이름"] += 1
        elif pii_type == "이메일":
            replacement = fake_emails[counters["이메일"] % len(fake_emails)]
            counters["이메일"] += 1
        elif pii_type == "전화번호":
            replacement = fake_phones[counters["전화번호"] % len(fake_phones)]
            counters["전화번호"] += 1
        else:
            replacement = f"[{pii_type}]"
        
        substitution_map[original] = replacement
        reverse_map[replacement] = original
        
        # 텍스트 치환
        masked_text = masked_text.replace(original, replacement)
    
    return masked_text, substitution_map, reverse_map