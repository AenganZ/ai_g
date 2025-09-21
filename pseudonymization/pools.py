# pseudonymization/pools.py
"""
가명 데이터풀 관리 모듈
탐지된 PII를 치환할 가명 데이터 관리
(탐지는 detection.py에서 CSV 파일 활용)
"""

import os
import random
import json
from typing import List, Dict, Any, Optional

# ==================== 복합 성씨 ====================
COMPOUND_SURNAMES = [
    '남궁', '황보', '제갈', '사공', '선우', '서문', '독고', '동방',
    '갈', '견', '경', '계', '고', '공', '곽', '구', '국', '궁', '궉', '금',
    '기', '길', '나', '남', '노', '뇌', '누', '단', '담', '당', '대', '도',
    '독고', '동', '동방', '두', '라', '랑', '려', '련', '렴', '로', '루', '류'
]

# ==================== 단일 성씨 ====================
SINGLE_SURNAMES = [
    '김', '이', '박', '최', '정', '강', '조', '윤', '장', '임',
    '한', '오', '서', '신', '권', '황', '안', '송', '류', '전',
    '홍', '고', '문', '양', '손', '배', '백', '허', '유', '남',
    '심', '노', '하', '곽', '성', '차', '주', '우', '구', '민'
]

# ==================== 가명용 기본 데이터 ====================
# 가명 생성에 사용할 단어들
FAKE_KEYWORDS = [
    '테스트', '가명', '익명', '무명', '사용자', '샘플', '더미', '임시'
]



# ==================== 제외 단어 리스트 (이름으로 오인되는 것들) ====================
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
    '거주', '근무', '방문', '이용', '가입', '탈퇴', '참석', '참여'
}

# ==================== 주소 데이터 ====================
# 시/도
PROVINCES = [
    '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'
]

# 시/군/구
DISTRICTS = [
    '강남구', '서초구', '송파구', '강동구', '마포구', '용산구', '종로구', '중구',
    '해운대구', '부산진구', '동래구', '사하구', '남동구', '부평구', '계양구',
    '수원시', '성남시', '고양시', '용인시', '부천시', '안산시', '안양시',
    '남양주시', '화성시', '평택시', '의정부시', '파주시', '시흥시'
]

# 동/읍/면
NEIGHBORHOODS = [
    '역삼동', '삼성동', '청담동', '논현동', '신사동', '압구정동', '대치동',
    '도곡동', '개포동', '일원동', '수서동', '세곡동', '자곡동', '율현동',
    '서초동', '반포동', '방배동', '양재동', '우면동', '원지동', '잠원동',
    '명동', '을지로', '충무로', '회현동', '남대문로', '북창동', '다동'
]

# ==================== 회사 데이터 ====================
COMPANIES = [
    # IT/테크
    '삼성전자', 'LG전자', 'SK하이닉스', '네이버', '카카오', '쿠팡', '배달의민족',
    '토스', '당근마켓', '야놀자', '컬리', '무신사', '지그재그', '에이블리',
    
    # 대기업
    '현대자동차', '기아', '포스코', '현대중공업', 'LG화학', 'SK이노베이션',
    '롯데그룹', '한화그룹', 'GS그룹', 'CJ그룹', '두산그룹', '한진그룹',
    
    # 금융
    'KB국민은행', '신한은행', '하나은행', '우리은행', '삼성증권', '미래에셋',
    
    # 유통/소비재
    '신세계', '롯데백화점', '현대백화점', '이마트', '홈플러스', '롯데마트',
    'CU', 'GS25', '세븐일레븐', '이디야커피', '스타벅스코리아', '맥도날드'
]

# ==================== 데이터풀 클래스 ====================
class DataPools:
    """데이터풀 관리 클래스"""
    
    def __init__(self):
        self.names = []
        self.fake_names = []
        self.emails = []
        self.phones = []
        self.addresses = []
        self.companies = []
        self._initialized = False
    
    def initialize(self, custom_data: Dict[str, List[str]] = None):
        """데이터풀 초기화 (가명 생성용만)"""
        print("📂 가명 데이터풀 초기화 중...")
        
        # 1. 가명용 이름 생성 (실제 이름이 아닌 가짜 이름)
        self.names = self._generate_fake_full_names()
        
        # 2. 가명 이름 생성 (익명001 등)
        self.fake_names = self._generate_fake_names()
        
        # 3. 이메일 생성
        self.emails = self._generate_emails()
        
        # 4. 전화번호 생성
        self.phones = self._generate_phones()
        
        # 5. 간소화된 주소 생성 (시/도 위주)
        self.addresses = self._generate_simple_addresses()
        
        # 6. 회사명
        self.companies = COMPANIES.copy()
        
        # 7. 커스텀 데이터 추가
        if custom_data:
            self._add_custom_data(custom_data)
        
        self._initialized = True
        self._print_stats()
    
    def _generate_fake_full_names(self) -> List[str]:
        """가명용 전체 이름 생성 (치환용)"""
        fake_full_names = []
        
        # 테스트용 유명인 이름들 (가명으로 사용)
        fake_full_names.extend([
            '홍길동', '김철수', '이영희', '박민수', '최지은',
            '정대한', '강미나', '조현우', '윤서연', '장동건'
        ])
        
        # 성씨 + 가명 조합
        for surname in SINGLE_SURNAMES[:10]:  # 주요 성씨만
            fake_full_names.extend([
                surname + '테스트',
                surname + '유저',
                surname + '샘플'
            ])
        
        return fake_full_names
    
    def _generate_simple_addresses(self) -> List[str]:
        """간소화된 주소 생성 (시/도 위주)"""
        addresses = []
        
        # 시/도만 (간소화)
        addresses.extend(PROVINCES)
        
        # 주요 도시 + 구 (몇 개만)
        addresses.extend([
            '서울 강남구', '서울 서초구', '서울 송파구',
            '부산 해운대구', '부산 부산진구',
            '대구 중구', '인천 남동구'
        ])
        
        return addresses
    
    def _generate_fake_names(self) -> List[str]:
        """익명 이름 생성 (익명001 형태)"""
        fake_names = []
        
        # 성씨 + 가명 키워드 (3글자)
        for surname in SINGLE_SURNAMES[:20]:  # 주요 성씨만
            for keyword in FAKE_KEYWORDS:
                if len(keyword) == 2:
                    fake_names.append(surname + keyword)
                elif len(keyword) == 3:
                    fake_names.append(surname + keyword[:2])
        
        # 특수 가명
        fake_names.extend(['홍길동', '김철수', '이영희', '박민수'])
        fake_names.extend(['A씨', 'B씨', 'C씨', 'X님', 'Y님', 'Z님'])
        
        # 익명001 형태
        for i in range(1, 21):
            fake_names.append(f'익명{i:03d}')
            fake_names.append(f'사용자{i:03d}')
        
        return fake_names
    
    def _generate_emails(self) -> List[str]:
        """이메일 주소 생성"""
        domains = ['gmail.com', 'naver.com', 'daum.net', 'kakao.com', 'hanmail.net']
        prefixes = ['user', 'test', 'sample', 'demo', 'mail', 'info']
        
        emails = []
        for i in range(100):
            prefix = random.choice(prefixes)
            number = random.randint(1000, 9999)
            domain = random.choice(domains)
            emails.append(f"{prefix}{number}@{domain}")
        
        return emails
    
    def _generate_phones(self) -> List[str]:
        """전화번호 생성"""
        phones = []
        
        # 010 번호 (주요)
        for i in range(100):
            middle = random.randint(0, 9999)
            last = random.randint(0, 9999)
            phones.append(f"010-{middle:04d}-{last:04d}")
        
        # 다른 번호
        prefixes = ['011', '016', '017', '018', '019']
        for prefix in prefixes:
            for i in range(5):
                middle = random.randint(0, 9999)
                last = random.randint(0, 9999)
                phones.append(f"{prefix}-{middle:04d}-{last:04d}")
        
        return phones
    

    
    def _add_custom_data(self, custom_data: Dict[str, List[str]]):
        """커스텀 데이터 추가"""
        if 'names' in custom_data:
            self.names.extend(custom_data['names'])
        if 'fake_names' in custom_data:
            self.fake_names.extend(custom_data['fake_names'])
        if 'emails' in custom_data:
            self.emails.extend(custom_data['emails'])
        if 'phones' in custom_data:
            self.phones.extend(custom_data['phones'])
        if 'addresses' in custom_data:
            self.addresses.extend(custom_data['addresses'])
        if 'companies' in custom_data:
            self.companies.extend(custom_data['companies'])
    
    def _print_stats(self):
        """통계 출력"""
        print(f"✅ 가명 데이터풀 초기화 완료")
        print(f"   📛 가명용 이름: {len(self.names)}개")
        print(f"   🎭 익명 이름: {len(self.fake_names)}개")
        print(f"   📧 이메일: {len(self.emails)}개")
        print(f"   📱 전화번호: {len(self.phones)}개")
        print(f"   🏠 주소: {len(self.addresses)}개")
        print(f"   🏢 회사: {len(self.companies)}개")
    
    def get_random_name(self) -> str:
        """랜덤 실제 이름 반환"""
        return random.choice(self.names) if self.names else "홍길동"
    
    def get_random_fake_name(self) -> str:
        """랜덤 가명 반환"""
        return random.choice(self.fake_names) if self.fake_names else "익명"
    
    def get_random_email(self) -> str:
        """랜덤 이메일 반환"""
        return random.choice(self.emails) if self.emails else "user@example.com"
    
    def get_random_phone(self) -> str:
        """랜덤 전화번호 반환"""
        return random.choice(self.phones) if self.phones else "010-0000-0000"
    
    def get_random_address(self) -> str:
        """랜덤 주소 반환 (간소화된)"""
        # 주로 시/도 단위로 반환 (간소화)
        # 먼저 시/도만 있는 것 찾기
        simple_addresses = [addr for addr in self.addresses 
                          if addr in PROVINCES or len(addr.split()) == 1]
        
        if simple_addresses:
            return random.choice(simple_addresses)
        
        # 없으면 시/도 + 시/군/구 형태
        two_part_addresses = [addr for addr in self.addresses 
                             if len(addr.split()) == 2]
        
        if two_part_addresses:
            return random.choice(two_part_addresses)
        
        # 그것도 없으면 아무거나
        return random.choice(self.addresses) if self.addresses else "서울"
    
    def get_random_company(self) -> str:
        """랜덤 회사명 반환"""
        return random.choice(self.companies) if self.companies else "테스트회사"
    
    def is_excluded_name(self, text: str) -> bool:
        """제외할 이름인지 확인"""
        return text in NAME_EXCLUDE_WORDS
    
    def save_to_file(self, filepath: str = "pools_backup.json"):
        """데이터풀을 파일로 저장"""
        data = {
            "names": self.names,
            "fake_names": self.fake_names,
            "emails": self.emails,
            "phones": self.phones,
            "addresses": self.addresses,
            "companies": self.companies
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"📁 데이터풀 저장됨: {filepath}")
    
    def load_from_file(self, filepath: str = "pools_backup.json"):
        """파일에서 데이터풀 로드"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.names = data.get('names', [])
            self.fake_names = data.get('fake_names', [])
            self.emails = data.get('emails', [])
            self.phones = data.get('phones', [])
            self.addresses = data.get('addresses', [])
            self.companies = data.get('companies', [])
            
            self._initialized = True
            print(f"📂 데이터풀 로드됨: {filepath}")
            self._print_stats()
        else:
            print(f"⚠️ 파일 없음: {filepath}")
            self.initialize()

# ==================== 전역 인스턴스 ====================
_pools_instance = None

def get_pools() -> DataPools:
    """데이터풀 싱글톤 인스턴스 반환"""
    global _pools_instance
    
    if _pools_instance is None:
        _pools_instance = DataPools()
        _pools_instance.initialize()
    
    return _pools_instance

def initialize_pools(custom_data: Dict[str, List[str]] = None):
    """데이터풀 초기화"""
    pools = get_pools()
    if not pools._initialized:
        pools.initialize(custom_data)

def reload_pools():
    """데이터풀 재로드"""
    global _pools_instance
    _pools_instance = DataPools()
    _pools_instance.initialize()
    print("🔄 데이터풀 재로드 완료")

# ==================== 테스트 ====================
if __name__ == "__main__":
    print("🎭 가명 데이터풀 모듈 테스트")
    print("=" * 60)
    
    # 초기화
    pools = get_pools()
    
    print("\n📝 가명 생성 샘플:")
    print(f"   가명 이름: {pools.get_random_name()}")
    print(f"   익명 이름: {pools.get_random_fake_name()}")
    print(f"   가짜 이메일: {pools.get_random_email()}")
    print(f"   가짜 전화번호: {pools.get_random_phone()}")
    print(f"   대체 주소: {pools.get_random_address()}")
    print(f"   대체 회사: {pools.get_random_company()}")
    
    # 복합 성씨 가명 테스트
    print("\n🏛️ 복합 성씨 가명 예시:")
    compound_fake_names = [name for name in pools.fake_names 
                          if any(name.startswith(s) for s in COMPOUND_SURNAMES)]
    if compound_fake_names:
        print(f"   {compound_fake_names[:5]}")
    else:
        print("   복합 성씨 가명 없음")
    
    # 제외 단어 테스트
    print("\n🚫 제외 단어 테스트:")
    test_words = ["김철수", "고객", "사용자", "홍길동"]
    for word in test_words:
        print(f"   '{word}' 제외?: {pools.is_excluded_name(word)}")