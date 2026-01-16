import streamlit as st
import random
import json
import os
import math

# =====================================================
# A7DO — Born Intelligence
# Touch ✓  Investigation ✓
# Footsteps only when moving
# Constant heartbeat
# Moving light window (sun / moon)
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Embodied • Curious • Temporal • Environmental")

SAVE_FILE = "a7do_memory.json"

# =====================================================
# CONSTANTS
# =====================================================

WORLD_LIMIT = 20.0
MAP_BIN_SIZE = 2.0

TOUCH_PERSIST = 3
INVESTIGATE_PERSIST = 4
ATTENTION_PERSIST = 6

RECALL_ALPHA = 0.2
MIN_AROUSAL = 0.15

# motion
MIN_MOVE_V = 0.25
MOVE_ACCEL = 0.12
MOVE_COST = 0.04
REST_GAIN = 0.07

# sound
BASE_HEART = 0.8
HEART_AROUSAL_GAIN = 0.6
FOOTSTEP_GAIN = 1.2
DISRUPTION_GAIN = 1.0

# light window (sun / moon)
LIGHT_WINDOW_RADIUS = 3.0
LIGHT_WINDOW_STRENGTH = 0.7
DAY_CYCLE = 120  # events per full sweep

# =====================================================
# UTIL
# =====================================================

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def ema(old, new, a=RECALL_ALPHA):
    return (1 - a) * old + a * new

def map_bin(x):
    return f"{int(x // MAP_BIN_SIZE) * MAP_BIN_SIZE:.1f}"

# =====================================================
# SAVE / LOAD
# =====================================================

def load_memory():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        if "recall" in data:
            data.setdefault("map", {})
            return data
        return {"recall": data, "map": {}}
    return {"recall": {}, "map": {}}

def save_memory():
    with open(SAVE_FILE, "w") as f:
        json.dump(
            {"recall": st.session_state.recall,
             "map": st.session_state.map_memory},
            f,
            indent=2
        )

# =====================================================
# INIT
# =====================================================

def init_state():
    mem = load_memory()

    st.session_state.event = 0

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
        "touch_timer": 0,
        "was_touching": False,
        "investigating": False,
        "investigate_timer": 0,
    }

    st.session_state.vision = {
        "dark": 0.0,
        "light": 0.0,
        "attn_timer": 0,
    }

    st.session_state.sound = {
        "heart": 0.0,
        "foot": 0.0,
        "rhythm": 0.0,
        "disruption": 0.0,
    }
    st.session_state.prev_rhythm = None

    st.session_state.recall = mem["recall"]
    st.session_state.map_memory = mem["map"]
    st.session_state.ledger = []

if "event" not in st.session_state:
    init_state()

# =====================================================
# LIGHT WINDOW (SUN / MOON)
# =====================================================

def light_window_position():
    phase = (st.session_state.event % DAY_CYCLE) / DAY_CYCLE
    return WORLD_LIMIT * phase

def light_window(x):
    center = light_window_position()
    dx = abs(x - center)
    if dx > LIGHT_WINDOW_RADIUS:
        return 0.0
    return LIGHT_WINDOW_STRENGTH * math.exp(-(dx / LIGHT_WINDOW_RADIUS) ** 2)

# =====================================================
# TOUCH → INVESTIGATION
# =====================================================

def update_touch():
    b = st.session_state.body
    touching = False

    if b["x"] <= 0:
        b["x"] = 0
        b["dir"] = 1
        touching = True
    elif b["x"] >= WORLD_LIMIT:
        b["x"] = WORLD_LIMIT
        b["dir"] = -1
        touching = True

    if touching and not b["was_touching"]:
        b["touch_timer"] = TOUCH_PERSIST
        b["investigating"] = True
        b["investigate_timer"] = INVESTIGATE_PERSIST

    if b["touch_timer"] > 0:
        b["touch"] = True
        b["touch_timer"] -= 1
    else:
        b["touch"] = False

    if b["investigating"]:
        b["investigate_timer"] -= 1
        if b["investigate_timer"] <= 0:
            b["investigating"] = False

    b["was_touching"] = touching

# =====================================================
# BODY (NO CLAMPING)
# =====================================================

def update_body(action):
    b = st.session_state.body

    if b["investigating"]:
        b["v"] = max(0.05, b["v"] * 0.5)

    if action == "MOVE":
        b["v"] = min(1.0, max(MIN_MOVE_V, b["v"] + MOVE_ACCEL))
        b["energy"] = max(0.0, b["energy"] - MOVE_COST)
    elif action == "REST":
        b["v"] = 0.0
        b["energy"] = min(1.0, b["energy"] + REST_GAIN)

    b["x"] += b["v"] * b["dir"]

# =====================================================
# VISION (LIGHT FIELD)
# =====================================================

def update_vision():
    b = st.session_state.body
    light = light_window(b["x"])
    dark = 1.0 - light

    st.session_state.vision["light"] = round(light, 3)
    st.session_state.vision["dark"] = round(dark, 3)

# =====================================================
# SOUND
# =====================================================

def update_sound():
    b = st.session_state.body
    e = st.session_state.emotion
    s = st.session_state.sound

    # Heartbeat ALWAYS present
    heart = BASE_HEART + HEART_AROUSAL_GAIN * e["arousal"]

    # Footsteps ONLY if moving
    if b["v"] > 0:
        if b["investigating"]:
            foot = FOOTSTEP_GAIN * b["v"] * random.uniform(0.3, 0.7)
        else:
            foot = FOOTSTEP_GAIN * b["v"]
    else:
        foot = 0.0

    rhythm = heart + foot

    prev = st.session_state.prev_rhythm
    dr = 0 if prev is None else abs(rhythm - prev)
    st.session_state.prev_rhythm = rhythm

    disruption = DISRUPTION_GAIN * dr + (0.7 if b["touch"] else 0)

    s.update({
        "heart": round(heart, 3),
        "foot": round(foot, 3),
        "rhythm": round(rhythm, 3),
        "disruption": round(disruption, 3),
    })

# =====================================================
# CHOICE
# =====================================================

def choose_action():
    b = st.session_state.body

    if b["investigating"]:
        return "MOVE"

    if b["energy"] < 0.35:
        return "REST"

    return "MOVE"

# =====================================================
# STEP
# =====================================================

def step_once():
    st.session_state.event += 1
    action = choose_action()
    update_body(action)
    update_touch()
    update_vision()
    update_sound()
    save_memory()

    b = st.session_state.body
    v = st.session_state.vision
    s = st.session_state.sound

    st.session_state.ledger.append({
        "event": st.session_state.event,
        "x": round(b["x"], 2),
        "v": round(b["v"], 2),
        "touch": b["touch"],
        "investigating": b["investigating"],
        "light": v["light"],
        "heart": s["heart"],
        "foot": s["foot"],
        "rhythm": s["rhythm"],
        "disruption": s["disruption"],
    })

# =====================================================
# CONTROLS
# =====================================================

c1, c2 = st.columns(2)
with c1:
    step = st.button("▶ Advance Event")
with c2:
    auto = st.toggle("Auto (20 steps)")

if step:
    step_once()
if auto:
    for _ in range(20):
        step_once()

# =====================================================
# DISPLAY
# =====================================================

st.subheader("🧍 Body")
st.json(st.session_state.body)

st.subheader("👁️ Vision (Light / Dark)")
st.json(st.session_state.vision)

st.subheader("🔊 Sound")
st.json(st.session_state.sound)

with st.expander("📜 Ledger"):
    for row in st.session_state.ledger[-25:]:
        st.write(row)