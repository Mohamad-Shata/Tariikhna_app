"""
The Library — a grid of every available story. Clicking "Read" opens the
reader page for that story.
"""
import streamlit as st
import storybook_api as api

st.set_page_config(page_title="Library · Tariikhna", page_icon="📚", layout="wide")
api.inject_base_css()

st.markdown("# 📚 The Library")
st.markdown(
    "<p class='tk-tagline'>Choose a story to read. Each one is a short, illustrated "
    "journey through a moment in Islamic history.</p>",
    unsafe_allow_html=True,
)
st.write("")

try:
    stories = api.list_stories()
except api.BackendError as exc:
    api.show_backend_error(exc)
    st.stop()

if not stories:
    st.info("No stories have been imported yet. Run `python import_storybook.py` in the backend.")
    st.stop()


PER_ROW = 3
for row_start in range(0, len(stories), PER_ROW):
    row = stories[row_start:row_start + PER_ROW]
    cols = st.columns(PER_ROW, gap="large")
    for col, story in zip(cols, row):
        with col:
            with st.container(border=True):
                if story.get("cover_image"):
                    st.image(story["cover_image"], use_container_width=True)

                st.markdown(f"### {story['title']}")
                st.markdown(
                    f"<span class='tk-age'>Ages {story.get('reading_age','—')}</span>"
                    f"&nbsp;&nbsp;<span class='tk-tagline'>{story.get('panel_count','?')} scenes</span>",
                    unsafe_allow_html=True,
                )

                intro = (story.get("introduction") or "").strip()
                if len(intro) > 170:
                    intro = intro[:170].rsplit(" ", 1)[0] + "…"
                st.markdown(f"<p class='tk-tagline'>{intro}</p>", unsafe_allow_html=True)

                if story.get("key_figures"):
                    st.markdown(api.chips(story["key_figures"]), unsafe_allow_html=True)

                st.write("")
                if st.button("📖  Read this story", key=f"read_{story['id']}",
                             use_container_width=True, type="primary"):
                    api.open_story(story["id"])
    st.write("")
