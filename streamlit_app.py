import streamlit as st
import random
import json
import os
import math

# =====================================================
# A7DO — Born Intelligence (Full Working Build)
# FIXED: Touch triggers correctly (boundary handled ONLY in update_touch)
# Touch → Investigation → Learning
# Vision: contrast gradients (no external lights)
# Sound: heartbeat + footsteps (rhythm & disruption)
# Memory: MAP + ATTENTION + persistence
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Embodied • Remembering • Attentive • Investigative")

SAVE_FILE = "a7do_memory.json"

# =====================================================
# CONSTANTS
# =====================================================

WORLD_LIMIT = 20.0
MAP_BIN_SIZE = 2.0

# touch / investigation
TOUCH_PERSIST = 3
INVESTIGATE_PERSIST = 4

# attention
ATTENTION_PERSIST = 6

# learning
RECALL_ALPHA = 0.2
MIN_AROUSAL = 0.15

# movement / energy
MIN_MOVE_V = 0.25
MOVE_ACCEL = 0.10
MOVE_COST = 0.04
REST_GAIN = 0.07

# vision sampling
GRAD_EPS = 0.35

# field → energy
DARK_DRAIN_THRESHOLD = 0.65
LIGHT_GAIN_THRESHOLD = 0.75

# sound model
BASE_HEART = 0.8
HEART_AROUSAL_GAIN = 1.8
FOOTSTEP_GAIN = 1.2
DISRUPTION_GAIN = 1.0

# appraisal
W_ENERGY = 0.9
W_TOUCH = 0.8
W_DARK = 0.5

# =====================================================
# UTIL
# =====================================================

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def ema(old, new, a=RECALL_ALPHA):
    return (1 - a) * old + a * new

def map_bin(x):
    start = float(int(x // MAP_BIN_SIZE) * MAP_BIN_SIZE)
    return f"{start:.1f}"

# =====================================================
# SAVE / LOAD (AUTO)
# =====================================================

def load_memory():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict) and "recall" in data:
            data.setdefault("map", {})
            return data
        # old format: treat as recall dict
        return {"recall": data if isinstance(data, dict) else {}, "map": {}}
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
# WORLD FIELD (VISION)
# =====================================================

def boundary_darkness(x):
    # darker at edges, lighter at center
    center = WORLD_LIMIT / 2
    d = abs(x - center) / center
    return clamp(d ** 1.6)

def mass_darkness(x, masses):
    total = 0.0
    for m in masses:
        dx = abs(x - m["x"])
        r = max(0.2, m["radius"])
        total += m["strength"] * math.exp(-(dx / r) ** 2)
    return clamp(total)

def light_well(x, wells):
    total = 0.0
    for w in wells:
        dx = abs(x - w["x"])
        r = max(0.2, w["radius"])
        total += w["strength"] * math.exp(-(dx / r) ** 2)
    return clamp(total)

def vision_field(x, masses, wells):
    darkness = clamp(boundary_darkness(x) + mass_darkness(x, masses))
    light = clamp((1 - darkness) + light_well(x, wells))
    return darkness, light

def vision_gradient(x, masses, wells):
    x1 = clamp(x - GRAD_EPS, 0, WORLD_LIMIT)
    x2 = clamp(x + GRAD_EPS, 0, WORLD_LIMIT)
    d1, _ = vision_field(x1, masses, wells)
    d2, _ = vision_field(x2, masses, wells)
    return (d2 - d1) / max(1e-6, (x2 - x1))

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
        "x": random.uniform(3, WORLD_LIMIT - 3),
        "v": 0.0,
        "dir": random.choice([-1, 1]),
        "energy": 1.0,

        "touch": False,
        "touch_timer": 0,
        "was_touching": False,

        "investigating": False,
        "investigate_timer": 0,
    }

    # dark mass & light recovery zones
    st.session_state.masses = [
        {"x": 14.0, "radius": 1.6, "strength": 0.75}
    ]
    st.session_state.wells = [
        {"x": 5.0, "radius": 2.2, "strength": 0.55}
    ]

    st.session_state.vision = {
        "darkness": 0.0,
        "light": 1.0,
        "grad": 0.0,
        "delta_dark": 0.0,

        "attn_dark": None,
        "attn_grad": None,
        "attn_timer": 0,
    }
    st.session_state.prev_dark = None

    st.session_state.sound = {
        "heart