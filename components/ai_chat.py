from __future__ import annotations

import time
from typing import List, Dict

import pandas as pd
import requests
import streamlit as st

from .utils import dataframe_to_compact_json


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Valid OpenRouter model IDs - verified from OpenRouter API
MODEL_OPTIONS = [
    "moonshotai/kimi-k2:free",     # Free Kimi model (primary)
    "moonshotai/kimi-k2",          # Alternative Kimi model
    "meta-llama/llama-3.2-3b-instruct:free",  # Free fallback
]


def _headers() -> Dict[str, str]:
    api_key = None
    try:
        api_key = st.secrets["openrouter"]["api_key"]  # type: ignore[index]
    except Exception:
        api_key = None
    if not api_key:
        raise RuntimeError("Missing OpenRouter API key in secrets. Add [openrouter].api_key to .streamlit/secrets.toml")
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/your-repo",  # Optional but recommended
        "X-Title": "R&D Dashboard",
    }


def ask_ai(filtered_df: pd.DataFrame, user_query: str) -> str:
    system_context = (
        "You are an AI assistant analyzing R&D ticket data. Respond concisely and accurately. "
        "Here is the current filtered ticket data as JSON array: " + dataframe_to_compact_json(filtered_df)
    )
    
    # Try each model until one works
    last_error = None
    for model in MODEL_OPTIONS:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_query},
            ],
        }
        
        for attempt in range(2):  # 2 attempts per model
            try:
                resp = requests.post(OPENROUTER_URL, headers=_headers(), json=payload, timeout=30)
                if resp.status_code == 429:
                    time.sleep(1 + attempt)
                    continue
                if resp.status_code in (404, 400):
                    # Model doesn't exist or invalid, try next one
                    error_detail = resp.text[:300] if hasattr(resp, 'text') else ""
                    last_error = f"Model '{model}' not available ({resp.status_code})"
                    break  # Try next model
                resp.raise_for_status()
                data = resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                raise ValueError("Unexpected API response format")
            except requests.exceptions.HTTPError as e:
                if resp.status_code in (404, 400):
                    # Already handled above, break to try next model
                    break
                if attempt == 1:
                    error_detail = resp.text[:300] if hasattr(resp, 'text') else str(e)
                    last_error = f"API error ({resp.status_code}): {error_detail}"
            except Exception as e:
                if attempt == 1:
                    last_error = str(e)
                time.sleep(0.5)
    
    # If all models failed
    raise RuntimeError(f"All models failed. Last error: {last_error}")


def chat_ui(filtered_df: pd.DataFrame) -> None:
    st.subheader("AI Assistant")
    
    # Check if API key is configured
    api_key_configured = False
    try:
        api_key = st.secrets["openrouter"]["api_key"]  # type: ignore[index]
        api_key_configured = bool(api_key)
    except Exception:
        pass
    
    if not api_key_configured:
        st.info("💡 AI chat requires an OpenRouter API key. Add `[openrouter].api_key` to `.streamlit/secrets.toml`. Get a free key at https://openrouter.ai/keys")
        return
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # type: ignore[attr-defined]

    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("Clear Chat"):
            st.session_state.chat_history = []  # type: ignore[attr-defined]
            st.toast("Chat cleared", icon="✅")

    for msg in st.session_state.chat_history:  # type: ignore[attr-defined]
        st.chat_message(msg["role"]).write(msg["content"])  # type: ignore[index]

    user_msg = st.chat_input("Ask about the filtered tickets…")
    if user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})  # type: ignore[attr-defined]
        st.chat_message("user").write(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    answer = ask_ai(filtered_df, user_msg)
                except Exception as e:
                    st.error(f"AI request failed: {e}")
                    return
                st.write(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})  # type: ignore[attr-defined]


