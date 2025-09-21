# pseudonymization/replacement.py
"""
워크플로우 기반 가명화 치환 모듈
토큰 기반 치환 시스템: [PER_0], [ORG_0], [LOC_0] 등
"""

import re
import random
from collections import defaultdict
from typing import Dict, List, Any, Tuple

class WorkflowReplacementManager:
    """워크플로우 기반 토큰 치환 관리자"""
    
    def __init__(self):
        self.substitution_map = {}  # 원본 → 토큰
        self.reverse_map = {}       # 토큰 → 원본  
        print("🔄 워크플로우 치환매니저 초기화")
    
    def create_substitution_map(self, items: List[Dict[str, Any]], token_map: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """치환 맵 생성 (토큰 기반)"""
        
        print(f"🗺️ 치환 맵 생성: {len(items)}개 항목")
        
        substitution_map = {}
        reverse_map = {}
        
        for item in items:
            original = item['value']
            token = token_map.get(original)
            
            if token:
                substitution_map[original] = token
                reverse_map[token] = original
                print(f"🗺️ 매핑: '{original}' ↔ {token}")
        
        self.substitution_map = substitution_map
        self.reverse_map = reverse_map
        
        print(f"🗺️ 치환 맵 생성 완료: {len(substitution_map)}개 매핑")
        
        return substitution_map, reverse_map
    
    def restore_from_tokens(self, tokenized_text: str, reverse_map: Dict[str, str]) -> str:
        """토큰을 원본으로 복원"""
        
        print("🔄 토큰 복원 시작")
        
        result = tokenized_text
        restored_count = 0
        
        # 모든 토큰을 원본으로 복원
        for token, original in reverse_map.items():
            if token in result:
                count = result.count(token)
                result = result.replace(token, original)
                restored_count += count
                print(f"🔄 복원: {token} → '{original}' ({count}번)")
        
        print(f"🔄 토큰 복원 완료: {restored_count}개 복원")
        
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
    
    print(f"🏷️ 토큰화 적용: {len(substitution_map)}개 매핑")
    
    result = text
    applied_count = 0
    
    # 긴 문자열부터 치환 (부분 문자열 문제 방지)
    sorted_items = sorted(substitution_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for original, token in sorted_items:
        if original in result:
            count = result.count(original)
            result = result.replace(original, token)
            applied_count += count
            print(f"🏷️ 토큰화: '{original}' → {token} ({count}번)")
    
    print(f"🏷️ 토큰화 완료: {applied_count}개 적용")
    return result

def restore_from_tokens(tokenized_text: str, reverse_map: Dict[str, str]) -> str:
    """토큰을 원본으로 복원"""
    manager = get_workflow_manager()
    return manager.restore_from_tokens(tokenized_text, reverse_map)

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
    'restore_text',
    'restore_text_smart', 
    'restore_from_tokens',
    'create_detailed_mapping_report',
    'remove_duplicates'
]