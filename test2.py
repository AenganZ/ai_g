#!/usr/bin/env python
# check_structure.py - 디렉토리 구조 확인 및 수정

import os
import sys

def check_directory_structure():
    """현재 디렉토리 구조 확인"""
    
    print("📁 현재 디렉토리 구조 확인")
    print("=" * 60)
    
    # 현재 스크립트 위치
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    
    print(f"현재 파일: {current_file}")
    print(f"현재 디렉토리: {current_dir}")
    print(f"작업 디렉토리: {os.getcwd()}")
    
    print("\n📂 디렉토리 내용:")
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        if os.path.isdir(item_path):
            print(f"  📁 {item}/")
            if item == "pseudonymization":
                # pseudonymization 폴더 내용 표시
                for subitem in os.listdir(item_path):
                    print(f"      📄 {subitem}")
        else:
            print(f"  📄 {item}")
    
    print("\n✅ 필수 파일 체크:")
    
    # 필수 파일들
    required = {
        "app.py": "메인 애플리케이션",
        "pseudonymization/__init__.py": "패키지 초기화",
        "pseudonymization/pools.py": "데이터풀 관리",
        "pseudonymization/detection.py": "PII 탐지",
        "pseudonymization/replacement.py": "가명화 치환",
        "pseudonymization/core.py": "통합 인터페이스",
        "pseudonymization/model.py": "NER 모델",
        "pseudonymization/manager.py": "전체 관리",
    }
    
    missing = []
    for filepath, description in required.items():
        full_path = os.path.join(current_dir, filepath)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"  ✅ {filepath} ({size} bytes) - {description}")
        else:
            print(f"  ❌ {filepath} - {description}")
            missing.append(filepath)
    
    # CSV 파일 체크 (선택적)
    print("\n📊 CSV 파일 체크 (선택적):")
    csv_files = ["name.csv", "address_road.csv"]
    for csv_file in csv_files:
        csv_path = os.path.join(current_dir, csv_file)
        if os.path.exists(csv_path):
            print(f"  ✅ {csv_file} 존재")
        else:
            print(f"  ⚠️ {csv_file} 없음 (기본값 사용)")
    
    if missing:
        print(f"\n❌ 누락된 파일: {len(missing)}개")
        for filepath in missing:
            print(f"  - {filepath}")
        
        # pseudonymization 폴더 생성 제안
        pseudo_dir = os.path.join(current_dir, "pseudonymization")
        if not os.path.exists(pseudo_dir):
            print(f"\n💡 pseudonymization 폴더가 없습니다.")
            print(f"   생성하려면: mkdir pseudonymization")
        
        return False
    else:
        print("\n✅ 모든 필수 파일이 존재합니다!")
        return True

def test_import():
    """간단한 import 테스트"""
    print("\n🧪 Import 테스트")
    print("=" * 60)
    
    # 현재 디렉토리를 Python 경로에 추가
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        # 패키지 import 시도
        import pseudonymization
        print("✅ pseudonymization 패키지 import 성공!")
        
        # 버전 정보 출력
        if hasattr(pseudonymization, '__version__'):
            print(f"   버전: {pseudonymization.__version__}")
        if hasattr(pseudonymization, '__title__'):
            print(f"   제목: {pseudonymization.__title__}")
        
        return True
        
    except ImportError as e:
        print(f"❌ pseudonymization 패키지 import 실패: {e}")
        
        # 더 자세한 진단
        pseudo_dir = os.path.join(current_dir, "pseudonymization")
        init_file = os.path.join(pseudo_dir, "__init__.py")
        
        if not os.path.exists(pseudo_dir):
            print("   원인: pseudonymization 폴더가 없습니다")
        elif not os.path.exists(init_file):
            print("   원인: __init__.py 파일이 없습니다")
        else:
            print("   원인: __init__.py 파일에 문법 오류가 있을 수 있습니다")
        
        return False

def main():
    """메인 함수"""
    print("🔍 프로젝트 구조 진단 도구")
    print("=" * 60)
    
    # 1. 디렉토리 구조 확인
    structure_ok = check_directory_structure()
    
    # 2. Import 테스트
    if structure_ok:
        import_ok = test_import()
        
        if import_ok:
            print("\n✅ 시스템 준비 완료!")
            print("\n다음 명령으로 서버를 실행하세요:")
            print("   python app.py")
        else:
            print("\n🔧 해결 방법:")
            print("1. __init__.py 파일에 문법 오류가 없는지 확인")
            print("2. 각 모듈 파일(.py)에 문법 오류가 없는지 확인")
            print("3. 순환 import가 없는지 확인")
    else:
        print("\n🔧 해결 방법:")
        print("1. pseudonymization 폴더를 생성하세요")
        print("2. 모든 모듈 파일을 pseudonymization 폴더에 넣으세요")
        print("3. __init__.py 파일을 pseudonymization 폴더에 넣으세요")
        
        print("\n📝 올바른 구조:")
        print("""
prompt-pseudonymization-server/
│
├── app.py
├── check_structure.py (이 파일)
├── test_imports.py
│
├── pseudonymization/
│   ├── __init__.py
│   ├── pools.py
│   ├── detection.py
│   ├── replacement.py
│   ├── core.py
│   ├── model.py
│   └── manager.py
│
├── name.csv (선택적)
└── address_road.csv (선택적)
        """)

if __name__ == "__main__":
    main()