import re
import json
import time
import logging
from typing import List, Any, Type, Optional
from pydantic import BaseModel, ValidationError
import anthropic
from prompts import JSON_REPAIR_SYSTEM, JSON_REPAIR_USER

logger = logging.getLogger(__name__)

def chunk_text(text: str, max_chars: int = 20000) -> List[str]:
    """
    Split text into chunks of at most max_chars, keeping paragraphs intact when possible.
    """
    if not text:
        return []
        
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # If a single paragraph is larger than max_chars, split by sentences or characters
        if len(para) > max_chars:
            # If we have something in current_chunk, push it first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # Split the giant paragraph by sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                if current_length + len(sentence) > max_chars:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = []
                        current_length = 0
                    # If single sentence is too big, hard slice it
                    if len(sentence) > max_chars:
                        chunks.append(sentence[:max_chars])
                    else:
                        current_chunk.append(sentence)
                        current_length = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_length += len(sentence) + 1
        else:
            if current_length + len(para) > max_chars:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_length = len(para)
            else:
                current_chunk.append(para)
                current_length += len(para) + 2
                
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks


def strip_json_fences(text: str) -> str:
    """
    Clean code block wrappers from LLM response (e.g. ```json ... ```)
    """
    text = text.strip()
    # Remove markdown code block markers
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text, flags=re.IGNORECASE)
    return text.strip()


def repair_json_content(raw_text: str, error_msg: str, llm_client, model: str = "claude-3-5-haiku-20241022") -> str:
    """
    Call Claude to fix a malformed JSON string.
    """
    try:
        user_prompt = JSON_REPAIR_USER.format(malformed_text=raw_text, error_message=error_msg)
        response = llm_client.messages.create(
            model=model,
            max_tokens=4000,
            system=JSON_REPAIR_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}]
        )
        repaired = strip_json_fences(response.content[0].text)
        return repaired
    except Exception as e:
        logger.error(f"Failed to repair JSON with LLM: {e}")
        return raw_text


def call_llm_with_retry(
    llm_client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    expected_type: Optional[Type[BaseModel]] = None,
    retries: int = 2
) -> Any:
    """
    Call Anthropic Claude API with exponential backoff on rate limits and transient errors.
    If expected_type is a Pydantic model, parses and validates JSON response, with a repair loop.
    """
    delay = 1.0
    last_error = None
    
    for attempt in range(retries + 1):
        try:
            response = llm_client.messages.create(
                model=model,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            raw_text = response.content[0].text
            clean_text = strip_json_fences(raw_text)
            
            if expected_type is None:
                return clean_text
                
            # Attempt to parse as JSON and validate
            try:
                data = json.loads(clean_text)
                return expected_type.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as parse_err:
                logger.warning(f"JSON parse error on attempt {attempt}: {parse_err}. Attempting repair...")
                # Try repair once
                repaired_text = repair_json_content(clean_text, str(parse_err), llm_client, model)
                try:
                    data = json.loads(repaired_text)
                    return expected_type.model_validate(data)
                except Exception as repair_err:
                    logger.error(f"Repair attempt failed: {repair_err}")
                    raise parse_err
                    
        except anthropic.RateLimitError as rate_err:
            last_error = rate_err
            if attempt < retries:
                logger.warning(f"Rate limit hit. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2.0
            else:
                raise rate_err
        except Exception as err:
            last_error = err
            if attempt < retries:
                logger.warning(f"Error calling LLM: {err}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2.0
            else:
                raise err
                
    raise last_error
