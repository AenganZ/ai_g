# pseudonymization/pools.py
"""
최적화된 데이터풀 관리 모듈 - 깔끔한 버전
CSV 데이터 내장 + 명확한 가명화 방식
"""

import os
import random
import json
import time
from typing import List, Dict, Any, Optional, Set

# CSV 데이터 내장 (성능 최적화)
KOREAN_FIRST_NAMES = [
    # 남성 이름
    '민준', '서준', '도윤', '예준', '시우', '주원', '하준', '지호', '준서', '건우',
    '현우', '우진', '선우', '연우', '정우', '성민', '준영', '성현', '지우', '현준',
    '기현', '민성', '재윤', '시온', '유준', '지한', '도현', '민규', '이준', '이안',
    '진우', '승우', '윤서', '태현', '민찬', '승현', '준호', '재민', '시현', '지원',
    '한결', '태윤', '유찬', '승민', '지환', '승현', '지훈', '민수', '현수', '준혁',
    
    # 여성 이름
    '서연', '서윤', '지우', '서현', '민서', '하은', '예은', '소율', '지민', '윤서',
    '하윤', '채원', '지원', '수빈', '다은', '예린', '시은', '소은', '유나', '예나',
    '채은', '아린', '수아', '연우', '가은', '나은', '혜원', '세은', '아윤', '가윤',
    '지아', '서아', '하린', '수연', '예원', '유진', '지현', '수민', '유은', '서율',
    '예서', '지윤', '하율', '채윤', '예진', '서진', '하서', '윤아', '채연', '유주',
    
    # 전통/일반 이름
    '철수', '영희', '순자', '영자', '정자', '미자', '혜자', '옥자', '금자', '순이',
    '영호', '정호', '성호', '민호', '진호', '기호', '태호', '용호', '석호', '동호',
    '성민', '현민', '준민', '진민', '태민', '윤민', '수민', '도민', '재민', '기민',
    '영미', '정미', '수미', '은미', '혜미', '지미', '선미', '경미', '남미', '귀미',
    '영수', '정수', '민수', '현수', '진수', '기수', '태수', '용수', '석수', '동수'
]

# 주소 데이터 내장
MAJOR_ADDRESSES = {
    'provinces': [
        '서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', 
        '대전광역시', '울산광역시', '세종특별자치시', '경기도', '강원도',
        '충청북도', '충청남도', '전라북도', '전라남도', '경상북도', '경상남도', 
        '제주특별자치도'
    ],
    
    'districts': [
        # 서울
        '강남구', '서초구', '송파구', '강동구', '마포구', '용산구', '종로구', '중구',
        '강서구', '양천구', '구로구', '금천구', '영등포구', '동작구', '관악구',
        '서대문구', '은평구', '노원구', '도봉구', '강북구', '성북구', '중랑구',
        '동대문구', '성동구', '광진구',
        
        # 부산
        '해운대구', '부산진구', '동래구', '사하구', '연제구', '수영구', '남구',
        '북구', '강서구', '사상구', '금정구', '영도구', '중구', '서구', '동구',
        
        # 경기도 주요 시
        '수원시', '성남시', '고양시', '용인시', '부천시', '안산시', '안양시',
        '남양주시', '화성시', '평택시', '의정부시', '파주시', '시흥시', '김포시'
    ],
    
    'roads': [
        # 서울 주요 도로
        '테헤란로', '강남대로', '논현로', '봉은사로', '도산대로', '압구정로',
        '청담로', '삼성로', '선릉로', '언주로', '영동대로', '한남대로',
        '이태원로', '한강대로', '여의대로', '마포대로', '홍익로', '연세로',
        '종로', '을지로', '퇴계로', '남대문로', '세종대로', '동대문로',
        
        # 부산 주요 도로
        '해운대로', '중앙대로', '수영로', '광안해변로', '달맞이길', '동백로',
        
        # 기타 도시 주요 도로
        '동성로', '명덕로', '달구벌대로',  # 대구
        '충장로', '금남로', '무등로',  # 광주
        '대전로', '둔산대로', '유성대로'  # 대전
    ]
}

# 성씨 데이터
SINGLE_SURNAMES = [
    '김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
    '한', '오', '서', '신', '권', '황', '안', '송', '류', '전',
    '홍', '고', '문', '양', '손', '배', '백', '허', '유', '남'
]

COMPOUND_SURNAMES = [
    '남궁', '황보', '제갈', '사공', '선우', '서문', '독고', '동방'
]

# 제외 단어 리스트
NAME_EXCLUDE_WORDS = {
    # 호칭/직책
    '고객', '회원', '사용자', '관리자', '직원', '담당자', '매니저', '대표',
    '선생', '교수', '의사', '간호사', '기사', '작가', '감독', '배우',
    '사장', '부장', '과장', '대리', '주임', '사원', '인턴', '팀장',
    
    # 가족 호칭
    '아버지', '어머니', '아빠', '엄마', '형', '누나', '동생', '언니',
    '오빠', '할아버지', '할머니', '삼촌', '이모', '고모', '외삼촌',
    
    # 시간 관련
    '오전', '오후', '내일', '어제', '오늘', '내년', '작년', '올해',
    
    # 행동/상태
    '예약', '문의', '확인', '취소', '변경', '신청', '접수', '처리',
    '거주', '근무', '방문', '이용', '가입', '탈퇴', '참석', '참여',
    
    # 일반 명사
    '이름', '성명', '실명', '가명', '별명', '닉네임',
    '문제', '상황', '일정', '계획', '방법', '결과', '과정'
}

class PseudonymGenerator:
    """명확한 가명 생성기"""
    
    def __init__(self):
        self.name_counter = 0
        self.phone_counter = 0
        self.email_counter = 0
        
    def get_fake_name(self) -> str:
        """김가명1, 이가명2 형식의 가명 생성"""
        self.name_counter += 1
        surnames = ['김', '이', '박', '최', '정', '홍', '강', '조']
        surname = surnames[(self.name_counter - 1) % len(surnames)]
        return f"{surname}가명{self.name_counter}"
    
    def get_fake_phone(self) -> str:
        """010-0000-0000부터 순차 증가"""
        self.phone_counter += 1
        last_four = f"{self.phone_counter:04d}"
        return f"010-0000-{last_four}"
    
    def get_fake_email(self) -> str:
        """Pseudonymization1@gamyeong.com 형식"""
        self.email_counter += 1
        return f"Pseudonymization{self.email_counter}@gamyeong.com"
    
    def get_simplified_address(self, original_address: str) -> str:
        """주소 간소화: 시/군/구만 추출"""
        # 시/도 우선 추출
        for province in MAJOR_ADDRESSES['provinces']:
            province_short = province.replace('특별시', '시').replace('광역시', '시').replace('특별자치시', '시').replace('도', '').replace('특별자치', '')
            if province_short in original_address:
                return province_short
        
        # 시/군/구 추출  
        for district in MAJOR_ADDRESSES['districts']:
            if district in original_address:
                if '시' in district:
                    return district
                else:
                    cities = ['대전', '대구', '부산', '인천', '광주', '수원', '성남']
                    city = random.choice(cities)
                    return f"{city}시"
        
        # 기본값
        default_cities = ['서울시', '부산시', '대구시', '인천시', '광주시', '대전시']
        return random.choice(default_cities)

class DataPools:
    """최적화된 데이터풀 (CSV 내장)"""
    
    def __init__(self):
        # 탐지용 데이터
        self.real_names: Set[str] = set()
        self.real_addresses: Set[str] = set()
        self.road_names: Set[str] = set()
        self.districts: Set[str] = set()
        self.provinces: Set[str] = set()
        
        # 가명화용 생성기
        self.generator = PseudonymGenerator()
        
        # 기타 데이터
        self.companies: List[str] = []
        
        self._initialized = False
    
    def initialize(self, custom_data: Dict = None):
        """초고속 초기화 (CSV 파일 없이)"""
        if self._initialized:
            return
        
        print("Fast data pool initialization (CSV embedded)...")
        start_time = time.time()
        
        # 탐지용 이름 생성
        self._generate_detection_names()
        
        # 탐지용 주소 데이터 준비
        self._prepare_address_data()
        
        # 기타 데이터 생성
        self._generate_company_data()
        
        # 커스텀 데이터 적용
        if custom_data:
            self._apply_custom_data(custom_data)
        
        self._initialized = True
        
        init_time = time.time() - start_time
        print(f"Fast data pool initialization completed! ({init_time:.3f}s)")
            
        print(f"Detection names: {len(self.real_names):,}")
        print(f"Detection roads: {len(self.road_names):,}")
        print(f"Detection districts: {len(self.districts):,}")
        print(f"Detection provinces: {len(self.provinces):,}")
        print(f"Companies: {len(self.companies):,}")
    
    def _generate_detection_names(self):
        """탐지용 이름 생성 (모든 성씨 + 이름 조합)"""
        all_surnames = SINGLE_SURNAMES + COMPOUND_SURNAMES
        
        for surname in all_surnames:
            for first_name in KOREAN_FIRST_NAMES:
                full_name = surname + first_name
                if 2 <= len(full_name) <= 4:
                    if full_name not in NAME_EXCLUDE_WORDS and first_name not in NAME_EXCLUDE_WORDS:
                        self.real_names.add(full_name)
    
    def _prepare_address_data(self):
        """탐지용 주소 데이터 준비"""
        # 시/도
        for province in MAJOR_ADDRESSES['provinces']:
            short_name = province.replace('특별시', '').replace('광역시', '').replace('특별자치시', '').replace('도', '').replace('특별자치', '')
            self.provinces.add(short_name)
            self.real_addresses.add(short_name)
        
        # 시/군/구
        for district in MAJOR_ADDRESSES['districts']:
            self.districts.add(district)
            self.real_addresses.add(district)
        
        # 도로명
        for road in MAJOR_ADDRESSES['roads']:
            self.road_names.add(road)
            self.real_addresses.add(road)
        
        # 조합 주소 생성
        for province in ['서울', '부산', '대구', '인천', '광주', '대전']:
            for district in random.sample(MAJOR_ADDRESSES['districts'][:20], 5):
                self.real_addresses.add(f"{province} {district}")
    
    def _generate_company_data(self):
        """회사 데이터 생성"""
        company_types = ['전자', '기술', '시스템', '솔루션', '서비스', '컴퍼니', '그룹', '코퍼레이션']
        company_prefixes = ['한국', '동아', '대한', '신한', '우리', '하나', '국민', '삼성', 'LG', 'SK']
        
        for prefix in company_prefixes:
            for type_name in company_types:
                self.companies.append(f"{prefix}{type_name}")
    
    def _apply_custom_data(self, custom_data: Dict):
        """커스텀 데이터 적용"""
        if 'names' in custom_data:
            self.real_names.update(custom_data['names'])
        if 'addresses' in custom_data:
            self.real_addresses.update(custom_data['addresses'])
        if 'companies' in custom_data:
            self.companies.extend(custom_data['companies'])

# 전역 인스턴스
_global_pools = None

def get_pools() -> DataPools:
    """데이터풀 싱글톤 인스턴스"""
    global _global_pools
    if _global_pools is None:
        _global_pools = DataPools()
        _global_pools.initialize()
    return _global_pools

def initialize_pools(custom_data: Dict = None):
    """데이터풀 초기화"""
    global _global_pools
    _global_pools = DataPools()
    _global_pools.initialize(custom_data)

def reload_pools():
    """데이터풀 재로드"""
    global _global_pools
    _global_pools = None
    get_pools()

def get_pool_stats() -> Dict[str, int]:
    """데이터풀 통계"""
    pools = get_pools()
    return {
        "detection_names": len(pools.real_names),
        "detection_addresses": len(pools.real_addresses),
        "detection_roads": len(pools.road_names),
        "detection_districts": len(pools.districts),
        "detection_provinces": len(pools.provinces),
        "companies": len(pools.companies)
    }