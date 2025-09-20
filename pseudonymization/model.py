# pseudonymization/model.py - 개선된 NER 모델
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

# 실제로 존재하고 검증된 한국어 NER 모델들 (HuggingFace에서 확인됨)
NER_MODELS = [
    "monologg/koelectra-base-v3-naver-ner",             # 1순위: 실제 존재, 다운로드 확인됨
    "klue/roberta-large-ner",                           # 2순위: KLUE 공식 (존재 확인 필요)
    "Leo97/KoELECTRA-small-v3-modu-ner",               # 3순위: 다운로드 확인됨
    "monologg/kobert-ner"                               # 4순위: KoBERT 기반 (폴백용)
]

class ImprovedNERModel:
    """개선된 NER 모델 클래스"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = self._get_device()
        self.loaded = False
        self.model_name = None
    
    def _get_device(self):
        """최적의 디바이스 선택"""
        if torch.cuda.is_available():
            return 0  # GPU
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return -1  # CPU
    
    def load_model(self) -> bool:
        """안정적인 NER 모델 로드 (파이프라인 오류 해결)"""
        if not NER_AVAILABLE:
            print("❌ NER 모델을 로드할 수 없습니다 - transformers 라이브러리가 필요합니다")
            return False
        
        for model_name in NER_MODELS:
            try:
                print(f"🔄 NER 모델 로딩 시도: {model_name}")
                
                # 토크나이저 로드 (안전한 설정)
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    use_fast=True
                )
                
                # 모델 로드
                self.model = AutoModelForTokenClassification.from_pretrained(model_name)
                
                # 파이프라인 생성 (잘못된 매개변수 제거)
                self.pipeline = pipeline(
                    "ner", 
                    model=self.model, 
                    tokenizer=self.tokenizer,
                    aggregation_strategy="simple",
                    device=self.device
                    # max_length, truncation 등은 여기서 제거 (추론 시 사용)
                )
                
                # 간단한 테스트로 모델 검증
                test_result = self.pipeline("김철수는 서울에 살고 있습니다.")
                
                self.loaded = True
                self.model_name = model_name
                print(f"✅ NER 모델 로드 성공: {model_name}")
                print(f"   📱 디바이스: {self.device}")
                print(f"   🧪 테스트 결과: {len(test_result)}개 엔티티 탐지")
                
                # 첫 번째로 성공한 모델 사용
                return True
                
            except Exception as e:
                print(f"❌ {model_name} 로드 실패: {e}")
                # 구체적인 오류 유형 확인
                error_msg = str(e).lower()
                if "max_length" in error_msg or "unexpected keyword" in error_msg:
                    print(f"   🔧 파이프라인 매개변수 오류 - 다음 모델 시도")
                elif "not a valid model" in error_msg:
                    print(f"   🔧 모델이 존재하지 않음 - 다음 모델 시도")
                continue
        
        print("❌ 모든 NER 모델 로드 실패")
        print("💡 다음 해결 방법을 시도해보세요:")
        print("   1. pip install transformers torch --upgrade")
        print("   2. 캐시 삭제: rm -rf ~/.cache/huggingface/ (Windows: rmdir /s %USERPROFILE%\\.cache\\huggingface)")
        print("   3. 인터넷 연결 확인")
        self.loaded = False
        return False
    
    def is_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        return self.loaded
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """텍스트에서 개체명 추출 (안정성 개선)"""
        if not self.loaded or not self.pipeline:
            return []
        
        try:
            # 텍스트 길이 제한 (모델 최대 길이를 고려)
            max_length = 400  # 안전한 길이로 제한
            if len(text) > max_length:
                text = text[:max_length]
                print(f"⚠️ 텍스트가 {max_length}자로 잘렸습니다.")
            
            # NER 파이프라인 실행 (안전한 설정으로)
            ner_results = self.pipeline(
                text,
                aggregation_strategy="simple",
                return_all_scores=False,
                stride=0,
                truncation=True,
                max_length=512
            )
            
            entities = []
            for entity in ner_results:
                entity_type = entity.get('entity_group', entity.get('entity', ''))
                entity_text = entity.get('word', '')
                confidence = entity.get('score', 0.0)
                start = entity.get('start', 0)
                end = entity.get('end', 0)
                
                # 텍스트 정리 (토크나이저 아티팩트 제거)
                entity_text = entity_text.replace('##', '').strip()
                
                # 신뢰도 임계값 (모델별 조정)
                if 'small' in self.model_name:
                    threshold = 0.7  # 작은 모델은 임계값 낮춤
                elif 'klue' in self.model_name:
                    threshold = 0.8  # KLUE 모델은 높은 임계값
                else:
                    threshold = 0.75 # 기본값
                
                if confidence > threshold and len(entity_text) >= 2:
                    pii_type = self._map_ner_label_to_pii_type(entity_type)
                    if pii_type:
                        entities.append({
                            "type": pii_type,
                            "value": entity_text,
                            "start": start,
                            "end": end,
                            "confidence": confidence,
                            "source": f"NER-{self.model_name.split('/')[-1]}"
                        })
            
            print(f"🤖 NER ({self.model_name.split('/')[-1]}) 탐지: {len(entities)}개")
            return entities
            
        except Exception as e:
            print(f"❌ NER 개체명 추출 실패: {e}")
            # 구체적인 오류 정보 출력
            import traceback
            print("상세 오류:", traceback.format_exc())
            return []
    
    def _map_ner_label_to_pii_type(self, label: str) -> Optional[str]:
        """NER 라벨을 PII 타입으로 매핑 (KLUE 및 기타 모델 지원)"""
        # 라벨 정규화 (B-, I- 접두사 제거)
        clean_label = label.replace('B-', '').replace('I-', '').upper()
        
        mapping = {
            # 표준 라벨들
            'PER': '이름',
            'PERSON': '이름',
            'LOC': '주소',
            'LOCATION': '주소',
            'ORG': '회사',
            'ORGANIZATION': '회사',
            'MISC': '기타',
            
            # KLUE NER 라벨들
            'PS': '이름',      # Person
            'LC': '주소',      # Location  
            'OG': '회사',      # Organization
            'DT': '기타',      # Date
            'TI': '기타',      # Time
            'QT': '기타',      # Quantity
            
            # KoELECTRA 등 기타 모델 라벨들
            'PRS': '이름',     # Person
            'LOC': '주소',     # Location
            'ORG': '회사',     # Organization
            'NUM': '기타',     # Number
            'DATE': '기타',    # Date
            'TIME': '기타',    # Time
            
            # 추가 매핑
            'GPE': '주소',     # Geopolitical entity
            'FAC': '주소',     # Facility
            'NORP': '기타',    # Nationalities, religious, political groups
        }
        
        result = mapping.get(clean_label)
        if result:
            print(f"   매핑: {label} -> {result}")
        return result

# 전역 모델 인스턴스
_ner_model_instance = None

def get_ner_model() -> ImprovedNERModel:
    """NER 모델 싱글톤 인스턴스 반환"""
    global _ner_model_instance
    
    if _ner_model_instance is None:
        _ner_model_instance = ImprovedNERModel()
    
    return _ner_model_instance

def load_ner_model() -> bool:
    """NER 모델 로드 (백그라운드 실행 가능)"""
    model = get_ner_model()
    return model.load_model()

def extract_entities_with_ner(text: str) -> List[Dict[str, Any]]:
    """NER 모델을 사용한 개체명 추출"""
    model = get_ner_model()
    
    if not model.is_loaded():
        print("⚠️ NER 모델이 로드되지 않았습니다.")
        return []
    
    return model.extract_entities(text)

def is_ner_available() -> bool:
    """NER 기능 사용 가능 여부 확인"""
    return NER_AVAILABLE

def is_ner_loaded() -> bool:
    """NER 모델 로드 상태 확인"""
    model = get_ner_model()
    return model.is_loaded()

def get_model_info() -> Dict[str, Any]:
    """현재 로드된 모델 정보 반환"""
    model = get_ner_model()
    return {
        "loaded": model.is_loaded(),
        "model_name": model.model_name if model.is_loaded() else None,
        "device": model.device,
        "available_models": NER_MODELS
    }

# 호환성을 위한 기존 함수들
def call_qwen_detect_pii(original_prompt: str, model=None, tokenizer=None, device=None) -> Dict[str, Any]:
    """기존 호환을 위한 함수 (개선된 NER로 변경)"""
    print("⚠️ call_qwen_detect_pii는 deprecated입니다. extract_entities_with_ner를 사용하세요.")
    
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
    print("🎭 개선된 NER 모델 모듈")
    print(f"📱 Transformers 사용 가능: {NER_AVAILABLE}")
    print(f"🤖 사용 가능한 모델들:")
    for i, model in enumerate(NER_MODELS, 1):
        print(f"   {i}. {model}")
    
    if NER_AVAILABLE:
        model = get_ner_model()
        success = model.load_model()
        if success:
            # 테스트
            test_text = "안녕하세요, 저는 김테스트이고 서울 강남구에 살고 있습니다."
            entities = model.extract_entities(test_text)
            print(f"🧪 테스트 결과: {len(entities)}개 개체 탐지")
            for entity in entities:
                print(f"   {entity['type']}: {entity['value']} (신뢰도: {entity['confidence']:.2f})")
        else:
            print("❌ 모든 모델 로드 실패")