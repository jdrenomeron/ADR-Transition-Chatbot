import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="MOHRE Transition Assistant", page_icon="💬", layout="centered")

APP_TITLE = "MOHRE Transition Assistant"
KB_FILENAME = "EmployeeTransition_Chatbot_Knowledge_Base_August_14_2026.xlsx"
REQUIRED_COLUMNS = ["Intent ID", "Category", "Primary Question", "Answer"]
OPTIONAL_COLUMNS = [
    "Alternate Phrasings (Sample Utterances)", "Keywords", "Quick Reply Options",
    "Requires Personalization", "Escalate to HR", "HR Owner", "Escalation Message"
]

SYSTEM_RULES = """You are the MOHRE Transition Assistant for employees affected by an employment transition.
Use ONLY the supplied knowledge-base excerpts. Do not use general legal knowledge, guess, or create policy.
If the answer is not clearly supported, say: 'I could not find a confirmed answer in the transition knowledge base. Please contact your HRBP for guidance.'
Preserve important conditions, exceptions, numbers, and distinctions such as UAE/GCC national, Golden Visa, grade, company-sponsored visa, and probation status.
If personalization is required and the employee has not provided the needed information, ask only for the required detail, such as grade or visa status.
Do not claim to approve, decide, submit, transfer, sign, or contact HR on the employee's behalf.
Keep the answer warm, concise, and easy to understand. End with the intent ID in this format: 'Reference: XXX-000'.
"""


def norm(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


@st.cache_data(show_spinner=False)
def load_kb(path: str):
    xls = pd.ExcelFile(path, engine="openpyxl")
    sheet = "HR_FAQ" if "HR_FAQ" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    df.columns = [norm(c) for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[df["Intent ID"].notna() & df["Answer"].notna()].copy()
    for col in df.columns:
        df[col] = df[col].map(norm)
    df["search_text"] = (
        df["Category"] + " " + df["Primary Question"] + " " +
        df["Alternate Phrasings (Sample Utterances)"] + " " + df["Keywords"]
    )
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
    matrix = vectorizer.fit_transform(df["search_text"])
    return df, vectorizer, matrix


def retrieve(question, df, vectorizer, matrix, top_k=5):
    query_vec = vectorizer.transform([question])
    scores = cosine_similarity(query_vec, matrix).flatten()
    best_idx = scores.argsort()[::-1][:top_k]
    results = df.iloc[best_idx].copy()
    results["score"] = scores[best_idx]
    return results


def context_from(results):
    blocks = []
    for _, row in results.iterrows():
        blocks.append(
            "\n".join([
                f"Intent ID: {row['Intent ID']}",
                f"Category: {row['Category']}",
                f"Primary question: {row['Primary Question']}",
                f"Answer: {row['Answer']}",
                f"Requires personalization: {row['Requires Personalization']}",
                f"Escalate to HR: {row['Escalate to HR']}",
                f"Escalation message: {row['Escalation Message']}",
            ])
        )
    return "\n\n---\n\n".join(blocks)


def get_api_key():
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")


def generate_answer(question, results):
    if results.empty or float(results.iloc[0]["score"]) < 0.08:
        return "I could not find a confirmed answer in the transition knowledge base. Please contact your HRBP for guidance."
    api_key = get_api_key()
    if not api_key:
        return "The chatbot is not connected to the AI service yet. The owner needs to add the GEMINI_API_KEY in Streamlit Secrets."
    client = genai.Client(api_key=api_key)
    prompt = f"""{SYSTEM_RULES}

KNOWLEDGE-BASE EXCERPTS:
{context_from(results)}

EMPLOYEE QUESTION:
{question}

Answer only from the excerpts above."""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text.strip() if response.text else "Please contact your HRBP for guidance."


st.title(APP_TITLE)
st.caption("AI answers grounded in the approved employee-transition knowledge base")
with st.expander("Important notice", expanded=False):
    st.write("This assistant provides general transition information only. It does not provide legal advice, make decisions, or replace HR guidance. Avoid entering passport numbers, Emirates ID numbers, medical information, bank details, or other personal data.")

kb_path = Path(__file__).parent / KB_FILENAME
if not kb_path.exists():
    st.error(f"Knowledge base not found. Add `{KB_FILENAME}` to the same GitHub folder as `app.py`.")
    st.stop()

try:
    df, vectorizer, matrix = load_kb(str(kb_path))
except Exception as exc:
    st.error(f"Could not load the knowledge base: {exc}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! Ask me about your MOHRE employment transition, work permit, visa, contract, benefits, leave, or onboarding."}]

suggestions = [
    "What documents are required for MOHRE?",
    "Can I travel during the visa transfer?",
    "Will my original joining date be recognized?",
]
cols = st.columns(3)
selected = None
for col, text in zip(cols, suggestions):
    if col.button(text, use_container_width=True):
        selected = text

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = selected or st.chat_input("Ask your question")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Checking the approved knowledge base..."):
            try:
                matches = retrieve(question, df, vectorizer, matrix)
                answer = generate_answer(question, matches)
            except Exception as e:
                answer = f"ERROR: {str(e)}"

        st.markdown(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
st.divider()
st.caption("For individual cases, deadlines, approvals, or document verification, contact your HRBP.")
