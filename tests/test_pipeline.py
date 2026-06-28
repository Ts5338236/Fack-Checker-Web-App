import pytest
from unittest.mock import MagicMock
from models import Claim, Verdict
from extractor import extract_claims
from verifier import get_verdict

def test_extract_claims_success():
    # Setup mock OpenAI client response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""
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
        """))
    ]
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run
    document_text = "AcmeTech has over 500 million active enterprise clients globally."
    claims = extract_claims(document_text, llm_client=mock_client, max_claims=5)
    
    # Assertions
    assert len(claims) == 1
    assert claims[0].claim_text == "AcmeTech has over 500 million active enterprise clients"
    assert claims[0].claim_type == "statistic"
    assert claims[0].search_query == "AcmeTech active enterprise clients 2025"


def test_extract_claims_malformed_json_triggers_repair():
    # Setup mock OpenAI client where first call returns malformed JSON, second is repaired
    mock_client = MagicMock()
    
    malformed_response = MagicMock()
    malformed_response.choices = [
        MagicMock(message=MagicMock(content='{"claims": [{"claim_text": "broken JSON due to unexpected EOF'))
    ]
    
    repaired_response = MagicMock()
    repaired_response.choices = [
        MagicMock(message=MagicMock(content="""
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
        """))
    ]
    
    # First call is main extraction, second is repair completions call
    mock_client.chat.completions.create.side_effect = [malformed_response, repaired_response]
    
    # Run
    document_text = "AcmeTech has over 500 million active enterprise clients globally."
    claims = extract_claims(document_text, llm_client=mock_client, max_claims=5)
    
    # Assertions
    assert len(claims) == 1
    assert claims[0].claim_text == "AcmeTech has over 500 million active enterprise clients"
    assert mock_client.chat.completions.create.call_count == 2


def test_get_verdict_schema_validation():
    # Setup mock OpenAI verdict response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="""
        {
          "verdict": "False",
          "confidence": "High",
          "real_fact": "AcmeTech does not exist and was never acquired by Apple.",
          "explanation": "No public acquisition records exist, and Apple did not acquire AcmeTech in June 2025.",
          "sources": ["https://www.apple.com/newsroom/"]
        }
        """))
    ]
    mock_client.chat.completions.create.return_value = mock_response
    
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
