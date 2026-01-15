import streamlit as st
import random
import copy
import json
import os

# =====================================================
# A7DO — BORN INTELLIGENCE
# SAVE + OBJECTS + CORRECT PHYSICS ORDER
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Embodied • Remembering • Object-aware • Self-correcting")

SAVE_FILE = "a7do_recall.json"

# =====================================================
# CONSTANTS
# =====================================================

GRID_SIZE = 8
WORLD_LIMIT = 20.0
OBJECT_RADIUS = 1.5   # 👈 FIX: prevent tunnelling

MIN_AROUSAL = 0.15
RECALL_ALPHA = 0.2

# Appraisal weights
W_K = 1.0
W_E = 0.4
W_T = 0.6
W_O = 0.8

# =====================================================
# SAVE / LOAD
# =====================================================

def load_recall():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_recall():
    with open(SAVE_FILE, "w") as f:
        json.dump(st.session_state.recall, f, indent=2)

# =====================================================
# INIT
# =====================================================

def init_state():
    st.session_state.event = 0

    st.session_state.square = [
        [random.random() for _ in range(GRID_SIZE)]
        for _ in range(GRID_SIZE)
    ]
    st.session_state.prev_square = copy.deepcopy(st.session_state.square)

    st.session_state.emotion = {
        "arousal": 0.4,
        "valence": 0.0,
        "confidence": 0.3,
    }

    st.session_state.body = {
        "x": random.uniform(2, WORLD_LIMIT - 2),
        "v": 0.0,
        "dir": random.choice([-1, 1]),
        "energy": 1.0,
        "touch": False,
    }

    # 🌍 OBJECT WORLD (1D)
    st.session_state.objects = [
        {"type": "resource", "x": 5.0, "strength": 0.4},
        {"type": "hazard", "x": 14.0, "strength": 0.5},
    ]

    st.session_state.vision = {
        "motion": 0.0,
        "object": None,
        "distance": None,
    }

    st.session_state.recall = load_recall()
    st.session_state.ledger = []

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
# WORLD
# =====================================================

def square_step(grid):
    return [
        [clamp(v + random.uniform(-0.05, 0.05)) for v in row]
        for row in grid
    ]

def square_features(grid):
    flat = [v for r in grid for v in r]
    mean = sum(flat) / len(flat)
    var = sum((v - mean) ** 2 for v in flat) / len(flat)
    return mean, var

# =====================================================
# BODY
# =====================================================

def update_body(action):
    b = st.session_state.body

    if action == "MOVE":
        b["v"] = min(1.0, b["v"] + 0.1)
        b["energy"] = max(0.0, b["energy"] - 0.05)

    elif action == "REST":
        b["v"] = 0.0
        b["energy"] = min(1.0, b["energy"] + 0.08)

    b["x"] += b["v"] * b["dir"]

# =====================================================
# TOUCH (BOUNDARIES)
# =====================================================

def update_touch():
    b = st.session_state.body

    if b["x"] <= 0:
        b["x"] = 0
        b["touch"] = True
        b["dir"] = 1

    elif b["x"] >= WORLD_LIMIT:
        b["x"] = WORLD_LIMIT
        b["touch"] = True
        b["dir"] = -1

    else:
        b["touch"] = False

# =====================================================
# VISION (AFTER MOVEMENT)
# =====================================================

def update_vision():
    # grid motion (novelty)
    prev = st.session_state.prev_square
    curr = st.session_state.square
    delta = sum(
        abs(curr[i][j] - prev[i][j])
        for i in range(GRID_SIZE)
        for j in range(GRID_SIZE)
    )
    st.session_state.vision["motion"] = delta / (GRID_SIZE ** 2)

    # object distance sensing
    b = st.session_state.body
    nearest = None
    nearest_dist = float("inf")

    for obj in st.session_state.objects:
        d = abs(obj["x"] - b["x"])
        if d < nearest_dist:
            nearest = obj
            nearest_dist = d

    if nearest_dist <= OBJECT_RADIUS:
        st.session_state.vision["object"] = nearest
        st.session_state.vision["distance"] = round(nearest_dist, 2)
    else:
        st.session_state.vision["object"] = None
        st.session_state.vision["distance"] = None

    st.session_state.prev_square = copy.deepcopy(curr)

# =====================================================
# OBJECT EFFECTS
# =====================================================

def apply_object_effects():
    obj = st.session_state.vision["object"]
    b = st.session_state.body

    if not obj:
        return 0.0

    if obj["type"] == "resource":
        b["energy"] = clamp(b["energy"] + obj["strength"])
        return +obj["strength"]

    if obj["type"] == "hazard":
        b["energy"] = clamp(b["energy"] - obj["strength"])
        return -obj["strength"]

    return 0.0

# =====================================================
# RECALL
# =====================================================

def recall_get(sig):
    if sig not in st.session_state.recall:
        st.session_state.recall[sig] = {
            "count": 0,
            "expected_K": 0.3,
            "valence": 0.0,
        }
    return st.session_state.recall[sig]

def appraisal(sig, K, energy_delta, touch):
    r = recall_get(sig)
    dK = r["expected_K"] - K
    t = 1.0 if touch else 0.0

    raw = W_K * dK + W_E * energy_delta - W_T * t
    return max(-1.0, min(1.0, raw * 2))

def recall_update(sig, K, val):
    r = recall_get(sig)
    r["count"] += 1
    r["expected_K"] = ema(r["expected_K"], K)
    r["valence"] = ema(r["valence"], val)

# =====================================================
# EMOTION
# =====================================================

def update_emotion(val):
    e = st.session_state.emotion
    e["valence"] = val
    e["arousal"] = clamp(e["arousal"] + abs(val))
    e["confidence"] = clamp(e["confidence"] + 0.05 * (1 - abs(val)))
    e["arousal"] = max(MIN_AROUSAL, e["arousal"])

# =====================================================
# CHOICE
# =====================================================

def choose_action():
    b = st.session_state.body
    v = st.session_state.vision

    if b["energy"] < 0.4:
        return "REST"

    if v["object"]:
        if v["object"]["type"] == "resource":
            return "MOVE"
        if v["object"]["type"] == "hazard":
            b["dir"] *= -1
            return "MOVE"

    return random.choice(["MOVE", "REST"])

# =====================================================
# CONTROLS
# =====================================================

c1, c2 = st.columns(2)
with c1:
    step = st.button("▶ Advance Event")
with c2:
    if st.button("⟲ Rebirth (keep memory)"):
        init_state()
        st.experimental_rerun()

# =====================================================
# EVENT LOOP (CORRECT ORDER)
# =====================================================

if step:
    st.session_state.event += 1

    # world evolves
    st.session_state.square = square_step(st.session_state.square)

    mean, var = square_features(st.session_state.square)
    K = var / (1 - mean + 1e-6)
    sig = f"{round(mean,2)}|{round(var,2)}"

    # choose + act
    action = choose_action()
    update_body(action)
    update_touch()

    # sense AFTER movement
    update_vision()

    # object interaction
    energy_before = st.session_state.body["energy"]
    apply_object_effects()
    energy_delta = st.session_state.body["energy"] - energy_before

    # evaluate + remember
    val = appraisal(sig, K, energy_delta, st.session_state.body["touch"])
    recall_update(sig, K, val)
    update_emotion(val)

    save_recall()

    st.session_state.ledger.append({
        "event": st.session_state.event,
        "x": round(st.session_state.body["x"], 2),
        "energy": round(st.session_state.body["energy"], 2),
        "touch": st.session_state.body["touch"],
        "vision_object": st.session_state.vision["object"],
        "distance": st.session_state.vision["distance"],
        "action": action,
        "valence": round(val, 2),
    })

# =====================================================
# DISPLAY
# =====================================================

st.subheader("🧍 Body")
st.json(st.session_state.body)

st.subheader("👁️ Vision")
st.json(st.session_state.vision)

st.subheader("❤️ Emotion")
st.json(st.session_state.emotion)

st.subheader("🌍 Objects")
for o in st.session_state.objects:
    st.write(o)

st.subheader("🧠 Recall (Persistent)")
for k, v in list(st.session_state.recall.items())[:5]:
    st.write(k, v)

with st.expander("📜 Ledger (Last 10)"):
    for row in st.session_state.ledger[-10:]:
        st.write(row)