# utils/logging.py - TXT 형식 로깅 (원본 호환)
import json
import os
from typing import Dict, Any, List

def append_json_to_file(path: str, new_entry: Dict[str, Any]) -> None:
    """JSON 엔트리를 TXT 파일에 한 줄씩 추가 (원본 시스템 호환)"""
    try:
        # JSON을 한 줄 문자열로 변환
        log_line = json.dumps(new_entry, ensure_ascii=False, separators=(',', ':')) + "\n"
        
        # 파일에 한 줄씩 추가
        with open(path, "a", encoding="utf-8") as f:
            f.write(log_line)
        
        # 로그 개수 제한 (선택적)
        limit_log_lines(path, max_lines=1000)
        
    except Exception as e:
        print(f"❌ 로그 저장 실패: {e}")

def limit_log_lines(path: str, max_lines: int = 1000) -> None:
    """로그 라인 수 제한"""
    try:
        if not os.path.exists(path):
            return
        
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if len(lines) > max_lines:
            # 최신 로그만 유지
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines[-max_lines:])
            print(f"📝 로그 파일 정리: {len(lines)} → {max_lines} 라인")
            
    except Exception as e:
        print(f"⚠️ 로그 정리 실패: {e}")

def load_logs_from_file(path: str) -> Dict[str, List]:
    """TXT 파일에서 로그 로드 (원본 호환)"""
    try:
        if not os.path.exists(path):
            return {"logs": []}
        
        logs = []
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        log_entry = json.loads(line)
                        logs.append(log_entry)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ 로그 파싱 오류 (라인 {line_num}): {e}")
                        continue
        
        return {"logs": logs}
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
    """로그 파일 삭제"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")  # 빈 파일로 초기화
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