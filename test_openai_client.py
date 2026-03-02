#!/usr/bin/env python3
"""
Test OpenAI client compatibility with Ollama.
"""

import sys
import time

def test_openai_client():
    """Test OpenAI client with Ollama."""
    print("Testing OpenAI client with Ollama...")

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
            timeout=30.0
        )

        # Test list models
        print("1. Testing model listing...")
        models = client.models.list()
        print(f"   Models: {[model.id for model in models.data[:3]]}...")

        # Test simple chat completion
        print("2. Testing simple chat completion...")
        start = time.time()
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": "Say hello in Chinese"}
            ],
            model="llama3:8b",
            temperature=0.1,
            max_tokens=20,
            timeout=60.0
        )

        elapsed = time.time() - start
        response = chat_completion.choices[0].message.content
        print(f"   Response after {elapsed:.1f}s: {response}")

        # Test with extraction-like prompt
        print("3. Testing extraction-like prompt...")
        test_text = "vsp文件夹是继电保护器模块"
        prompt = f"""Extract entities from this text: {test_text}

Return JSON: [{{"text": "entity", "type": "type"}}]"""

        start = time.time()
        extraction_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="llama3:8b",
            temperature=0.1,
            max_tokens=100,
            timeout=120.0
        )

        elapsed = time.time() - start
        extraction_response = extraction_completion.choices[0].message.content
        print(f"   Response after {elapsed:.1f}s: {extraction_response[:200]}...")

        print("\n✅ OpenAI client compatible with Ollama!")
        return True

    except Exception as e:
        print(f"\n❌ OpenAI client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_openai_client()
    sys.exit(0 if success else 1)