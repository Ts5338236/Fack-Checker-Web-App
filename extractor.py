import logging
import re
import pdfplumber
from typing import List, Optional
from models import Claim, ClaimsList
from prompts import CLAIM_EXTRACTION_SYSTEM, CLAIM_EXTRACTION_USER
from utils import chunk_text, call_llm_with_retry

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file) -> str:
    """
    Extracts all text from a PDF file using pdfplumber.
    Supports file-like objects or absolute file paths.
    """
    text_content = []
    try:
        with pdfplumber.open(file) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text.strip())
                else:
                    logger.warning(f"No text extracted from page {page_num}.")
    except Exception as e:
        logger.error(f"Error opening or reading PDF: {e}")
        raise ValueError(f"Failed to read PDF file: {e}")
        
    return "\n\n".join(text_content).strip()


def extract_claims(document_text: str, llm_client, model: str = "gpt-4o-mini", max_claims: int = 15) -> List[Claim]:
    """
    Splits the document text into chunks, calls Claude to extract claims,
    and returns a deduplicated list of claims capped at max_claims.
    """
    if not document_text.strip():
        logger.warning("Empty document text passed to extract_claims.")
        return []
        
    chunks = chunk_text(document_text)
    all_claims = []
    seen_normalized_claims = set()
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing claim extraction chunk {i+1}/{len(chunks)}")
        user_prompt = CLAIM_EXTRACTION_USER.format(text=chunk)
        
        try:
            claims_list_obj = call_llm_with_retry(
                llm_client=llm_client,
                model=model,
                system_prompt=CLAIM_EXTRACTION_SYSTEM,
                user_prompt=user_prompt,
                expected_type=ClaimsList
            )
            
            if claims_list_obj and hasattr(claims_list_obj, 'claims'):
                for claim in claims_list_obj.claims:
                    # Clean and normalize to deduplicate
                    norm_text = re.sub(r'\W+', '', claim.claim_text).lower()
                    if norm_text not in seen_normalized_claims:
                        seen_normalized_claims.add(norm_text)
                        all_claims.append(claim)
                        
        except Exception as e:
            logger.error(f"Failed to extract claims from chunk {i+1}: {e}")
            
    # Cap total claims to keep performance and API costs bounded
    if len(all_claims) > max_claims:
        logger.info(f"Capping claims from {len(all_claims)} to {max_claims}")
        all_claims = all_claims[:max_claims]
        
    return all_claims
