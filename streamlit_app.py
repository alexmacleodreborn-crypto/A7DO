import streamlit as st
from a7do_core.core.engine import A7DOEngine
from a7do_core.square.square_world import SquareWorld
from a7do_core.sled.sled_adapter import SLEDAdapter

# -------------------------------------------------
# STREAMLIT SETUP
# -------------------------------------------------

st.set_page_config(
    page_title="A7DO — Born Intelligence",
    layout="wide"
)

st.title("🧠 A7DO — Born Intelligence")
st.caption("Structure-first • Persistence • Decoherence • No training")

# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------

if "engine" not in st.session_state:
    square = SquareWorld(size=16)
    sled = SLEDAdapter()
    st.session_state.engine = A7DOEngine(
        square_world=square,
        sled_adapter=sled
    )
    st.session_state.step = 0

engine = st.session_state.engine

# -------------------------------------------------
# CONTROLS
# -------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    if st.button("▶ Advance One Event"):
        engine.step()
        st.session_state.step += 1

with col2:
    if st.button("⟲ Reset (Rebirth)"):
        st.session_state.clear()
        st.experimental_rerun()

# -------------------------------------------------
# DISPLAY
# -------------------------------------------------

state = engine.last_state

st.subheader(f"Event Count: {st.session_state.step}")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Trap Strength (Z)", f"{state.trap.Z:.3f}")
    st.metric("Entropy Export (Σ)", f"{state.trap.sigma:.3f}")

with c2:
    st.metric("Portal Score (K)", f"{state.trap.K:.3f}")
    st.metric("Regime", state.trap.regime)

with c3:
    st.metric("Arousal", f"{state.emotion.arousal:.2f}")
    st.metric("Valence", f"{state.emotion.valence:.2f}")

# -------------------------------------------------
# PATTERNS
# -------------------------------------------------

st.subheader("📌 Persistent Patterns")

for p in state.patterns:
    st.write(
        f"• `{p.signature}` | persistence={p.persistence} | decohered={p.decohered}"
    )

# -------------------------------------------------
# MIND MAP
# -------------------------------------------------

st.subheader("🕸 Mind Map (Decohered Concepts Only)")
st.json(state