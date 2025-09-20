"""
로깅 유틸리티 모듈
JSON 형태의 로그를 파일에 저장하고 관리합니다.
"""
import json
import os
from typing import Dict, Any

def append_json_to_file(path: str, new_entry: Dict[str, Any]) -> None:
    """JSON 엔트리를 로그 파일에 추가"""
    # 파일 전체를 {"logs":[ ... ]}로 유지
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"logs": []}
    else:
        data = {"logs": []}
    
    if "logs" not in data or not isinstance(data["logs"], list):
        data["logs"] = []
    
    data["logs"].append(new_entry)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
