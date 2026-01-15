import streamlit as st
import random

# =====================================================
# A7DO — BORN INTELLIGENCE (SINGLE FILE)
# Persistence → Competition → Selection
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Persistence • Competition • Decoherence • Sandy’s Law • No Training")

# =====================================================
# CONSTANTS (COGNITIVE CONSTRAINTS)
# =====================================================

GRID_SIZE = 8
MAX_CONCEPTS = 6              # cognitive capacity
DECOHERENCE_THRESHOLD = 3     # persistence needed
REPLACEMENT_THRESHOLD = 5     # must be stronger to replace

# =====================================================
# SESSION STATE (BIRTH)
# =====================================================

if "event" not in st.session_state:
    st.session_state.event = 0
    st.session_state.square = [[random.random() for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    st.session_state.patterns = {}
    st.session_state.concepts = set()
    st.session_state.ledger = []
    st.session_state.emotion = {
        "arousal": 0.4,
        "valence": 0.0,
        "confidence": 0.3,
    }

# =====================================================
# SQUARE MICRODYNAMICS
# =====================================================

def square_step(grid):
    return [
        [max(0, min(1, v + random.uniform(-0.05, 0.05))) for v in row]
        for row in grid
    ]

def square_features(grid):
    flat = [v for r in grid for v in r]
    mean = sum(flat) / len(flat)
    var = sum((v - mean) ** 2 for v in flat) / len(flat)
    return mean, var

# =====================================================
# SANDY’S LAW TRAP (STRUCTURAL)
# =====================================================

def trap_state(mean, variance):
    sigma = variance
    Z = 1.0 - mean
    K = sigma / (Z + 1e-6)

    if K > 1.1:
        regime = "ZENO"
    elif K > 0.6:
        regime = "TRANSITION"
    else:
        regime = "CLASSICAL"

    return Z, sigma, K, regime

# =====================================================
# PATTERNS → COMPETITION → DECOHERENCE
# =====================================================

def update_patterns(signature, regime):
    patterns = st.session_state.patterns
    concepts = st.session_state.concepts

    p = patterns.setdefault(signature, {"count": 0, "decohered": False})

    if regime == "CLASSICAL":
        p["count"] += 1

    # Attempt decoherence
    if p["count"] >= DECOHERENCE_THRESHOLD and not p["decohered"]:

        # Capacity available
        if len(concepts) < MAX_CONCEPTS:
            p["decohered"] = True
            concepts.add(signature)

        else:
            # Find weakest existing concept
            weakest = min(concepts, key=lambda c: patterns[c]["count"])

            # Replace only if significantly stronger
            if p["count"] > patterns[weakest]["count"] + REPLACEMENT_THRESHOLD:
                patterns[weakest]["decohered"] = False
                concepts.remove(weakest)

                p["decohered"] = True
                concepts.add(signature)

# =====================================================
# EMOTION REGULATION (PHYSICAL, NOT SYMBOLIC)
# =====================================================

def update_emotion(regime):
    e = st.session_state.emotion

    if regime == "CLASSICAL":
        e["confidence"] = min(1.0, e["confidence"] + 0.03)
        e["arousal"] = max(0.0, e["arousal"] - 0.02)

    elif regime == "TRANSITION":
        e["arousal"] = min(1.0, e["arousal"] + 0.05)
        e["confidence"] = max(0.0, e["confidence"] - 0.03)

    elif regime == "ZENO":
        e["arousal"] = min(1.0, e["arousal"] + 0.1)
        e["confidence"] = max(0.0, e["confidence"] - 0.1)

# =====================================================
# CHOICE ENGINE (CONSTRAINED)
# =====================================================

def choose_action(regime):
    e = st.session_state.emotion

    if regime == "ZENO":
        return "HOLD"

    if e["confidence"] > 0.7 and e["arousal"] < 0.3:
        return "EXPLORE"

    return "OBSERVE"

# =====================================================
# EVENT ADVANCE
# =====================================================

if st.button("▶ Advance Event"):
    st.session_state.event += 1

    st.session_state.square = square_step(st.session_state.square)
    mean, var = square_features(st.session_state.square)
    Z, sigma, K, regime = trap_state(mean, var)

    signature = f"{round(mean,2)}|{round(var,2)}"
    update_patterns(signature, regime)
    update_emotion(regime)
    action = choose_action(regime)

    st.session_state.ledger.append({
        "event": st.session_state.event,
        "Z": round(Z, 3),
        "Σ": round(sigma, 3),
        "K": round(K, 3),
        "regime": regime,
        "pattern": signature,
        "action": action
    })

# =====================================================
# REBIRTH
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

st.subheader("🧠 Active Concepts (Competitive)")
for c in st.session_state.concepts:
    st.write(
        c,
        "→ persistence:",
        st.session_state.patterns[c]["count"]
    )

st.subheader("❤️ Emotion State")
st.json(st.session_state.emotion)

with st.expander("📜 Ledger (Last 10 Events)"):
    for row in st.session_state.ledger[-10:]:
        st.write(row)