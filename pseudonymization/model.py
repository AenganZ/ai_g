# pseudonymization/model.py - AenganZ NER 모델 (모듈화 버전)
import os
import torch
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# NER 모델 관련 import
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False
    print("⚠️ Transformers 라이브러리가 없습니다. pip install transformers torch를 실행하세요.")

# AenganZ에서 사용하는 NER 모델 설정
AENGANZ_NER_MODEL = "monologg/koelectra-base-v3-naver-ner"

class AenganZNERModel:
    """AenganZ 방식의 NER 모델 클래스"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = self._get_device()
        self.loaded = False
    
    def _get_device(self):
        """최적의 디바이스 선택"""
        if torch.cuda.is_available():
            return 0  # GPU
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return -1  # CPU
    
    def load_model(self) -> bool:
        """AenganZ 방식의 NER 모델 로드"""
        if not NER_AVAILABLE:
            print("❌ NER 모델을 로드할 수 없습니다 - transformers 라이브러리가 필요합니다")
            return False
        
        try:
            print(f"🔄 NER 모델 로딩 중... ({AENGANZ_NER_MODEL})")
            
            # 토크나이저와 모델 로드
            self.tokenizer = AutoTokenizer.from_pretrained(AENGANZ_NER_MODEL)
            self.model = AutoModelForTokenClassification.from_pretrained(AENGANZ_NER_MODEL)
            
            # 파이프라인 생성
            self.pipeline = pipeline(
                "ner", 
                model=self.model, 
                tokenizer=self.tokenizer,
                aggregation_strategy="simple",
                device=self.device
            )
            
            self.loaded = True
            print("✅ AenganZ NER 모델 로드 완료!")
            print(f"   📱 디바이스: {self.device}")
            print(f"   🤖 모델: {AENGANZ_NER_MODEL}")
            return True
            
        except Exception as e:
            print(f"❌ NER 모델 로드 실패: {e}")
            print("💡 해결 방법:")
            print("   1. 인터넷 연결 확인")
            print("   2. pip install transformers torch")
            print("   3. Hugging Face 모델 다운로드 재시도")
            self.loaded = False
            return False
    
    def is_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        return self.loaded
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """텍스트에서 개체명 추출 (AenganZ 방식)"""
        if not self.loaded or not self.pipeline:
            return []
        
        try:
            # NER 파이프라인 실행
            ner_results = self.pipeline(text)
            
            entities = []
            for entity in ner_results:
                entity_type = entity['entity_group']
                entity_text = entity['word']
                confidence = entity['score']
                start = entity['start']
                end = entity['end']
                
                # 신뢰도 임계값 (AenganZ 기준)
                if confidence > 0.7:
                    pii_type = self._map_ner_label_to_pii_type(entity_type)
                    if pii_type:
                        entities.append({
                            "type": pii_type,
                            "value": entity_text,
                            "start": start,
                            "end": end,
                            "confidence": confidence,
                            "source": "NER"
                        })
            
            return entities
            
        except Exception as e:
            print(f"❌ NER 개체명 추출 실패: {e}")
            return []
    
    def _map_ner_label_to_pii_type(self, label: str) -> Optional[str]:
        """NER 라벨을 PII 타입으로 매핑 (AenganZ 방식)"""
        mapping = {
            'PER': '이름',
            'PERSON': '이름',
            'LOC': '주소',
            'LOCATION': '주소',
            'ORG': '회사',
            'ORGANIZATION': '회사'
        }
        return mapping.get(label)

# 전역 모델 인스턴스
_ner_model_instance = None

def get_ner_model() -> AenganZNERModel:
    """NER 모델 싱글톤 인스턴스 반환"""
    global _ner_model_instance
    
    if _ner_model_instance is None:
        _ner_model_instance = AenganZNERModel()
    
    return _ner_model_instance

def load_ner_model() -> bool:
    """NER 모델 로드 (백그라운드 실행 가능)"""
    model = get_ner_model()
    return model.load_model()

def extract_entities_with_ner(text: str) -> List[Dict[str, Any]]:
    """NER 모델을 사용한 개체명 추출"""
    model = get_ner_model()
    
    if not model.is_loaded():
        print("⚠️ NER 모델이 로드되지 않았습니다. 먼저 load_ner_model()을 호출하세요.")
        return []
    
    return model.extract_entities(text)

def is_ner_available() -> bool:
    """NER 기능 사용 가능 여부 확인"""
    return NER_AVAILABLE

def is_ner_loaded() -> bool:
    """NER 모델 로드 상태 확인"""
    model = get_ner_model()
    return model.is_loaded()

# 호환성을 위한 기존 함수들
def call_qwen_detect_pii(original_prompt: str, model=None, tokenizer=None, device=None) -> Dict[str, Any]:
    """기존 Qwen 방식 호환을 위한 함수 (AenganZ NER로 변경)"""
    print("⚠️ call_qwen_detect_pii는 deprecated입니다. extract_entities_with_ner를 사용하세요.")
    
    # AenganZ NER 모델 사용
    entities = extract_entities_with_ner(original_prompt)
    
    return {
        "items": entities,
        "contains_pii": len(entities) > 0
    }

def pick_device_and_dtype():
    """디바이스 및 데이터 타입 선택 (호환성)"""
    model = get_ner_model()
    device = model.device
    
    if device == 0:  # GPU
        return "cuda", torch.bfloat16
    elif device == "mps":  # Apple Silicon
        return "mps", torch.float16
    else:  # CPU
        return "cpu", torch.float32

def load_model():
    """모델 로드 (호환성)"""
    return load_ner_model()

# 모듈 초기화 시 정보 출력
if __name__ == "__main__":
    print("🎭 AenganZ NER 모델 모듈")
    print(f"📱 Transformers 사용 가능: {NER_AVAILABLE}")
    print(f"🤖 모델: {AENGANZ_NER_MODEL}")
    
    if NER_AVAILABLE:
        model = get_ner_model()
        success = model.load_model()
        if success:
            # 테스트
            test_text = "안녕하세요, 저는 김테스트입니다."
            entities = model.extract_entities(test_text)
            print(f"🧪 테스트 결과: {len(entities)}개 개체 탐지")
            for entity in entities:
                print(f"   {entity['type']}: {entity['value']} (신뢰도: {entity['confidence']:.2f})")
        else:
            print("❌ 모델 로드 실패")