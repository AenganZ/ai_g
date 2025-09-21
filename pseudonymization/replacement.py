# pseudonymization/replacement.py
"""
워크플로우 기반 치환 모듈 - 실제 가명 치환 지원
"""

import re
from typing import Dict, List, Any
from .pools import get_pools

class WorkflowReplacementManager:
    """워크플로우용 치환 매니저 (실제 가명 치환)"""
    
    def __init__(self):
        self.pools = get_pools()
        self.name_counter = 0
        self.phone_counter = 0
        self.email_counter = 0
        self.address_counter = 0
        
    def create_substitution_map(self, items: List[Dict[str, Any]], token_map: Dict[str, str]) -> tuple:
        """치환 맵 생성 (토큰 → 실제 가명)"""
        
        print("치환 맵 생성: {}개 항목".format(len(items)))
        
        substitution_map = {}  # 원본 → 가명
        reverse_map = {}       # 가명 → 원본
        
        for item in items:
            original_value = item['value']
            pii_type = item['type']
            
            # 이미 처리된 경우 건너뛰기
            if original_value in substitution_map:
                continue
            
            # 타입별 가명 생성
            if pii_type == "이름":
                fake_value = self._generate_fake_name()
            elif pii_type == "전화번호":
                fake_value = self._generate_fake_phone()
            elif pii_type == "이메일":
                fake_value = self._generate_fake_email()
            elif pii_type == "주소":
                fake_value = self._generate_fake_address(original_value)
            else:
                fake_value = f"[{pii_type}_가명]"
            
            substitution_map[original_value] = fake_value
            reverse_map[fake_value] = original_value
            
            print("매핑: '{}' ↔ {} ↔ '{}'".format(original_value, token_map.get(original_value, '???'), fake_value))
        
        print("치환 맵 생성 완료: {}개 매핑".format(len(substitution_map)))
        return substitution_map, reverse_map
    
    def _generate_fake_name(self) -> str:
        """가명 이름 생성 (김가명, 이가명 형태)"""
        surnames = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임']
        fake_words = ['가명', '익명', '무명', '차명', '별명', '테스트', '샘플', '더미', '임시', '대체']
        
        surname = surnames[self.name_counter % len(surnames)]
        fake_word = fake_words[self.name_counter % len(fake_words)]
        self.name_counter += 1
        
        return surname + fake_word
    
    def _generate_fake_phone(self) -> str:
        """가짜 전화번호 생성 (010-0000-0000부터 1씩 증가)"""
        fake_phone = f"010-{self.phone_counter:04d}-0000"
        self.phone_counter += 1
        return fake_phone
    
    def _generate_fake_email(self) -> str:
        """가짜 이메일 생성"""
        domains = ['example.com', 'test.co.kr', 'sample.net', 'demo.org']
        domain = domains[self.email_counter % len(domains)]
        fake_email = f"user{self.email_counter:03d}@{domain}"
        self.email_counter += 1
        return fake_email
    
    def _generate_fake_address(self, original: str) -> str:
        """가짜 주소 생성 (시/도만 표시)"""
        # 원본이 시/도인 경우 그대로 + "시" 추가
        if original in self.pools.provinces:
            if not original.endswith('시') and not original.endswith('도'):
                return original + '시'
            return original
        
        # 구/군인 경우 해당하는 시/도로 변환
        if original in self.pools.districts:
            # 주요 구에 해당하는 시 매핑
            district_to_city = {
                '강남구': '서울시', '강북구': '서울시', '강서구': '서울시', '강동구': '서울시',
                '서초구': '서울시', '송파구': '서울시', '마포구': '서울시', '용산구': '서울시',
                '종로구': '서울시', '중구': '서울시', '동구': '대전시', '서구': '대전시',
                '남구': '부산시', '북구': '대구시', '해운대구': '부산시', '부산진구': '부산시',
                '수성구': '대구시', '달서구': '대구시'
            }
            return district_to_city.get(original, '서울시')
        
        # 기타 경우 기본 주소 풀에서 선택
        fake_addresses = ['서울시', '부산시', '대구시', '인천시', '광주시', '대전시', '울산시']
        return fake_addresses[self.address_counter % len(fake_addresses)]

class ReplacementManager:
    """기본 치환 매니저 (호환성)"""
    
    def __init__(self):
        self.workflow_manager = WorkflowReplacementManager()
    
    def create_substitution_map(self, items: List[Dict[str, Any]], token_map: Dict[str, str]) -> tuple:
        return self.workflow_manager.create_substitution_map(items, token_map)

def get_workflow_manager() -> WorkflowReplacementManager:
    """워크플로우 매니저 싱글톤"""
    if not hasattr(get_workflow_manager, '_instance'):
        get_workflow_manager._instance = WorkflowReplacementManager()
    return get_workflow_manager._instance

def apply_tokenization(text: str, substitution_map: Dict[str, str]) -> str:
    """토큰화 적용 (원본 → 가명)"""
    
    print("토큰화 적용: {}개 매핑".format(len(substitution_map)))
    
    result_text = text
    replacement_count = 0
    
    # 길이 순으로 정렬 (긴 것부터 치환하여 부분 매칭 방지)
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, replacement in sorted_items:
        if original in result_text:
            count = result_text.count(original)
            result_text = result_text.replace(original, replacement)
            replacement_count += count
            print("토큰화: '{}' → {} ({}번)".format(original, replacement, count))
    
    print("토큰화 완료: {}개 적용".format(replacement_count))
    return result_text

def restore_from_tokens(text: str, reverse_map: Dict[str, str]) -> str:
    """토큰에서 원본으로 복원"""
    
    print("토큰 복원 시작")
    
    result_text = text
    
    # 길이 순으로 정렬 (긴 것부터 복원)
    sorted_items = sorted(reverse_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for fake_value, original_value in sorted_items:
        if fake_value in result_text:
            result_text = result_text.replace(fake_value, original_value)
            print("복원: '{}' → '{}'".format(fake_value, original_value))
    
    print("토큰 복원 완료")
    return result_text

def create_detailed_mapping_report(substitution_map: Dict[str, str], reverse_map: Dict[str, str]) -> str:
    """상세 매핑 리포트 생성"""
    
    if not substitution_map:
        return "매핑된 항목이 없습니다."
    
    report = ["=" * 50]
    report.append("치환 매핑 리포트")
    report.append("=" * 50)
    
    for i, (original, fake) in enumerate(substitution_map.items(), 1):
        report.append(f"{i}. '{original}' → '{fake}'")
    
    report.append("=" * 50)
    report.append(f"총 {len(substitution_map)}개 항목 치환됨")
    
    return "\n".join(report)

# 호환성 함수들
def apply_replacements(text: str, substitution_map: Dict[str, str]) -> str:
    """호환성: 치환 적용"""
    return apply_tokenization(text, substitution_map)

def restore_text(text: str, reverse_map: Dict[str, str]) -> str:
    """호환성: 텍스트 복원"""
    return restore_from_tokens(text, reverse_map)

def remove_duplicates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """중복 제거"""
    seen = set()
    unique_items = []
    
    for item in items:
        key = (item.get('value', ''), item.get('start', 0), item.get('end', 0))
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    
    return unique_items