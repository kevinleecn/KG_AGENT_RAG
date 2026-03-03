"""
简单测试融合问答引擎 - 避免 Unicode 问题
"""
import os
import sys
import io

# 设置 UTF-8 编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 从配置管理器加载配置
from config.config_manager import get_config_manager
config_manager = get_config_manager()
llm_config = config_manager.get_llm_config()
neo4j_config = config_manager.get_neo4j_config()

os.environ['OPENAI_API_KEY'] = llm_config.get('api_key', 'your-api-key')
os.environ['NEO4J_USER'] = neo4j_config.get('username', 'neo4j')
os.environ['NEO4J_PASSWORD'] = neo4j_config.get('password', 'your-password')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.qa.fusion_qa_engine import FusionKGQAEngine

def main():
    print("=" * 60)
    print("Testing Fusion KG-LLM QA Engine")
    print("=" * 60)

    engine = FusionKGQAEngine()

    # Test 1: Question classification
    print("\n[Test 1] Question Classification")
    print("-" * 40)

    test_cases = [
        ("你是谁？", "llm_only"),
        ("你是哪个模型？", "llm_only"),
        ("阿里巴巴的 CEO 是谁？", "kg_only"),
        ("张三和李四有什么关系？", "kg_llm_fusion"),
        ("你好", "chat"),
    ]

    all_passed = True
    for question, expected in test_cases:
        actual = engine._classify_question(question)
        status = "PASS" if actual == expected else "FAIL"
        if actual != expected:
            all_passed = False
        print(f"  {status}: '{question}' -> {actual}")

    print(f"\nClassification: {'ALL PASSED' if all_passed else 'SOME FAILED'}")

    # Test 2: LLM-only questions (like "你是谁")
    print("\n[Test 2] LLM-Only Questions (e.g., '你是谁')")
    print("-" * 40)

    questions = [
        "你是谁？",
        "你是哪个大模型？",
        "介绍一下你自己",
    ]

    for question in questions:
        print(f"\nQ: {question}")
        response = engine.ask_question(question)
        answer = response.get('answer', 'No answer')
        qtype = response.get('metadata', {}).get('question_type', 'unknown')
        print(f"A: {answer[:150]}...")
        print(f"Type: {qtype}, Confidence: {response.get('confidence', 0):.0%}")

    # Test 3: API endpoint
    print("\n[Test 3] API Endpoint Test")
    print("-" * 40)

    try:
        import requests
        response = requests.post(
            "http://localhost:5000/chat/ask-enhanced",
            json={"question": "你是谁？"},
            timeout=30
        )
        result = response.json()
        print(f"API Response: {result.get('answer', 'N/A')[:100]}...")
        print(f"Question Type: {result.get('metadata', {}).get('question_type', 'N/A')}")
    except requests.exceptions.ConnectionError:
        print("Server not running. Start Flask app to test API.")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
