"""
LLM Service - Unified LLM calling interface with logging and retries
High cohesion: All LLM-related logic in one place
"""

import json
import time
from typing import Dict, List, Optional, Any, Type
from pydantic import BaseModel
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

from backend.config import settings


class LLMResponse(BaseModel):
    """Standard LLM response wrapper."""
    content: str
    parsed: Optional[Dict] = None
    model: str
    tokens_used: int = 0
    latency_ms: int = 0
    success: bool = True
    error: Optional[str] = None


class LLMService:
    """
    Unified LLM Service with:
    - Automatic retries with exponential backoff
    - JSON cleaning (markdown removal)
    - Token tracking
    - Structured logging
    """
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.model = model or getattr(settings, 'OPENAI_MODEL', 'deepseek-chat')
        
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        logger.info(f"[LLMService] Initialized | model={self.model} base_url={self.base_url}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIConnectionError, openai.RateLimitError))
    )
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        json_mode: bool = True,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """
        Make an LLM call with automatic retries and logging.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            temperature: Sampling temperature
            json_mode: Whether to request JSON output
            max_tokens: Maximum response tokens
            
        Returns:
            LLMResponse with content and metadata
        """
        start_time = time.time()
        call_id = f"{int(start_time * 1000) % 100000}"
        
        logger.debug(f"[LLMService] Call started | id={call_id} json_mode={json_mode}")
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if json_mode else None
            )
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Parse JSON if requested
            parsed = None
            if json_mode:
                try:
                    cleaned = self._clean_json(content)
                    parsed = json.loads(cleaned)
                except json.JSONDecodeError as e:
                    logger.warning(f"[LLMService] JSON parse failed | id={call_id} error={e}")
            
            logger.info(
                f"[LLMService] Call success | id={call_id} "
                f"tokens={tokens_used} latency={latency_ms}ms"
            )
            
            return LLMResponse(
                content=content,
                parsed=parsed,
                model=self.model,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                success=True
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[LLMService] Call failed | id={call_id} error={e}")
            
            return LLMResponse(
                content="",
                model=self.model,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )
    
    async def call_with_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[BaseModel],
        temperature: float = 0.7
    ) -> tuple[Optional[BaseModel], LLMResponse]:
        """
        Call LLM and validate response against a Pydantic schema.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            schema: Pydantic model class to validate against
            temperature: Sampling temperature
            
        Returns:
            Tuple of (parsed model or None, raw response)
        """
        response = await self.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            json_mode=True
        )
        
        if not response.success or not response.parsed:
            return None, response
        
        try:
            validated = schema.model_validate(response.parsed)
            return validated, response
        except Exception as e:
            logger.warning(f"[LLMService] Schema validation failed | error={e}")
            return None, response
    
    def _clean_json(self, content: str) -> str:
        """Remove markdown code blocks from JSON response."""
        content = content.strip()
        
        # Remove leading markdown
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        
        # Remove trailing markdown
        if content.endswith('```'):
            content = content[:-3]
        
        return content.strip()


# Singleton instance for reuse
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create singleton LLM service."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
