# MOHRE Transition AI Chatbot

A public Streamlit chatbot that retrieves relevant FAQ rows from the Excel knowledge base and asks Gemini to answer only from those rows.

## Files

- `app.py`: chatbot application
- `requirements.txt`: Python packages
- `.streamlit/config.toml`: visual theme
- `EmployeeTransition_Chatbot_Knowledge_Base_August_14_2026.xlsx`: add this workbook beside `app.py`

## Deploy on Streamlit Community Cloud

1. Create a private GitHub repository and upload this folder plus the Excel workbook.
2. In Google AI Studio, create a Gemini API key.
3. In Streamlit Community Cloud, create an app from the repository and set the main file to `app.py`.
4. In the app's **Settings > Secrets**, add:

```toml
GEMINI_API_KEY = "paste-your-key-here"
```

5. Save the secret, deploy the app, test representative MOHRE questions, then share the app URL.

## Security checklist before public sharing

- Obtain approval to expose the workbook's answers externally.
- Remove confidential, personal, case-specific, or internal-only information.
- Keep the GitHub repository private.
- Never store the API key in code, Excel, or GitHub.
- Do not ask users for passport, Emirates ID, medical, banking, or other sensitive data.
- Review answers and escalation wording with HR, Legal, Privacy, and Information Security.
- Be aware that free-tier AI services may process submitted prompts under their provider terms.

## How grounding works

1. Excel rows are indexed locally using TF-IDF.
2. The top matching FAQ excerpts are sent with the employee's question to Gemini.
3. Gemini is instructed to answer only from those excerpts.
4. Low-confidence questions are escalated to HRBP.

## Local test

Create `.streamlit/secrets.toml` with the key shown above, place the workbook beside `app.py`, then run:

```bash
pip install -r requirements.txt
streamlit run app.py
```
