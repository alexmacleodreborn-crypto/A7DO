import streamlit as st
import random
import math
import json
import os

# =====================================================
# A7DO — Scene-Based World with Planning
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Scene World")
st.caption("Embodied • Scene-aware • Planning")

SAVE_FILE = "a7do_memory.json"

# =====================================================
# WORLD CONSTANTS
# =====================================================

WORLD_SIZE = 20.0
TOUCH_PERSIST = 3
INVESTIGATE_PERSIST = 4

DAY_LENGTH = 200  # events per full cycle
RAIN_CHANCE = 0.02

# =====================================================
# UTIL
# =====================================================

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def load_memory():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(mem):
    with open(SAVE_FILE, "w") as f:
        json.dump(mem, f, indent=2)

# =====================================================
# INIT
# =====================================================

def init_state():
    st.session_state.event = 0

    st.session_state.body = {
        "x": random.uniform(3, WORLD_SIZE-3),
        "y": random.uniform(3, WORLD_SIZE-3),
        "vx": 0.3,
        "vy": 0.2,
        "energy": 1.0,
        "touch": False,
        "investigating": False,
        "investigate_timer": 0,
    }

    st.session_state.gps = {"x": 0.0, "y": 0.0}

    st.session_state.weather = {
        "rain": False,
        "wind": random.uniform(-0.05, 0.05),
    }

    st.session_state.scene = {
        "light": 0.0,
        "sound": [],
        "visuals": [],
    }

    # red spherical thing
    st.session_state.ball = {
        "x": WORLD_SIZE/2 + 2,
        "y": WORLD_SIZE/2 - 1,
        "radius": 0.8,
    }

    st.session_state.memory = load_memory()
    st.session_state.log = []

if "event" not in st.session_state:
    init_state()

# =====================================================
# TIME / SKY
# =====================================================

def sky_state():
    phase = (st.session_state.event % DAY_LENGTH) / DAY_LENGTH
    if phase < 0.25:
        return "sunrise"
    elif phase < 0.5:
        return "day"
    elif phase < 0.75:
        return "sunset"
    else:
        return "night"

# =====================================================
# WEATHER
# =====================================================

def update_weather():
    if random.random() < RAIN_CHANCE:
        st.session_state.weather["rain"] = True
    if st.session_state.weather["rain"] and random.random() < 0.05:
        st.session_state.weather["rain"] = False

# =====================================================
# SCENE PERCEPTION
# =====================================================

def perceive_scene():
    body = st.session_state.body
    scene = {"sound": [], "visuals": []}

    sky = sky_state()

    # light
    if sky in ["day", "sunrise", "sunset"]:
        scene["light"] = 0.8
    else:
        scene["light"] = 0.3

    # sky sounds
    if sky == "sunrise":
        scene["sound"].append("soft chirping")
    if sky == "night":
        scene["sound"].append("distant howling")
        scene["visuals"].append("stars scattered")

    # rain
    if st.session_state.weather["rain"]:
        scene["sound"].append("water falling")
        scene["visuals"].append("moving droplets")

    # rainbow after rain
    if not st.session_state.weather["rain"] and sky == "day":
        scene["visuals"].append("faint colour arc")

    # ball perception
    dx = body["x"] - st.session_state.ball["x"]
    dy = body["y"] - st.session_state.ball["y"]
    d = math.sqrt(dx*dx + dy*dy)
    if d < 2.0:
        scene["visuals"].append("round red-shifted shape")

    st.session_state.scene = scene

# =====================================================
# TOUCH & INVESTIGATION
# =====================================================

def resolve_touch():
    b = st.session_state.body
    touched = False

    if b["x"] <= 0 or b["x"] >= WORLD_SIZE:
        b["vx"] *= -1
        touched = True
    if b["y"] <= 0 or b["y"] >= WORLD_SIZE:
        b["vy"] *= -1
        touched = True

    if touched:
        b["touch"] = True
        b["investigating"] = True
        b["investigate_timer"] = INVESTIGATE_PERSIST
    else:
        b["touch"] = False

    if b["investigating"]:
        b["investigate_timer"] -= 1
        if b["investigate_timer"] <= 0:
            b["investigating"] = False

# =====================================================
# PLAN (short horizon)
# =====================================================

def plan():
    b = st.session_state.body
    # predict next step
    nx = b["x"] + b["vx"]
    ny = b["y"] + b["vy"]

    # anticipate collision
    if nx <= 0 or nx >= WORLD_SIZE:
        b["vx"] *= -0.5
    if ny <= 0 or ny >= WORLD_SIZE:
        b["vy"] *= -0.5

    # slow if investigating
    if b["investigating"]:
        b["vx"] *= 0.5
        b["vy"] *= 0.5

# =====================================================
# STEP
# =====================================================

def step():
    st.session_state.event += 1

    update_weather()
    plan()

    b = st.session_state.body
    b["x"] += b["vx"] + st.session_state.weather["wind"]
    b["y"] += b["vy"]

    resolve_touch()
    perceive_scene()

    st.session_state.gps["x"] = round(b["x"], 2)
    st.session_state.gps["y"] = round(b["y"], 2)

    st.session_state.log.append({
        "event": st.session_state.event,
        "gps": st.session_state.gps,
        "touch": b["touch"],
        "investigating": b["investigating"],
        "scene": st.session_state.scene,
    })

    save_memory(st.session_state.memory)

# =====================================================
# UI
# =====================================================

if st.button("▶ Advance"):
    step()

if st.toggle("Auto"):
    for _ in range(10):
        step()

st.subheader("🧭 GPS")
st.json(st.session_state.gps)

st.subheader("🌍 Scene")
st.json(st.session_state.scene)

with st.expander("📜 Log"):
    for row in st.session_state.log[-15:]:
        st.write(row)