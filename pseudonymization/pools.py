# Pools module
import secrets
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class Pool:
    name: List[str]
    phone: List[str]
    email: List[str]
    address: List[str]

DEFAULT_POOL = Pool(
    name=["홍길동","김철수","이영희","박민준","최서연","정우진","윤아름","장도윤","서지민","조하린",
          "한도현","임가은","강시우","오지훈","문다은","신태현","배서윤","권지후","백나윤","우재민"],
    phone=["010-1111-2222","010-2222-3333","010-3333-4444","010-4444-5555","010-5555-6666",
           "010-6666-7777","010-7777-8888","010-8888-9999","010-0000-1111","010-1212-3434",
           "010-9090-8080","010-4545-6767"],
    email=["name1@example.com","name2@example.com","mask@example.org","foo.bar@masked.co.kr",
           "user1@test.com","user2@test.com","sample@demo.kr","masked@privacy.net"],
    address=["서울특별시","부산광역시","대구광역시","인천광역시","광주광역시","대전광역시",
             "울산광역시","세종특별자치시","경기도","강원도","충청북도","충청남도"]
)

# 타입별 순환 인덱스
POOL_IDX = {"이름":0, "전화번호":0, "주소":0, "나이":0, "이메일":0}

def next_from_pool(pool_list: List[str], idx: int) -> Tuple[str, int]:
    """풀에서 다음 토큰을 순환적으로 선택"""
    if not pool_list:
        return ("[MASKED]", idx)
    v = pool_list[idx % len(pool_list)]
    return v, idx + 1

def pick_token(token_type: str) -> str:
    """타입별 토큰을 풀에서 하나 선택(라운드로빈; 실패시 랜덤)."""
    try:
        if token_type == "이름":
            token, POOL_IDX["이름"] = next_from_pool(DEFAULT_POOL.name, POOL_IDX["이름"])
            return token
        if token_type == "전화번호":
            token, POOL_IDX["전화번호"] = next_from_pool(DEFAULT_POOL.phone, POOL_IDX["전화번호"])
            return token
        if token_type == "주소":
            token, POOL_IDX["주소"] = next_from_pool(DEFAULT_POOL.address, POOL_IDX["주소"])
            return token
        if token_type == "이메일":
            token, POOL_IDX["이메일"] = next_from_pool(DEFAULT_POOL.email, POOL_IDX["이메일"])
            return token
        if token_type == "나이":
            # 나이는 랜덤하게 20~65 사이
            return str(secrets.randbelow(46) + 20)
    except Exception:
        # 폴백: 랜덤
        pools = {
            "이름": DEFAULT_POOL.name,
            "전화번호": DEFAULT_POOL.phone,
            "주소": DEFAULT_POOL.address,
            "이메일": DEFAULT_POOL.email
        }
        arr = pools.get(token_type, DEFAULT_POOL.name)
        return secrets.choice(arr)
    # 미지정 타입은 그대로 반환 방지용 임의 문자열
    return "MASKED"
