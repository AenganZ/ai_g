# pseudonymization/detection.py
"""
PII 탐지 모듈
CSV 파일(name.csv, address_road.csv)을 활용한 정확한 탐지
"""

import os
import re
from typing import List, Dict, Any, Set
from .pools import get_pools, COMPOUND_SURNAMES, SINGLE_SURNAMES

# ==================== CSV 데이터 로더 ====================
class DetectionData:
    """탐지용 데이터 관리"""
    
    def __init__(self):
        self.real_names: Set[str] = set()  # name.csv에서 로드한 실제 이름들
        self.real_addresses: Set[str] = set()  # address_road.csv에서 로드한 실제 주소들
        self.road_names: Set[str] = set()  # 도로명만
        self.districts: Set[str] = set()  # 시군구만
        self._loaded = False
    
    def load(self):
        """CSV 파일에서 탐지용 데이터 로드"""
        if self._loaded:
            return
        
        print("🔍 탐지용 데이터 로딩 중...")
        
        # name.csv 로드
        self._load_names()
        
        # address_road.csv 로드
        self._load_addresses()
        
        self._loaded = True
        print(f"✅ 탐지 데이터 로드 완료 (이름: {len(self.real_names)}개, 주소: {len(self.real_addresses)}개)")
    
    def _load_names(self):
        """name.csv에서 실제 이름 로드"""
        if not os.path.exists('name.csv'):
            print("⚠️ name.csv 없음 - 기본 탐지 모드")
            return
        
        try:
            try:
                import pandas as pd
                df = pd.read_csv('name.csv', encoding='utf-8')
                first_names = df['이름'].tolist()
                
                # 성씨와 조합하여 전체 이름 생성 (탐지용)
                all_surnames = SINGLE_SURNAMES + COMPOUND_SURNAMES
                
                for surname in all_surnames:
                    for first_name in first_names:
                        full_name = surname + first_name
                        if 2 <= len(full_name) <= 4:  # 2-4글자만
                            self.real_names.add(full_name)
                
                # 이름만도 추가 (성씨 없이)
                for first_name in first_names:
                    if 2 <= len(first_name) <= 3:
                        self.real_names.add(first_name)
                
                print(f"   📛 name.csv: {len(first_names)}개 → {len(self.real_names)}개 이름 조합")
                
            except ImportError:
                import csv
                with open('name.csv', 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        first_name = row['이름']
                        # 모든 성씨와 조합
                        for surname in SINGLE_SURNAMES + COMPOUND_SURNAMES:
                            self.real_names.add(surname + first_name)
                        # 이름만도 추가
                        if 2 <= len(first_name) <= 3:
                            self.real_names.add(first_name)
                            
        except Exception as e:
            print(f"❌ name.csv 로드 실패: {e}")
    
    def _load_addresses(self):
        """address_road.csv에서 실제 주소 로드"""
        if not os.path.exists('address_road.csv'):
            print("⚠️ address_road.csv 없음 - 기본 탐지 모드")
            return
        
        try:
            try:
                import pandas as pd
                df = pd.read_csv('address_road.csv', encoding='utf-8')
                
                # 도로명
                road_names = df['도로명'].dropna().unique()
                self.road_names.update(road_names)
                
                # 시도 + 시군구 조합
                for _, row in df.iterrows():
                    # 시도만
                    self.real_addresses.add(row['시도'])
                    
                    # 시군구만
                    if pd.notna(row['시군구']):
                        self.districts.add(row['시군구'])
                        
                        # 시도 + 시군구
                        self.real_addresses.add(f"{row['시도']} {row['시군구']}")
                    
                    # 도로명과 조합
                    if pd.notna(row['도로명']):
                        self.real_addresses.add(row['도로명'])
                        
                        # 시군구 + 도로명
                        if pd.notna(row['시군구']):
                            self.real_addresses.add(f"{row['시군구']} {row['도로명']}")
                
                print(f"   🏠 address_road.csv: {len(road_names)}개 도로명, {len(self.real_addresses)}개 주소 조합")
                
            except ImportError:
                import csv
                with open('address_road.csv', 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['시도']:
                            self.real_addresses.add(row['시도'])
                        if row['시군구']:
                            self.districts.add(row['시군구'])
                            self.real_addresses.add(f"{row['시도']} {row['시군구']}")
                        if row['도로명']:
                            self.road_names.add(row['도로명'])
                            self.real_addresses.add(row['도로명'])
                            
        except Exception as e:
            print(f"❌ address_road.csv 로드 실패: {e}")

# 전역 탐지 데이터 인스턴스
_detection_data = None

def get_detection_data() -> DetectionData:
    """탐지 데이터 싱글톤 인스턴스"""
    global _detection_data
    if _detection_data is None:
        _detection_data = DetectionData()
        _detection_data.load()
    return _detection_data

# ==================== 정규식 패턴 ====================
# 이메일
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

# 전화번호 (다양한 형식)
PHONE_PATTERN = re.compile(
    r'(?:010|011|016|017|018|019|02|031|032|033|041|042|043|044|051|052|053|054|055|061|062|063|064)'
    r'[-.\s]?\d{3,4}[-.\s]?\d{4}'
)

# 나이
AGE_PATTERN = re.compile(r'(\d{1,3})\s*(?:세|살)')

# 주민등록번호
RRN_PATTERN = re.compile(r'\d{6}[-\s]?\d{7}')

# 신용카드
CARD_PATTERN = re.compile(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}')

# ==================== PII 탐지 함수 ====================
def detect_pii_enhanced(text: str) -> Dict[str, Any]:
    """강화된 PII 탐지 (CSV 데이터 활용)"""
    items = []
    pools = get_pools()
    detection_data = get_detection_data()
    
    print(f"🔍 PII 분석: {text[:50]}...")
    
    # 1. NER 모델 사용
    ner_items = detect_with_ner(text)
    items.extend(ner_items)
    
    # 2. CSV 기반 이름 탐지 (높은 정확도)
    name_items = detect_names_from_csv(text, detection_data)
    items.extend(name_items)
    
    # 3. CSV 기반 주소 탐지 (높은 정확도)
    address_items = detect_addresses_from_csv(text, detection_data)
    items.extend(address_items)
    
    # 4. 정규식 패턴 탐지
    regex_items = detect_with_regex(text, pools)
    items.extend(regex_items)
    
    # 5. 중복 제거 및 병합
    unique_items = merge_detections(items)
    
    # 6. 결과 반환
    result = {
        "contains_pii": len(unique_items) > 0,
        "items": unique_items,
        "stats": {
            "ner": len(ner_items),
            "csv_names": len(name_items),
            "csv_addresses": len(address_items),
            "regex": len(regex_items),
            "total": len(unique_items)
        }
    }
    
    print(f"🎯 최종 탐지 결과: {len(unique_items)}개")
    for idx, item in enumerate(unique_items, 1):
        print(f"   #{idx} {item['type']}: '{item['value']}' (신뢰도: {item['confidence']:.2f}, 출처: {item['source']})")
    
    return result

def detect_names_from_csv(text: str, detection_data: DetectionData) -> List[Dict[str, Any]]:
    """CSV 데이터 기반 이름 탐지 (조사 제거 포함)"""
    items = []
    
    if not detection_data.real_names:
        return items
    
    print(f"👤 CSV 기반 이름 탐지 중... ({len(detection_data.real_names)}개 이름)")
    
    # 조사 제거를 위한 패턴 - 문자열 제대로 닫기
    josa_pattern = re.compile(r'(님|씨|군|양|이|가|을|를|에게|에서|한테|께서|께|는|은|이가|이를|이는|이와|이여|아|야)$')
    
    # 텍스트에서 실제 이름 찾기
    for name in detection_data.real_names:
        if name in text:
            # 모든 출현 위치 찾기
            start = 0
            while True:
                pos = text.find(name, start)
                if pos == -1:
                    break
                
                # 이름 뒤에 조사가 있는지 확인
                end_pos = pos + len(name)
                actual_end = end_pos
                
                # 조사가 붙어있는 경우 처리 (예: "이영희님")
                if end_pos < len(text):
                    rest_text = text[end_pos:]
                    josa_match = josa_pattern.match(rest_text)
                    if josa_match:
                        actual_end = end_pos  # 조사는 포함하지 않음
                
                # 앞 문자 확인 (단어 경계)
                before_ok = pos == 0 or not text[pos-1].isalnum()
                
                if before_ok:
                    items.append({
                        "type": "이름",
                        "value": name,
                        "start": pos,
                        "end": pos + len(name),
                        "confidence": 0.95,
                        "source": "CSV-Names"
                    })
                    print(f"   ✅ 이름 탐지 (CSV): '{name}'")
                
                start = pos + 1
    
    # 조사가 붙은 형태도 검색 (이영희님, 김철수씨 등)
    for name in detection_data.real_names:
        # 이름 + 조사 패턴으로 검색
        pattern = re.compile(f'{re.escape(name)}(님|씨|군|양)')
        for match in pattern.finditer(text):
            items.append({
                "type": "이름",
                "value": name,  # 이름만 저장
                "start": match.start(),
                "end": match.start() + len(name),
                "confidence": 0.95,
                "source": "CSV-Names"
            })
            print(f"   ✅ 이름 탐지 (CSV+조사): '{name}' from '{match.group()}'")
    
    return items

def detect_addresses_from_csv(text: str, detection_data: DetectionData) -> List[Dict[str, Any]]:
    """CSV 데이터 기반 주소 탐지"""
    items = []
    
    # 시/도 이름들 (기본)
    provinces = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
                 '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']
    
    print(f"🏠 CSV 기반 주소 탐지 중...")
    
    # 1. 시/도 탐지 (기본)
    for province in provinces:
        if province in text:
            for match in re.finditer(re.escape(province), text):
                items.append({
                    "type": "주소",
                    "value": province,
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "source": "Basic-Province"
                })
                print(f"   ✅ 시/도 탐지: '{province}'")
    
    # 2. CSV 도로명 찾기
    if detection_data.road_names:
        for road_name in detection_data.road_names:
            if road_name in text and len(road_name) >= 2:
                for match in re.finditer(re.escape(road_name), text):
                    items.append({
                        "type": "주소",
                        "value": road_name,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.95,
                        "source": "CSV-Roads"
                    })
                    print(f"   ✅ 도로명 탐지 (CSV): '{road_name}'")
    
    # 3. 시군구 찾기
    if detection_data.districts:
        for district in detection_data.districts:
            if district in text and len(district) >= 2:
                for match in re.finditer(re.escape(district), text):
                    items.append({
                        "type": "주소",
                        "value": district,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.9,
                        "source": "CSV-Districts"
                    })
                    print(f"   ✅ 시군구 탐지 (CSV): '{district}'")
    
    # 4. 조합된 주소 찾기 (시도 + 시군구 등)
    if detection_data.real_addresses:
        for address in detection_data.real_addresses:
            if address in text and len(address) >= 3:
                for match in re.finditer(re.escape(address), text):
                    items.append({
                        "type": "주소",
                        "value": address,
                        "start": match.start(),
                        "end": match.end(),
                        "confidence": 0.95,
                        "source": "CSV-Addresses"
                    })
    
    return items

def detect_with_ner(text: str) -> List[Dict[str, Any]]:
    """NER 모델을 사용한 탐지"""
    items = []
    
    try:
        from .model import extract_entities_with_ner, is_ner_loaded
        
        if is_ner_loaded():
            print("🤖 NER 모델로 개체명 추출 중...")
            ner_items = extract_entities_with_ner(text)
            items.extend(ner_items)
            print(f"   NER 결과: {len(ner_items)}개 탐지")
    except Exception as e:
        print(f"⚠️ NER 모델 사용 실패: {e}")
    
    return items

def detect_with_regex(text: str, pools) -> List[Dict[str, Any]]:
    """정규식 패턴을 사용한 탐지"""
    items = []
    
    print("🔎 정규식 패턴으로 추가 탐지 중...")
    
    # 이메일
    for match in EMAIL_PATTERN.finditer(text):
        items.append({
            "type": "이메일",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex"
        })
    
    # 전화번호
    for match in PHONE_PATTERN.finditer(text):
        items.append({
            "type": "전화번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex"
        })
    
    # 주민등록번호
    for match in RRN_PATTERN.finditer(text):
        items.append({
            "type": "주민등록번호",
            "value": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "Regex"
        })
    
    # 나이
    for match in AGE_PATTERN.finditer(text):
        items.append({
            "type": "나이",
            "value": match.group(1),
            "start": match.start(),
            "end": match.end(),
            "confidence": 0.9,
            "source": "Regex"
        })
    
    return items

def merge_detections(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """중복 제거 및 병합 (CSV 우선순위 높음)"""
    if not items:
        return []
    
    print("🧹 중복 제거 및 정렬 중...")
    
    # 우선순위: CSV > NER > Regex
    priority_map = {
        'CSV-Names': 0,
        'CSV-Roads': 0,
        'CSV-Districts': 0,
        'CSV-Addresses': 0,
        'Basic-Province': 0,
        'NER': 1,
        'Regex': 2,
        'Pattern': 3
    }
    
    # 위치 기반 정렬 (우선순위 고려)
    items.sort(key=lambda x: (x['start'], priority_map.get(x['source'].split('-')[0], 4)))
    
    # 겹치는 탐지 제거 (같은 값은 하나만)
    unique_items = []
    seen_values = set()
    
    for item in items:
        # 같은 값이 이미 있으면 스킵
        value_key = (item['type'], item['value'])
        if value_key in seen_values:
            continue
        
        # 겹치는 위치의 다른 아이템 확인
        overlap = False
        for existing in unique_items[:]:  # 복사본으로 순회
            if item['start'] < existing['end'] and item['end'] > existing['start']:
                # 같은 위치에 있는 경우
                if item['start'] == existing['start'] and item['end'] == existing['end']:
                    # 우선순위가 높은 것 선택
                    item_priority = priority_map.get(item['source'].split('-')[0], 4)
                    existing_priority = priority_map.get(existing['source'].split('-')[0], 4)
                    
                    if item_priority < existing_priority:
                        unique_items.remove(existing)
                        unique_items.append(item)
                        seen_values.discard((existing['type'], existing['value']))
                        seen_values.add(value_key)
                    overlap = True
                    break
        
        if not overlap:
            unique_items.append(item)
            seen_values.add(value_key)
    
    # 최종 정렬
    unique_items.sort(key=lambda x: x['start'])
    
    return unique_items

# ==================== 테스트 ====================
if __name__ == "__main__":
    print("🔍 PII 탐지 모듈 테스트 (CSV 활용)")
    print("=" * 60)
    
    # CSV 파일 확인
    print("\n📁 CSV 파일 상태:")
    print(f"   name.csv: {'✅ 있음' if os.path.exists('name.csv') else '❌ 없음'}")
    print(f"   address_road.csv: {'✅ 있음' if os.path.exists('address_road.csv') else '❌ 없음'}")
    
    # 탐지 데이터 로드
    detection_data = get_detection_data()
    print(f"\n📊 로드된 탐지 데이터:")
    print(f"   이름: {len(detection_data.real_names)}개")
    print(f"   주소: {len(detection_data.real_addresses)}개")
    print(f"   도로명: {len(detection_data.road_names)}개")
    
    # 테스트 케이스
    test_cases = [
        "김민준님이 서울시 강남구 테헤란로에 삽니다. 010-1234-5678",
        "이서준 고객님, 부산광역시 해운대구 예약 확인되었습니다.",
        "박지우씨는 대구광역시 중구 동성로에서 일합니다.",
        "남궁민수님의 연락처는 02-123-4567입니다.",
        "이영희님 25세, 대구 중구 거주하시는 분이시죠?"
    ]
    
    for text in test_cases:
        print(f"\n테스트: {text}")
        result = detect_pii_enhanced(text)
        
        print(f"통계: NER={result['stats']['ner']}, "
              f"CSV이름={result['stats']['csv_names']}, "
              f"CSV주소={result['stats']['csv_addresses']}, "
              f"정규식={result['stats']['regex']}")
        
        if result['items']:
            for item in result['items']:
                print(f"  - {item['type']}: {item['value']} (출처: {item['source']})")
        else:
            print("  탐지된 PII 없음")