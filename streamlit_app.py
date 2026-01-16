import streamlit as st
import math
import random

# =====================================================
# A7DO — Embodied World (Improved Motion, FIXED)
# =====================================================

st.set_page_config(layout="wide")
st.title("🧠 A7DO — Embodied World")

WORLD_SIZE = 20.0
CELL_SIZE = 4.0

BALL_RADIUS = 0.6
BALL_FRICTION = 0.90
BALL_REBOUND = 0.7

BODY_SPEED = 0.4
BODY_HEIGHT_BASE = 0.5

# =====================================================
# HELPERS (FIXED LOCATION)
# =====================================================

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# =====================================================
# INIT
# =====================================================

def init():
    st.session_state.event = 0

    # BODY (A7DO)
    st.session_state.body = {
        "x": 5.0,
        "y": 5.0,
        "z": BODY_HEIGHT_BASE,
        "vx": BODY_SPEED,
        "vy": BODY_SPEED * 0.8,
        "energy": 1.0,
        "touch": False,
        "walking": True,
    }

    # GPS (felt position)
    st.session_state.gps = {
        "x": 0.0,
        "y": 0.0,
        "z": BODY_HEIGHT_BASE,
    }

    # MAP
    st.session_state.map = {}

    # BALL (reactive object)
    st.session_state.ball = {
        "x": 10.0,
        "y": 10.0,
        "vx": 0.0,
        "vy": 0.0,
        "moving": False,
    }

    st.session_state.scene = {}
    st.session_state.log = []

if "event" not in st.session_state:
    init()

# =====================================================
# MAP
# =====================================================

def map_cell(x, y):
    return f"{int(x // CELL_SIZE)},{int(y // CELL_SIZE)}"

def update_map(cell, scene, touched):
    m = st.session_state.map.setdefault(cell, {
        "visits": 0,
        "touches": 0,
        "sounds": [],
    })
    m["visits"] += 1
    m["sounds"].extend(scene["sound"])
    if touched:
        m["touches"] += 1

# =====================================================
# BODY MOTION
# =====================================================

def move_body():
    b = st.session_state.body
    b["x"] += b["vx"]
    b["y"] += b["vy"]

    touched = False

    if b["x"] <= 0 or b["x"] >= WORLD_SIZE:
        b["vx"] *= -1
        touched = True
    if b["y"] <= 0 or b["y"] >= WORLD_SIZE:
        b["vy"] *= -1
        touched = True

    b["touch"] = touched

    # vertical vibration from motion (felt height)
    speed = math.sqrt(b["vx"]**2 + b["vy"]**2)
    b["z"] = BODY_HEIGHT_BASE + clamp(speed * 0.2, 0, 0.5)

# =====================================================
# BALL PHYSICS
# =====================================================

def update_ball():
    ball = st.session_state.ball
    body = st.session_state.body

    dx = ball["x"] - body["x"]
    dy = ball["y"] - body["y"]
    dist = math.sqrt(dx*dx + dy*dy)

    # TOUCH BALL (proximity-based)
    if dist < BALL_RADIUS:
        norm = max(dist, 0.01)
        ball["vx"] = (dx / norm) * 0.6
        ball["vy"] = (dy / norm) * 0.6
        ball["moving"] = True
        body["touch"] = True

        # impact vibration
        body["z"] += 0.3

    # move ball
    if ball["moving"]:
        ball["x"] += ball["vx"]
        ball["y"] += ball["vy"]

        # wall rebound
        if ball["x"] <= 0 or ball["x"] >= WORLD_SIZE:
            ball["vx"] *= -BALL_REBOUND
        if ball["y"] <= 0 or ball["y"] >= WORLD_SIZE:
            ball["vy"] *= -BALL_REBOUND

        # friction
        ball["vx"] *= BALL_FRICTION
        ball["vy"] *= BALL_FRICTION

        # stop if slow
        if abs(ball["vx"]) < 0.02 and abs(ball["vy"]) < 0.02:
            ball["vx"] = 0.0
            ball["vy"] = 0.0
            ball["moving"] = False

# =====================================================
# SCENE
# =====================================================

def build_scene():
    body = st.session_state.body
    ball = st.session_state.ball

    scene = {"sound": [], "visual": []}

    speed = math.sqrt(body["vx"]**2 + body["vy"]**2)
    if speed > 0.05:
        scene["sound"].append("footsteps")

    if body["touch"]:
        scene["sound"].append("thud")

    dx = body["x"] - ball["x"]
    dy = body["y"] - ball["y"]
    if math.sqrt(dx*dx + dy*dy) < 2.0:
        scene["visual"].append("round red-shifted shape")

    st.session_state.scene = scene

# =====================================================
# STEP
# =====================================================

def step():
    st.session_state.event += 1
    st.session_state.body["touch"] = False

    move_body()
    update_ball()
    build_scene()

    # GPS update
    b = st.session_state.body
    st.session_state.gps["x"] = round(b["x"], 2)
    st.session_state.gps["y"] = round(b["y"], 2)
    st.session_state.gps["z"] = round(b["z"], 2)

    cell = map_cell(b["x"], b["y"])
    update_map(cell, st.session_state.scene, b["touch"])

    st.session_state.log.append({
        "event": st.session_state.event,
        "gps": st.session_state.gps.copy(),
        "touch": b["touch"],
        "scene": st.session_state.scene,
    })

# =====================================================
# UI
# =====================================================

if st.button("▶ Step"):
    step()

if st.toggle("Auto"):
    for _ in range(10):
        step()

st.subheader("🧭 GPS (felt position)")
st.json(st.session_state.gps)

st.subheader("🧍 Body")
st.json(st.session_state.body)

st.subheader("🔴 Ball")
st.json(st.session_state.ball)

st.subheader("🌍 Scene")
st.json(st.session_state.scene)

st.subheader("🗺 Map")
st.json(st.session_state.map)

with st.expander("📜 Log"):
    for row in st.session_state.log[-10:]:
        st.write(row)