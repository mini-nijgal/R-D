from __future__ import annotations

import time
from typing import Dict

import pandas as pd
import requests
import streamlit as st

from .utils import dataframe_to_compact_json

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FREE_MODEL = "moonshotai/kimi-k2:free"


def _get_api_key() -> str | None:
    try:
        return st.secrets["openrouter"]["api_key"]  # type: ignore[index]
    except Exception:
        return None


def generate_ai_summary(df: pd.DataFrame) -> None:
    """Generate automatic AI summary of the filtered data"""
    api_key = _get_api_key()
    
    if not api_key:
        st.info("💡 Add OpenRouter API key to secrets to enable AI summaries. Get a free key at https://openrouter.ai/keys")
        return
    
    if df.empty:
        st.info("No data to summarize.")
        return
    
    # Cache summary based on data hash
    data_hash = str(hash(str(df.head(50).to_dict())))
    cache_key = f"ai_summary_{data_hash}"
    
    if cache_key in st.session_state:
        st.markdown(st.session_state[cache_key])
        return
    
    with st.spinner("🤖 Generating AI summary..."):
        system_prompt = (
            "You are an AI assistant analyzing R&D ticket data. "
            "Provide a concise, insightful summary (2-3 paragraphs) covering: "
            "1) Overall ticket status distribution and trends, "
            "2) Key insights about workload, priorities, or bottlenecks, "
            "3) Notable patterns or recommendations. "
            "Be specific with numbers and actionable insights."
        )
        
        user_prompt = (
            f"Analyze this ticket data and provide a summary:\n\n"
            f"{dataframe_to_compact_json(df, max_rows=50)}"
        )
        
        payload = {
            "model": FREE_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            summary = data["choices"][0]["message"]["content"].strip()
            
            # Cache the summary
            st.session_state[cache_key] = summary
            st.markdown(summary)
        except Exception as e:
            st.error(f"Failed to generate summary: {e}")

