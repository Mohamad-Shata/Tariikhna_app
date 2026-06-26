"""
Tiny client for the Tariikhna backend, shared by all Streamlit pages.

The backend base URL is resolved in this order, so the same frontend works
locally and when deployed:
  1. st.secrets["TARIIKHNA_API_URL"]   (Streamlit Community Cloud → Settings → Secrets)
  2. TARIIKHNA_API_URL environment variable
  3. http://127.0.0.1:8000             (local default)
"""
import os
import time
import requests
import streamlit as st


def _resolve_api_url() -> str:
    # st.secrets raises if there is no secrets file at all, so guard it.
    try:
        if "TARIIKHNA_API_URL" in st.secrets:
            return str(st.secrets["TARIIKHNA_API_URL"]).rstrip("/")
    except Exception:
        pass
    return os.environ.get("TARIIKHNA_API_URL", "http://127.0.0.1:8000").rstrip("/")


API_URL = _resolve_api_url()

# Warm storybook palette, reused across pages for inline-styled bits.
PALETTE = {
    "ink": "#3d2b1f",
    "amber": "#b5651d",
    "cream": "#fdf6ec",
    "sand": "#f6e8d6",
    "muted": "#8a7763",
}


class BackendError(Exception):
    """Raised when the backend can't be reached or returns an error."""


@st.cache_data(ttl=60, show_spinner=False)
def list_stories() -> list[dict]:
    """All stories as summary cards. Cached briefly to keep paging snappy."""
    return _get("/library/stories")


@st.cache_data(ttl=60, show_spinner=False)
def get_story(story_id: int) -> dict:
    """One story with its ordered panels."""
    return _get(f"/library/stories/{story_id}")


# Free hosts (e.g. Render free tier) sleep when idle and cold-start on the first
# request, which can take ~30-50s. Retry a few times before giving up so the
# first page load after a nap succeeds instead of erroring.
_RETRIES = 3
_TIMEOUT = 30


def _get(path: str):
    url = f"{API_URL}{path}"
    last_exc = None
    for attempt in range(_RETRIES):
        try:
            resp = requests.get(url, timeout=_TIMEOUT)
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(2 * (attempt + 1))  # back off while the backend wakes
            continue

        if resp.status_code == 404:
            raise BackendError("That story could not be found.")
        if resp.status_code in (502, 503, 504):
            last_exc = BackendError(f"Backend not ready yet ({resp.status_code}).")
            time.sleep(2 * (attempt + 1))
            continue
        if resp.status_code >= 400:
            raise BackendError(f"Backend error {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    raise BackendError(
        f"Couldn't reach the backend at {API_URL}. "
        f"It may be starting up (free hosts sleep when idle) — try again in a moment.\n\n({last_exc})"
    )


READER_PAGE = "pages/2_📖_Read_Story.py"


def open_story(story_id: int) -> None:
    """Navigate to the Reader for a story.

    st.switch_page() drops query params, so the selection is carried in
    st.session_state (survives the page switch); the query param is set too so
    the resulting URL is shareable / refresh-safe."""
    st.session_state["story_id"] = int(story_id)
    st.query_params["story_id"] = str(story_id)
    st.switch_page(READER_PAGE)


def show_backend_error(exc: Exception) -> None:
    """Render a friendly, actionable error block when the API is unavailable."""
    st.error("⚠️ The story library isn't available right now.")
    st.caption(str(exc))
    with st.expander("How to start the backend"):
        st.code(
            "cd tariikhna/backend\n"
            "uvicorn app.main:app --reload\n\n"
            "# (one-time) load the stories into the database:\n"
            "python import_storybook.py",
            language="bash",
        )
        st.write(f"Frontend is configured to call: `{API_URL}`")


def inject_base_css() -> None:
    """Shared CSS: typography, cards, chips, hero — kept in one place."""
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {PALETTE['cream']}; }}
        h1, h2, h3, h4 {{ color: {PALETTE['ink']}; font-family: Georgia, 'Times New Roman', serif; }}
        .tk-tagline {{ color: {PALETTE['muted']}; font-size: 1.05rem; }}
        .tk-chip {{
            display: inline-block; background: {PALETTE['sand']}; color: {PALETTE['ink']};
            border: 1px solid #e4d3bb; border-radius: 999px; padding: 2px 12px;
            margin: 3px 4px 3px 0; font-size: 0.82rem; font-family: Georgia, serif;
        }}
        .tk-age {{
            display:inline-block; background: {PALETTE['amber']}; color: #fff;
            border-radius: 6px; padding: 1px 10px; font-size: 0.78rem; font-weight: 600;
        }}
        .tk-card {{
            background: #fff; border: 1px solid #ecdcc4; border-radius: 14px;
            padding: 0.4rem 0.9rem 0.9rem; box-shadow: 0 2px 10px rgba(120,80,40,0.06);
        }}
        .tk-narrative {{
            font-family: Georgia, 'Times New Roman', serif; font-size: 1.18rem;
            line-height: 1.85; color: {PALETTE['ink']};
        }}
        .tk-panelnum {{
            color: {PALETTE['amber']}; font-weight: 700; letter-spacing: 0.12em;
            font-size: 0.8rem; text-transform: uppercase;
        }}
        .tk-moral {{
            border-left: 3px solid {PALETTE['amber']}; padding: 4px 0 4px 12px;
            margin-top: 10px; color: {PALETTE['muted']}; font-style: italic; font-size: 0.95rem;
        }}
        .tk-context {{
            background: {PALETTE['sand']}; border-radius: 12px; padding: 16px 20px;
            font-family: Georgia, serif; color: {PALETTE['ink']}; line-height: 1.7;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def chips(items: list[str]) -> str:
    """Return HTML for a row of pill 'chips' (e.g. key figures)."""
    return " ".join(f"<span class='tk-chip'>{i}</span>" for i in (items or []))
