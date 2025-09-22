# utils/logging.py - 로깅 유틸리티 모듈
"""
로깅 관련 공통 함수들
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional

def append_json_to_file(path: str, new_entry: Dict[str, Any]) -> None:
    """JSON 엔트리를 로그 파일에 추가"""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"logs": []}
    except:
        data = {"logs": []}
    
    if "logs" not in data or not isinstance(data["logs"], list):
        data["logs"] = []
    
    data["logs"].append(new_entry)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_logs_from_file(path: str) -> Dict[str, List]:
    """로그 파일에서 데이터 로드"""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"logs": []}
    except Exception as e:
        print(f"로그 로드 실패: {e}")
        return {"logs": []}

def get_log_stats(path: str) -> Dict[str, Any]:
    """로그 파일 통계 정보"""
    data = load_logs_from_file(path)
    logs = data.get("logs", [])
    
    if not logs:
        return {
            "total_logs": 0,
            "file_size": 0,
            "latest_log": None,
            "oldest_log": None
        }
    
    file_size = os.path.getsize(path) if os.path.exists(path) else 0
    
    return {
        "total_logs": len(logs),
        "file_size": file_size,
        "latest_log": logs[-1].get("time") if logs else None,
        "oldest_log": logs[0].get("time") if logs else None
    }

def clear_logs(path: str) -> bool:
    """로그 파일 초기화"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"logs": []}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"로그 초기화 실패: {e}")
        return False

def backup_logs(path: str, backup_dir: str = "backups") -> Optional[str]:
    """로그 파일 백업"""
    try:
        if not os.path.exists(path):
            return None
        
        # 백업 디렉토리 생성
        os.makedirs(backup_dir, exist_ok=True)
        
        # 백업 파일명 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        backup_filename = f"{name}_{timestamp}{ext}"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # 파일 복사
        shutil.copy2(path, backup_path)
        
        print(f"로그 백업 완료: {backup_path}")
        return backup_path
        
    except Exception as e:
        print(f"로그 백업 실패: {e}")
        return None

# 호환성 함수들
def append_log_entry(path: str, entry: Dict[str, Any]) -> None:
    """로그 엔트리 추가 (호환성)"""
    append_json_to_file(path, entry)

def read_logs(path: str) -> Dict[str, List]:
    """로그 읽기 (호환성)"""
    return load_logs_from_file(path)