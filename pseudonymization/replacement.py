# pseudonymization/replacement.py
"""
워크플로우 기반 가명화 치환 모듈 (수정된 버전)
토큰 기반 치환 + 가명화 치환 시스템
"""

import re
import random
from collections import defaultdict
from typing import Dict, List, Any, Tuple
from .pools import get_pools

class WorkflowReplacementManager:
    """워크플로우 기반 토큰 치환 관리자 (가명화 지원)"""
    
    def __init__(self):
        self.substitution_map = {}  # 원본 → 토큰
        self.reverse_map = {}       # 토큰 → 원본
        self.fake_substitution_map = {}  # 원본 → 가명
        self.fake_reverse_map = {}       # 가명 → 원본
        
        # 카운터들
        self.name_counter = 0
        self.phone_counter = 0
        self.address_counter = 0
        
        print("워크플로우 치환매니저 초기화")
    
    def create_substitution_map(self, items: List[Dict[str, Any]], token_map: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """치환 맵 생성 (토큰 기반 + 가명화)"""
        
        print(f"치환 맵 생성: {len(items)}개 항목")
        
        substitution_map = {}
        reverse_map = {}
        fake_substitution_map = {}
        fake_reverse_map = {}
        
        pools = get_pools()
        
        for item in items:
            original = item['value']
            pii_type = item['type']
            token = token_map.get(original)
            
            if token:
                # 토큰 매핑
                substitution_map[original] = token
                reverse_map[token] = original
                
                # 가명화 매핑 생성
                fake_value = self._generate_fake_value(original, pii_type, pools)
                fake_substitution_map[original] = fake_value
                fake_reverse_map[fake_value] = original
                
                print(f"매핑: '{original}' ↔ {token} ↔ '{fake_value}'")
        
        self.substitution_map = substitution_map
        self.reverse_map = reverse_map
        self.fake_substitution_map = fake_substitution_map
        self.fake_reverse_map = fake_reverse_map
        
        print(f"치환 맵 생성 완료: {len(substitution_map)}개 매핑")
        
        return substitution_map, reverse_map
    
    def _generate_fake_value(self, original: str, pii_type: str, pools) -> str:
        """PII 타입별 가명 값 생성"""
        
        if pii_type == '이름':
            return self._generate_fake_name(original, pools)
        elif pii_type == '전화번호':
            return self._generate_fake_phone()
        elif pii_type == '주소':
            return self._generate_fake_address(original, pools)
        elif pii_type == '이메일':
            return self._generate_fake_email(original)
        else:
            return f"[가명_{pii_type}]"
    
    def _generate_fake_name(self, original: str, pools) -> str:
        """가명 이름 생성 (김가명, 이가명 형태)"""
        
        # 성씨 추출 (첫 글자 또는 두 글자)
        if len(original) >= 2 and original[:2] in pools.compound_surnames:
            surname = original[:2]
        elif len(original) >= 1 and original[0] in pools.single_surnames:
            surname = original[0]
        else:
            # 기본 성씨 사용
            surnames = ['김', '이', '박', '최', '정', '강', '조', '윤']
            surname = surnames[self.name_counter % len(surnames)]
        
        # 가명 단어들
        fake_words = ['가명', '익명', '무명', '별명', '차명', '임명', '성명', '호명']
        fake_word = fake_words[self.name_counter % len(fake_words)]
        
        fake_name = surname + fake_word
        self.name_counter += 1
        
        return fake_name
    
    def _generate_fake_phone(self) -> str:
        """가짜 전화번호 생성 (010-0000-0000부터 1씩 증가)"""
        fake_phone = f"010-{self.phone_counter:04d}-0000"
        self.phone_counter += 1
        return fake_phone
    
    def _generate_fake_address(self, original: str, pools) -> str:
        """가짜 주소 생성 (시/도만 표시)"""
        
        # 원본 주소에서 시/도 찾기
        for province in pools.provinces:
            if province in original:
                return province + "시"
        
        # 못 찾으면 기본 주소 사용
        fake_addresses = ['서울시', '부산시', '대구시', '인천시', '광주시', '대전시', '울산시', '경기도']
        fake_address = fake_addresses[self.address_counter % len(fake_addresses)]
        self.address_counter += 1
        
        return fake_address
    
    def _generate_fake_email(self, original: str) -> str:
        """가짜 이메일 생성"""
        domains = ['example.com', 'test.org', 'sample.net', 'fake.co.kr']
        domain = domains[self.name_counter % len(domains)]
        return f"user{self.name_counter:03d}@{domain}"
    
    def apply_fake_substitution(self, text: str) -> str:
        """가명화 치환 적용"""
        if not self.fake_substitution_map:
            return text
        
        print(f"가명화 치환 적용: {len(self.fake_substitution_map)}개 매핑")
        
        result = text
        applied_count = 0
        
        # 긴 문자열부터 치환 (부분 문자열 문제 방지)
        sorted_items = sorted(self.fake_substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
        
        for original, fake_value in sorted_items:
            if original in result:
                count = result.count(original)
                result = result.replace(original, fake_value)
                applied_count += count
                print(f"가명화: '{original}' → '{fake_value}' ({count}번)")
        
        print(f"가명화 치환 완료: {applied_count}개 적용")
        return result
    
    def restore_from_tokens(self, tokenized_text: str, reverse_map: Dict[str, str]) -> str:
        """토큰을 원본으로 복원"""
        
        print("토큰 복원 시작")
        
        result = tokenized_text
        restored_count = 0
        
        # 모든 토큰을 원본으로 복원
        for token, original in reverse_map.items():
            if token in result:
                count = result.count(token)
                result = result.replace(token, original)
                restored_count += count
                print(f"복원: {token} → '{original}' ({count}번)")
        
        print(f"토큰 복원 완료: {restored_count}개 복원")
        
        return result
    
    def restore_from_fake(self, fake_text: str) -> str:
        """가명화된 텍스트를 원본으로 복원"""
        
        print("가명화 복원 시작")
        
        result = fake_text
        restored_count = 0
        
        # 모든 가명을 원본으로 복원
        for fake_value, original in self.fake_reverse_map.items():
            if fake_value in result:
                count = result.count(fake_value)
                result = result.replace(fake_value, original)
                restored_count += count
                print(f"가명화 복원: '{fake_value}' → '{original}' ({count}번)")
        
        print(f"가명화 복원 완료: {restored_count}개 복원")
        
        return result

# 전역 매니저 인스턴스
_workflow_manager = None

def get_workflow_manager():
    """WorkflowReplacementManager 싱글톤 인스턴스"""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowReplacementManager()
    return _workflow_manager

def apply_tokenization(text: str, substitution_map: Dict[str, str]) -> str:
    """토큰화 적용"""
    if not substitution_map:
        return text
    
    print(f"토큰화 적용: {len(substitution_map)}개 매핑")
    
    result = text
    applied_count = 0
    
    # 긴 문자열부터 치환 (부분 문자열 문제 방지)
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, token in sorted_items:
        if original in result:
            count = result.count(original)
            result = result.replace(original, token)
            applied_count += count
            print(f"토큰화: '{original}' → {token} ({count}번)")
    
    print(f"토큰화 완료: {applied_count}개 적용")
    return result

def apply_fake_substitution(text: str) -> str:
    """가명화 치환 적용"""
    manager = get_workflow_manager()
    return manager.apply_fake_substitution(text)

def restore_from_tokens(tokenized_text: str, reverse_map: Dict[str, str]) -> str:
    """토큰을 원본으로 복원"""
    manager = get_workflow_manager()
    return manager.restore_from_tokens(tokenized_text, reverse_map)

def restore_from_fake(fake_text: str) -> str:
    """가명화된 텍스트를 원본으로 복원"""
    manager = get_workflow_manager()
    return manager.restore_from_fake(fake_text)

def create_detailed_mapping_report(substitution_map: Dict[str, str], reverse_map: Dict[str, str]) -> str:
    """상세 매핑 리포트 생성"""
    report = "워크플로우 기반 토큰 매핑 리포트\n"
    report += "=" * 50 + "\n"
    
    by_type = defaultdict(list)
    
    for original, token in substitution_map.items():
        # 토큰에서 타입 추출
        if '[PER_' in token:
            pii_type = '이름'
        elif '[ORG_' in token:
            pii_type = '회사'
        elif '[LOC_' in token:
            pii_type = '주소'
        elif '[EMAIL_' in token:
            pii_type = '이메일'
        elif '[PHONE_' in token:
            pii_type = '전화번호'
        elif '[AGE_' in token:
            pii_type = '나이'
        elif '[RRN_' in token:
            pii_type = '주민등록번호'
        elif '[CARD_' in token:
            pii_type = '신용카드'
        elif '[ACCT_' in token:
            pii_type = '계좌번호'
        else:
            pii_type = '기타'
        
        by_type[pii_type].append((original, token))
    
    for pii_type, mappings in by_type.items():
        report += f"\n{pii_type} ({len(mappings)}개 항목):\n"
        for original, token in mappings:
            report += f"   • {original} ↔ {token}\n"
    
    report += f"\n전체: {len(substitution_map)}개 PII 토큰화됨\n"
    report += "워크플로우 기반 양방향 매핑 완료\n"
    
    return report

def create_fake_mapping_report() -> str:
    """가명화 매핑 리포트 생성"""
    manager = get_workflow_manager()
    
    report = "가명화 치환 매핑 리포트\n"
    report += "=" * 50 + "\n"
    
    by_type = defaultdict(list)
    
    for original, fake_value in manager.fake_substitution_map.items():
        # 원본에서 타입 추론
        if any(char.isdigit() for char in original) and '-' in original:
            if original.startswith('010'):
                pii_type = '전화번호'
            else:
                pii_type = '기타번호'
        elif '@' in original:
            pii_type = '이메일'
        elif any(word in original for word in ['시', '구', '동', '로', '가']):
            pii_type = '주소'
        else:
            pii_type = '이름'
        
        by_type[pii_type].append((original, fake_value))
    
    for pii_type, mappings in by_type.items():
        report += f"\n{pii_type} ({len(mappings)}개 항목):\n"
        for original, fake_value in mappings:
            report += f"   • {original} → {fake_value}\n"
    
    report += f"\n전체: {len(manager.fake_substitution_map)}개 PII 가명화됨\n"
    
    return report

# 호환성을 위한 기존 클래스
class ReplacementManager(WorkflowReplacementManager):
    """호환성을 위한 클래스"""
    
    def assign_replacements(self, items: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """호환성을 위한 메서드 - 토큰 맵 사용"""
        
        # 토큰 맵 생성
        token_map = {}
        type_counters = {}
        
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
            
            if pii_type not in type_counters:
                type_counters[pii_type] = 0
            
            prefix = type_prefixes.get(pii_type, 'MISC')
            token = f"[{prefix}_{type_counters[pii_type]}]"
            
            token_map[pii_value] = token
            type_counters[pii_type] += 1
        
        return self.create_substitution_map(items, token_map)

# 호환성 함수들
def apply_replacements_smart(text: str, substitution_map: Dict[str, str]) -> str:
    return apply_tokenization(text, substitution_map)

def apply_replacements(text: str, substitution_map: Dict[str, str]) -> str:
    return apply_tokenization(text, substitution_map)

def restore_text_smart(tokenized_text: str, reverse_map: Dict[str, str]) -> str:
    return restore_from_tokens(tokenized_text, reverse_map)

def restore_text(tokenized_text: str, reverse_map: Dict[str, str]) -> str:
    return restore_from_tokens(tokenized_text, reverse_map)

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

# 워크플로우 핵심 함수 export
__all__ = [
    'ReplacementManager',
    'WorkflowReplacementManager',
    'apply_replacements',
    'apply_replacements_smart',
    'apply_tokenization',
    'apply_fake_substitution',
    'restore_text',
    'restore_text_smart', 
    'restore_from_tokens',
    'restore_from_fake',
    'create_detailed_mapping_report',
    'create_fake_mapping_report',
    'remove_duplicates'
]