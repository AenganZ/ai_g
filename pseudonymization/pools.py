# pseudonymization/pools.py
import csv
import os
from typing import Dict, Set

# 복합 성씨
COMPOUND_SURNAMES = {'남궁', '황보', '독고', '사공', '제갈', '서문', '선우', '동방', '어금', '망절'}

# 단일 성씨
SINGLE_SURNAMES = {
    '김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '류', '전',
    '홍', '고', '문', '양', '손', '배', '조', '백', '허', '유', '남', '심', '노', '정', '하', '곽', '성', '차', '주', '우',
    '구', '신', '임', '나', '전', '민', '유', '진', '지', '엄', '채', '원', '천', '방', '공', '강', '현', '함', '변', '염',
    '양', '변', '여', '추', '노', '도', '소', '신', '석', '선', '설', '마', '길', '연', '위', '표', '명', '기', '반', '왕',
    '금', '옥', '육', '인', '맹', '제', '모', '장', '남', '탁', '국', '여', '진', '어', '은', '편', '구', '용'
}

# 제외 단어 목록
NAME_EXCLUDE_WORDS = {
    # 문법 요소들
    '이름은', '이고', '이며', '으로', '에서', '에게', '에서', '부터', '까지', '하고', '하며', '하는', '입니다', '있습니다',
    '그런데', '하지만', '그래서', '따라서', '그러나', '또한', '그리고', '또는',
    '만약', '만일', '혹시', '아마', '정말', '진짜', '거짓', '가짜',
    '아직', '벌써', '이미', '곧', '즉시', '바로', '천천히', '빨리', '매우', '조금',
    
    # 지역명들
    '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종', '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
    '강남', '강북', '강서', '강동', '서초', '송파', '마포', '용산', '종로', '중구', '동구', '서구', '남구', '북구',
    '영등포', '관악', '성북', '동대문', '노원', '은평', '서대문', '금천', '구로', '도봉', '동작', '성동', '중랑', '양천',
    '해운대', '부산진', '동래', '수성', '달서', '달성',
    '강남구', '강북구', '강서구', '강동구', '서초구', '송파구', '마포구', '용산구에', '에서', '중구에', '남구에',
    
    # 일반적인 명사들
    '사람', '학생', '선생', '교수', '의사', '간호사', '회사원', '직원', '사장', '부장', '과장', '팀장', '회장', '고객', '손님',
    '남자', '여자', '아이', '어른', '청년', '노인', '아기', '아들', '딸', '엄마', '아빠', '부모', '가족', '친구', '동료',
    '학교', '회사', '병원', '은행', '시장', '상점', '식당', '카페', '호텔', '집', '방', '건물', '사무실',
    
    # 시간/날짜 관련
    '오늘', '어제', '내일', '모레', '지난', '다음', '이번', '올해', '작년', '내년', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일',
    '아침', '점심', '저녁', '밤', '새벽', '오전', '오후', '시간', '분', '초',
    
    # 감정/상태 표현
    '기쁘다', '슬프다', '화나다', '즐겁다', '행복하다', '우울하다', '피곤하다', '배고프다', '목마르다',
    '좋다', '나쁘다', '싫다', '미안', '고마워', '죄송', '반가워', '잘가', '안녕히', '수고',
    
    # 일반 동사/형용사 어미
    '가다', '오다', '보다', '듣다', '말하다', '먹다', '마시다', '자다', '일어나다', '앉다', '서다', '걷다', '뛰다',
    '크다', '작다', '높다', '낮다', '길다', '짧다', '넓다', '좁다', '무겁다', '가볍다',
    
    # 업무/연락 관련
    '거주하시', '분이시', '연락처', '연락', '문의사항', '문의', '질문', '답변', '확인', '예약',
    '고객님', '손님', '선생님', '님', '씨', '양', '군', '메일', '보내드렸', '보내드린', '보내서'
}

class DataPools:
    """데이터풀 클래스 - 전국 시/구 데이터 포함"""
    
    def __init__(self):
        self._initialized = False
        self.real_names = set()
        self.real_addresses = set()
        self.road_names = set()
        self.companies = set()
        
        # 전국 지역 데이터 (완전판)
        self.provinces = {
            '서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시', '세종특별자치시',
            '경기도', '강원도', '충청북도', '충청남도', '전라북도', '전라남도', '경상북도', '경상남도', '제주특별자치도',
            '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종'
        }
        
        self.cities = {
            # 특별시/광역시
            '서울시', '부산시', '대구시', '인천시', '광주시', '대전시', '울산시', '세종시',
            
            # 경기도
            '수원시', '성남시', '의정부시', '안양시', '부천시', '광명시', '평택시', '동두천시', '안산시', '고양시',
            '과천시', '구리시', '남양주시', '오산시', '시흥시', '군포시', '의왕시', '하남시', '용인시', '파주시',
            '이천시', '안성시', '김포시', '화성시', '광주시', '양주시', '포천시', '여주시',
            
            # 강원도
            '춘천시', '원주시', '강릉시', '동해시', '태백시', '속초시', '삼척시',
            
            # 충북
            '청주시', '충주시', '제천시',
            
            # 충남
            '천안시', '공주시', '보령시', '아산시', '서산시', '논산시', '계룡시', '당진시',
            
            # 전북
            '전주시', '군산시', '익산시', '정읍시', '남원시', '김제시',
            
            # 전남
            '목포시', '여수시', '순천시', '나주시', '광양시',
            
            # 경북
            '포항시', '경주시', '김천시', '안동시', '구미시', '영주시', '영천시', '상주시', '문경시', '경산시',
            
            # 경남
            '창원시', '진주시', '통영시', '사천시', '김해시', '밀양시', '거제시', '양산시',
            
            # 제주
            '제주시', '서귀포시'
        }
        
        self.districts = {
            # 서울특별시 25개 구
            '종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구',
            '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구',
            '관악구', '서초구', '강남구', '송파구', '강동구',
            
            # 부산광역시 16개 구·군
            '중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구', '해운대구', '사하구',
            '금정구', '강서구', '연제구', '수영구', '사상구', '기장군',
            
            # 대구광역시 8개 구·군
            '중구', '동구', '서구', '남구', '북구', '수성구', '달서구', '달성군',
            
            # 인천광역시 10개 구·군
            '중구', '동구', '미추홀구', '연수구', '남동구', '부평구', '계양구', '서구', '강화군', '옹진군',
            
            # 광주광역시 5개 구
            '동구', '서구', '남구', '북구', '광산구',
            
            # 대전광역시 5개 구
            '동구', '중구', '서구', '유성구', '대덕구',
            
            # 울산광역시 5개 구·군
            '중구', '남구', '동구', '북구', '울주군'
        }
        
        # 성씨 데이터
        self.compound_surnames = COMPOUND_SURNAMES
        self.single_surnames = SINGLE_SURNAMES
        
        # 제외 단어 리스트
        self.name_exclude_words = NAME_EXCLUDE_WORDS
        
        # 기본 실명 목록 (확실한 이름들만)
        self._load_basic_names()
        
        # 가명 풀 (치환용)
        self.fake_names = self._generate_fake_names()
        self.fake_phones = self._generate_fake_phones()
        self.fake_addresses = self._generate_fake_addresses()
        self.fake_emails = self._generate_fake_emails()
    
    def _load_basic_names(self):
        """기본 실명 목록 로드 (확실한 이름들만)"""
        basic_names = {
            # 확실한 이름들만 포함
            '민준', '서준', '도윤', '예준', '시우', '주원', '하준', '지호', '지후', '준우',
            '현우', '준서', '도현', '지훈', '건우', '우진', '선우', '민재', '현준', '유준',
            '홍길동', '김철수', '이영희', '박민수', '최영숙', '정미영', '강동원', '송혜교',
            '윤서', '지우', '서현', '하은', '예은', '지민', '채원', '수아', '지윤', '서연',
            '다은', '소율', '하윤', '민서', '예린', '채윤', '유진', '지안', '서영', '시은'
        }
        
        # 제외 단어가 포함된 것들 필터링
        filtered_names = set()
        for name in basic_names:
            if name not in self.name_exclude_words and len(name) >= 2:
                filtered_names.add(name)
        
        self.real_names = filtered_names
    
    def _generate_fake_names(self) -> list:
        """가명 이름 생성 (김가명, 이가명 형태)"""
        surnames = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임']
        fake_words = ['가명', '익명', '무명', '차명', '별명', '테스트', '샘플', '더미', '임시', '대체']
        
        fake_names = []
        for surname in surnames:
            for fake_word in fake_words:
                fake_names.append(surname + fake_word)
        
        return fake_names
    
    def _generate_fake_phones(self) -> list:
        """가짜 전화번호 생성 (010-0000-0000부터 1씩 증가)"""
        fake_phones = []
        for i in range(10000):
            fake_phones.append(f"010-{i:04d}-0000")
        return fake_phones
    
    def _generate_fake_addresses(self) -> list:
        """가짜 주소 생성 (시/도만 표시)"""
        return ['서울시', '부산시', '대구시', '인천시', '광주시', '대전시', '울산시', '경기도', '강원도', '충북도']
    
    def _generate_fake_emails(self) -> list:
        """가짜 이메일 생성"""
        fake_emails = []
        domains = ['example.com', 'test.co.kr', 'sample.net', 'demo.org']
        for i in range(1000):
            fake_emails.append(f"user{i:03d}@{domains[i % len(domains)]}")
        return fake_emails
    
    def initialize(self, custom_data: Dict = None):
        """데이터풀 초기화"""
        if self._initialized:
            return
        
        print("데이터풀 초기화 중...")
        
        # 커스텀 데이터만 추가
        if custom_data:
            if 'names' in custom_data:
                filtered_custom_names = set()
                for name in custom_data['names']:
                    if name not in self.name_exclude_words and len(name) >= 2:
                        filtered_custom_names.add(name)
                self.real_names.update(filtered_custom_names)
                print(f"커스텀 이름 {len(filtered_custom_names)}개 추가")
        
        self._initialized = True
        
        print(f"데이터풀 초기화 완료:")
        print(f"  - 실명: {len(self.real_names)}개")
        print(f"  - 시/도: {len(self.provinces)}개")
        print(f"  - 시: {len(self.cities)}개") 
        print(f"  - 구/군: {len(self.districts)}개")
        print(f"  - 제외단어: {len(self.name_exclude_words)}개")

# 전역 인스턴스
_pools_instance = None

def get_pools() -> DataPools:
    """DataPools 싱글톤 인스턴스 반환"""
    global _pools_instance
    if _pools_instance is None:
        _pools_instance = DataPools()
    return _pools_instance

def initialize_pools(custom_data: Dict = None):
    """데이터풀 초기화"""
    pools = get_pools()
    pools.initialize(custom_data)

def reload_pools():
    """데이터풀 재로드"""
    global _pools_instance
    _pools_instance = None
    initialize_pools()

def get_data_pool_stats() -> Dict[str, int]:
    """데이터풀 통계 정보"""
    pools = get_pools()
    return {
        "탐지_이름수": len(pools.real_names),
        "탐지_주소수": len(pools.real_addresses),
        "탐지_도로수": len(pools.road_names),
        "탐지_시군구수": len(pools.districts),
        "탐지_시도수": len(pools.provinces),
        "탐지_시수": len(pools.cities),
        "회사수": len(pools.companies)
    }