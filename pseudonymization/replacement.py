# pseudonymization/replacement.py
"""
가명화 치환 모듈 - 깔끔한 버전
김가명1, 010-0000-0001, Pseudonymization1@gamyeong.com 형식
"""

import random
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from .pools import get_pools

class ReplacementManager:
    """명확한 가명화 치환 관리자"""
    
    def __init__(self):
        self.pools = get_pools()
        
        # 일관성 유지를 위한 매핑 히스토리
        self.name_mappings: Dict[str, str] = {}
        self.email_mappings: Dict[str, str] = {}
        self.phone_mappings: Dict[str, str] = {}
        self.address_mappings: Dict[str, str] = {}
        self.company_mappings: Dict[str, str] = {}
        self.age_mappings: Dict[str, str] = {}
        self.rrn_mappings: Dict[str, str] = {}
        self.card_mappings: Dict[str, str] = {}
        
        # 사용된 값들 추적
        self.used_fake_names: set = set()
        self.used_fake_phones: set = set()
        self.used_fake_emails: set = set()
    
    def assign_replacements(self, items: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """탐지된 PII에 명확한 가명 할당"""
        substitution_map = {}
        reverse_map = {}
        
        print(f"Clear pseudonym assignment started: {len(items)} items")
        
        # 타입별로 그룹화
        items_by_type = defaultdict(list)
        for item in items:
            items_by_type[item['type']].append(item['value'])
        
        # 각 타입별로 처리
        for pii_type, values in items_by_type.items():
            unique_values = list(set(values))
            
            if pii_type == '이름':
                self._handle_names_fake(unique_values, substitution_map, reverse_map)
            elif pii_type == '전화번호':
                self._handle_phones_sequential(unique_values, substitution_map, reverse_map)
            elif pii_type == '이메일':
                self._handle_emails_pseudonym(unique_values, substitution_map, reverse_map)
            elif pii_type == '주소':
                self._handle_addresses_simplified(unique_values, substitution_map, reverse_map)
            elif pii_type == '회사':
                self._handle_companies_generic(unique_values, substitution_map, reverse_map)
            elif pii_type == '나이':
                self._handle_ages_similar(unique_values, substitution_map, reverse_map)
            elif pii_type == '주민등록번호':
                self._handle_rrn_fake(unique_values, substitution_map, reverse_map)
            elif pii_type == '신용카드':
                self._handle_cards_fake(unique_values, substitution_map, reverse_map)
            else:
                self._handle_generic_masked(pii_type, unique_values, substitution_map, reverse_map)
        
        print(f"Clear pseudonym assignment completed: {len(substitution_map)} mappings")
        return substitution_map, reverse_map
    
    def _handle_names_fake(self, names: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """이름 → 김가명1, 이가명2 형식"""
        for name in names:
            if name in self.name_mappings:
                replacement = self.name_mappings[name]
            else:
                replacement = self.pools.generator.get_fake_name()
                
                while replacement in self.used_fake_names:
                    replacement = self.pools.generator.get_fake_name()
                
                self.name_mappings[name] = replacement
                self.used_fake_names.add(replacement)
            
            substitution_map[name] = replacement
            reverse_map[replacement] = name
            print(f"Name: {name} → {replacement}")
    
    def _handle_phones_sequential(self, phones: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """전화번호 → 010-0000-0001 순차 증가"""
        for phone in phones:
            if phone in self.phone_mappings:
                replacement = self.phone_mappings[phone]
            else:
                replacement = self.pools.generator.get_fake_phone()
                
                while replacement in self.used_fake_phones:
                    replacement = self.pools.generator.get_fake_phone()
                
                self.phone_mappings[phone] = replacement
                self.used_fake_phones.add(replacement)
            
            substitution_map[phone] = replacement
            reverse_map[replacement] = phone
            print(f"Phone: {phone} → {replacement}")
    
    def _handle_emails_pseudonym(self, emails: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """이메일 → Pseudonymization1@gamyeong.com 형식"""
        for email in emails:
            if email in self.email_mappings:
                replacement = self.email_mappings[email]
            else:
                replacement = self.pools.generator.get_fake_email()
                
                while replacement in self.used_fake_emails:
                    replacement = self.pools.generator.get_fake_email()
                
                self.email_mappings[email] = replacement
                self.used_fake_emails.add(replacement)
            
            substitution_map[email] = replacement
            reverse_map[replacement] = email
            print(f"Email: {email} → {replacement}")
    
    def _handle_addresses_simplified(self, addresses: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """주소 → 시/군/구만 (간소화)"""
        for address in addresses:
            if address in self.address_mappings:
                replacement = self.address_mappings[address]
            else:
                replacement = self.pools.generator.get_simplified_address(address)
                self.address_mappings[address] = replacement
            
            substitution_map[address] = replacement
            reverse_map[replacement] = address
            print(f"Address: {address} → {replacement}")
    
    def _handle_companies_generic(self, companies: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """회사 → 일반적인 회사명"""
        generic_companies = [
            '테스트회사', '샘플기업', '가명조직', '임시회사', '예시기업',
            '더미회사', '가상기업', '모의회사', '시험조직', '연습회사'
        ]
        
        for company in companies:
            if company in self.company_mappings:
                replacement = self.company_mappings[company]
            else:
                replacement = random.choice(generic_companies)
                self.company_mappings[company] = replacement
            
            substitution_map[company] = replacement
            reverse_map[replacement] = company
            print(f"Company: {company} → {replacement}")
    
    def _handle_ages_similar(self, ages: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """나이 → 비슷한 연령대로 변경"""
        for age in ages:
            if age in self.age_mappings:
                replacement = self.age_mappings[age]
            else:
                try:
                    original_age = int(age)
                    min_age = max(20, original_age - 5)
                    max_age = min(65, original_age + 5)
                    replacement = str(random.randint(min_age, max_age))
                except:
                    replacement = str(random.randint(25, 45))
                
                self.age_mappings[age] = replacement
            
            substitution_map[age] = replacement
            reverse_map[replacement] = age
            print(f"Age: {age} → {replacement}")
    
    def _handle_rrn_fake(self, rrns: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """주민등록번호 → 가상의 주민등록번호"""
        for rrn in rrns:
            if rrn in self.rrn_mappings:
                replacement = self.rrn_mappings[rrn]
            else:
                year = random.randint(70, 99)
                month = random.randint(1, 12)
                day = random.randint(1, 28)
                gender = random.randint(1, 4)
                rest = random.randint(100000, 999999)
                
                replacement = f"{year:02d}{month:02d}{day:02d}-{gender}{rest:06d}"
                self.rrn_mappings[rrn] = replacement
            
            substitution_map[rrn] = replacement
            reverse_map[replacement] = rrn
            print(f"RRN: {rrn} → {replacement}")
    
    def _handle_cards_fake(self, cards: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """신용카드 → 가상의 카드번호"""
        for card in cards:
            if card in self.card_mappings:
                replacement = self.card_mappings[card]
            else:
                last_four = f"{random.randint(1, 9999):04d}"
                replacement = f"0000-0000-0000-{last_four}"
                self.card_mappings[card] = replacement
            
            substitution_map[card] = replacement
            reverse_map[replacement] = card
            print(f"Card: {card} → {replacement}")
    
    def _handle_generic_masked(self, pii_type: str, values: List[str], substitution_map: Dict[str, str], reverse_map: Dict[str, str]):
        """기타 타입 → 마스킹"""
        for value in values:
            replacement = f"[{pii_type.upper()}_MASKED]"
            
            substitution_map[value] = replacement
            reverse_map[replacement] = value
            print(f"{pii_type}: {value} → {replacement}")

def apply_replacements_smart(text: str, substitution_map: Dict[str, str]) -> str:
    """스마트 텍스트 치환 (순서 고려)"""
    if not substitution_map:
        return text
    
    print(f"Smart text substitution: {len(substitution_map)} mappings")
    
    # 긴 문자열부터 치환
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    result = text
    replacements_made = 0
    
    for original, replacement in sorted_items:
        if original in result:
            old_count = result.count(original)
            result = result.replace(original, replacement)
            
            if old_count > 0:
                replacements_made += 1
                print(f"Substitution: '{original}' → '{replacement}' ({old_count} times)")
    
    print(f"Smart substitution completed: {replacements_made} applied")
    return result

def restore_text_smart(pseudonymized_text: str, reverse_map: Dict[str, str]) -> str:
    """스마트 텍스트 복원"""
    if not reverse_map:
        return pseudonymized_text
    
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    result = pseudonymized_text
    for pseudonym, original in sorted_items:
        result = result.replace(pseudonym, original)
    
    return result

def create_detailed_mapping_report(substitution_map: Dict[str, str], reverse_map: Dict[str, str]) -> str:
    """상세한 매핑 리포트 생성"""
    if not substitution_map:
        return "No mapped items."
    
    report = "Detailed Pseudonymization Mapping Report\n"
    report += "=" * 50 + "\n"
    
    by_type = defaultdict(list)
    
    for original, replacement in substitution_map.items():
        if '@' in original:
            pii_type = 'Email'
        elif any(char.isdigit() for char in original) and ('010' in original or '02' in original):
            pii_type = 'Phone'
        elif original.count('-') == 2 and len(original.replace('-', '')) == 13:
            pii_type = 'RRN'
        elif original.count('-') == 3 and len(original.replace('-', '')) == 16:
            pii_type = 'Card'
        elif original.isdigit() and 1 <= int(original) <= 120:
            pii_type = 'Age'
        elif any(keyword in original for keyword in ['시', '구', '군', '로', '동']):
            pii_type = 'Address'
        elif len(original) >= 2 and all(ord('가') <= ord(char) <= ord('힣') for char in original):
            pii_type = 'Name'
        else:
            pii_type = 'Other'
        
        by_type[pii_type].append((original, replacement))
    
    for pii_type, mappings in by_type.items():
        report += f"\n{pii_type} ({len(mappings)} items):\n"
        for original, replacement in mappings:
            report += f"   • {original} → {replacement}\n"
    
    report += f"\nTotal: {len(substitution_map)} PII pseudonymized\n"
    report += "All pseudonyms are clearly distinguishable.\n"
    
    return report

# 호환성 함수들
def apply_replacements(text: str, substitution_map: Dict[str, str]) -> str:
    return apply_replacements_smart(text, substitution_map)

def restore_text(pseudonymized_text: str, reverse_map: Dict[str, str]) -> str:
    return restore_text_smart(pseudonymized_text, reverse_map)

def remove_duplicates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """중복 제거 (위치 기반)"""
    unique_items = []
    seen_positions = set()
    
    for item in items:
        position_key = (item['start'], item['end'], item['value'])
        if position_key not in seen_positions:
            unique_items.append(item)
            seen_positions.add(position_key)
    
    return unique_items