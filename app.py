import os
import io
import csv
import logging
import streamlit as st
import anthropic
from dotenv import load_dotenv

from extractor import extract_text_from_pdf, extract_claims
from verifier import search_web, get_verdict
from models import ClaimVerificationReport

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load local environment variables if available
load_dotenv()

# App configuration
st.set_page_config(
    page_title="Fact-Check Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* App font override */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Glowing title */
    .glow-text {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0.2rem;
        text-shadow: 0 0 20px rgba(168, 85, 247, 0.1);
    }
    
    .subtitle-text {
        color: #94a3b8;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* Premium Glassmorphic Cards for Stats */
    .stats-container {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 2.5rem;
        flex-wrap: wrap;
    }
    
    .stat-card {
        flex: 1;
        min-width: 200px;
        padding: 1.5rem;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        text-align: center;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        border-color: rgba(255, 255, 255, 0.2);
        box-shadow: 0 12px 40px 0 rgba(168, 85, 247, 0.15);
    }
    
    .stat-val {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    
    .stat-label {
        font-size: 0.9rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
    }
    
    /* Specific card border highlights */
    .card-total { border-left: 4px solid #6366f1; }
    .card-verified { border-left: 4px solid #10b981; }
    .card-inaccurate { border-left: 4px solid #f59e0b; }
    .card-false { border-left: 4px solid #ef4444; }
    
    /* Glow highlights for values */
    .val-total { color: #818cf8; }
    .val-verified { color: #34d399; }
    .val-inaccurate { color: #fbbf24; }
    .val-false { color: #f87171; }
    
    /* Premium expander header override */
    div[data-testid="stExpander"] {
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        background-color: rgba(255, 255, 255, 0.02) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        margin-bottom: 12px !important;
        transition: all 0.2s ease;
    }
    
    div[data-testid="stExpander"]:hover {
        border-color: rgba(255, 255, 255, 0.15) !important;
        background-color: rgba(255, 255, 255, 0.04) !important;
    }
    
    /* Custom Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper to fetch API keys securely
def get_api_keys():
    # Try st.secrets
    anthropic_key = None
    tavily_key = None
    
    if hasattr(st, "secrets"):
        anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
        tavily_key = st.secrets.get("TAVILY_API_KEY")
        
    # Fallback to os.environ
    if not anthropic_key:
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not tavily_key:
        tavily_key = os.environ.get("TAVILY_API_KEY")
        
    return anthropic_key, tavily_key

anthropic_key_secret, tavily_key_secret = get_api_keys()

# Sidebar Setup
with st.sidebar:
    st.markdown("### 🛠️ Configuration")
    
    # Allow user override if not set in secrets
    anthropic_key_input = st.text_input(
        "Anthropic API Key", 
        value=anthropic_key_secret or "", 
        type="password",
        help="Required for claim extraction and verdict reasoning (Claude 3.5 Haiku)."
    )
    tavily_key_input = st.text_input(
        "Tavily API Key", 
        value=tavily_key_secret or "", 
        type="password",
        help="Required for searching live web facts."
    )
    
    # Save active keys
    active_anthropic_key = anthropic_key_input.strip()
    active_tavily_key = tavily_key_input.strip()
    
    st.markdown("---")
    st.markdown("### 💡 How It Works")
    st.markdown("""
    1. **PDF Text Extraction**  
       Extracts paragraphs and technical assertions page-by-page.
    2. **Factual Claim Discovery**  
       Claude filters text for checkable stats, dates, financials, and technical specifications.
    3. **Live Web Check**  
       Each claim is searched on Tavily to capture top search results.
    4. **Verdict Evaluation**  
       Claude cross-references findings to grade the claim as Verified, Inaccurate, or False.
    """)
    
    st.markdown("---")
    st.markdown("**Version 1.0 (MVP)**")
    st.markdown("Maximum limit: **15 claims** per document to bound API cost and response time.")

# Main Page Layout
st.markdown('<div class="glow-text">Fact-Check Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">The Truth Layer for Technical Specs, Statistics, and Marketing Claims</div>', unsafe_allow_html=True)

# Main container for file upload
uploaded_file = st.file_uploader("Upload a marketing one-pager, PDF report, or blog article", type=["pdf"])

if uploaded_file is not None:
    # Key validation
    if not active_anthropic_key or not active_tavily_key:
        st.error("🔑 API keys are missing. Please enter them in the sidebar or configure `secrets.toml` to proceed.")
    else:
        # Initialize Anthropic Client
        llm_client = anthropic.Anthropic(api_key=active_anthropic_key)
        
        # Main verification flow container
        st.markdown("### ⚙️ Verification Pipeline")
        
        # Pipeline status box
        pipeline_status = st.status("Initializing processing...", expanded=True)
        
        try:
            # Stage 1: Text extraction
            pipeline_status.write("📄 Reading PDF pages and extracting text...")
            raw_text = extract_text_from_pdf(uploaded_file)
            
            if not raw_text.strip():
                pipeline_status.update(label="❌ Extraction Failed", state="error", expanded=True)
                st.error("No text could be extracted from this PDF. It might be scanned/image-only or corrupt.")
            else:
                # Stage 2: Claim Extraction
                pipeline_status.write("🧠 Analyzing document structure for factual claims (statistics, dates, finances, technical specs)...")
                claims = extract_claims(raw_text, llm_client=llm_client)
                
                if not claims:
                    pipeline_status.update(label="⚠️ Processing Complete - No Claims Found", state="complete")
                    st.info("No verifyable factual claims (statistics, dates, financial, or technical specs) were found in this document.")
                else:
                    pipeline_status.write(f"🔍 Discovered **{len(claims)}** unique checkable claims. Commencing live web search...")
                    
                    # Stage 3: Live Verification loop
                    reports = []
                    progress_bar = st.progress(0.0)
                    
                    for idx, claim in enumerate(claims):
                        pipeline_status.write(f"🌐 Verifying claim {idx+1}/{len(claims)}: *\"{claim.claim_text[:50]}...\"*")
                        
                        try:
                            # 1. Search web
                            search_results = search_web(claim.search_query, api_key=active_tavily_key)
                            # 2. Get LLM verdict
                            verdict = get_verdict(claim, search_results, llm_client=llm_client)
                            
                            reports.append(ClaimVerificationReport(claim=claim, verdict=verdict))
                        except Exception as claim_err:
                            logger.error(f"Error checking claim {idx}: {claim_err}")
                            reports.append(ClaimVerificationReport(
                                claim=claim, 
                                error_message=f"System error: {str(claim_err)}"
                            ))
                            
                        # Update progress
                        progress_bar.progress((idx + 1) / len(claims))
                        
                    pipeline_status.update(label="✨ Analysis Complete!", state="complete", expanded=False)
                    progress_bar.empty()
                    
                    # Compute statistics
                    total_claims = len(reports)
                    verified_count = sum(1 for r in reports if r.verdict and r.verdict.verdict == "Verified")
                    inaccurate_count = sum(1 for r in reports if r.verdict and r.verdict.verdict == "Inaccurate")
                    false_count = sum(1 for r in reports if (r.verdict and r.verdict.verdict == "False") or r.error_message)
                    
                    # Display Premium Dashboard Metrics
                    st.markdown(f"""
                    <div class="stats-container">
                        <div class="stat-card card-total">
                            <div class="stat-val val-total">{total_claims}</div>
                            <div class="stat-label">Claims Checked</div>
                        </div>
                        <div class="stat-card card-verified">
                            <div class="stat-val val-verified">{verified_count}</div>
                            <div class="stat-label">Verified</div>
                        </div>
                        <div class="stat-card card-inaccurate">
                            <div class="stat-val val-inaccurate">{inaccurate_count}</div>
                            <div class="stat-label">Inaccurate</div>
                        </div>
                        <div class="stat-card card-false">
                            <div class="stat-val val-false">{false_count}</div>
                            <div class="stat-label">False / Unverifiable</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display detailed results
                    st.markdown("### 📋 Detailed Verification Report")
                    
                    for idx, report in enumerate(reports):
                        claim = report.claim
                        
                        # Handle pipeline errors
                        if report.error_message:
                            title = f"🔴 Claim #{idx+1} (Error): {claim.claim_text[:80]}..."
                            with st.expander(title):
                                st.error(f"Failed to check claim: {report.error_message}")
                                st.markdown(f"**Original Context**: *\"{claim.context}\"*")
                            continue
                            
                        verdict = report.verdict
                        verdict_label = verdict.verdict
                        
                        # Set theme style based on verdict
                        if verdict_label == "Verified":
                            icon = "🟢"
                            color_func = st.success
                        elif verdict_label == "Inaccurate":
                            icon = "🟡"
                            color_func = st.warning
                        else:
                            icon = "🔴"
                            color_func = st.error
                            
                        # Expander header
                        title_text = f"{icon} **[{verdict_label}]** {claim.claim_text}"
                        if len(title_text) > 100:
                            title_text = title_text[:97] + "..."
                            
                        with st.expander(title_text):
                            st.markdown(f"** Factual Claim:** \"{claim.claim_text}\"")
                            st.markdown(f"**📍 Original Context:** *\"{claim.context}\"*")
                            
                            # Render verdict styling block
                            color_func(f"**Verdict:** {verdict_label} | **Confidence:** {verdict.confidence}")
                            
                            # Facts & Explanations
                            st.markdown(f"**📌 Stated/Correct Fact:** {verdict.real_fact}")
                            st.markdown(f"**📖 Explanation:** {verdict.explanation}")
                            
                            # Sources
                            if verdict.sources:
                                st.markdown("**🔗 Verified Sources:**")
                                for src in verdict.sources:
                                    st.markdown(f"- [{src}]({src})")
                            else:
                                st.markdown("*No sources cited.*")
                                
                    # Export functions
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    # Build CSV Report
                    csv_buffer = io.StringIO()
                    csv_writer = csv.writer(csv_buffer)
                    csv_writer.writerow(["Claim Text", "Claim Type", "Context", "Verdict", "Confidence", "Real/Correct Fact", "Explanation", "Sources"])
                    
                    for r in reports:
                        if r.error_message:
                            csv_writer.writerow([r.claim.claim_text, r.claim.claim_type, r.claim.context, "Error", "Low", "N/A", r.error_message, ""])
                        else:
                            csv_writer.writerow([
                                r.claim.claim_text, r.claim.claim_type, r.claim.context, 
                                r.verdict.verdict, r.verdict.confidence, r.verdict.real_fact, 
                                r.verdict.explanation, "; ".join(r.verdict.sources)
                            ])
                            
                    col1.download_button(
                        label="📥 Download CSV Report",
                        data=csv_buffer.getvalue(),
                        file_name="fact_check_report.csv",
                        mime="text/csv"
                    )
                    
                    # Build Markdown Report
                    md_report = []
                    md_report.append("# Fact-Check Verification Report\n")
                    md_report.append(f"**Summary**: Discovered {total_claims} claims. {verified_count} Verified, {inaccurate_count} Inaccurate, {false_count} False.\n")
                    md_report.append("| Claim | Type | Verdict | Correct/Real Fact | Sources |")
                    md_report.append("|---|---|---|---|---|")
                    
                    for r in reports:
                        if r.error_message:
                            md_report.append(f"| {r.claim.claim_text} | {r.claim.claim_type} | Error | N/A | None |")
                        else:
                            sources_str = ", ".join([f"[Link]({s})" for s in r.verdict.sources]) if r.verdict.sources else "None"
                            md_report.append(f"| {r.claim.claim_text} | {r.claim.claim_type} | {r.verdict.verdict} | {r.verdict.real_fact} | {sources_str} |")
                            
                    md_report.append("\n\n## Details\n")
                    for idx, r in enumerate(reports, 1):
                        if r.error_message:
                            md_report.append(f"### {idx}. {r.claim.claim_text}\n- **Verdict**: Error\n- **Details**: {r.error_message}\n")
                        else:
                            md_report.append(
                                f"### {idx}. {r.claim.claim_text}\n"
                                f"- **Verdict**: **{r.verdict.verdict}** (Confidence: {r.verdict.confidence})\n"
                                f"- **Stated/Correct Fact**: {r.verdict.real_fact}\n"
                                f"- **Context**: *\"{r.claim.context}\"*\n"
                                f"- **Explanation**: {r.verdict.explanation}\n"
                                f"- **Sources**:\n"
                            )
                            for src in r.verdict.sources:
                                md_report.append(f"  - [{src}]({src})")
                            md_report.append("\n")
                            
                    col2.download_button(
                        label="📥 Download Markdown Report",
                        data="\n".join(md_report),
                        file_name="fact_check_report.md",
                        mime="text/markdown"
                    )
                    
        except Exception as e:
            pipeline_status.update(label="❌ Pipeline Failed", state="error", expanded=True)
            st.exception(e)
            st.error(f"An unexpected error occurred during processing: {e}")
