import streamlit as st
import random
import copy

# =====================================================
# A7DO — BORN INTELLIGENCE
# Embodiment • Vision • Touch • Recall • Valence • Escape
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Learning through embodiment, memory, and choice")

# =====================================================
# CONSTANTS
# =====================================================

GRID_SIZE = 8
WORLD_LIMIT = 20.0

SHOCK_PROBABILITY = 0.08
SHOCK_MAGNITUDE = 0.6

DECAY_RATE = 0.01
MIN_AROUSAL = 0.15

RECALL_ALPHA = 0.2
CONF_LEARN_RATE = 0.06
CONF_FORGET_RATE = 0.03

# Appraisal weights
W_K = 1.0
W_E = 0.35
W_M = 0.25
W_T = 0.6

# =====================================================
# INITIALISATION
# =====================================================

def init_state():
    st.session_state.event = 0

    st.session_state.square = [
        [random.random() for _ in range(GRID_SIZE)]
        for _ in range(GRID_SIZE)
    ]
    st.session_state.prev_square = copy.deepcopy(st.session_state.square)

    st.session_state.patterns = {}
    st.session_state.concepts = set()
    st.session_state.ledger = []

    st.session_state.emotion = {
        "arousal": 0.4,
        "valence": 0.0,
        "confidence": 0.3,
    }

    # 👇 BODY NOW HAS DIRECTION
    st.session_state.body = {
        "x": 0.0,
        "v": 0.0,
        "dir": 1,      # +1 or -1
        "energy": 1.0,
        "touch": False,
    }

    st.session_state.vision = {"motion": 0.0}

    st.session_state.recall = {}

if "event" not in st.session_state:
    init_state()

# =====================================================
# UTIL
# =====================================================

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def ema(old, new, a=RECALL_ALPHA):
    return (1 - a) * old + a * new

# =====================================================
# ENVIRONMENT
# =====================================================

def square_step(grid, scale=1.0):
    return [
        [clamp(v + random.uniform(-0.05, 0.05) * scale) for v in row]
        for row in grid
    ]

def apply_shock(grid):
    cx = random.randint(0, GRID_SIZE - 1)
    cy = random.randint(0, GRID_SIZE - 1)
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            d = abs(i - cx) + abs(j - cy)
            inf = max(0, SHOCK_MAGNITUDE - 0.15 * d)
            if inf > 0:
                grid[i][j] = clamp(grid[i][j] + random.uniform(-inf, inf))
    return grid

def square_features(grid):
    flat = [v for r in grid for v in r]
    mean = sum(flat) / len(flat)
    var = sum((v - mean) ** 2 for v in flat) / len(flat)
    return mean, var

# =====================================================
# SENSES
# =====================================================

def update_vision():
    prev = st.session_state.prev_square
    curr = st.session_state.square
    delta = 0.0
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            delta += abs(curr[i][j] - prev[i][j])
    st.session_state.vision["motion"] = delta / (GRID_SIZE ** 2)
    st.session_state.prev_square = copy.deepcopy(curr)

def update_touch():
    b = st.session_state.body

    if b["x"] <= 0:
        b["x"] = 0.0
        b["touch"] = True
        b["v"] = 0.0
        b["dir"] = 1       # bounce right

    elif b["x"] >= WORLD_LIMIT:
        b["x"] = WORLD_LIMIT
        b["touch"] = True
        b["v"] = 0.0
        b["dir"] = -1      # bounce left

    else:
        b["touch"] = False

# =====================================================
# BODY
# =====================================================

def update_body(action):
    b = st.session_state.body

    if action == "EXPLORE":
        b["v"] = min(1.0, b["v"] + 0.1)
        b["energy"] = max(0.0, b["energy"] - 0.06)

    elif action == "OBSERVE":
        b["v"] = max(0.0, b["v"] - 0.08)
        b["energy"] = min(1.0, b["energy"] + 0.05)

    elif action == "HOLD":
        b["v"] = 0.0
        b["energy"] = min(1.0, b["energy"] + 0.1)

    # 👇 MOVEMENT NOW USES DIRECTION
    b["x"] += b["v"] * b["dir"]

# =====================================================
# TRAP STATE (SANDY’S LAW)
# =====================================================

def trap_state(mean, var):
    Z = 1.0 - mean
    K = var / (Z + 1e-6)

    if K > 1.1:
        r = "ZENO"
    elif K > 0.6:
        r = "TRANSITION"
    else:
        r = "CLASSICAL"

    return K, r

# =====================================================
# RECALL
# =====================================================

def recall_get(sig):
    if sig not in st.session_state.recall:
        st.session_state.recall[sig] = {
            "count": 0,
            "expected_K": 0.3,
            "expected_energy": 0.8,
            "expected_motion": 0.1,
            "valence": 0.0,
            "conf_floor": 0.2,
            "escape_bias": 0.0,
        }
    return st.session_state.recall[sig]

def appraisal(sig, K, energy, motion, touch):
    r = recall_get(sig)

    dK = r["expected_K"] - K
    dE = energy - r["expected_energy"]
    dM = motion - r["expected_motion"]
    t = 1.0 if touch else 0.0

    raw = W_K*dK + W_E*dE + W_M*dM - W_T*t
    val = max(-1.0, min(1.0, raw * 2.5))

    pred_err = abs(K - r["expected_K"])
    return val, pred_err

def recall_update(sig, K, energy, motion, touch, valence, pred_err):
    r = recall_get(sig)
    r["count"] += 1

    r["expected_K"] = ema(r["expected_K"], K)
    r["expected_energy"] = ema(r["expected_energy"], energy)
    r["expected_motion"] = ema(r["expected_motion"], motion)
    r["valence"] = ema(r["valence"], valence)

    good = max(0.0, 0.15 - pred_err) / 0.15
    bad = max(0.0, pred_err - 0.15) / 0.35
    r["conf_floor"] = clamp(
        r["conf_floor"] + CONF_LEARN_RATE*good - CONF_FORGET_RATE*bad
    )

    if touch:
        r["escape_bias"] = ema(r["escape_bias"], 1.0 - motion)
    else:
        r["escape_bias"] = ema(r["escape_bias"], 0.0)

# =====================================================
# EMOTION
# =====================================================

def update_emotion(regime, sig):
    e = st.session_state.emotion
    b = st.session_state.body
    v = st.session_state.vision
    r = recall_get(sig)

    e["arousal"] = clamp(e["arousal"] + 0.4 * v["motion"] + 0.1 * b["v"])
    if b["touch"]:
        e["arousal"] = clamp(e["arousal"] + 0.2)

    e["confidence"] = max(
        r["conf_floor"],
        clamp(e["confidence"] - 0.1 * (1.0 - b["energy"]))
    )

    e["arousal"] = max(MIN_AROUSAL, e["arousal"])

# =====================================================
# CHOICE
# =====================================================

def choose_action(sig):
    b = st.session_state.body
    r = recall_get(sig)

    scores = {}

    for a in ["EXPLORE", "OBSERVE", "HOLD"]:
        s = 0.0

        if b["energy"] < 0.35 and a == "EXPLORE":
            s += 0.4

        if b["touch"] and r["valence"] < -0.1:
            if a == "HOLD":
                s += 0.8
            if a == "EXPLORE":
                s -= 0.3

        if r["escape_bias"] > 0.2 and a == "HOLD":
            s += 0.3

        scores[a] = s

    return min(scores, key=scores.get), scores

# =====================================================
# CONTROLS
# =====================================================

col1, col2, col3 = st.columns(3)
with col1:
    force_shock = st.button("⚡ Force Shock")
with col2:
    step = st.button("▶ Advance Event")
with col3:
    if st.button("⟲ Rebirth"):
        st.session_state.clear()
        init_state()
        st.experimental_rerun()

# =====================================================
# STEP
# =====================================================

if step:
    st.session_state.event += 1

    st.session_state.square = square_step(st.session_state.square)
    if force_shock or random.random() < SHOCK_PROBABILITY:
        st.session_state.square = apply_shock(st.session_state.square)

    update_vision()

    mean, var = square_features(st.session_state.square)
    K, regime = trap_state(mean, var)
    sig = f"{round(mean,2)}|{round(var,2)}"

    action, scores = choose_action(sig)
    update_body(action)
    update_touch()

    motion = st.session_state.vision["motion"]
    energy = st.session_state.body["energy"]
    touch = st.session_state.body["touch"]

    valence, pred_err = appraisal(sig, K, energy, motion, touch)
    recall_update(sig, K, energy, motion, touch, valence, pred_err)

    st.session_state.emotion["valence"] = valence
    update_emotion(regime, sig)

    st.session_state.ledger.append({
        "event": st.session_state.event,
        "action": action,
        "scores": scores,
        "K": round(K,3),
        "valence": round(valence,3),
        "touch": touch,
        "x": round(st.session_state.body["x"],2),
        "dir": st.session_state.body["dir"],
    })

# =====================================================
# DISPLAY
# =====================================================

st.subheader("❤️ Emotion")
st.json(st.session_state.emotion)

st.subheader("🧍 Body")
st.json(st.session_state.body)

st.subheader("👁️ Vision")
st.json(st.session_state.vision)

st.subheader("🗃️ Recall (Top)")
for sig, r in list(st.session_state.recall.items())[:6]:
    st.write(sig, r)

with st.expander("📜 Ledger (Last 10)"):
    for row in st.session_state.ledger[-10:]:
        st.write(row)