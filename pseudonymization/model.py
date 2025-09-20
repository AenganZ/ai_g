# pseudonymization/model.py - 실제 작동하는 한국어 NER 모델들
import os
import torch
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# NER 모델 관련 import
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False
    print("⚠️ Transformers 라이브러리가 없습니다. pip install transformers torch를 실행하세요.")

# 실제 존재하고 작동하는 한국어 NER 모델들 (검증됨)
NER_MODELS = [
    # 1순위: 검증된 성능 좋은 모델들
    "monologg/koelectra-base-v3-naver-ner",     # 네이버 데이터, 검증됨 ✅
    "Leo97/KoELECTRA-small-v3-modu-ner",       # 모두의 말뭉치, 빠름 ✅
    
    # 2순위: 대안 모델들
    "KPF/KPF-bert-ner",                        # 한국언론진흥재단, 신문 특화 ✅
    "beomi/kcbert-base",                        # KcBERT (NER 파인튜닝 필요하지만 베이스로 사용 가능)
    
    # 3순위: 다른 접근법 (GLiNER 등)
    # "taeminlee/gliner_ko",                    # GLiNER 방식 (다른 사용법)
]

class WorkingNERModel:
    """실제 작동하는 NER 모델 클래스"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = self._get_device()
        self.loaded = False
        self.model_name = None
        self.load_time = 0
        self.inference_times = []
    
    def _get_device(self):
        """최적의 디바이스 선택"""
        if torch.cuda.is_available():
            return 0  # GPU 사용
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return -1  # CPU
    
    def load_model(self) -> bool:
        """실제 작동하는 NER 모델 로드"""
        if not NER_AVAILABLE:
            print("❌ NER 모델을 로드할 수 없습니다 - transformers 라이브러리가 필요합니다")
            return False
        
        start_time = time.time()
        
        for model_name in NER_MODELS:
            try:
                print(f"🔄 NER 모델 로딩 시도: {model_name}")
                
                # 토크나이저 로드
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    use_fast=True,
                    trust_remote_code=True
                )
                
                # 모델 로드 (dtype 파라미터로 수정)
                self.model = AutoModelForTokenClassification.from_pretrained(
                    model_name,
                    dtype=torch.float16 if self.device != -1 else torch.float32,  # torch_dtype 대신 dtype 사용
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )
                
                # GPU 사용 시 모델 이동
                if self.device != -1:
                    self.model = self.model.to(self.device)
                
                # 파이프라인 생성 (문제 있는 파라미터 제거)
                self.pipeline = pipeline(
                    "ner", 
                    model=self.model, 
                    tokenizer=self.tokenizer,
                    aggregation_strategy="simple",
                    device=self.device,
                    # return_all_scores, batch_size, max_length 등 문제 있는 파라미터 제거
                )
                
                # 테스트 문장으로 모델 검증
                test_text = "홍길동은 서울 강남구 테헤란로에 살고 있습니다."
                test_start = time.time()
                test_result = self.pipeline(test_text)
                test_time = (time.time() - test_start) * 1000  # ms 단위
                
                self.loaded = True
                self.model_name = model_name
                self.load_time = time.time() - start_time
                
                print(f"✅ NER 모델 로드 성공: {model_name}")
                print(f"   📱 디바이스: {self.device}")
                print(f"   ⏱️ 로드 시간: {self.load_time:.2f}초")
                print(f"   🚀 테스트 추론 시간: {test_time:.1f}ms")
                print(f"   🧪 테스트 결과: {len(test_result)}개 엔티티 탐지")
                
                # 테스트 결과 출력
                for entity in test_result:
                    print(f"   - {entity.get('entity_group', 'N/A')}: {entity.get('word', 'N/A')} (신뢰도: {entity.get('score', 0):.3f})")
                
                return True
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ {model_name} 로드 실패: {e}")
                
                # 구체적인 오류 분석
                if "not a valid model identifier" in error_msg:
                    print(f"   💡 모델이 존재하지 않습니다 - 다음 모델 시도")
                elif "unexpected keyword argument" in error_msg:
                    print(f"   💡 파이프라인 파라미터 오류 - 다음 모델 시도")
                elif "token" in error_msg and "permission" in error_msg:
                    print(f"   💡 비공개 저장소 - 다음 모델 시도")
                
                continue
        
        print("❌ 모든 NER 모델 로드 실패")
        print("💡 해결 방법:")
        print("   1. pip install transformers torch --upgrade")
        print("   2. 인터넷 연결 확인")
        print("   3. HuggingFace 토큰 설정 (필요시)")
        self.loaded = False
        return False
    
    def is_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        return self.loaded
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """빠르고 안정적인 개체명 추출"""
        if not self.loaded or not self.pipeline:
            return []
        
        start_time = time.time()
        
        try:
            # 텍스트 길이 제한
            if len(text) > 400:
                text = text[:400]
                print(f"⚠️ 텍스트가 400자로 제한되었습니다.")
            
            # NER 추론 실행 (안전한 파라미터만 사용)
            ner_results = self.pipeline(text)
            
            # 결과 처리 및 토크나이저 아티팩트 복원
            entities = []
            
            # 연속된 토큰 합치기 (##로 분리된 것들)
            merged_results = self._merge_subword_tokens(ner_results, text)
            
            for entity in merged_results:
                entity_type = entity.get('entity_group', entity.get('entity', ''))
                entity_text = entity.get('word', '').strip()
                confidence = entity.get('score', 0.0)
                start = entity.get('start', 0)
                end = entity.get('end', 0)
                
                # 토크나이저 아티팩트 제거
                entity_text = entity_text.replace('##', '').replace('▁', ' ').strip()
                
                # 신뢰도 임계값 (주소는 매우 낮게)
                if any(keyword in entity_type.upper() for keyword in ['LC', 'LOC', 'LOCATION']):
                    threshold = 0.5  # 주소는 매우 낮은 임계값
                elif any(keyword in entity_type.upper() for keyword in ['PS', 'PER', 'PERSON']):
                    threshold = 0.7  # 이름은 중간 임계값
                else:
                    threshold = 0.6  # 기본 임계값 (B, I 태그용)
                
                print(f"   📊 엔티티 검토: '{entity_text}' (타입: {entity_type}, 신뢰도: {confidence:.3f}, 임계값: {threshold})")
                
                if confidence > threshold and len(entity_text) >= 2:
                    pii_type = self._map_ner_label_to_pii_type(entity_type)
                    if pii_type and pii_type != '기타':  # '기타'는 제외하고 실제 PII만
                        entities.append({
                            "type": pii_type,
                            "value": entity_text,
                            "start": start,
                            "end": end,
                            "confidence": confidence,
                            "source": f"NER-{self.model_name.split('/')[-1]}"
                        })
                        print(f"   ✅ 추가됨: {pii_type} = '{entity_text}'")
                    else:
                        print(f"   ❌ 제외됨: 매핑 실패 또는 기타 타입")
            
            # 성능 측정
            inference_time = (time.time() - start_time) * 1000
            self.inference_times.append(inference_time)
            
            print(f"🤖 NER ({self.model_name.split('/')[-1]}) 탐지: {len(entities)}개 ({inference_time:.1f}ms)")
            return entities
            
        except Exception as e:
            print(f"❌ NER 개체명 추출 실패: {e}")
            return []
    
    def _map_ner_label_to_pii_type(self, label: str) -> Optional[str]:
        """NER 라벨을 PII 타입으로 매핑 (monologg/koelectra 모델 특화)"""
        # 실제 모델 출력 확인 및 디버깅
        print(f"   🔍 원본 라벨: '{label}'")
        
        # B-, I- 접두사 제거
        clean_label = label.replace('B-', '').replace('I-', '').upper().strip()
        print(f"   🧹 정리된 라벨: '{clean_label}'")
        
        # monologg/koelectra-base-v3-naver-ner 모델의 실제 라벨들
        mapping = {
            # 기본 BIO 태그들 (monologg 모델에서 사용)
            'B': '기타',        # Begin (일반적인 시작 태그)
            'I': '기타',        # Inside (일반적인 내부 태그)
            'O': None,          # Outside (엔티티 아님)
            
            # 실제 엔티티 타입들 (koelectra-naver-ner 기준)
            'PER': '이름',      # Person
            'PERSON': '이름',
            'LOC': '주소',      # Location
            'LOCATION': '주소',
            'ORG': '회사',      # Organization  
            'ORGANIZATION': '회사',
            'MISC': '기타',     # Miscellaneous
            
            # KLUE 스타일 라벨들
            'PS': '이름',       # Person
            'LC': '주소',       # Location
            'OG': '회사',       # Organization
            'DT': '기타',       # Date
            'TI': '기타',       # Time
            'QT': '기타',       # Quantity
            
            # 확장 라벨들
            'PRS': '이름',
            'GPE': '주소',      # Geopolitical entity
            'FAC': '주소',      # Facility
            'DATE': '기타',
            'TIME': '기타',
            'MONEY': '기타',
            'PERCENT': '기타',
            
            # KPF-BERT-NER 라벨들
            'PERSON_NAME': '이름',
            'LOCATION_NAME': '주소',
            'ORGANIZATION_NAME': '회사',
        }
        
        result = mapping.get(clean_label)
        print(f"   ➡️ 매핑 결과: {label} -> {result}")
        
        # 매핑되지 않은 라벨 경고
        if result is None and clean_label not in ['O', '']:
            print(f"   ⚠️ 알 수 없는 라벨: '{label}' ('{clean_label}')")
            # 컨텍스트 기반 추론 시도
            if any(keyword in clean_label.lower() for keyword in ['name', 'person', '이름', '인명']):
                result = '이름'
            elif any(keyword in clean_label.lower() for keyword in ['loc', 'location', 'place', '위치', '주소', '지역']):
                result = '주소'  
            elif any(keyword in clean_label.lower() for keyword in ['org', 'organization', '기관', '회사']):
                result = '회사'
            else:
                result = '기타'  # 알 수 없는 것은 기타로 분류
            print(f"   🤖 추론 결과: {result}")
        
        return result
    
    def _merge_subword_tokens(self, ner_results: List[Dict], original_text: str) -> List[Dict]:
        """서브워드 토큰들을 합쳐서 완전한 단어로 복원"""
        if not ner_results:
            return []
        
        merged = []
        current_entity = None
        
        for entity in ner_results:
            word = entity.get('word', '')
            entity_group = entity.get('entity_group', entity.get('entity', ''))
            start = entity.get('start', 0)
            end = entity.get('end', 0)
            score = entity.get('score', 0.0)
            
            # ##로 시작하는 서브워드 토큰 처리
            if word.startswith('##'):
                if current_entity:
                    # 이전 엔티티와 합치기
                    current_entity['word'] += word.replace('##', '')
                    current_entity['end'] = end
                    current_entity['score'] = min(current_entity['score'], score)  # 최소 신뢰도 사용
                continue
            
            # 새로운 엔티티 시작
            if current_entity:
                merged.append(current_entity)
            
            current_entity = {
                'word': word,
                'entity_group': entity_group,
                'start': start,
                'end': end,
                'score': score
            }
        
        # 마지막 엔티티 추가
        if current_entity:
            merged.append(current_entity)
        
        # 원본 텍스트 기준으로 정확한 위치 재계산
        for entity in merged:
            word = entity['word'].replace('▁', ' ').strip()
            if word in original_text:
                actual_start = original_text.find(word)
                if actual_start != -1:
                    entity['start'] = actual_start
                    entity['end'] = actual_start + len(word)
            entity['word'] = word
        
        print(f"   🔧 서브워드 합치기: {len(ner_results)}개 -> {len(merged)}개")
        for entity in merged:
            print(f"      - {entity['entity_group']}: '{entity['word']}' (신뢰도: {entity['score']:.3f})")
        
        return merged
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        if not self.inference_times:
            return {}
        
        avg_time = sum(self.inference_times) / len(self.inference_times)
        min_time = min(self.inference_times)
        max_time = max(self.inference_times)
        
        return {
            "model_name": self.model_name,
            "device": self.device,
            "load_time": self.load_time,
            "avg_inference_time": avg_time,
            "min_inference_time": min_time,
            "max_inference_time": max_time,
            "total_inferences": len(self.inference_times)
        }

# GLiNER 모델 클래스 (대안)
class GLiNERModel:
    """GLiNER 기반 한국어 NER 모델 (대안)"""
    
    def __init__(self):
        self.model = None
        self.loaded = False
        self.model_name = "taeminlee/gliner_ko"
    
    def load_model(self) -> bool:
        """GLiNER 모델 로드"""
        try:
            from gliner import GLiNER
            print(f"🔄 GLiNER 모델 로딩 시도: {self.model_name}")
            
            self.model = GLiNER.from_pretrained(self.model_name)
            self.loaded = True
            
            print(f"✅ GLiNER 모델 로드 성공: {self.model_name}")
            return True
            
        except ImportError:
            print("❌ GLiNER 라이브러리가 없습니다. pip install gliner를 실행하세요.")
            return False
        except Exception as e:
            print(f"❌ GLiNER 모델 로드 실패: {e}")
            return False
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """GLiNER로 개체명 추출"""
        if not self.loaded or not self.model:
            return []
        
        try:
            # GLiNER 사용법
            entities = self.model.predict_entities(
                text, 
                ["person", "location", "organization"]  # 영어 라벨
            )
            
            results = []
            for entity in entities:
                pii_type = {
                    "person": "이름",
                    "location": "주소", 
                    "organization": "회사"
                }.get(entity['label'], "기타")
                
                results.append({
                    "type": pii_type,
                    "value": entity['text'],
                    "start": entity['start'],
                    "end": entity['end'],
                    "confidence": entity['score'],
                    "source": "GLiNER"
                })
            
            return results
            
        except Exception as e:
            print(f"❌ GLiNER 추출 실패: {e}")
            return []

# 전역 모델 인스턴스 (싱글톤)
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
    success = model.load_model()
    
    # 기본 모델 실패 시 GLiNER 시도
    if not success:
        print("🔄 GLiNER 모델로 대안 시도...")
        gliner = GLiNERModel()
        return gliner.load_model()
    
    return success

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
    
    base_info = {
        "loaded": model.is_loaded(),
        "model_name": model.model_name if model.is_loaded() else None,
        "device": model.device,
        "available_models": NER_MODELS
    }
    
    if model.is_loaded():
        base_info.update(model.get_performance_stats())
    
    return base_info

# 호환성을 위한 기존 함수들
def call_qwen_detect_pii(original_prompt: str, model=None, tokenizer=None, device=None) -> Dict[str, Any]:
    """기존 호환을 위한 함수 (deprecated)"""
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
        return "cuda", torch.float16
    elif device == "mps":  # Apple Silicon
        return "mps", torch.float16
    else:  # CPU
        return "cpu", torch.float32

def load_model():
    """모델 로드 (호환성)"""
    return load_ner_model()

# 모듈 초기화 시 정보 출력
if __name__ == "__main__":
    print("🎭 실제 작동하는 한국어 NER 모델 모듈")
    print(f"📱 Transformers 사용 가능: {NER_AVAILABLE}")
    print(f"🎯 목표: 100-300ms 실시간 추론")
    print(f"🔧 수정사항: 파라미터 오류 해결, 실존 모델만 사용")
    print(f"🤖 검증된 모델들:")
    
    for i, model in enumerate(NER_MODELS, 1):
        print(f"   {i}. {model}")
    
    if NER_AVAILABLE:
        print("\n🔄 모델 로드 테스트 시작...")
        success = load_ner_model()
        
        if success:
            print("\n🧪 주소 인식 테스트:")
            test_cases = [
                "이영희님은 서울 강남구에 살고 있습니다.",
                "김철수는 부산 해운대구 센텀시티 거주합니다.",
                "대구 중구 동성로에서 만나요."
            ]
            
            for i, test_text in enumerate(test_cases, 1):
                entities = extract_entities_with_ner(test_text)
                address_found = any(e['type'] == '주소' for e in entities)
                print(f"   테스트 {i}: {'✅' if address_found else '❌'} '{test_text}'")
                if entities:
                    for entity in entities:
                        print(f"      - {entity['type']}: {entity['value']} (신뢰도: {entity['confidence']:.3f})")
        else:
            print("❌ 모든 모델 로드 실패")
            print("💡 대안: GLiNER 설치 시도 - pip install gliner")