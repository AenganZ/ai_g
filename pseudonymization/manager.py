# pseudonymization/manager.py
"""
가명화 매니저 모듈 - 깔끔한 버전
NER 간소화 + Regex 중심 + 명확한 가명화
"""

import time
import threading
from typing import Dict, Any, Optional, List
from .core import pseudonymize_text, load_data_pools, get_data_pool_stats
from .pools import reload_pools
from .replacement import ReplacementManager

class PseudonymizationManager:
    """최적화된 가명화 관리자"""
    
    def __init__(self):
        self.initialized = False
        self.data_pools_loaded = False
        self.replacement_manager = None
        self.start_time = time.time()
        
        # NER 관련
        self.ner_model_loading = False
        self.ner_enabled = False
        self.auto_load_ner = True
        
        # 통계
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_pii_detected": 0,
            "processing_times": [],
            "ner_mode_requests": 0,
            "avg_detection_time": 0,
            "avg_replacement_time": 0
        }
    
    def initialize(self, auto_load_ner: bool = True, custom_data: Dict = None) -> bool:
        """매니저 초기화"""
        if self.initialized:
            print("PseudonymizationManager already initialized")
            return True
        
        print("Initializing PseudonymizationManager...")
        
        try:
            # 데이터풀 초기화
            print("Loading data pools...")
            load_data_pools(custom_data)
            self.data_pools_loaded = True
            print("Data pools loaded successfully")
            
            # 통계 출력
            stats = get_data_pool_stats()
            print(f"Detection names: {stats['detection_names']:,}")
            print(f"Detection roads: {stats['detection_roads']:,}")
            print(f"Detection districts: {stats['detection_districts']:,}")
            
            # ReplacementManager 초기화
            self.replacement_manager = ReplacementManager()
            print("ReplacementManager initialized")
            
            # NER 모델 로드
            self.auto_load_ner = auto_load_ner
            if auto_load_ner:
                print("NER simplified mode enabled")
                try:
                    self._start_ner_model_loading()
                except Exception as e:
                    print(f"NER model loading skipped: {e}")
            else:
                print("Regex-only mode")
            
            self.initialized = True
            init_time = time.time() - self.start_time
            print(f"PseudonymizationManager initialized successfully ({init_time:.3f}s)")
            return True
            
        except Exception as e:
            print(f"Manager initialization failed: {e}")
            self.initialized = False
            return False
    
    def _start_ner_model_loading(self):
        """NER 모델 백그라운드 로딩 시작"""
        try:
            from .model import is_ner_loaded
            
            if not self.ner_model_loading and not is_ner_loaded():
                self.ner_model_loading = True
                threading.Thread(
                    target=self._load_ner_model_background,
                    daemon=True,
                    name="NER-Simple-Loader"
                ).start()
                print("NER model background loading started...")
        except Exception as e:
            print(f"NER model loading skipped: {e}")
            self.ner_model_loading = False
    
    def _load_ner_model_background(self):
        """백그라운드에서 NER 모델 로드"""
        try:
            from .model import load_ner_model
            start_time = time.time()
            success = load_ner_model()
            
            elapsed = time.time() - start_time
            
            if success:
                self.ner_enabled = True
                print(f"NER model loaded successfully ({elapsed:.1f}s)")
            else:
                print(f"NER model loading failed ({elapsed:.1f}s)")
            
        except Exception as e:
            print(f"NER model background loading failed: {e}")
        finally:
            self.ner_model_loading = False
    
    def pseudonymize(self, text: str, log_id: str = None, detailed_report: bool = True) -> Dict[str, Any]:
        """텍스트 가명화"""
        if not self.initialized:
            raise RuntimeError("PseudonymizationManager not initialized")
        
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        print(f"Pseudonymization request: {time.strftime('%H:%M:%S')}")
        if log_id:
            print(f"ID: {log_id}")
        print(f"Original text: {text}")
        
        try:
            # 가명화 실행
            result = pseudonymize_text(text, detailed_report=detailed_report)
            
            # 통계 업데이트
            processing_time = time.time() - start_time
            self.stats["successful_requests"] += 1
            self.stats["total_pii_detected"] += len(result['detection']['items'])
            self.stats["processing_times"].append(processing_time)
            
            if self.ner_enabled:
                self.stats["ner_mode_requests"] += 1
            
            # 세부 시간 통계
            if 'detection_time' in result['stats']:
                if self.stats["avg_detection_time"] == 0:
                    self.stats["avg_detection_time"] = result['stats']['detection_time']
                else:
                    self.stats["avg_detection_time"] = (self.stats["avg_detection_time"] + result['stats']['detection_time']) / 2
            
            if 'replacement_time' in result['stats']:
                if self.stats["avg_replacement_time"] == 0:
                    self.stats["avg_replacement_time"] = result['stats']['replacement_time']
                else:
                    self.stats["avg_replacement_time"] = (self.stats["avg_replacement_time"] + result['stats']['replacement_time']) / 2
            
            print(f"Pseudonymization completed ({len(result['detection']['items'])} items detected)")
            
            # 로그 저장
            if log_id:
                self._save_log(log_id, text, result)
            
            return result
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            print(f"Pseudonymization failed: {e}")
            raise
    
    def _save_log(self, log_id: str, original_text: str, result: Dict[str, Any]):
        """로그 저장"""
        try:
            import json
            log_entry = {
                "id": log_id,
                "timestamp": time.time(),
                "original_length": len(original_text),
                "detected_items": len(result['detection']['items']),
                "processing_time": result['processing_time'],
                "items_by_type": result['stats']['items_by_type'],
                "detection_stats": result['stats']['detection_stats'],
                "ner_enabled": self.ner_enabled
            }
            
            with open("pseudo-log.json", "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            print("Log saved to pseudo-log.json")
            
        except Exception as e:
            print(f"Log saving failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """매니저 상태 조회"""
        uptime = time.time() - self.start_time
        
        avg_processing_time = None
        if self.stats["processing_times"]:
            avg_processing_time = sum(self.stats["processing_times"]) / len(self.stats["processing_times"])
        
        # NER 모델 상태 확인
        ner_loaded = False
        try:
            from .model import is_ner_loaded
            ner_loaded = is_ner_loaded()
        except:
            pass
        
        # 모드 결정
        if self.ner_enabled and ner_loaded:
            mode = "NER simplified + Regex"
        else:
            mode = "Regex only"
        
        return {
            "initialized": self.initialized,
            "uptime": uptime,
            "mode": mode,
            "data_pools": {
                "loaded": self.data_pools_loaded,
                "stats": get_data_pool_stats() if self.data_pools_loaded else {}
            },
            "ner_model": {
                "enabled": self.ner_enabled,
                "loaded": ner_loaded,
                "loading": self.ner_model_loading,
                "auto_load": self.auto_load_ner
            },
            "statistics": {
                "total_requests": self.stats["total_requests"],
                "successful_requests": self.stats["successful_requests"],
                "failed_requests": self.stats["failed_requests"],
                "success_rate": f"{(self.stats['successful_requests'] / max(1, self.stats['total_requests']) * 100):.1f}%",
                "total_pii_detected": self.stats["total_pii_detected"],
                "avg_processing_time": f"{avg_processing_time:.3f}s" if avg_processing_time else None,
                "avg_detection_time": f"{self.stats['avg_detection_time']:.3f}s" if self.stats['avg_detection_time'] else None,
                "avg_replacement_time": f"{self.stats['avg_replacement_time']:.3f}s" if self.stats['avg_replacement_time'] else None,
                "ner_mode_requests": self.stats["ner_mode_requests"]
            }
        }
    
    def force_load_ner_model(self) -> bool:
        """NER 모델 강제 로드"""
        if self.ner_model_loading:
            print("NER model is already loading")
            return False
        
        try:
            from .model import is_ner_loaded, load_ner_model
            
            if is_ner_loaded():
                self.ner_enabled = True
                print("NER model is already loaded")
                return True
            
            print("Force loading NER model...")
            success = load_ner_model()
            
            if success:
                self.ner_enabled = True
                print("NER model force loaded successfully")
            else:
                print("NER model force loading failed")
            
            return success
            
        except Exception as e:
            print(f"NER model loading failed: {e}")
            return False
    
    def disable_ner(self):
        """NER 모델 비활성화"""
        self.ner_enabled = False
        print("Switched to Regex-only mode")
    
    def reload_data_pools(self):
        """데이터풀 재로드"""
        print("Reloading data pools...")
        
        try:
            reload_pools()
            self.data_pools_loaded = True
            self.replacement_manager = ReplacementManager()
            print("Data pools reloaded successfully")
        except Exception as e:
            print(f"Data pools reloading failed: {e}")
            self.data_pools_loaded = False
            raise
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        from .core import get_performance_benchmark
        
        # 기본 벤치마크
        benchmark = get_performance_benchmark()
        
        # 매니저 통계 추가
        status = self.get_status()
        
        return {
            "manager_status": status,
            "benchmark": benchmark,
            "recommendations": self._get_performance_recommendations(status, benchmark)
        }
    
    def _get_performance_recommendations(self, status: Dict, benchmark: Dict) -> List[str]:
        """성능 최적화 권장사항"""
        recommendations = []
        
        # 처리 시간 기반 권장사항
        avg_time = status['statistics']['avg_processing_time']
        if avg_time and float(avg_time.replace('s', '')) > 1.0:
            recommendations.append("Processing time exceeds 1 second. Consider reducing text length or batch processing.")
        
        # NER 상태 기반 권장사항
        if not status['ner_model']['loaded']:
            recommendations.append("NER model not loaded. Use force_load_ner_model() to improve detection accuracy.")
        
        # 성공률 기반 권장사항
        success_rate = float(status['statistics']['success_rate'].replace('%', ''))
        if success_rate < 95:
            recommendations.append(f"Success rate is {success_rate}%. Check input text format.")
        
        # 기본 권장사항
        if not recommendations:
            recommendations.append("System is operating optimally.")
        
        return recommendations
    
    def reset_stats(self):
        """통계 초기화"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_pii_detected": 0,
            "processing_times": [],
            "ner_mode_requests": 0,
            "avg_detection_time": 0,
            "avg_replacement_time": 0
        }
        print("Statistics reset successfully")

# 글로벌 인스턴스
_global_manager = None

def get_manager() -> PseudonymizationManager:
    """매니저 싱글톤 인스턴스"""
    global _global_manager
    if _global_manager is None:
        _global_manager = PseudonymizationManager()
        _global_manager.initialize(auto_load_ner=True)
    return _global_manager

def is_manager_ready() -> bool:
    """매니저 준비 상태 확인"""
    manager = get_manager()
    return manager.initialized

def get_manager_status() -> Dict[str, Any]:
    """매니저 상태 조회"""
    manager = get_manager()
    return manager.get_status()

def pseudonymize_with_manager(text: str, log_id: str = None, detailed_report: bool = True) -> Dict[str, Any]:
    """매니저를 통한 가명화"""
    manager = get_manager()
    return manager.pseudonymize(text, log_id=log_id, detailed_report=detailed_report)

def force_load_ner() -> bool:
    """NER 모델 강제 로드"""
    manager = get_manager()
    return manager.force_load_ner_model()

def disable_ner_mode():
    """NER 모드 비활성화"""
    manager = get_manager()
    manager.disable_ner()

def get_performance_report() -> Dict[str, Any]:
    """성능 리포트 조회"""
    manager = get_manager()
    return manager.get_performance_report()