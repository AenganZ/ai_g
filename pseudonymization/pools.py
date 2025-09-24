# pseudonymization/pools.py - 모듈화된 데이터풀 (import 오류 수정)
import random
from typing import List, Set, Dict, Any

class DataPools:
    """데이터풀 관리 클래스"""
    
    def __init__(self):
        # 실제 가명 데이터풀 (숫자 없음)
        self.fake_names = [
            "김가명", "이가명", "박무명", "최가명", "정무명", "홍가명", 
            "조무명", "윤가명", "장무명", "임가명", "한가명", "오무명",
            "서가명", "신무명", "권가명", "황무명", "안가명", "송무명",
            "전가명", "홍무명", "고가명", "강무명", "조가명", "윤무명",
            "유가명", "백무명", "남가명", "노무명", "문가명", "변무명"
        ]
        
        self.fake_emails = [
            "user001@example.com", "user002@test.co.kr", "user003@gmail.com", 
            "user004@naver.com", "user005@daum.net", "user006@yahoo.com",
            "user007@hotmail.com", "user008@outlook.com", "user009@live.com",
            "user010@kakao.com"
        ]
        
        self.fake_phones = []  # 동적 생성
        
        self.fake_addresses = [
            "서울", "부산", "대구", "인천", "광주", "대전", 
            "울산", "세종", "경기", "강원", "충북", "충남",
            "전북", "전남", "경북", "경남", "제주"
        ]
        
        # 실명 목록 (확실한 이름들만)
        self.real_names = [
            "민준", "서준", "도윤", "예준", "시우", "주원", "하준", "지호", 
            "지후", "준우", "현우", "준서", "도현", "지훈", "건우", "우진",
            "서연", "서윤", "서현", "지우", "민서", "하윤", "하은", "윤서", 
            "채원", "지윤", "지유", "지민", "지원", "지안", "수아", "은서",
            "김철수", "이영희", "박민수", "최수영", "정다은", "홍길동", 
            "조민지", "윤서연", "장우진", "임수빈", "한지우", "오채원",
            "김민준", "이서연", "박도현", "최지우", "정하은", "홍준서",
            "조채원", "윤지호", "장서현", "임민서", "한지훈", "오하윤"
        ]
        
        # 강화된 제외 단어 목록
        self.name_exclude_words = {
            # 문법 요소
            "이름은", "이고", "이며", "라고", "입니다", "이에요", "예요", "이야", "야",
            "으로", "로", "에서", "에게", "에게서", "한테", "에", "을", "를", "이", "가",
            "은", "는", "의", "와", "과", "하고", "랑", "이랑", "께", "한", "만", "도", 
            
            # 지역명
            "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
            "충북", "충남", "전북", "전남", "경북", "경남", "제주", "강남", "서초", "중구",
            "해운대", "동구", "서구", "남구", "북구", "수영구", "연제구", "사하구",
            
            # 동사/형용사
            "거주하시", "분이시죠", "이시", "하시", "드시", "하세요", "드세요", "주세요",
            "가세요", "오세요", "보세요", "메일", "보내", "받으", "연락", "문의", "예약", 
            "확인", "살고", "있습니다",
            
            # 일반 명사 (고객 포함!)
            "고객", "고객님", "손님", "회원", "회원님", "선생님", "교수님", "대표님", 
            "사장님", "부장님", "과장님", "팀장님", "매니저님", "직원", "학생", "선생", 
            "교수", "의사", "간호사", "경찰", "소방관", "군인", "공무원", "회사원",
            "선배", "후배", "동료", "친구", "지인", "가족", "부모", "자녀", "형제", "자매",
            
            # 기타
            "사람", "사람들", "분들", "여러분", "모든", "모두", "전부", "일부"
        }
        
        # 하드코딩된 주소 데이터
        self.address_data = self._get_hardcoded_address_data()
        
        # 전국 시/도
        self.provinces = self.address_data.get("provinces", [])
        
        # 전국 시/구/군
        self.cities = self.address_data.get("cities", [])
        
        # 도로명
        self.roads = self.address_data.get("roads", [])
        
        self.districts = self.address_data.get("districts", [])
        
        # 카운터들
        self.name_counter = 0
        self.phone_counter = 0
        self.email_counter = 0
        self.address_counter = 0
    
    def _get_hardcoded_address_data(self) -> Dict[str, List[str]]:
        """하드코딩된 주소 데이터 반환 (김포 및 새로운 지역 추가)"""
        return {
            "provinces": [
                "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", 
                "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"
            ],
            "cities": [
                # 서울 구
                "강남", "서초", "중구", "종로", "용산", "성동", "광진", "동대문", "중랑", 
                "성북", "강북", "도봉", "노원", "은평", "서대문", "마포", "양천", "강서", 
                "구로", "금천", "영등포", "동작", "관악", "송파", "강동",
                # 부산 구/군
                "해운대", "수영", "연제", "동래", "남", "북", "동", "서", "중", "영도", 
                "부산진", "사상", "사하", "강서", "기장",
                # 대구 구/군
                "수성", "달성", "달서", "서", "중", "동", "남", "북",
                # 인천 구/군
                "남동", "부평", "계양", "서", "중", "동", "연수", "미추홀", "강화", "옹진",
                # 광주 구
                "서", "남", "동", "북", "광산",
                # 대전 구
                "유성", "서", "중", "동", "대덕",
                # 울산 구/군
                "남", "동", "북", "중", "울주",
                # 경기도 주요 시/군 (김포 추가!)
                "수원", "성남", "고양", "용인", "부천", "안산", "안양", "남양주", "화성", 
                "평택", "의정부", "시흥", "파주", "김포", "광명", "광주", "군포", "오산",
                "하남", "양주", "구리", "안성", "포천", "의왕", "여주", "동두천", "과천",
                # 기타 주요 시/군
                "청주", "천안", "전주", "포항", "창원", "마산", "진주", "순천", "목포",
                "여수", "군산", "익산", "정읍", "남원", "김제", "완주", "고창", "부안",
                "춘천", "원주", "강릉", "동해", "태백", "속초", "삼척",
                "제천", "충주", "단양", "음성", "진천", "괴산", "증평", "보은", "옥천", "영동",
                "서산", "당진", "아산", "공주", "보령", "논산", "계룡", "금산", "부여", "서천", "청양", "홍성", "예산", "태안"
            ],
            "roads": [
                "강남대", "테헤란", "올림픽", "한강", "세종", "종로", "명동", "충무", "퇴계", 
                "을지", "소공", "남대문", "북창", "다동", "인사", "관철", "견지", "삼일", 
                "돈화문", "안국", "화개", "재동", "계동", "가회", "삼청", "팔판", "효자", 
                "통인", "자하문", "청운", "누상", "누하", "옥인", "해운대", "광안", "센텀", 
                "동래", "서면", "남포", "중앙", "동성", "서부", "수성", "달성", "동대구", 
                "신천", "반월당", "두류", "평리", "송도", "구월", "부평", "계양", "청라",
                "상무", "수완", "첨단", "유성", "둔산", "은행", "대덕", "삼성", "진해", "마산",
                "김포공항", "구래", "양촌", "대곶", "통진", "하성", "월곶", "장기", "운양",
                "판교", "분당", "일산", "중동", "송도신도시", "동탄", "광교", "위례", "검단"
            ],
            "districts": []
        }
    
    def get_fake_name(self) -> str:
        """실제 가명 반환 (숫자 없음)"""
        if self.name_counter < len(self.fake_names):
            name = self.fake_names[self.name_counter]
            self.name_counter += 1
            return name
        else:
            # 풀이 부족하면 재사용
            return random.choice(self.fake_names)
    
    def get_fake_phone(self) -> str:
        """가짜 전화번호 반환 (010-0000-0000부터 1씩 증가)"""
        phone = f"010-0000-{self.phone_counter:04d}"
        self.phone_counter += 1
        return phone
    
    def get_fake_email(self) -> str:
        """가짜 이메일 반환"""
        if self.email_counter < len(self.fake_emails):
            email = self.fake_emails[self.email_counter]
            self.email_counter += 1
            return email
        else:
            # 패턴 기반 생성
            email = f"user{self.email_counter:03d}@example.com"
            self.email_counter += 1
            return email
    
    def get_fake_address(self) -> str:
        """가짜 주소 반환 (시/도 단위)"""
        if self.address_counter < len(self.fake_addresses):
            addr = self.fake_addresses[self.address_counter]
            self.address_counter += 1
            return addr
        else:
            return random.choice(self.fake_addresses)
    
    def reset_counters(self):
        """카운터 리셋"""
        self.name_counter = 0
        self.phone_counter = 0
        self.email_counter = 0
        self.address_counter = 0

# 전역 인스턴스
_data_pools = None

def get_pools() -> DataPools:
    """데이터풀 인스턴스 반환"""
    global _data_pools
    if _data_pools is None:
        _data_pools = DataPools()
    return _data_pools

def initialize_pools():
    """데이터풀 초기화"""
    global _data_pools
    _data_pools = DataPools()
    print("데이터풀 초기화 완료")

def reload_pools():
    """데이터풀 재로드"""
    initialize_pools()

def get_data_pool_stats() -> Dict[str, Any]:
    """데이터풀 통계 반환"""
    pools = get_pools()
    
    return {
        "real_names": len(pools.real_names),
        "fake_names": len(pools.fake_names),
        "fake_emails": len(pools.fake_emails),
        "fake_addresses": len(pools.fake_addresses),
        "exclude_words": len(pools.name_exclude_words),
        "provinces": len(pools.provinces),
        "cities": len(pools.cities),
        "roads": len(pools.roads) if hasattr(pools, 'roads') else 0,
        "districts": len(pools.districts),
        "address_data_loaded": True,
        "counters": {
            "name_counter": pools.name_counter,
            "phone_counter": pools.phone_counter,
            "email_counter": pools.email_counter,
            "address_counter": pools.address_counter
        }
    }

# 호환성을 위한 변수들 (필요한 것만 유지)
NAME_EXCLUDE_WORDS = get_pools().name_exclude_words