"""Test LLM API key from database"""
import asyncio
import json

from backend.database import AsyncSessionLocal
from backend.services.credentials_service import CredentialsService, CredentialKey

async def test_llm_key():
    async with AsyncSessionLocal() as db:
        service = CredentialsService(db)
        
        # Get stored credentials
        api_key = await service.get_credential(CredentialKey.OPENAI_API_KEY, "OPENAI_API_KEY")
        base_url = await service.get_credential(CredentialKey.OPENAI_BASE_URL, "OPENAI_BASE_URL")
        model = await service.get_credential(CredentialKey.OPENAI_MODEL, "OPENAI_MODEL")
        
        if api_key and len(api_key) > 12:
            masked_key = f"{api_key[:8]}...{api_key[-4:]}"
        else:
            masked_key = "NOT SET or TOO SHORT"
        
        print(f"API Key: {masked_key}")
        print(f"Base URL: {base_url}")
        print(f"Model: {model}")
        
        if not api_key:
            print("ERROR: No API key found!")
            return
        
        # Test LLM call
        import openai
        client = openai.AsyncOpenAI(
            api_key=api_key, 
            base_url=base_url or "https://api.deepseek.com/v1"
        )
        
        print("\nTesting LLM call...")
        response = await client.chat.completions.create(
            model=model or "deepseek-chat",
            messages=[{"role": "user", "content": "Say hello in 3 words"}],
            max_tokens=200
        )

        # Verify actual returned content and structure
        try:
            choices = response.choices or []
            print(f"choices_len={len(choices)}")
            if choices:
                ch0 = choices[0]
                msg0 = ch0.message
                content0 = getattr(msg0, "content", None)
                role0 = getattr(msg0, "role", None)
                finish0 = getattr(ch0, "finish_reason", None)
                print(f"finish_reason={finish0}")
                print(f"role={role0}")
                print(f"content_repr={repr(content0)}")

                # Some providers may return additional fields
                reasoning = getattr(msg0, "reasoning_content", None)
                tool_calls = getattr(msg0, "tool_calls", None)
                if reasoning is not None:
                    print(f"reasoning_content_repr={repr(reasoning)}")
                if tool_calls is not None:
                    print(f"tool_calls={tool_calls}")
        except Exception as e:
            print(f"ERROR while inspecting response: {e}")

        # Print a compact dump for debugging (truncate)
        try:
            dump = response.model_dump()
            dump_text = json.dumps(dump, ensure_ascii=False, indent=2)
            print("\nResponse dump (truncated):")
            print(dump_text[:2000])
        except Exception as e:
            print(f"ERROR dumping response: {e}")

        print("\nSUCCESS (request completed without exception)")

if __name__ == "__main__":
    asyncio.run(test_llm_key())
