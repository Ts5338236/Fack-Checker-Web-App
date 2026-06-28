import pytest
from unittest.mock import MagicMock
from models import Claim, Verdict, ClaimsList
from extractor import extract_claims
from verifier import get_verdict
from utils import call_llm_with_retry

def test_extract_claims_success():
    # Setup mock LLM response
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(text="""
        {
          "claims": [
            {
              "claim_text": "AcmeTech has over 500 million active enterprise clients",
              "claim_type": "statistic",
              "context": "As of 2025, AcmeTech has over 500 million active enterprise clients globally.",
              "search_query": "AcmeTech active enterprise clients 2025"
            }
          ]
        }
        """)
    ]
    mock_client.messages.create.return_value = mock_message
    
    # Run
    document_text = "AcmeTech has over 500 million active enterprise clients globally."
    claims = extract_claims(document_text, llm_client=mock_client, max_claims=5)
    
    # Assertions
    assert len(claims) == 1
    assert claims[0].claim_text == "AcmeTech has over 500 million active enterprise clients"
    assert claims[0].claim_type == "statistic"
    assert claims[0].search_query == "AcmeTech active enterprise clients 2025"


def test_extract_claims_malformed_json_triggers_repair():
    # Setup mock LLM where the first response is malformed, second is repaired
    mock_client = MagicMock()
    
    malformed_response = MagicMock()
    malformed_response.content = [MagicMock(text='{"claims": [{"claim_text": "broken JSON due to unexpected EOF')]
    
    repaired_response = MagicMock()
    repaired_response.content = [
        MagicMock(text="""
        {
          "claims": [
            {
              "claim_text": "AcmeTech has over 500 million active enterprise clients",
              "claim_type": "statistic",
              "context": "As of 2025, AcmeTech has over 500 million active enterprise clients globally.",
              "search_query": "AcmeTech active enterprise clients 2025"
            }
          ]
        }
        """)
    ]
    
    # First call is the main extraction (malformed JSON), second is the JSON repair prompt call
    mock_client.messages.create.side_effect = [malformed_response, repaired_response]
    
    # Run
    document_text = "AcmeTech has over 500 million active enterprise clients globally."
    claims = extract_claims(document_text, llm_client=mock_client, max_claims=5)
    
    # Assertions - it should successfully recover and return the parsed claim
    assert len(claims) == 1
    assert claims[0].claim_text == "AcmeTech has over 500 million active enterprise clients"
    # Ensure client was called twice (once for initial parse, once for repair)
    assert mock_client.messages.create.call_count == 2


def test_get_verdict_schema_validation():
    # Setup mock LLM verdict response
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(text="""
        {
          "verdict": "False",
          "confidence": "High",
          "real_fact": "AcmeTech does not exist and was never acquired by Apple.",
          "explanation": "No public acquisition records exist, and Apple did not acquire AcmeTech in June 2025.",
          "sources": ["https://www.apple.com/newsroom/"]
        }
        """)
    ]
    mock_client.messages.create.return_value = mock_message
    
    claim = Claim(
        claim_text="AcmeTech was acquired by Apple Inc. for $150 billion",
        claim_type="financial",
        context="In June 2025, AcmeTech was acquired by Apple Inc. for $150 billion.",
        search_query="Apple acquires AcmeTech 150 billion 2025"
    )
    
    search_results = [
        MagicMock(title="Apple Newsroom", snippet="No such acquisition found.", url="https://www.apple.com/newsroom/", published_date=None)
    ]
    
    # Run
    verdict = get_verdict(claim, search_results, llm_client=mock_client)
    
    # Assertions
    assert verdict.verdict == "False"
    assert verdict.confidence == "High"
    assert verdict.real_fact == "AcmeTech does not exist and was never acquired by Apple."
    assert "https://www.apple.com/newsroom/" in verdict.sources
