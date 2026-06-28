import os
import logging
from typing import List
from tavily import TavilyClient
from models import Claim, SearchResult, Verdict
from prompts import VERDICT_REASONING_SYSTEM, VERDICT_REASONING_USER
from utils import call_llm_with_retry

logger = logging.getLogger(__name__)

def search_web(query: str, api_key: str) -> List[SearchResult]:
    """
    Query the Tavily Search API for the given claim query.
    Returns a list of SearchResult models (up to 5 results).
    """
    if not api_key:
        logger.error("Tavily API key is missing. Skipping search.")
        return []
        
    try:
        tavily = TavilyClient(api_key=api_key)
        # Call search
        response = tavily.search(query=query, max_results=5, search_depth="advanced")
        results = response.get("results", [])
        
        search_results = []
        for res in results:
            search_results.append(
                SearchResult(
                    title=res.get("title", "No Title"),
                    snippet=res.get("content", ""),
                    url=res.get("url", ""),
                    published_date=res.get("published_date")
                )
            )
        return search_results
    except Exception as e:
        logger.error(f"Tavily Search API failed for query '{query}': {e}")
        return []


def get_verdict(
    claim: Claim, 
    search_results: List[SearchResult], 
    llm_client, 
    model: str = "gpt-4o-mini"
) -> Verdict:
    """
    Evaluates a claim's veracity against search results using Claude.
    Returns a Verdict object. If search results are empty or the LLM evaluation fails,
    returns a fallback verdict.
    """
    # Safe default fallback in case of absolute failure
    fallback_verdict = Verdict(
        verdict="False",
        confidence="Low",
        real_fact="No corroborating source found — likely fabricated or unverifiable.",
        explanation="The web search yielded no results, or there was a system error validating the claim.",
        sources=[]
    )
    
    if not search_results:
        logger.warning(f"No search results returned for query: {claim.search_query}")
        return fallback_verdict
        
    # Format search results into a clean string for the prompt
    formatted_results = []
    for idx, res in enumerate(search_results, start=1):
        snippet_text = (
            f"[{idx}] Title: {res.title}\n"
            f"    URL: {res.url}\n"
            f"    Snippet: {res.snippet}\n"
        )
        if res.published_date:
            snippet_text += f"    Published Date: {res.published_date}\n"
        formatted_results.append(snippet_text)
        
    search_results_text = "\n".join(formatted_results)
    
    user_prompt = VERDICT_REASONING_USER.format(
        claim_text=claim.claim_text,
        claim_context=claim.context,
        claim_type=claim.claim_type,
        search_results_text=search_results_text
    )
    
    try:
        verdict_obj = call_llm_with_retry(
            llm_client=llm_client,
            model=model,
            system_prompt=VERDICT_REASONING_SYSTEM,
            user_prompt=user_prompt,
            expected_type=Verdict
        )
        return verdict_obj
    except Exception as e:
        logger.error(f"Verdict reasoning failed for claim '{claim.claim_text}': {e}")
        return fallback_verdict
