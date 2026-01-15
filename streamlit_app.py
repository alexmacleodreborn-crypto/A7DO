import streamlit as st
import random
import copy

# =====================================================
# A7DO — BORN INTELLIGENCE (SINGLE FILE)
# Embodiment + Sensing + Choice
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Persistence • Competition • Shock • Decay • Curiosity • Choice • Body")

# =====================================================
# CONSTANTS
# =====================================================

GRID_SIZE = 8

MAX_CONCEPTS = 6
DECOHERENCE_THRESHOLD = 3
REPLACEMENT_THRESHOLD = 5

SHOCK_PROBABILITY = 0.08
SHOCK_MAGNITUDE = 0.6

DECAY_RATE = 0.01
MIN_AROUSAL = 0.15

# =====================================================
# SESSION STATE (BIRTH)
# =====================================================

if "event" not in st.session_state:
    st.session_state.event = 0

    # Environment
    st.session_state.square = [
        [random.random() for _ in range(GRID_SIZE)]
        for _ in range(GRID_SIZE)
    ]

    # Cognition
    st.session_state.patterns = {}
    st.session_state.concepts = set()
    st.session_state.ledger = []

    # Emotion
    st.session_state.emotion = {
        "arousal": 0.4,
        "valence": 0.0,
        "confidence": 0.3,
    }

    # Body (Embodiment)
    st.session_state.body = {
        "x": 0.0,
        "v": 0.0,
        "energy": 1.0
    }

# =====================================================
# SQUARE MICRODYNAMICS
# =====================================================

def square_step(grid, scale=1.0):
    return [
        [max(0, min(1, v + random.uniform(-0.05, 0.05) * scale)) for v in row]
        for row in grid
    ]

def apply_shock(grid):
    cx = random.randint(0, GRID_SIZE - 1)
    cy = random.randint(0, GRID_SIZE - 1)

    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            dist = abs(i - cx) + abs(j - cy)
            influence = max(0, SHOCK_MAGNITUDE - 0.15 * dist)
            if influence > 0:
                grid[i][j] = max(
                    0,
                    min(1, grid[i][j] + random.uniform(-influence, influence))
                )
    return grid

def square_features(grid):
    flat = [v for r in grid for v in r]
    mean = sum(flat) / len(flat)
    var = sum((v - mean) ** 2 for v in flat) / len(flat)
    return mean, var

# =====================================================
# SANDY’S LAW TRAP
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
# PATTERN DECAY (IRREVERSIBILITY)
# =====================================================

def decay_patterns():
    for p in st.session_state.patterns.values():
        if p["count"] > 0:
            p["count"] = max(0, p["count"] - DECAY_RATE)

# =====================================================
# PATTERNS → COMPETITION → DECOHERENCE
# =====================================================

def update_patterns(signature, regime):
    patterns = st.session_state.patterns
    concepts = st.session_state.concepts

    p = patterns.setdefault(signature, {"count": 0, "decohered": False})

    if regime == "CLASSICAL":
        p["count"] += 1

    if p["count"] >= DECOHERENCE_THRESHOLD and not p["decohered"]:
        if len(concepts) < MAX_CONCEPTS:
            p["decohered"] = True
            concepts.add(signature)
        else:
            weakest = min(concepts, key=lambda c: patterns[c]["count"])
            if p["count"] > patterns[weakest]["count"] + REPLACEMENT_THRESHOLD:
                patterns[weakest]["decohered"] = False
                concepts.remove(weakest)
                p["decohered"] = True
                concepts.add(signature)

# =====================================================
# BODY DYNAMICS (EMBODIMENT)
# =====================================================

def update_body(action):
    b = st.session_state.body

    if action == "EXPLORE":
        b["v"] = min(1.0, b["v"] + 0.1)
        b["energy"] = max(0.0, b["energy"] - 0.05)

    elif action == "OBSERVE":
        b["v"] = max(0.0, b["v"] - 0.05)
        b["energy"] = min(1.0, b["energy"] + 0.03)

    elif action == "HOLD":
        b["v"] = 0.0
        b["energy"] = min(1.0, b["energy"] + 0.01)

    b["x"] += b["v"]

# =====================================================
# EMOTION REGULATION + PROPRIOCEPTION
# =====================================================

def update_emotion(regime, shocked):
    e = st.session_state.emotion
    b = st.session_state.body

    if shocked:
        e["arousal"] = min(1.0, e["arousal"] + 0.25)
        e["confidence"] = max(0.0, e["confidence"] - 0.25)

    elif regime == "CLASSICAL":
        e["confidence"] = min(1.0, e["confidence"] + 0.03)
        e["arousal"] = max(0.0, e["arousal"] - 0.02)

    elif regime == "TRANSITION":
        e["arousal"] = min(1.0, e["arousal"] + 0.06)
        e["confidence"] = max(0.0, e["confidence"] - 0.05)

    elif regime == "ZENO":
        e["arousal"] = min(1.0, e["arousal"] + 0.12)
        e["confidence"] = max(0.0, e["confidence"] - 0.15)

    # Proprioception (body → mind)
    e["arousal"] = min(1.0, e["arousal"] + 0.1 * b["v"])
    e["confidence"] = max(0.0, e["confidence"] - 0.2 * (1.0 - b["energy"]))

    # Curiosity floor
    e["arousal"] = max(MIN_AROUSAL, e["arousal"])

# =====================================================
# CHOICE ENGINE (PREDICTIVE)
# =====================================================

def predict_action_K(action, grid):
    test_grid = copy.deepcopy(grid)

    if action == "OBSERVE":
        test_grid = square_step(test_grid, scale=0.5)
    elif action == "EXPLORE":
        test_grid = square_step(test_grid, scale=1.2)
    elif action == "HOLD":
        pass

    mean, var = square_features(test_grid)
    _, _, K, regime = trap_state(mean, var)

    penalty = 0
    if regime == "ZENO":
        penalty = 2.0
    elif regime == "TRANSITION":
        penalty = 0.5

    return K + penalty

def choose_action(grid):
    candidates = ["OBSERVE", "EXPLORE", "HOLD"]
    scored = {a: predict_action_K(a, grid) for a in candidates}
    return min(scored, key=scored.get)

# =====================================================
# EVENT ADVANCE
# =====================================================

force_shock = st.button("⚡ Force Shock")

if st.button("▶ Advance Event"):
    st.session_state.event += 1

    shocked = False
    st.session_state.square = square_step(st.session_state.square)

    if force_shock or random.random() < SHOCK_PROBABILITY:
        st.session_state.square = apply_shock(st.session_state.square)
        shocked = True

    decay_patterns()

    mean, var = square_features(st.session_state.square)
    Z, sigma, K, regime = trap_state(mean, var)

    signature = f"{round(mean,2)}|{round(var,2)}"
    update_patterns(signature, regime)
    update_emotion(regime, shocked)

    action = choose_action(st.session_state.square)
    update_body(action)

    st.session_state.ledger.append({
        "event": st.session_state.event,
        "shock": shocked,
        "Z": round(Z, 3),
        "Σ": round(sigma, 3),
        "K": round(K, 3),
        "regime": regime,
        "pattern": signature,
        "action": action,
        "body": dict(st.session_state.body)
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
    st.write("**Shock Event:**", "YES ⚡" if last["shock"] else "No")

st.subheader("🧠 Active Concepts")
for c in st.session_state.concepts:
    st.write(c, "→ persistence:", round(st.session_state.patterns[c]["count"], 2))

st.subheader("❤️ Emotion State")
st.json(st.session_state.emotion)

st.subheader("🧍 Body Awareness")
st.json(st.session_state.body)

with st.expander("📜 Ledger (Last 10 Events)"):
    for row in st.session_state.ledger[-10:]:
        st.write(row)