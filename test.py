#!/usr/bin/env python
# test_imports.py - 모든 모듈 import 테스트

import sys
import os

def test_imports():
    """모든 모듈이 제대로 import 되는지 테스트"""
    
    print("=" * 60)
    print("🧪 Import 테스트 시작")
    print("=" * 60)
    
    errors = []
    
    # 1. pools.py 테스트
    try:
        from pseudonymization.pools import (
            DataPools, get_pools, initialize_pools, 
            COMPOUND_SURNAMES, SINGLE_SURNAMES, NAME_EXCLUDE_WORDS
        )
        print("✅ pools.py import 성공")
    except Exception as e:
        print(f"❌ pools.py import 실패: {e}")
        errors.append(("pools.py", e))
    
    # 2. detection.py 테스트
    try:
        from pseudonymization.detection import (
            detect_pii_enhanced, detect_with_ner, detect_with_regex,
            detect_names_from_csv, detect_addresses_from_csv, merge_detections
        )
        print("✅ detection.py import 성공")
    except Exception as e:
        print(f"❌ detection.py import 실패: {e}")
        errors.append(("detection.py", e))
    
    # 3. replacement.py 테스트
    try:
        from pseudonymization.replacement import (
            ReplacementManager, apply_replacements, 
            restore_text, remove_duplicates
        )
        print("✅ replacement.py import 성공")
    except Exception as e:
        print(f"❌ replacement.py import 실패: {e}")
        errors.append(("replacement.py", e))
    
    # 4. model.py 테스트
    try:
        from pseudonymization.model import (
            load_ner_model, is_ner_loaded, 
            extract_entities_with_ner, get_ner_model
        )
        print("✅ model.py import 성공")
    except Exception as e:
        print(f"❌ model.py import 실패: {e}")
        errors.append(("model.py", e))
    
    # 5. core.py 테스트
    try:
        from pseudonymization.core import (
            pseudonymize_text, restore_original,
            load_data_pools, get_data_pool_stats
        )
        print("✅ core.py import 성공")
    except Exception as e:
        print(f"❌ core.py import 실패: {e}")
        errors.append(("core.py", e))
    
    # 6. manager.py 테스트
    try:
        from pseudonymization.manager import (
            PseudonymizationManager, get_manager,
            is_manager_ready, get_manager_status
        )
        print("✅ manager.py import 성공")
    except Exception as e:
        print(f"❌ manager.py import 실패: {e}")
        errors.append(("manager.py", e))
    
    # 7. __init__.py 전체 테스트
    try:
        import pseudonymization
        print("✅ pseudonymization 패키지 전체 import 성공")
    except Exception as e:
        print(f"❌ pseudonymization 패키지 import 실패: {e}")
        errors.append(("__init__.py", e))
    
    # 결과 출력
    print("=" * 60)
    if errors:
        print(f"❌ {len(errors)}개 모듈에서 오류 발생:")
        for module, error in errors:
            print(f"   - {module}: {error}")
        print("\n🔧 해결 방법:")
        print("1. 위의 오류 메시지를 확인하세요")
        print("2. 누락된 함수나 클래스를 추가하세요")
        print("3. 순환 import가 있는지 확인하세요")
    else:
        print("✅ 모든 모듈 import 성공!")
        
        # 간단한 기능 테스트
        try:
            print("\n📝 간단한 기능 테스트:")
            
            # 데이터풀 초기화
            from pseudonymization import initialize_pools, get_pools
            initialize_pools()
            pools = get_pools()
            print(f"   데이터풀: {len(pools.names)}개 이름")
            
            # 가명화 테스트
            from pseudonymization import pseudonymize_text
            result = pseudonymize_text("테스트 010-1234-5678")
            print(f"   가명화 테스트: OK")
            
            print("\n✅ 시스템 준비 완료! app.py를 실행할 수 있습니다.")
            
        except Exception as e:
            print(f"\n⚠️ 기능 테스트 실패: {e}")
    
    return len(errors) == 0

if __name__ == "__main__":
    # 현재 디렉토리를 Python 경로에 추가
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    # 테스트 실행
    success = test_imports()
    
    # 종료 코드
    sys.exit(0 if success else 1)