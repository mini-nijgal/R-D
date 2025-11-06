from __future__ import annotations

import streamlit as st


SESSION_USER_KEY = "auth_user"


def is_authenticated() -> bool:
    return SESSION_USER_KEY in st.session_state and bool(st.session_state[SESSION_USER_KEY])


def get_user() -> str | None:
    return st.session_state.get(SESSION_USER_KEY)


def logout_button() -> None:
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.pop(SESSION_USER_KEY, None)
        st.rerun()


def login_view(title: str = "Sign in") -> None:
    # Modern login design
    st.markdown("""
    <div class="login-container">
        <div class="login-card">
            <div class="login-icon">📊</div>
            <div class="login-title">Avathon VAIA R&D Tickets Dashboard</div>
            <div class="login-subtitle">Sign in to access your dashboard</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Centered form
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        with st.container():
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 2.5rem;
                        border-radius: 15px;
                        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                        margin: 1rem 0;">
            """, unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                st.markdown("### 🔐 Login", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                username = st.text_input(
                    "👤 Username",
                    placeholder="Enter your username",
                    key="login_username"
                )
                st.markdown("<br>", unsafe_allow_html=True)
                
                show_pw = st.checkbox("👁️ Show password", value=False)
                password = st.text_input(
                    "🔒 Password",
                    type=("text" if show_pw else "password"),
                    placeholder="Enter your password",
                    key="login_password"
                )
                st.markdown("<br>", unsafe_allow_html=True)
                
                submitted = st.form_submit_button(
                    "🚀 Login",
                    use_container_width=True,
                    type="primary"
                )
            
            st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        # Try to load from secrets; if unavailable, fall back to dev creds
        users_map = None
        try:
            users_map = st.secrets["auth"]["users"]  # type: ignore[index]
        except Exception:
            users_map = None
        if not users_map:
            users_map = {"admin": "admin123"}
            st.info("Using default dev credentials (admin / admin123). Configure [auth] in secrets.toml for production.")
        if username and users_map.get(username) == password:
            st.session_state[SESSION_USER_KEY] = username
            st.success("Logged in")
            st.rerun()
        else:
            st.error("Invalid credentials")


def require_auth() -> None:
    if not is_authenticated():
        login_view("R&D Tickets Dashboard – Login")
        st.stop()


