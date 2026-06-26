"""
The Reader — shown when a story is opened from the Library.

Layout: the story title and context up top, then each scene as an illustration
beside its narrative text (alternating sides), and the closing reflection at the
end. A toggle switches between the two generated illustration sets.

The selected story is passed via the ?story_id= query parameter.
"""
import streamlit as st
import storybook_api as api

st.set_page_config(page_title="Read · Tariikhna", page_icon="📖", layout="wide")
api.inject_base_css()

# ── Resolve which story to show ───────────────────────────────────────────────
# Prefer the URL (?story_id=) for deep-links/refresh; fall back to session_state
# set by the navigation buttons (st.switch_page drops query params).
raw_id = st.query_params.get("story_id") or st.session_state.get("story_id")
if not raw_id:
    st.markdown("# 📖 Reader")
    st.info("No story selected yet. Head to the Library to pick one.")
    if st.button("📚  Go to the Library"):
        st.switch_page("pages/1_📚_Stories.py")
    st.stop()

try:
    story_id = int(raw_id)
except (ValueError, TypeError):
    st.error("Invalid story id.")
    st.stop()

# Keep session + URL in sync so a refresh keeps showing the same story.
st.session_state["story_id"] = story_id
if st.query_params.get("story_id") != str(story_id):
    st.query_params["story_id"] = str(story_id)

try:
    story = api.get_story(story_id)
except api.BackendError as exc:
    api.show_backend_error(exc)
    st.stop()

# ── Top bar ───────────────────────────────────────────────────────────────────
top_l, top_r = st.columns([3, 1])
with top_l:
    if st.button("←  Back to the Library"):
        st.switch_page("pages/1_📚_Stories.py")

panels = story.get("panels", [])

# Which illustration variants exist across this story?
available = []
for key in ("base", "v1"):
    if any(p.get("image_variants", {}).get(key) for p in panels):
        available.append(key)
labels = {"base": "Storybook", "v1": "Detailed"}

with top_r:
    if len(available) > 1:
        choice = st.radio(
            "Illustrations",
            options=available,
            format_func=lambda k: labels.get(k, k),
            horizontal=True,
            label_visibility="collapsed",
        )
    else:
        choice = available[0] if available else None


def panel_image(panel: dict) -> str | None:
    variants = panel.get("image_variants", {})
    if choice and variants.get(choice):
        return variants[choice]
    return panel.get("image_url")  # fallback to default


# ── Title + context ───────────────────────────────────────────────────────────
st.markdown(f"# {story['title']}")
meta_bits = []
if story.get("reading_age"):
    meta_bits.append(f"<span class='tk-age'>Ages {story['reading_age']}</span>")
if story.get("source"):
    meta_bits.append(f"<span class='tk-tagline'>Source: {story['source']}</span>")
if meta_bits:
    st.markdown("&nbsp;&nbsp;".join(meta_bits), unsafe_allow_html=True)

if story.get("key_figures"):
    st.markdown(api.chips(story["key_figures"]), unsafe_allow_html=True)

if story.get("introduction"):
    st.write("")
    st.markdown(
        f"<div class='tk-context'>{story['introduction']}</div>",
        unsafe_allow_html=True,
    )

st.write("")
st.divider()

# ── Scenes: image beside narrative text, alternating sides ────────────────────
for i, panel in enumerate(panels):
    img = panel_image(panel)
    text_block = (
        f"<div class='tk-panelnum'>Scene {panel.get('panel_number', i + 1)}</div>"
        f"<h3 style='margin:0.2rem 0 0.6rem;'>{panel.get('title','')}</h3>"
        f"<div class='tk-narrative'>{panel.get('narrative_text','')}</div>"
    )
    if panel.get("moral_lesson"):
        text_block += f"<div class='tk-moral'>💛 {panel['moral_lesson']}</div>"

    image_left = i % 2 == 0  # alternate for visual rhythm
    left, right = st.columns([1, 1], gap="large", vertical_alignment="center")
    if image_left:
        with left:
            if img:
                st.image(img, use_container_width=True)
        with right:
            st.markdown(text_block, unsafe_allow_html=True)
    else:
        with left:
            st.markdown(text_block, unsafe_allow_html=True)
        with right:
            if img:
                st.image(img, use_container_width=True)
    st.write("")
    st.divider()

# ── Closing reflection ────────────────────────────────────────────────────────
if story.get("conclusion"):
    st.markdown("### 🌙 In the end")
    st.markdown(
        f"<div class='tk-context'>{story['conclusion']}</div>",
        unsafe_allow_html=True,
    )

if story.get("moral_lesson"):
    st.write("")
    st.markdown(
        f"<div class='tk-moral' style='font-size:1.1rem;'>"
        f"<b>The lesson:</b> {story['moral_lesson']}</div>",
        unsafe_allow_html=True,
    )

st.write("")
st.write("")
nav_l, nav_r = st.columns(2)
with nav_l:
    if st.button("←  Back to the Library", key="bottom_back", use_container_width=True):
        st.switch_page("pages/1_📚_Stories.py")
with nav_r:
    if st.button("🏠  Home", key="bottom_home", use_container_width=True):
        st.switch_page("streamlit_app.py")
