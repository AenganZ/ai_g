# utils/logging.py - JSON 형식 로깅 (가독성 개선)
import json
import os
from typing import Dict, Any, List

def append_json_to_file(path: str, new_entry: Dict[str, Any]) -> None:
    """JSON 엔트리를 파일에 추가 (가독성 좋은 JSON 형식)"""
    try:
        # 기존 파일 읽기
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {"logs": []}
        else:
            data = {"logs": []}
        
        # logs 배열 확인
        if "logs" not in data or not isinstance(data["logs"], list):
            data["logs"] = []
        
        # 새 엔트리 추가
        data["logs"].append(new_entry)
        
        # 로그 개수 제한 (최대 100개)
        if len(data["logs"]) > 100:
            data["logs"] = data["logs"][-100:]
        
        # 가독성 좋은 JSON으로 저장
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"📝 로그 저장됨: {path}")
        
    except Exception as e:
        print(f"❌ 로그 저장 실패: {e}")

def load_logs_from_file(path: str) -> Dict[str, List]:
    """JSON 파일에서 로그 로드"""
    try:
        if not os.path.exists(path):
            return {"logs": []}
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "logs" not in data:
            return {"logs": []}
        
        return data
        
    except Exception as e:
        print(f"❌ 로그 로드 실패: {e}")
        return {"logs": []}

def get_log_stats(path: str) -> Dict[str, Any]:
    """로그 통계 정보 반환"""
    try:
        logs_data = load_logs_from_file(path)
        logs = logs_data.get("logs", [])
        
        if not logs:
            return {
                "total_logs": 0,
                "pii_detections": 0,
                "success_rate": 0,
                "latest_log": None
            }
        
        # 통계 계산
        total_logs = len(logs)
        pii_detections = sum(1 for log in logs 
                           if log.get("detection", {}).get("contains_pii", False))
        success_rate = (pii_detections / total_logs * 100) if total_logs > 0 else 0
        latest_log = logs[-1] if logs else None
        
        return {
            "total_logs": total_logs,
            "pii_detections": pii_detections,
            "success_rate": round(success_rate, 2),
            "latest_log_time": latest_log.get("time") if latest_log else None,
            "file_size_kb": round(os.path.getsize(path) / 1024, 2) if os.path.exists(path) else 0
        }
        
    except Exception as e:
        print(f"❌ 로그 통계 계산 실패: {e}")
        return {
            "total_logs": 0,
            "pii_detections": 0,
            "success_rate": 0,
            "latest_log": None,
            "error": str(e)
        }

def clear_logs(path: str) -> bool:
    """로그 파일 초기화"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"logs": []}, f, ensure_ascii=False, indent=2)
        print(f"✅ 로그 파일 초기화: {path}")
        return True
    except Exception as e:
        print(f"❌ 로그 삭제 실패: {e}")
        return False

def backup_logs(path: str, backup_path: str = None) -> bool:
    """로그 파일 백업"""
    try:
        if not os.path.exists(path):
            print(f"⚠️ 백업할 로그 파일이 없습니다: {path}")
            return False
        
        if backup_path is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{path}.backup_{timestamp}"
        
        import shutil
        shutil.copy2(path, backup_path)
        
        print(f"✅ 로그 백업 완료: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ 로그 백업 실패: {e}")
        return False

# 호환성을 위한 기존 함수명
def append_log_entry(path: str, entry: Dict[str, Any]) -> None:
    """기존 이름 호환성"""
    append_json_to_file(path, entry)

def read_logs(path: str) -> Dict[str, List]:
    """기존 이름 호환성"""
    return load_logs_from_file(path)