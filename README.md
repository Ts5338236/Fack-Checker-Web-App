# Fact-Check Agent — AI Marketing Claim Verifier

Fact-Check Agent is a automated "Truth Layer" application designed to verify technical marketing claims, statistical disclosures, dates, and financial metrics in PDF documents. The application parses PDFs, extracts key factual assertions using Claude 3.5 Haiku, executes live search queries via Tavily Search API, and evaluates the claims as **Verified**, **Inaccurate**, or **False** with stated correct figures and verified source links.

---

## Architecture Pipeline

```
               [ Upload PDF ]
                     │
                     ▼
         [ 1. PDF Text Extraction ]
               (pdfplumber)
                     │
                     ▼
       [ 2. Claim Extraction (Claude) ]
       - statistic | date | financial | technical
       - standalone search query generation
                     │
                     ▼
       [ 3. Web Fact-Search (Tavily) ]
       - queries run concurrently per claim
       - captures top 5 results & snippets
                     │
                     ▼
      [ 4. Verdict Reasoning (Claude) ]
      - evaluates claims vs search data
      - categorizes: Verified | Inaccurate | False
                     │
                     ▼
         [ 5. Dynamic Dashboard ]
         - Streamlit UI stats & metrics
         - Exportable reports (CSV & Markdown)
```

---

## Setup & Local Installation

### Prerequisites
* Python 3.11 or higher installed on your system.
* Anthropic API Key (for Claude 3.5 Haiku).
* Tavily API Key (for search queries).

### Setup Steps
1. **Clone or Open project directory:**
   ```bash
   cd "c:/Users/sony/Desktop/Fact chcek web app"
   ```

2. **Create and Activate a virtual environment:**
   ```bash
   # Create environment
   python -m venv .venv
   
   # Activate environment (Windows PowerShell)
   .venv\Scripts\Activate.ps1
   
   # Activate environment (Windows Command Prompt)
   .venv\Scripts\activate.bat
   
   # Activate environment (Linux/macOS)
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure secrets:**
   Create a `secrets.toml` file under the `.streamlit` directory:
   ```bash
   mkdir .streamlit
   notepad .streamlit/secrets.toml
   ```
   Paste the following keys:
   ```toml
   ANTHROPIC_API_KEY = "your_actual_anthropic_api_key"
   TAVILY_API_KEY = "your_actual_tavily_api_key"
   ```

5. **Run the application locally:**
   ```bash
   streamlit run app.py
   ```

---

## Running Unit Tests
We have built unit tests to validate the extraction schema, JSON repair path, and verdict logic with mocked API clients. Run them using:
```bash
python -m pytest tests/test_pipeline.py
```

---

## Testing Factual Claims (Trap Document Verification)

We have included a programmatic PDF generator at `sample_docs/generate_trap_doc.py` that created `sample_docs/trap_document_test.pdf`. This trap document contains intentional factual inaccuracies, outdated statistics, and fabricated claims to test the verification pipeline:

* **Stated Price**: flat rate of $49 per user per month (Checkable pricing).
* **Outdated/Fabricated Growth Metric**: Over 500 million active enterprise clients globally (impossible statistic).
* **Incorrect Capital**: Identifies Sydney as the capital city of Australia (geographical error, correct is Canberra).
* **Fabricated Acquisition**: AcmeTech was acquired by Apple Inc. for $150 billion in June 2025 (completely fabricated event).

### How to test:
1. Start the Streamlit app.
2. Upload the `sample_docs/trap_document_test.pdf`.
3. Check the results dashboard:
   * **Inaccurate/False** will flag the Apple Acquisition and Australia Capital claims.
   * The app will report correct facts (e.g., that Canberra is the capital of Australia) and provide live reference links.

---

## Streamlit Cloud Deployment

To deploy this application to Streamlit Community Cloud:

1. **Commit and Push to a Public GitHub Repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Fact-Check Agent"
   # Create a public repository on GitHub, then link and push:
   git remote add origin https://github.com/Ts5338236/Fack-Checker-Web-App.git
   git branch -M main
   git push -u origin main
   ```
2. **Deploy on Streamlit**:
   * Navigate to [Streamlit Community Cloud](https://streamlit.io/cloud).
   * Log in using your GitHub account.
   * Click **New App**, select your repository, branch (`main`), and entrypoint file (`app.py`).
3. **Configure Secrets**:
   * In the App Settings dashboard on Streamlit Cloud, find the **Secrets** section.
   * Paste your keys into the text box:
     ```toml
     ANTHROPIC_API_KEY = "your_actual_anthropic_api_key"
     TAVILY_API_KEY = "your_actual_tavily_api_key"
     ```
   * Save and click **Deploy**.

---

## Known Limitations
* **Claim Capping**: Capped at 15 claims per document to prevent high rate-limiting costs and long evaluation delays.
* **Language Support**: Designed primarily for English documents and search indexes.
* **Text-based PDFs only**: Scanned/scraped images require pre-processing (OCR) which is not supported in the MVP.

## Deployed APP URL
https://fack-checker-web-app.streamlit.app/
