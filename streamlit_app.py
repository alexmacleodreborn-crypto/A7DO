import streamlit as st
import random
import math

# =====================================================
# A7DO — BORN INTELLIGENCE (MOBILE SINGLE-FILE CORE)
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Persistence • Decoherence • Sandy’s Law • No Training")

# =====================================================
# SESSION STATE
# =====================================================

if "event" not in st.session_state:
    st.session_state.event = 0
    st.session_state.square = [[random.random() for _ in range(8)] for _ in range(8)]
    st.session_state.patterns = {}
    st.session_state.concepts = set()
    st.session_state.ledger = []
    st.session_state.emotion = {
        "arousal": 0.3,
        "valence": 0.0,
        "confidence": 0.2,
    }

# =====================================================
# SQUARE MICRODYNAMICS
# =====================================================

def square_step(grid):
    new = []
    for row in grid:
        new.append([max(0, min(1, v + random.uniform(-0.05, 0.05))) for v in row])
    return new

def square_features(grid):
    flat = [v for r in grid for v in r]
    return {
        "mean": sum(flat) / len(flat),
        "variance": sum((v - sum(flat)/len(flat))**2 for v in flat) / len(flat)
    }

# =====================================================
# SANDY’S LAW TRAP (SIMPLIFIED BUT STRUCTURAL)
# =====================================================

def trap_state(features):
    sigma = features["variance"]
    Z = 1.0 - features["mean"]
    K = sigma / (Z + 1e-6)

    if K > 1.1:
        regime = "ZENO"
    elif K > 0.6:
        regime = "TRANSITION"
    else:
        regime = "CLASSICAL"

    return Z, sigma, K, regime

# =====================================================
# PATTERNS & DECOHERENCE
# =====================================================

def observe_pattern(features):
    return f"{round(features['mean'],2)}|{round(features['variance'],2)}"

def update_patterns(sig, regime):
    p = st.session_state.patterns.setdefault(sig, {"count": 0, "decohered": False})
    if regime == "CLASSICAL":
        p["count"] += 1
    if p["count"] >= 3:
        p["decohered"] = True
        st.session_state.concepts.add(sig)

# =====================================================
# EMOTION REGULATION
# =====================================================

def update_emotion(regime):
    e = st.session_state.emotion
    if regime == "CLASSICAL":
        e["confidence"] = min(1, e["confidence"] + 0.05)
        e["arousal"] = max(0, e["arousal"] - 0.02)
    elif regime == "ZENO":
        e["arousal"] = min(1, e["arousal"] + 0.1)
        e["confidence"] = max(0, e["confidence"] - 0.1)

# =====================================================
# CHOICE ENGINE
# =====================================================

def choose_action(regime):
    if regime == "ZENO":
        return "HOLD"
    if st.session_state.emotion["confidence"] > 0.6:
        return "EXPLORE"
    return "OBSERVE"

# =====================================================
# ADVANCE EVENT
# =====================================================

if st.button("▶ Advance Event"):
    st.session_state.event += 1

    st.session_state.square = square_step(st.session_state.square)
    feats = square_features(st.session_state.square)
    Z, sigma, K, regime = trap_state(feats)

    sig = observe_pattern(feats)
    update_patterns(sig, regime)
    update_emotion(regime)
    action = choose_action(regime)

    st.session_state.ledger.append({
        "event": st.session_state.event,
        "Z": round(Z,3),
        "Σ": round(sigma,3),
        "K": round(K,3),
        "regime": regime,
        "pattern": sig,
        "action": action
    })

# =====================================================
# RESET (REBIRTH)
# =====================================================

if st.button("⟲ Rebirth"):
    st.session_state.clear()
    st.experimental_rerun()

# =====================================================
# DISPLAY
# =====================================================

if st.session_state.ledger:
    last = st.session_state.ledger[-1]

    c1, c2, c3 = st.columns(3)
    c1.metric("Trap Z", last["Z"])
    c2.metric("Entropy Σ", last["Σ"])
    c3.metric("Portal K", last["K"])

    st.write("**Regime:**", last["regime"])
    st.write("**Chosen Action:**", last["action"])

st.subheader("📌 Persistent Patterns")
for k, v in st.session_state.patterns.items():
    st.write(k, "→", v)

st.subheader("🧠 Decohered Concepts")
st.write(list(st.session_state.concepts))

st.subheader("❤️ Emotion State")
st.json(st.session_state.emotion)

with st.expander("📜 Ledger"):
    for row in st.session_state.ledger[-10:]:
        st.write(row)