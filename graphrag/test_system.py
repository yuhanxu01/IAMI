#!/usr/bin/env python3
"""
IAMI GraphRAG 系统测试脚本
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """测试模块导入"""
    print("Testing imports...")
    try:
        from graphrag.indexer import IAMIDataLoader, IAMIGraphIndexerSync, IndexConfig
        from graphrag.visualizer import IAMIGraphVisualizer
        print("✓ All modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_data_loader():
    """测试数据加载器"""
    print("\nTesting data loader...")
    try:
        from graphrag.indexer import IAMIDataLoader

        loader = IAMIDataLoader("./memory")
        documents = loader.load_all_data()

        print(f"✓ Loaded {len(documents)} documents")

        if documents:
            print(f"  Sample document types:")
            types = {}
            for doc in documents:
                doc_type = doc.get('type', 'unknown')
                types[doc_type] = types.get(doc_type, 0) + 1

            for doc_type, count in sorted(types.items()):
                print(f"    - {doc_type}: {count}")

        return True
    except Exception as e:
        print(f"✗ Data loader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """测试配置"""
    print("\nTesting configuration...")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("✗ DEEPSEEK_API_KEY not set")
        print("  Please set it in .env file or environment")
        return False

    print("✓ API key is set")
    return True


def test_visualizer():
    """测试可视化器"""
    print("\nTesting visualizer...")
    try:
        from graphrag.visualizer import IAMIGraphVisualizer

        viz = IAMIGraphVisualizer()
        print("✓ Visualizer initialized")
        return True
    except Exception as e:
        print(f"✗ Visualizer test failed: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 50)
    print("IAMI GraphRAG System Tests")
    print("=" * 50)

    results = []

    # 测试导入
    results.append(("Imports", test_imports()))

    # 测试配置
    results.append(("Configuration", test_config()))

    # 测试数据加载器
    results.append(("Data Loader", test_data_loader()))

    # 测试可视化器
    results.append(("Visualizer", test_visualizer()))

    # 总结
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Set DEEPSEEK_API_KEY in .env file")
        print("2. Run: python graphrag/cli.py build")
        print("3. Run: python graphrag/cli.py query 'your question'")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
