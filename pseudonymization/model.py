# pseudonymization/model.py
"""
NER 모델 관리 모듈 - KPF/KPF-bert-ner 적용
"""

import time
from typing import List, Dict, Any, Optional

# NER 관련 라이브러리 (선택적)
try:
    import torch
    from transformers import (
        AutoModelForTokenClassification, 
        AutoTokenizer, 
        pipeline
    )
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False
    print("transformers 라이브러리가 설치되지 않았습니다")

# KPF BERT NER 모델
NER_MODELS = [
    "KPF/KPF-bert-ner",  # 메인 모델
    "monologg/koelectra-base-v3-naver-ner",  # 백업 모델
]

class WorkingNERModel:
    """KPF BERT NER 모델 클래스"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = self._get_device()
        self.loaded = False
        self.model_name = None
        self.id2label = None
    
    def _get_device(self):
        """최적의 디바이스 선택"""
        if not NER_AVAILABLE:
            return -1
            
        if torch.cuda.is_available():
            return 0  # GPU
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return -1  # CPU
    
    def is_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        return self.loaded
    
    def load_model(self) -> bool:
        """KPF BERT NER 모델 로드"""
        if not NER_AVAILABLE:
            print("NER 모델을 로드할 수 없습니다 - transformers 라이브러리가 필요합니다")
            return False
        
        for model_name in NER_MODELS:
            try:
                print(f"NER 모델 로딩 중: {model_name}")
                
                # 토크나이저와 모델 로드
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForTokenClassification.from_pretrained(model_name)
                self.model_name = model_name
                
                # 라벨 매핑 저장
                self.id2label = self.model.config.id2label
                print(f"라벨 매핑: {list(self.id2label.values())[:10]}...")
                
                # 파이프라인 생성
                self.pipeline = pipeline(
                    "ner", 
                    model=self.model, 
                    tokenizer=self.tokenizer,
                    aggregation_strategy="simple",
                    device=self.device
                )
                
                # 디바이스 설정 출력
                if self.device == 0:
                    print("장치 설정: GPU 사용")
                elif self.device == "mps":
                    print("장치 설정: Apple Silicon 사용")
                else:
                    print("장치 설정: CPU 사용")
                
                # 테스트
                test_text = "김철수는 서울 강남구에 살고 있습니다."
                test_result = self.pipeline(test_text)
                print(f"모델 테스트 성공: {len(test_result)}개 엔티티 탐지")
                
                self.loaded = True
                print(f"NER 모델 로드 성공: {model_name}")
                return True
                
            except Exception as e:
                print(f"모델 {model_name} 로드 실패: {e}")
                continue
        
        print("모든 NER 모델 로드 실패")
        return False
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """텍스트에서 엔티티 추출"""
        if not self.loaded or not self.pipeline:
            return []
        
        try:
            # NER 실행
            start_time = time.time()
            raw_entities = self.pipeline(text)
            processing_time = time.time() - start_time
            
            # 결과 정규화
            entities = []
            for entity in raw_entities:
                # KPF 모델 결과 형식에 맞게 조정
                entity_type = self._map_kpf_label(entity.get('entity_group', entity.get('label', 'MISC')))
                
                if entity_type and entity.get('score', 0) > 0.7:  # 신뢰도 임계값
                    entities.append({
                        'type': entity_type,
                        'label': entity_type,
                        'text': entity['word'],
                        'value': entity['word'],
                        'start': entity['start'],
                        'end': entity['end'],
                        'confidence': entity['score'],
                        'model': self.model_name
                    })
            
            print(f"NER 처리 완료: {len(entities)}개 엔티티 ({processing_time:.3f}초)")
            return entities
            
        except Exception as e:
            print(f"NER 처리 오류: {e}")
            return []
    
    def _map_kpf_label(self, label: str) -> Optional[str]:
        """KPF 모델 라벨을 PII 타입으로 매핑"""
        
        # KPF 모델의 라벨 매핑
        label_mapping = {
            'PER': '이름',
            'PERSON': '이름', 
            'PS': '이름',
            'LOC': '주소',
            'LOCATION': '주소',
            'LC': '주소',
            'ORG': '조직',
            'ORGANIZATION': '조직',
            'OG': '조직',
            'MISC': '기타',
            'MT': '기타',
            'DT': '날짜',
            'DATE': '날짜',
            'TI': '시간',
            'TIME': '시간',
            'QT': '수량',
            'QUANTITY': '수량'
        }
        
        # B-, I- 접두사 제거
        clean_label = label.replace('B-', '').replace('I-', '').upper()
        return label_mapping.get(clean_label, None)

# 전역 모델 인스턴스
_ner_model_instance = None

def get_ner_model() -> WorkingNERModel:
    """NER 모델 싱글톤 인스턴스 반환"""
    global _ner_model_instance
    
    if _ner_model_instance is None:
        _ner_model_instance = WorkingNERModel()
    
    return _ner_model_instance

def load_ner_model() -> bool:
    """NER 모델 로드"""
    model = get_ner_model()
    return model.load_model()

def extract_entities_with_ner(text: str) -> List[Dict[str, Any]]:
    """NER 모델을 사용한 개체명 추출"""
    model = get_ner_model()
    
    if not model.is_loaded():
        # 모델이 로드되지 않았으면 로드 시도
        if not model.load_model():
            print("NER 모델을 로드할 수 없습니다")
            return []
    
    return model.extract_entities(text)

def is_ner_available() -> bool:
    """NER 기능 사용 가능 여부 확인"""
    return NER_AVAILABLE

def is_ner_loaded() -> bool:
    """NER 모델 로드 상태 확인"""
    model = get_ner_model()
    return model.is_loaded()

# 호환성 함수들
def call_qwen_detect_pii(original_prompt: str, model=None, tokenizer=None, device=None) -> Dict[str, Any]:
    """기존 호환을 위한 함수"""
    entities = extract_entities_with_ner(original_prompt)
    return {
        "items": entities,
        "contains_pii": len(entities) > 0
    }

def pick_device_and_dtype():
    """디바이스 및 데이터 타입 선택"""
    if not NER_AVAILABLE:
        return "cpu", None
        
    model = get_ner_model()
    device = model.device
    
    if device == 0:  # GPU
        return "cuda", torch.float16
    elif device == "mps":  # Apple Silicon
        return "mps", torch.float16
    else:  # CPU
        return "cpu", torch.float32

def load_model():
    """모델 로드 (호환성)"""
    return load_ner_model()