import streamlit as st
import math
import random

# =====================================================
# A7DO — MAP / BODY / SCENE / OBJECT
# =====================================================

st.set_page_config(layout="wide")
st.title("🧠 A7DO — Embodied World")

WORLD_SIZE = 20.0
CELL_SIZE = 4.0
BALL_RADIUS = 0.6

# =====================================================
# INIT
# =====================================================

def init():
    st.session_state.event = 0

    # BODY
    st.session_state.body = {
        "x": 5.0,
        "y": 5.0,
        "vx": 0.4,
        "vy": 0.3,
        "energy": 1.0,
        "touch": False,
        "walking": True,
    }

    # MAP (cells)
    st.session_state.map = {}

    # BALL (reactive object)
    st.session_state.ball = {
        "x": 10.0,
        "y": 10.0,
        "vx": 0.0,
        "vy": 0.0,
    }

    st.session_state.scene = {}
    st.session_state.log = []

if "event" not in st.session_state:
    init()

# =====================================================
# MAP
# =====================================================

def map_cell(x, y):
    cx = int(x // CELL_SIZE)
    cy = int(y // CELL_SIZE)
    return f"{cx},{cy}"

def update_map(cell, scene):
    m = st.session_state.map.setdefault(cell, {
        "visits": 0,
        "touches": 0,
        "sounds": [],
    })
    m["visits"] += 1
    m["sounds"].extend(scene["sound"])

# =====================================================
# BODY MOVEMENT
# =====================================================

def move_body():
    b = st.session_state.body
    b["x"] += b["vx"]
    b["y"] += b["vy"]

    # wall collisions
    if b["x"] <= 0 or b["x"] >= WORLD_SIZE:
        b["vx"] *= -1
        b["touch"] = True
    if b["y"] <= 0 or b["y"] >= WORLD_SIZE:
        b["vy"] *= -1
        b["touch"] = True

# =====================================================
# OBJECT PHYSICS (BALL)
# =====================================================

def update_ball():
    ball = st.session_state.ball
    body = st.session_state.body

    # distance body → ball
    dx = body["x"] - ball["x"]
    dy = body["y"] - ball["y"]
    d = math.sqrt(dx*dx + dy*dy)

    if d < BALL_RADIUS:
        # TOUCH BALL → it rolls
        ball["vx"] = -dx * 0.3
        ball["vy"] = -dy * 0.3
        body["touch"] = True

    # apply ball motion
    ball["x"] += ball["vx"]
    ball["y"] += ball["vy"]

    # friction
    ball["vx"] *= 0.85
    ball["vy"] *= 0.85

# =====================================================
# SCENE (derived, not stored)
# =====================================================

def build_scene():
    body = st.session_state.body
    scene = {"sound": [], "visual": []}

    # walking sound
    speed = math.sqrt(body["vx"]**2 + body["vy"]**2)
    if speed > 0.05:
        scene["sound"].append("footsteps")

    # touch sound
    if body["touch"]:
        scene["sound"].append("thud")

    # ball visual
    scene["visual"].append("red spherical shape")

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

    cell = map_cell(st.session_state.body["x"], st.session_state.body["y"])
    update_map(cell, st.session_state.scene)

    st.session_state.log.append({
        "event": st.session_state.event,
        "pos": (round(st.session_state.body["x"],2),
                round(st.session_state.body["y"],2)),
        "touch": st.session_state.body["touch"],
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

st.subheader("🧍 Body")
st.json(st.session_state.body)

st.subheader("🔴 Ball")
st.json(st.session_state.ball)

st.subheader("🌍 Scene (Now)")
st.json(st.session_state.scene)

st.subheader("🗺 Map Cells")
st.json(st.session_state.map)

with st.expander("📜 Log"):
    for row in st.session_state.log[-10:]:
        st.write(row)