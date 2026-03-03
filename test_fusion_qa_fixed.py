"""
测试 KG-LLM 融合问答引擎 - 修复 Windows 编码问题
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

def test_question_classification():
    """测试问题分类"""
    print("=" * 60)
    print("测试问题分类")
    print("=" * 60)

    engine = FusionKGQAEngine()

    test_cases = [
        ("你是谁？", "llm_only", "助手身份"),
        ("你是哪个模型？", "llm_only", "模型询问"),
        ("解释一下量子力学", "llm_only", "通用知识"),
        ("阿里巴巴的 CEO 是谁？", "kg_only", "图谱检索"),
        ("张三和李四有什么关系？", "kg_llm_fusion", "关系查询"),
        ("如果人工智能取代人类工作会怎样？", "kg_llm_fusion", "假设性问题"),
        ("比较阿里巴巴和腾讯", "kg_llm_fusion", "实体比较"),
        ("你好", "chat", "问候"),
        ("谢谢", "chat", "感谢"),
    ]

    correct = 0
    for question, expected_type, description in test_cases:
        actual_type = engine._classify_question(question)
        status = "OK" if actual_type == expected_type else "FAIL"
        if actual_type == expected_type:
            correct += 1
        print(f"{status} {description}: '{question}' -> {actual_type} (expected: {expected_type})")

    print(f"\n分类准确率：{correct}/{len(test_cases)} = {correct/len(test_cases)*100:.0f}%")
    print()

def test_assistant_info():
    """测试助手信息查询"""
    print("=" * 60)
    print("测试助手信息查询")
    print("=" * 60)

    engine = FusionKGQAEngine()
    info = engine.get_assistant_info()

    print(f"助手名称：{info['name']}")
    print(f"模型：{info['model']}")
    print(f"LLM 可用：{info['llm_available']}")
    print(f"KG 可用：{info['kg_available']}")
    print("能力:")
    for cap in info['capabilities']:
        print(f"  - {cap}")

    print()

def test_llm_only_questions():
    """测试 LLM_ONLY 类型问题"""
    print("=" * 60)
    print("测试 LLM_ONLY 问题（直接用 LLM 回答）")
    print("=" * 60)

    engine = FusionKGQAEngine()

    questions = [
        "你是谁？",
        "你是哪个大模型？",
        "你有什么功能？",
        "介绍一下你自己",
    ]

    for question in questions:
        print(f"\n问：{question}")
        response = engine.ask_question(question)
        # 限制输出长度，避免 emoji 编码问题
        answer = response.get('answer', 'No answer')[:150].replace('\n', ' ')
        print(f"答：{answer}...")
        print(f"类型：{response.get('answer_type', 'N/A')}")
        print(f"置信度：{response.get('confidence', 0):.0%}")

    print()

def test_kg_questions():
    """测试 KG 类型问题"""
    print("=" * 60)
    print("测试 KG/融合问题")
    print("=" * 60)

    engine = FusionKGQAEngine()

    questions = [
        "文档中提到了哪些实体？",
        "作者是谁？",
        "这篇文章的关键词是什么？",
    ]

    for question in questions:
        print(f"\n问：{question}")
        response = engine.ask_question(question)
        answer = response.get('answer', 'No answer')[:150].replace('\n', ' ')
        print(f"答：{answer}...")
        print(f"类型：{response.get('answer_type', 'N/A')}")
        print(f"图谱结果数：{len(response.get('evidence', {}).get('graph_results', []))}")

    print()

def test_api_endpoint():
    """测试 API 端点"""
    print("=" * 60)
    print("测试 API 端点")
    print("=" * 60)

    import requests

    base_url = "http://localhost:5000"

    test_questions = [
        "你是谁？",
        "你是哪个模型？",
        "介绍一下你自己",
    ]

    for question in test_questions:
        print(f"\n问：{question}")
        try:
            response = requests.post(
                f"{base_url}/chat/ask-enhanced",
                json={"question": question},
                timeout=30
            )
            result = response.json()
            answer = result.get('answer', 'N/A')[:100].replace('\n', ' ')
            print(f"答：{answer}...")
            print(f"类型：{result.get('metadata', {}).get('question_type', 'N/A')}")
        except requests.exceptions.ConnectionError:
            print("无法连接到服务器，请先启动 Flask 应用")
        except Exception as e:
            print(f"错误：{e}")

    print()

if __name__ == "__main__":
    print("KG-LLM 融合问答引擎测试\n")

    # 运行所有测试
    test_question_classification()
    test_assistant_info()
    test_llm_only_questions()
    test_kg_questions()
    test_api_endpoint()

    print("\n测试完成！")
