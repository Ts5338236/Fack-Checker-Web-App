from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class Claim(BaseModel):
    claim_text: str = Field(..., description="The exact factual assertion extracted from the text.")
    claim_type: Literal["statistic", "date", "financial", "technical"] = Field(
        ..., 
        description="The category of claim: statistic (percentages, ratios), date, financial (revenue, cost, funding), or technical (uptime, speeds, performance)."
    )
    context: str = Field(..., description="The sentence or surrounding context where the claim appears.")
    search_query: str = Field(
        ..., 
        description="An optimized, standalone search query to verify this specific claim online. Do not include LLM prompts, quotes, or conversational elements."
    )

class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str
    published_date: Optional[str] = None

class Verdict(BaseModel):
    verdict: Literal["Verified", "Inaccurate", "False"] = Field(
        ..., 
        description="Verified: matches current live data. Inaccurate: close but wrong/outdated. False: unsupported or contradicted."
    )
    confidence: Literal["High", "Medium", "Low"] = Field(
        ..., 
        description="The confidence score of the evaluation based on the quality of source materials."
    )
    real_fact: str = Field(
        ..., 
        description="The correct, current fact, or 'No reliable data found' if no corroborating source was found."
    )
    explanation: str = Field(
        ..., 
        description="A concise 1-2 sentence explanation of the reasoning behind the verdict."
    )
    sources: List[str] = Field(
        default_factory=list, 
        description="List of URL links used to substantiate the verdict."
    )

class ClaimVerificationReport(BaseModel):
    claim: Claim
    verdict: Optional[Verdict] = None
    error_message: Optional[str] = None

class ClaimsList(BaseModel):
    claims: List[Claim]

