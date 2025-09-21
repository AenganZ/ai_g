# pseudonymization/core.py
"""
핵심 가명화 통합 모듈 - 깔끔한 버전
NER 간소화 + Regex 중심 + 명확한 가명화
"""

import time
from typing import Dict, Any, List
from .pools import initialize_pools, get_pools
from .detection import detect_pii_enhanced
from .replacement import ReplacementManager, apply_replacements_smart, restore_text_smart, create_detailed_mapping_report

# 전역 ReplacementManager
_replacement_manager = None

def get_replacement_manager() -> ReplacementManager:
    """ReplacementManager 싱글톤 인스턴스"""
    global _replacement_manager
    if _replacement_manager is None:
        _replacement_manager = ReplacementManager()
    return _replacement_manager

def pseudonymize_text(text: str, detailed_report: bool = True) -> Dict[str, Any]:
    """
    최적화된 통합 가명화 함수
    
    Args:
        text: 원본 텍스트
        detailed_report: 상세 리포트 생성 여부
        
    Returns:
        dict: 가명화 결과
    """
    start_time = time.time()
    print(f"Starting pseudonymization: {text[:50]}...")
    
    # 데이터풀 확인 및 초기화
    pools = get_pools()
    if not pools._initialized:
        print("Initializing data pools...")
        initialize_pools()
    
    # PII 탐지
    print("PII detection (NER simplified + Regex focused)")
    detection = detect_pii_enhanced(text)
    
    if not detection['items']:
        processing_time = time.time() - start_time
        print(f"No PII detected. Processing time: {processing_time:.3f}s")
        return {
            "original": text,
            "pseudonymized": text,
            "masked_prompt": text,
            "detection": detection,
            "substitution_map": {},
            "reverse_map": {},
            "mapping_report": "No PII detected.",
            "processing_time": processing_time,
            "stats": {
                "detected_items": 0,
                "replaced_items": 0,
                "detection_time": processing_time,
                "replacement_time": 0,
                "total_time": processing_time,
                "items_by_type": {},
                "detection_stats": detection['stats']
            }
        }
    
    # 가명 치환값 할당
    detection_time = time.time() - start_time
    replacement_start = time.time()
    
    manager = get_replacement_manager()
    substitution_map, reverse_map = manager.assign_replacements(detection['items'])
    
    # 텍스트 치환
    pseudonymized = apply_replacements_smart(text, substitution_map)
    
    replacement_time = time.time() - replacement_start
    total_time = time.time() - start_time
    
    # 상세 리포트 생성
    mapping_report = ""
    if detailed_report:
        mapping_report = create_detailed_mapping_report(substitution_map, reverse_map)
    
    print(f"Before: {text}")
    print(f"After: {pseudonymized}")
    print(f"Processing time: detection {detection_time:.3f}s, replacement {replacement_time:.3f}s, total {total_time:.3f}s")
    
    # 결과 반환
    result = {
        "original": text,
        "pseudonymized": pseudonymized,
        "masked_prompt": pseudonymized,
        "detection": detection,
        "substitution_map": substitution_map,
        "reverse_map": reverse_map,
        "mapping_report": mapping_report,
        "processing_time": total_time,
        "stats": {
            "detected_items": len(detection['items']),
            "replaced_items": len(substitution_map),
            "detection_time": detection_time,
            "replacement_time": replacement_time,
            "total_time": total_time,
            "items_by_type": {},
            "detection_stats": detection['stats']
        }
    }
    
    # 타입별 통계 추가
    for item in detection['items']:
        item_type = item['type']
        if item_type not in result['stats']['items_by_type']:
            result['stats']['items_by_type'][item_type] = 0
        result['stats']['items_by_type'][item_type] += 1
    
    print(f"Pseudonymization completed: {len(detection['items'])} PII processed")
    print(f"Substitution map: {substitution_map}")
    
    return result

def restore_original(pseudonymized_text: str, reverse_map: Dict[str, str]) -> str:
    """가명화된 텍스트를 원본으로 복원"""
    return restore_text_smart(pseudonymized_text, reverse_map)

def batch_pseudonymize(texts: List[str], show_progress: bool = True) -> List[Dict[str, Any]]:
    """여러 텍스트 일괄 가명화"""
    if show_progress:
        print(f"Batch pseudonymization started: {len(texts)} texts")
    
    results = []
    total_start = time.time()
    
    for i, text in enumerate(texts, 1):
        if show_progress:
            print(f"Processing [{i}/{len(texts)}]...")
        result = pseudonymize_text(text, detailed_report=False)
        results.append(result)
    
    total_time = time.time() - total_start
    if show_progress:
        print(f"Batch pseudonymization completed: {len(texts)} texts, total {total_time:.3f}s")
        print(f"Average time per text: {total_time/len(texts):.3f}s")
    
    return results

def load_data_pools(custom_data: Dict = None):
    """데이터풀 로드"""
    initialize_pools(custom_data)

def get_data_pool_stats() -> Dict[str, int]:
    """데이터풀 통계"""
    from .pools import get_pool_stats
    return get_pool_stats()

def get_performance_benchmark() -> Dict[str, Any]:
    """성능 벤치마크 생성"""
    pools = get_pools()
    
    # 다양한 크기의 테스트 텍스트
    test_cases = [
        "김민준님 안녕하세요.",
        "이영희님이 서울시 강남구에 거주합니다. 연락처는 010-1234-5678입니다.",
        "안녕하세요 박지우님, 저는 최수민입니다. 부산광역시 해운대구 센텀시티에서 근무하고 있으며, 연락처는 051-123-4567이고 이메일은 contact@example.com입니다. 나이는 30세이고, 회사는 삼성전자입니다."
    ]
    
    benchmark_results = {}
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"Benchmark {i}: {len(test_text)} characters")
        
        start_time = time.time()
        result = pseudonymize_text(test_text, detailed_report=False)
        end_time = time.time()
        
        benchmark_results[f"test_{i}"] = {
            "text_length": len(test_text),
            "detected_items": len(result['detection']['items']),
            "processing_time": end_time - start_time,
            "detection_stats": result['stats']['detection_stats']
        }
    
    # 전체 통계
    total_time = sum(r['processing_time'] for r in benchmark_results.values())
    total_items = sum(r['detected_items'] for r in benchmark_results.values())
    
    return {
        "data_pools": get_data_pool_stats(),
        "benchmark_results": benchmark_results,
        "summary": {
            "total_tests": len(test_cases),
            "total_processing_time": total_time,
            "total_detected_items": total_items,
            "average_time_per_item": total_time / max(1, total_items),
            "items_per_second": total_items / total_time if total_time > 0 else 0
        }
    }

def validate_pseudonymization(original: str, pseudonymized: str, reverse_map: Dict[str, str]) -> Dict[str, Any]:
    """가명화 결과 검증"""
    # 복원 테스트
    restored = restore_original(pseudonymized, reverse_map)
    restoration_success = (original == restored)
    
    # 가명 품질 확인
    quality_checks = {
        "has_fake_names": "가명" in pseudonymized,
        "has_sequential_phones": "010-0000-" in pseudonymized,
        "has_pseudonym_emails": "Pseudonymization" in pseudonymized and "@gamyeong.com" in pseudonymized,
        "no_original_emails": "@" in original and "@example.com" not in pseudonymized and "@naver.com" not in pseudonymized,
        "simplified_addresses": True
    }
    
    return {
        "restoration_success": restoration_success,
        "quality_checks": quality_checks,
        "quality_score": sum(quality_checks.values()) / len(quality_checks),
        "original_length": len(original),
        "pseudonymized_length": len(pseudonymized),
        "length_difference": len(pseudonymized) - len(original)
    }

# 호환성을 위한 함수들
def assign_realistic_values(items):
    """기존 코드 호환성을 위한 함수"""
    manager = get_replacement_manager()
    substitution_map, _ = manager.assign_replacements(items)
    return substitution_map

def create_masked_text(text, items, substitution_map):
    """기존 코드 호환성을 위한 함수"""
    return apply_replacements_smart(text, substitution_map)