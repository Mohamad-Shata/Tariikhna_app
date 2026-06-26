"""
Tariikhna — Home page.

Tariikhna (تاريخنا, "our history") turns authentic Islamic historical narratives
into gentle, historically-corrected illustrated stories for children.

Run from the frontend/ folder:
    streamlit run streamlit_app.py
"""
import streamlit as st
import storybook_api as api

st.set_page_config(
    page_title="Tariikhna — Our History",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

api.inject_base_css()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center; padding: 1.4rem 0 0.4rem;">
        <div style="font-size:3.4rem; line-height:1;">📖</div>
        <h1 style="font-size:3rem; margin:0.3rem 0 0;">Tariikhna</h1>
        <div style="color:#b5651d; letter-spacing:0.35em; font-size:1.1rem;">تاريخنا · OUR HISTORY</div>
        <p class="tk-tagline" style="max-width:680px; margin:1rem auto 0;">
            Authentic Islamic history, retold as gentle illustrated storybooks for children —
            each scene historically reviewed, beautifully painted, and paired with a kind lesson.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
col_l, col_c, col_r = st.columns([1, 1, 1])
with col_c:
    if st.button("📚  Browse the Library", use_container_width=True, type="primary"):
        st.switch_page("pages/1_📚_Stories.py")

st.write("")
st.divider()

# ── What it is ────────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns(3)
with f1:
    st.markdown("### 🕌  Historically corrected")
    st.markdown(
        "<span class='tk-tagline'>Every panel is reviewed for historical accuracy and "
        "respectful depiction before it reaches a child's eyes.</span>",
        unsafe_allow_html=True,
    )
with f2:
    st.markdown("### 🎨  Gentle illustrations")
    st.markdown(
        "<span class='tk-tagline'>Soft, warm, hand-painted watercolor scenes designed "
        "for ages 6–12 — calm, dignified, and never frightening.</span>",
        unsafe_allow_html=True,
    )
with f3:
    st.markdown("### 💛  A lesson in every story")
    st.markdown(
        "<span class='tk-tagline'>Kindness, patience, mercy and equality — each story "
        "carries a moral children can carry with them.</span>",
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ── Featured stories preview ──────────────────────────────────────────────────
st.markdown("## ✨ Featured stories")
try:
    stories = api.list_stories()
except api.BackendError as exc:
    api.show_backend_error(exc)
    st.stop()

if not stories:
    st.info("No stories have been imported yet. Run `python import_storybook.py` in the backend.")
    st.stop()

cols = st.columns(min(len(stories), 4))
for col, story in zip(cols, stories[:4]):
    with col:
        if story.get("cover_image"):
            st.image(story["cover_image"], use_column_width=True)
        st.markdown(f"**{story['title']}**")
        st.markdown(
            f"<span class='tk-age'>Ages {story.get('reading_age','—')}</span>",
            unsafe_allow_html=True,
        )
        if st.button("Read", key=f"home_read_{story['id']}", use_container_width=True):
            api.open_story(story["id"])

st.write("")
st.caption("Use the sidebar to navigate · Built for the Tariikhna graduation project.")
