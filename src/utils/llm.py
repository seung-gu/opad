"""Common utilities for OpenAI API calls."""

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment.
    
    Returns:
        OpenAI API key
        
    Raises:
        ValueError: If API key is not configured
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return api_key


def parse_json_from_content(content: str) -> dict | None:
    """Parse JSON from LLM response content.
    
    Handles various formats:
    - Plain JSON: {"key": "value"}
    - JSON in markdown code blocks: ```json {...} ```
    - JSON with surrounding text
    
    Args:
        content: Raw content string from LLM
        
    Returns:
        Parsed JSON dict, or None if parsing fails
    """
    try:
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            json_match = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_match = content.split("```")[1].split("```")[0]
        elif "{" in content:
            # Extract JSON from text that might have surrounding content
            start = content.index("{")
            end = content.rindex("}") + 1
            json_match = content[start:end]
        else:
            json_match = content
        
        return json.loads(json_match.strip())
    except (json.JSONDecodeError, ValueError, IndexError) as e:
        logger.debug("Failed to parse JSON from content", extra={
            "error": str(e),
            "content_preview": content[:200]
        })
        return None


async def call_openai_chat(
    prompt: str,
    model: str = "gpt-4.1-mini",
    max_tokens: int = 200,
    temperature: float = 0,
    timeout: float = 30.0
) -> str:
    """Call OpenAI Chat Completions API.
    
    Args:
        prompt: User prompt/message content
        model: OpenAI model name (default: gpt-4.1-mini)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0 for deterministic)
        timeout: Request timeout in seconds
        
    Returns:
        Content string from LLM response
        
    Raises:
        ValueError: If API key is not configured
        httpx.TimeoutException: If request times out
        httpx.RequestError: If request fails
        RuntimeError: If API returns error or no content
    """
    api_key = get_openai_api_key()
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }],
                "max_tokens": max_tokens,
                "temperature": temperature
            }
        )
        
        if response.status_code != 200:
            error_text = response.text
            logger.error("OpenAI API error", extra={
                "status": response.status_code,
                "error": error_text
            })
            raise RuntimeError(f"OpenAI API error: {response.status_code} - {error_text}")
        
        data = response.json()
        logger.debug("OpenAI API response", extra={"response": data})
        
        # Extract content from response
        content = None
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            if "message" in choice:
                content = choice["message"].get("content", "").strip()
            elif "delta" in choice:
                content = choice["delta"].get("content", "").strip()
        
        if not content:
            logger.error("No content in OpenAI response", extra={"response": data})
            raise RuntimeError("No content returned from OpenAI")
        
        return content


def get_llm_error_response(e: Exception) -> tuple[int, str]:
    """Get HTTP status code and detail message for LLM-related exceptions.
    
    Args:
        e: Exception to handle
        
    Returns:
        Tuple of (status_code, detail_message)
    """
    if isinstance(e, ValueError):
        return (500, "OpenAI API key not configured")
    elif isinstance(e, httpx.TimeoutException):
        return (504, "OpenAI API timeout")
    elif isinstance(e, httpx.RequestError):
        return (503, "OpenAI API unavailable")
    elif isinstance(e, RuntimeError):
        return (500, f"OpenAI API error: {str(e)}")
    else:
        return (500, "Internal server error")
