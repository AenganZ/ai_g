# pseudonymization/replacement.py
"""
가명화 치환 모듈
탐지된 PII를 실제 데이터로 치환
"""

import random
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from .pools import get_pools

class ReplacementManager:
    """가명화 치환 관리자"""
    
    def __init__(self):
        self.pools = get_pools()
        self.used_names = set()
        self.used_emails = set()
        self.used_phones = set()
        self.used_companies = set()
    
    def assign_replacements(self, items: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """탐지된 PII에 대체값 할당"""
        substitution_map = {}  # 원본 → 가명
        reverse_map = {}       # 가명 → 원본
        
        # 타입별로 그룹화
        items_by_type = defaultdict(list)
        for item in items:
            items_by_type[item['type']].append(item['value'])
        
        # 주소 처리 (먼저 처리해서 간소화)
        if '주소' in items_by_type:
            self._handle_addresses(items_by_type['주소'], substitution_map, reverse_map)
        
        # 이름 처리
        if '이름' in items_by_type:
            self._handle_names(items_by_type['이름'], substitution_map, reverse_map)
        
        # 전화번호 처리
        if '전화번호' in items_by_type:
            self._handle_phones(items_by_type['전화번호'], substitution_map, reverse_map)
        
        # 이메일 처리
        if '이메일' in items_by_type:
            self._handle_emails(items_by_type['이메일'], substitution_map, reverse_map)
        
        # 회사 처리
        if '회사' in items_by_type:
            self._handle_companies(items_by_type['회사'], substitution_map, reverse_map)
        
        # 나이 처리
        if '나이' in items_by_type:
            self._handle_ages(items_by_type['나이'], substitution_map, reverse_map)
        
        # 주민등록번호 처리
        if '주민등록번호' in items_by_type:
            self._handle_rrn(items_by_type['주민등록번호'], substitution_map, reverse_map)
        
        # 신용카드 처리
        if '신용카드' in items_by_type:
            self._handle_cards(items_by_type['신용카드'], substitution_map, reverse_map)
        
        return substitution_map, reverse_map
    
    def _handle_addresses(self, addresses: List[str], sub_map: Dict, rev_map: Dict):
        """주소 간소화 처리"""
        unique_addresses = list(set(addresses))
        
        print(f"🏠 주소 간소화: {len(unique_addresses)}개 → 1개 지역명")
        
        # 하나의 간단한 지역으로 통합
        fake_location = self.pools.get_random_address()
        print(f"   선택된 지역: {fake_location}")
        
        for addr in unique_addresses:
            sub_map[addr] = fake_location
            if fake_location not in rev_map:
                rev_map[fake_location] = addr
            print(f"   주소 간소화: '{addr}' → '{fake_location}'")
    
    def _handle_names(self, names: List[str], sub_map: Dict, rev_map: Dict):
        """이름 처리"""
        for original_name in set(names):
            # 이미 처리된 경우 스킵
            if original_name in sub_map:
                continue
            
            # 중복 방지를 위한 가명 선택
            fake_name = self._get_unique_fake_name()
            
            sub_map[original_name] = fake_name
            rev_map[fake_name] = original_name
            print(f"   할당: {original_name} → {fake_name}")
    
    def _get_unique_fake_name(self) -> str:
        """중복되지 않는 가명 이름 선택"""
        attempts = 0
        while attempts < 100:
            fake_name = self.pools.get_random_fake_name()
            if fake_name not in self.used_names:
                self.used_names.add(fake_name)
                return fake_name
            attempts += 1
        
        # 시도 실패 시 번호 붙이기
        base_name = self.pools.get_random_fake_name()
        counter = 1
        while f"{base_name}{counter}" in self.used_names:
            counter += 1
        final_name = f"{base_name}{counter}"
        self.used_names.add(final_name)
        return final_name
    
    def _handle_phones(self, phones: List[str], sub_map: Dict, rev_map: Dict):
        """전화번호 처리"""
        for phone in set(phones):
            if phone in sub_map:
                continue
            
            # 중복되지 않는 전화번호 생성
            fake_phone = self._get_unique_phone()
            
            sub_map[phone] = fake_phone
            rev_map[fake_phone] = phone
            print(f"   할당: {phone} → {fake_phone}")
    
    def _get_unique_phone(self) -> str:
        """중복되지 않는 전화번호 생성"""
        attempts = 0
        while attempts < 100:
            fake_phone = self.pools.get_random_phone()
            if fake_phone not in self.used_phones:
                self.used_phones.add(fake_phone)
                return fake_phone
            attempts += 1
        
        # 완전 랜덤 생성
        while True:
            fake_phone = f"010-{random.randint(0, 9999):04d}-{random.randint(0, 9999):04d}"
            if fake_phone not in self.used_phones:
                self.used_phones.add(fake_phone)
                return fake_phone
    
    def _handle_emails(self, emails: List[str], sub_map: Dict, rev_map: Dict):
        """이메일 처리"""
        for email in set(emails):
            if email in sub_map:
                continue
            
            fake_email = self._get_unique_email()
            
            sub_map[email] = fake_email
            rev_map[fake_email] = email
    
    def _get_unique_email(self) -> str:
        """중복되지 않는 이메일 생성"""
        attempts = 0
        while attempts < 100:
            fake_email = self.pools.get_random_email()
            if fake_email not in self.used_emails:
                self.used_emails.add(fake_email)
                return fake_email
            attempts += 1
        
        # 완전 랜덤 생성
        counter = random.randint(10000, 99999)
        fake_email = f"user{counter}@example.com"
        self.used_emails.add(fake_email)
        return fake_email
    
    def _handle_companies(self, companies: List[str], sub_map: Dict, rev_map: Dict):
        """회사명 처리"""
        for company in set(companies):
            if company in sub_map:
                continue
            
            # 다른 회사로 치환
            available = [c for c in self.pools.companies 
                        if c != company and c not in self.used_companies]
            
            if available:
                fake_company = random.choice(available)
                self.used_companies.add(fake_company)
            else:
                fake_company = f"테스트회사{random.randint(1, 99)}"
            
            sub_map[company] = fake_company
            rev_map[fake_company] = company
    
    def _handle_ages(self, ages: List[str], sub_map: Dict, rev_map: Dict):
        """나이 처리"""
        for age in set(ages):
            if age in sub_map:
                continue
            
            try:
                original_age = int(age)
                # ±10년 범위로 변경
                fake_age = str(max(1, original_age + random.randint(-10, 10)))
            except:
                fake_age = str(random.randint(20, 65))
            
            sub_map[age] = fake_age
            rev_map[fake_age] = age
    
    def _handle_rrn(self, rrns: List[str], sub_map: Dict, rev_map: Dict):
        """주민등록번호 마스킹"""
        for rrn in set(rrns):
            if rrn in sub_map:
                continue
            
            # 앞 6자리만 남기고 마스킹
            if len(rrn) >= 6:
                masked = rrn[:6] + "-*******"
            else:
                masked = "******-*******"
            
            sub_map[rrn] = masked
            rev_map[masked] = rrn
    
    def _handle_cards(self, cards: List[str], sub_map: Dict, rev_map: Dict):
        """신용카드 마스킹"""
        for card in set(cards):
            if card in sub_map:
                continue
            
            # 앞 4자리와 뒤 4자리만 보이게
            clean_card = card.replace("-", "").replace(" ", "")
            if len(clean_card) >= 16:
                masked = f"{clean_card[:4]}-****-****-{clean_card[-4:]}"
            else:
                masked = "****-****-****-****"
            
            sub_map[card] = masked
            rev_map[masked] = card

def apply_replacements(text: str, substitution_map: Dict[str, str]) -> str:
    """텍스트에 치환 적용"""
    masked = text
    
    # 길이가 긴 것부터 치환 (짧은 것이 긴 것의 일부인 경우 방지)
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, replacement in sorted_items:
        if original in masked:
            masked = masked.replace(original, replacement)
            print(f"🔧 치환: '{original}' → '{replacement}'")
    
    # 후처리: 연속된 같은 단어 제거
    masked = remove_duplicates(masked)
    
    return masked

def remove_duplicates(text: str) -> str:
    """연속된 중복 단어 제거"""
    words = text.split()
    cleaned_words = []
    prev_word = None
    
    for word in words:
        if word != prev_word:
            cleaned_words.append(word)
        else:
            print(f"   🔧 중복 제거: '{word}' 연속 발생 → 1개로 통합")
        prev_word = word
    
    return ' '.join(cleaned_words)

def restore_text(masked_text: str, reverse_map: Dict[str, str]) -> str:
    """가명화된 텍스트 복원"""
    restored = masked_text
    
    # 길이가 긴 것부터 복원
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake, original in sorted_items:
        if fake in restored:
            restored = restored.replace(fake, original)
    
    return restored

# ==================== 테스트 ====================
if __name__ == "__main__":
    print("🔄 가명화 치환 모듈 테스트")
    
    # 테스트 데이터
    test_items = [
        {"type": "이름", "value": "김철수"},
        {"type": "이름", "value": "고객"},  # 제외되어야 함
        {"type": "주소", "value": "부산"},
        {"type": "주소", "value": "해운대구"},
        {"type": "전화번호", "value": "010-1234-5678"},
        {"type": "이메일", "value": "test@example.com"},
        {"type": "회사", "value": "삼성전자"}
    ]
    
    # 치환 관리자
    manager = ReplacementManager()
    
    # 치환값 할당
    sub_map, rev_map = manager.assign_replacements(test_items)
    
    print("\n📝 치환 맵:")
    for original, fake in sub_map.items():
        print(f"   {original} → {fake}")
    
    # 텍스트 적용 테스트
    test_text = "김철수 고객님, 부산 해운대구의 삼성전자에서 일하시는 분이시군요. 010-1234-5678로 연락드리겠습니다."
    
    masked_text = apply_replacements(test_text, sub_map)
    print(f"\n원본: {test_text}")
    print(f"가명: {masked_text}")
    
    # 복원 테스트
    restored = restore_text(masked_text, rev_map)
    print(f"복원: {restored}")