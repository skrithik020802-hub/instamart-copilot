# Instamart Customer Intelligence & Support Copilot

## Overview
This repository contains the complete 21-day Capstone Project for Swiggy Instamart, addressing data quality cleaning, customer RFM segmentation & lapse prediction, support ticket triage with privacy guardrails, and automated policy RAG refund agents.

## Reproduce
1. Clone the repository and switch to `main`:
   ```bash
   git clone https://github.com/skrithik0208/instamart-copilot.git
   cd instamart-copilot
   git checkout main
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Generate raw synthetic datasets:
   ```bash
   python generate_data.py
   ```
4. Run pipeline components sequentially:
   ```bash
   python part_a.py
   python part_b.py
   python part_c.py
   python part_d.py
   ```

## Part A
- **Audit Raw Data:** Audited 13,084 order rows, 119 exact duplicate rows, 656 pending rows, 12,309 distinct order IDs, 106 non-numeric amounts, 106 negative delivery times, 2,541 blank delivery times, 24 raw city spellings, and 10 raw gender spellings.
- **Clean Customers:** Standardized to 6 cities (Pune: 227, Delhi: 210, Bengaluru: 197, Chennai: 191, Hyderabad: 191, Mumbai: 184). Mapped genders to female (610), male (560), unknown (30). Median city age imputed for missing ages.
- **Clean Orders:** Standardized 12,309 rows (11,110 completed, 1,199 cancelled). Total completed order amount: INR 2,998,668.80.
- **Database & Queries:** Stored in `data/instamart.db`. Executed 7 SQL queries under `sql/queries.sql`.

## Part B
- **RFM Clustering:** Fitted K-Means (K=4 chosen based on silhouette score and business interpretability). Segment sizes: ~436, 138 (Premium), 419, 182.
- **Lapse Prediction:** Trained Logistic Regression (best C=1, F1 ~0.62) and Random Forest (best depth 8, leaf 10, F1 ~0.65). Evaluated pre-cutoff features (cutoff: 2025-09-01).

## Part C
- **Guardrails & Redaction:** Applied regex redactions across 164 tickets (55 emails, 91 phone numbers, 132 order IDs, 278 total). 4 empty tickets skipped, 4 long tickets flagged (>400 tokens).
- **Triage Performance:** Zero-shot accuracy 85.7%, Few-shot accuracy 100%. Generated `outputs/triage_results.csv` and `outputs/triage_budget_demo.csv`.

## Part D
- **Policy RAG:** Chunked 5 policy documents into 15 chunks (40 words, 10 overlap). Achieved 12/12 retrieval accuracy on answerable questions.
- **ReAct Refund Agent:** Executed 7 agent scenarios. Handled INR > 1000 supervisor escalations, stop-safely limits (`FALLBACK_MAX_ITERATIONS`, `FALLBACK_TOKEN_LIMIT`, `FALLBACK_TIMEOUT`), and resumable state checkpoints under `state/`.

## Limitations and Next Steps
- Synthetic offline LLM sandbox lacks open-ended semantic reasoning.
- Future work: Migrate to production vector databases (Chroma/FAISS) and real LLM APIs with real-time webhooks.
