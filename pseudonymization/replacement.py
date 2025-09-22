# pseudonymization/replacement.py
"""
가명화 치환 모듈 (주소 스마트 치환 개선)
- 토큰 기반 치환
- 실제 가명 기반 치환  
- 주소 연속 구문 스마트 치환
"""

import re
from typing import Dict, List, Any, Tuple
from .pools import get_pools

class ReplacementManager:
    """기본 치환 매니저 (토큰 기반)"""
    
    def __init__(self):
        self.replacement_map = {}
        self.reverse_map = {}
    
    def apply_tokenization(self, text: str, items: List[Dict[str, Any]]) -> Tuple[str, Dict[str, str], Dict[str, str]]:
        """토큰 기반 치환"""
        
        tokenized_text = text
        substitution_map = {}
        reverse_map = {}
        
        type_counters = {}
        
        for item in items:
            original = item['value']
            pii_type = item['type']
            
            if original in substitution_map:
                continue
            
            # 타입별 카운터 초기화
            if pii_type not in type_counters:
                type_counters[pii_type] = 0
            
            # 토큰 생성
            if pii_type == "이름":
                token = f"[PER_{type_counters[pii_type]}]"
            elif pii_type == "전화번호":
                token = f"[PHONE_{type_counters[pii_type]}]"
            elif pii_type == "주소":
                token = f"[LOC_{type_counters[pii_type]}]"
            elif pii_type == "이메일":
                token = f"[EMAIL_{type_counters[pii_type]}]"
            elif pii_type == "주민등록번호":
                token = f"[SSN_{type_counters[pii_type]}]"
            else:
                token = f"[{pii_type.upper()}_{type_counters[pii_type]}]"
            
            substitution_map[original] = token
            reverse_map[token] = original
            type_counters[pii_type] += 1
        
        # 텍스트 치환
        for original, token in substitution_map.items():
            tokenized_text = tokenized_text.replace(original, token)
        
        return tokenized_text, substitution_map, reverse_map

class WorkflowReplacementManager:
    """워크플로우 기반 치환 매니저 (주소 스마트 치환)"""
    
    def __init__(self):
        self.pools = get_pools()
        self.counters = {
            "이름": 0,
            "전화번호": 0,
            "이메일": 0,
            "주소": 0,
            "주민등록번호": 0
        }
    
    def apply_pseudonymization(self, text: str, items: List[Dict[str, Any]]) -> Tuple[str, Dict[str, str], Dict[str, str]]:
        """실제 가명 기반 치환 (주소 스마트 처리)"""
        
        print("치환 맵 생성: {}개 항목".format(len(items)))
        
        pseudonymized_text = text
        substitution_map = {}
        reverse_map = {}
        
        # 주소와 비주소 항목 분리
        address_items = [item for item in items if item['type'] == '주소']
        non_address_items = [item for item in items if item['type'] != '주소']
        
        # 주소 스마트 치환 처리
        if address_items:
            pseudonymized_text, addr_sub_map, addr_rev_map = self._process_address_smart_replacement(
                pseudonymized_text, address_items
            )
            substitution_map.update(addr_sub_map)
            reverse_map.update(addr_rev_map)
        
        # 비주소 항목들 처리
        for item in non_address_items:
            original = item['value']
            pii_type = item['type']
            
            if original in substitution_map:
                continue
            
            # 가명 생성
            replacement = self._generate_replacement(pii_type, original)
            
            substitution_map[original] = replacement
            reverse_map[replacement] = original
            
            print(f"매핑: '{original}' ↔ '{replacement}'")
        
        print(f"치환 맵 생성 완료: {len(substitution_map)}개 매핑")
        
        # 비주소 텍스트 치환 적용
        print("가명화 적용: {}개 매핑".format(len([k for k in substitution_map.keys() if not k.startswith('주소_')])))
        
        replaced_count = 0
        for original, replacement in substitution_map.items():
            if not original.startswith('주소_') and original in pseudonymized_text:
                pseudonymized_text = pseudonymized_text.replace(original, replacement)
                replaced_count += 1
                print(f"가명화: '{original}' → {replacement} ({replaced_count}번)")
        
        print(f"가명화 완료: {replaced_count}개 적용")
        
        return pseudonymized_text, substitution_map, reverse_map
    
    def _process_address_smart_replacement(self, text: str, address_items: List[Dict[str, Any]]) -> Tuple[str, Dict[str, str], Dict[str, str]]:
        """주소 스마트 치환 처리 - 큰 단위만 남기고 나머지 제거"""
        
        print(f"주소 스마트 치환: {len(address_items)}개 주소 발견")
        
        substitution_map = {}
        reverse_map = {}
        processed_text = text
        
        if not address_items:
            return processed_text, substitution_map, reverse_map
        
        # 주소 항목들을 위치순으로 정렬
        sorted_addresses = sorted(address_items, key=lambda x: x['start'])
        
        # 가장 큰 단위 주소 찾기 (시/도 우선)
        main_address = None
        for addr_item in sorted_addresses:
            addr_value = addr_item['value']
            # 시/도 단위인지 확인
            if addr_value in self.pools.provinces or any(addr_value.startswith(p) for p in self.pools.provinces):
                main_address = addr_value
                break
        
        # 시/도가 없으면 첫 번째 주소 사용
        if not main_address:
            main_address = sorted_addresses[0]['value']
        
        print(f"대표 주소 선택: '{main_address}'")
        
        # 연속된 주소 구문을 대표 주소로 치환
        # 예: "부산 해운대구" → "부산"
        address_values = [item['value'] for item in sorted_addresses]
        
        # 연속된 주소 패턴 생성 및 치환
        # 가장 긴 연속 구문부터 처리
        for start_idx in range(len(address_values)):
            for end_idx in range(len(address_values), start_idx, -1):
                if end_idx - start_idx <= 1:  # 단일 주소는 스킵
                    continue
                    
                # 연속 주소 구문 생성
                sequence = address_values[start_idx:end_idx]
                pattern = r'\s*'.join([re.escape(addr) for addr in sequence])
                
                # 텍스트에서 해당 패턴 찾기
                if re.search(pattern, processed_text):
                    # 대표 주소로 치환
                    processed_text = re.sub(pattern, main_address, processed_text)
                    print(f"주소 연속 구문 치환: '{' '.join(sequence)}' → '{main_address}'")
                    
                    substitution_map[f"주소_연속_{start_idx}_{end_idx}"] = main_address
                    reverse_map[main_address] = ' '.join(sequence)
                    
                    return processed_text, substitution_map, reverse_map
        
        # 연속 구문이 없으면 개별 주소들 중 메인 주소가 아닌 것들만 제거
        for addr_item in sorted_addresses:
            original = addr_item['value']
            if original != main_address:
                # 다른 주소들은 제거 (공백으로 치환)
                pattern = r'\s*' + re.escape(original) + r'\s*'
                before = processed_text
                processed_text = re.sub(pattern, ' ', processed_text)
                if before != processed_text:
                    print(f"부차 주소 제거: '{original}'")
                    substitution_map[f"제거_{original}"] = ""
                    reverse_map[""] = original
        
        # 연속 공백 정리
        processed_text = re.sub(r'\s+', ' ', processed_text).strip()
        
        return processed_text, substitution_map, reverse_map
    
    # _clean_address 함수 제거 (더 이상 사용하지 않음)
    
    def _generate_replacement(self, pii_type: str, original: str) -> str:
        """타입별 가명 생성"""
        
        if pii_type == "이름":
            replacement = self.pools.fake_names[self.counters["이름"] % len(self.pools.fake_names)]
            self.counters["이름"] += 1
            return replacement
        
        elif pii_type == "전화번호":
            replacement = self.pools.fake_phones[self.counters["전화번호"] % len(self.pools.fake_phones)]
            self.counters["전화번호"] += 1
            return replacement
        
        elif pii_type == "이메일":
            replacement = self.pools.fake_emails[self.counters["이메일"] % len(self.pools.fake_emails)]
            self.counters["이메일"] += 1
            return replacement
        
        elif pii_type == "주소":
            # 원본 주소를 분석해서 적절한 가명 주소 선택
            replacement = self._generate_fake_address(original)
            self.counters["주소"] += 1
            return replacement
        
        elif pii_type == "주민등록번호":
            # 주민등록번호는 고정된 패턴 사용
            replacement = "000000-0000000"
            self.counters["주민등록번호"] += 1
            return replacement
        
        else:
            return f"[{pii_type}]"
    
    def _generate_fake_address(self, original: str) -> str:
        """주소별 적절한 가명 주소 생성"""
        
        # 원본 주소 그대로 반환 (접미사 제거하지 않음)
        if original in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]:
            return original
        elif original in ["경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]:
            return original
        else:
            # 기타 지역은 순환하는 가명 주소 사용
            fake_address = self.pools.fake_addresses[self.counters["주소"] % len(self.pools.fake_addresses)]
            # 접미사 제거
            for suffix in ["시", "도"]:
                if fake_address.endswith(suffix):
                    return fake_address[:-len(suffix)]
            return fake_address

def apply_replacements(text: str, items: List[Dict[str, Any]], use_fake: bool = True) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    """치환 적용 (통합 함수)"""
    
    if use_fake:
        manager = WorkflowReplacementManager()
        return manager.apply_pseudonymization(text, items)
    else:
        manager = ReplacementManager()
        return manager.apply_tokenization(text, items)

def restore_text(masked_text: str, reverse_map: Dict[str, str]) -> str:
    """텍스트 복원"""
    
    restored_text = masked_text
    
    for replacement, original in reverse_map.items():
        restored_text = restored_text.replace(replacement, original)
    
    return restored_text

def restore_from_tokens(tokenized_text: str, token_map: Dict[str, str]) -> str:
    """토큰에서 원본 복원"""
    
    restored_text = tokenized_text
    
    # token_map: {원본: 토큰} -> {토큰: 원본}으로 변환
    reverse_token_map = {token: original for original, token in token_map.items()}
    
    for token, original in reverse_token_map.items():
        restored_text = restored_text.replace(token, original)
    
    return restored_text

def create_detailed_mapping_report(items: List[Dict[str, Any]], substitution_map: Dict[str, str]) -> Dict[str, Any]:
    """상세한 매핑 리포트 생성"""
    
    report = {
        "total_items": len(items),
        "by_type": {},
        "mappings": []
    }
    
    # 타입별 집계
    for item in items:
        pii_type = item['type']
        if pii_type not in report["by_type"]:
            report["by_type"][pii_type] = 0
        report["by_type"][pii_type] += 1
    
    # 매핑 정보
    for item in items:
        original = item['value']
        replacement = substitution_map.get(original, original)
        
        report["mappings"].append({
            "type": item['type'],
            "original": original,
            "replacement": replacement,
            "position": f"{item['start']}-{item['end']}",
            "confidence": item['confidence'],
            "source": item['source']
        })
    
    return report

def remove_duplicates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """중복 항목 제거"""
    
    seen = set()
    unique_items = []
    
    for item in items:
        key = (item['type'], item['value'], item['start'], item['end'])
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    
    return unique_items

# ===== 호환성 함수들 =====
def get_workflow_manager() -> WorkflowReplacementManager:
    """워크플로우 매니저 인스턴스 반환"""
    return WorkflowReplacementManager()

def apply_tokenization(text: str, items: List[Dict[str, Any]]) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    """토큰화 적용 (호환성)"""
    manager = ReplacementManager()
    return manager.apply_tokenization(text, items)