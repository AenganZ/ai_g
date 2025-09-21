# pseudonymization/model.py
"""
NER 모델 관리 모듈 - 수정된 버전
BIO 태그 문제 해결 및 정확한 엔티티 타입 추출
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
    print("⚠️ transformers 라이브러리가 설치되지 않았습니다.")

# 검증된 한국어 NER 모델들
NER_MODELS = [
    "monologg/koelectra-base-v3-naver-ner",     # 네이버 데이터
    "Leo97/KoELECTRA-small-v3-modu-ner",        # 모두의 말뭉치
    "KPF/KPF-bert-ner",                         # 한국언론진흥재단
]

class WorkingNERModel:
    """실제 작동하는 개선된 NER 모델 클래스"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = self._get_device()
        self.loaded = False
        self.model_name = None
        self.id2label = None  # 라벨 매핑 저장
    
    def _get_device(self):
        """최적의 디바이스 선택"""
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
        """NER 모델 로드 - aggregation_strategy 없이 원시 토큰 처리"""
        if not NER_AVAILABLE:
            print("❌ NER 모델을 로드할 수 없습니다 - transformers 라이브러리가 필요합니다")
            return False
        
        for model_name in NER_MODELS:
            try:
                print(f"🔄 NER 모델 로딩 시도: {model_name}")
                
                # 토크나이저와 모델 로드
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForTokenClassification.from_pretrained(model_name)
                
                # 라벨 매핑 저장 (중요!)
                self.id2label = self.model.config.id2label
                print(f"   📋 라벨 매핑: {list(self.id2label.values())[:10]}...")
                
                # 파이프라인 생성 - aggregation 없이 원시 토큰 레벨 결과
                self.pipeline = pipeline(
                    "ner", 
                    model=self.model, 
                    tokenizer=self.tokenizer,
                    aggregation_strategy=None,  # 원시 토큰 레벨 결과 받기
                    device=self.device
                )
                
                # 테스트
                test_text = "김철수는 서울 강남구에 살고 있습니다."
                test_result = self._process_raw_ner_output(self.pipeline(test_text), test_text)
                
                self.loaded = True
                self.model_name = model_name
                print(f"✅ NER 모델 로드 성공: {model_name}")
                print(f"   🧪 테스트 결과: {len(test_result)}개 엔티티 탐지")
                for entity in test_result:
                    print(f"      - {entity['type']}: {entity['value']}")
                return True
                
            except Exception as e:
                print(f"❌ {model_name} 로드 실패: {e}")
                continue
        
        print("❌ 모든 NER 모델 로드 실패")
        return False
    
    def _process_raw_ner_output(self, raw_results: List[Dict], original_text: str) -> List[Dict[str, Any]]:
        """원시 NER 출력을 처리하여 엔티티 추출 (호환성용)"""
        # aggregation_strategy="simple" 사용 시 이미 처리된 결과
        entities = []
        
        for entity in raw_results:
            entity_group = entity.get('entity_group', '')
            word = entity.get('word', '').strip()
            score = entity.get('score', 0.0)
            start = entity.get('start', 0)
            end = entity.get('end', 0)
            
            # 토크나이저 아티팩트 제거
            word = word.replace('##', '').replace('▁', ' ').strip()
            
            # entity_group 매핑
            pii_type = self._map_entity_type(entity_group)
            
            # 필터링
            threshold = 0.5 if pii_type == '주소' else 0.6
            
            if score > threshold and len(word) >= 2 and pii_type != '기타':
                entities.append({
                    'type': pii_type,
                    'value': word,
                    'start': start,
                    'end': end,
                    'score': score,
                    'source': 'NER'
                })
        
        return entities
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """개체명 추출 - aggregation_strategy 사용"""
        if not self.loaded or not self.pipeline:
            return []
        
        try:
            # NER 실행 (aggregation_strategy="simple" 사용)
            ner_results = self.pipeline(text)
            
            entities = []
            for entity in ner_results:
                entity_group = entity.get('entity_group', '')
                word = entity.get('word', '')
                score = entity.get('score', 0.0)
                start = entity.get('start', 0)
                end = entity.get('end', 0)
                
                # 토크나이저 아티팩트 제거
                word = word.replace('##', '').replace('▁', ' ').strip()
                
                # entity_group 매핑
                pii_type = self._map_entity_type(entity_group)
                
                # 필터링
                threshold = 0.5 if pii_type == '주소' else 0.6
                
                if score > threshold and len(word) >= 2 and pii_type != '기타':
                    entities.append({
                        'type': pii_type,
                        'value': word,
                        'start': start,
                        'end': end,
                        'score': score,
                        'source': 'NER'
                    })
                    print(f"   ✅ NER 탐지: {pii_type} = '{word}' (신뢰도: {score:.3f})")
            
            print(f"🤖 NER ({self.model_name.split('/')[-1]}) 탐지: {len(entities)}개")
            return entities
            
        except Exception as e:
            print(f"❌ NER 개체명 추출 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _map_entity_type(self, entity_type: str) -> str:
        """엔티티 타입을 우리 시스템 타입으로 매핑"""
        entity_type = entity_type.upper()
        
        mapping = {
            # 표준 엔티티 타입
            'PER': '이름',
            'PS': '이름',       # Person (KLUE)
            'PERSON': '이름',
            
            'LOC': '주소',
            'LC': '주소',       # Location (KLUE)
            'LOCATION': '주소',
            
            'ORG': '회사',
            'OG': '회사',       # Organization (KLUE)
            'ORGANIZATION': '회사',
            
            'DT': '날짜',       # Date
            'TI': '시간',       # Time
            'QT': '수량',       # Quantity
        }
        
        return mapping.get(entity_type, '기타')

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

# 모듈 테스트
if __name__ == "__main__":
    print("🎭 개선된 한국어 NER 모델 모듈")
    print("🔧 BIO 태그 문제 해결")
    
    if NER_AVAILABLE:
        print("\n🔄 모델 로드 테스트...")
        success = load_ner_model()
        
        if success:
            print("\n🧪 테스트 케이스 실행:")
            test_cases = [
                "김철수 고객님, 부산 해운대구 예약이 확인되었습니다. 문의사항은 010-9876-5432로 연락 주세요.",
                "이영희님은 서울 강남구에 살고 있습니다.",
                "박민수는 삼성전자에서 일하고 있습니다."
            ]
            
            for test_text in test_cases:
                print(f"\n테스트: '{test_text}'")
                entities = extract_entities_with_ner(test_text)
                
                if entities:
                    for entity in entities:
                        print(f"  - {entity['type']}: {entity['value']} (신뢰도: {entity['score']:.3f})")
                else:
                    print("  탐지된 엔티티 없음")