# pseudonymization/model.py - 라벨 매핑 문제 해결
"""
NER 모델 관리 모듈 - KPF/KPF-bert-ner 라벨 매핑 수정
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
    """KPF BERT NER 모델 클래스 (라벨 매핑 수정)"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = self._get_device()
        self.loaded = False
        self.model_name = None
        self.id2label = None
        self.label_map = None  # 수동 라벨 매핑 추가
    
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
    
    def _create_manual_label_map(self):
        """수동 라벨 매핑 생성 (LABEL_숫자 -> 의미 있는 라벨)"""
        # KPF 모델의 실제 라벨 매핑 (추측 기반)
        # 로그에서 보면: 김철(LABEL_96), 부산(LABEL_70), 해운대구(LABEL_72), 010(LABEL_115)
        self.label_map = {
            # 인명 관련 (LABEL_96, LABEL_246은 이름의 일부로 보임)
            'LABEL_96': 'B-PER',    # 김철
            'LABEL_246': 'I-PER',   # ##수 (이름 연결)
            
            # 지명 관련
            'LABEL_70': 'B-LOC',    # 부산 (지역 시작)
            'LABEL_72': 'I-LOC',    # 해운대구 (지역 연결)
            
            # 전화번호 관련
            'LABEL_115': 'B-PHONE', # 010 (전화번호 시작)
            'LABEL_265': 'I-PHONE', # 나머지 번호
            
            # 기타/일반 텍스트
            'LABEL_299': 'O',       # 일반 텍스트 (고객님, 예약이... 등)
        }
        
        print(f"🗺️ 수동 라벨 매핑 생성: {len(self.label_map)}개 매핑")
        for label_id, mapped in self.label_map.items():
            print(f"  - {label_id} -> {mapped}")
    
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
                print(f"📋 원본 라벨 개수: {len(self.id2label)}")
                
                # 수동 매핑 생성
                self._create_manual_label_map()
                
                # 파이프라인 생성 (aggregation_strategy 변경)
                self.pipeline = pipeline(
                    "ner", 
                    model=self.model, 
                    tokenizer=self.tokenizer,
                    aggregation_strategy="max",  # "simple"에서 변경
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
                print(f"🧪 모델 테스트 결과: {len(test_result)}개 엔티티 탐지")
                
                self.loaded = True
                print(f"✅ NER 모델 로드 성공: {model_name}")
                return True
                
            except Exception as e:
                print(f"❌ 모델 {model_name} 로드 실패: {e}")
                continue
        
        print("❌ 모든 NER 모델 로드 실패")
        return False
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """텍스트에서 엔티티 추출 (라벨 매핑 개선)"""
        if not self.loaded or not self.pipeline:
            print("⚠️ NER 모델이 로드되지 않음")
            return []
        
        try:
            # NER 실행
            start_time = time.time()
            raw_entities = self.pipeline(text)
            processing_time = time.time() - start_time
            
            print(f"🔍 NER 원본 출력 (간략):")
            print(f"  입력: {text}")
            print(f"  탐지된 개수: {len(raw_entities)}")
            
            # 결과 정규화
            entities = []
            for i, entity in enumerate(raw_entities):
                entity_group = entity.get('entity_group', 'UNKNOWN')
                word = entity.get('word', '').replace('##', '')  # BERT 토큰 정리
                score = float(entity.get('score', 0.0))
                start = entity.get('start', 0)
                end = entity.get('end', 0)
                
                # 수동 라벨 매핑 적용
                mapped_label = self.label_map.get(entity_group, entity_group)
                mapped_type = self._map_label_to_type(mapped_label)
                
                print(f"  [{i}] {entity_group} -> {mapped_label} -> {mapped_type}: '{word}' ({score:.3f})")
                
                if mapped_type and score > 0.8:  # 높은 신뢰도만
                    # 연속된 토큰 병합 (김철 + ##수 -> 김철수)
                    if (entities and 
                        entities[-1]['type'] == mapped_type and 
                        entities[-1]['end'] == start):
                        # 이전 엔티티와 병합
                        entities[-1]['value'] += word
                        entities[-1]['text'] += word
                        entities[-1]['end'] = end
                        entities[-1]['confidence'] = max(entities[-1]['confidence'], score)
                        print(f"    병합됨: '{entities[-1]['value']}'")
                    else:
                        # 새 엔티티 추가
                        processed_entity = {
                            'type': mapped_type,
                            'label': mapped_type,
                            'text': word,
                            'value': word,
                            'start': start,
                            'end': end,
                            'confidence': score,
                            'model': self.model_name,
                            'original_label': entity_group
                        }
                        entities.append(processed_entity)
                        print(f"    추가됨: {processed_entity}")
                else:
                    print(f"    제외됨 (타입: {mapped_type}, 점수: {score:.3f})")
            
            print(f"🏁 NER 처리 완료: {len(entities)}개 엔티티 ({processing_time:.3f}초)")
            return entities
            
        except Exception as e:
            print(f"❌ NER 처리 오류: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _map_label_to_type(self, label: str) -> Optional[str]:
        """매핑된 라벨을 PII 타입으로 변환"""
        
        # B-, I- 접두사 제거
        clean_label = label.replace('B-', '').replace('I-', '').upper()
        
        # 타입 매핑
        type_mapping = {
            'PER': '이름',
            'PERSON': '이름',
            'LOC': '주소', 
            'LOCATION': '주소',
            'ORG': '조직',
            'ORGANIZATION': '조직',
            'PHONE': '전화번호',
            'EMAIL': '이메일',
            'MISC': '기타'
        }
        
        return type_mapping.get(clean_label, None)

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
            print("❌ NER 모델을 로드할 수 없습니다")
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