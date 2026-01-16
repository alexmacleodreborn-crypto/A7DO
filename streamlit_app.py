import streamlit as st
import random
import json
import os
import math

# =====================================================
# A7DO — Born Intelligence (Full Working Build)
# Touch → Investigation → Learning
# Vision: contrast gradients
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
# WORLD FIELD (VISION)
# =====================================================

def boundary_darkness(x):
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

        # 👇 NEW
        "investigating": False,
        "investigate_timer": 0,
    }

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
# TOUCH → INVESTIGATION
# =====================================================

def update_touch():
    b = st.session_state.body
    touching_now = False

    if b["x"] <= 0:
        b["x"] = 0
        b["dir"] = 1
        touching_now = True
    elif b["x"] >= WORLD_LIMIT:
        b["x"] = WORLD_LIMIT
        b["dir"] = -1
        touching_now = True

    # EDGE TRIGGER
    if touching_now and not b["was_touching"]:
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

    b["was_touching"] = touching_now

# =====================================================
# VISION + ATTENTION
# =====================================================

def update_vision_and_attention():
    b = st.session_state.body
    v = st.session_state.vision

    d, l = vision_field(b["x"], st.session_state.masses, st.session_state.wells)
    g = vision_gradient(b["x"], st.session_state.masses, st.session_state.wells)

    v["delta_dark"] = 0 if st.session_state.prev_dark is None else d - st.session_state.prev_dark
    st.session_state.prev_dark = d

    v["darkness"] = d
    v["light"] = l
    v["grad"] = g

    salient = (d > 0.65) or abs(g) > 0.1 or b["investigating"]
    if salient:
        v["attn_dark"] = d
        v["attn_grad"] = g
        v["attn_timer"] = ATTENTION_PERSIST
    else:
        v["attn_timer"] = max(0, v["attn_timer"] - 1)
        if v["attn_timer"] == 0:
            v["attn_dark"] = None
            v["attn_grad"] = None

# =====================================================
# SOUND (RHYTHM)
# =====================================================

def update_sound():
    b = st.session_state.body
    e = st.session_state.emotion
    v = st.session_state.vision
    s = st.session_state.sound

    heart = BASE_HEART + HEART_AROUSAL_GAIN * e["arousal"]

    if b["investigating"]:
        foot = FOOTSTEP_GAIN * abs(b["v"]) * random.uniform(0.3, 0.7)
    else:
        foot = FOOTSTEP_GAIN * abs(b["v"])

    rhythm = heart + foot

    prev = st.session_state.prev_rhythm
    dr = 0 if prev is None else abs(rhythm - prev)
    st.session_state.prev_rhythm = rhythm

    disruption = DISRUPTION_GAIN * (dr + abs(v["delta_dark"])) + (0.7 if b["touch"] else 0)

    s.update({
        "heart": round(heart, 3),
        "foot": round(foot, 3),
        "rhythm": round(rhythm, 3),
        "disruption": round(disruption, 3),
    })

# =====================================================
# BODY
# =====================================================

def update_body(action):
    b = st.session_state.body

    if b["investigating"]:
        b["v"] = max(0.05, b["v"] * 0.5)

    if action == "MOVE":
        b["v"] = min(1.0, max(MIN_MOVE_V, b["v"] + MOVE_ACCEL))
        b["energy"] = max(0.0, b["energy"] - MOVE_COST)
    elif action == "REST":
        b["v"] = 0
        b["energy"] = min(1.0, b["energy"] + REST_GAIN)

    b["x"] += b["v"] * b["dir"]

# =====================================================
# ENERGY FROM FIELD
# =====================================================

def apply_field_energy():
    b = st.session_state.body
    v = st.session_state.vision
    before = b["energy"]

    if v["darkness"] > DARK_DRAIN_THRESHOLD:
        b["energy"] = clamp(b["energy"] - (v["darkness"] - DARK_DRAIN_THRESHOLD) * 0.12)

    if v["light"] > LIGHT_GAIN_THRESHOLD:
        b["energy"] = clamp(b["energy"] + (v["light"] - LIGHT_GAIN_THRESHOLD) * 0.10)

    return b["energy"] - before

# =====================================================
# MAP MEMORY
# =====================================================

def update_map(valence, energy_delta):
    b = st.session_state.body
    v = st.session_state.vision
    key = map_bin(b["x"])

    if key not in st.session_state.map_memory:
        st.session_state.map_memory[key] = {
            "visits": 0,
            "avg_valence": 0.0,
            "avg_dark": 0.0,
            "avg_energy": 0.0,
            "touches": 0,
        }

    cell = st.session_state.map_memory[key]
    cell["visits"] += 1
    cell["avg_valence"] = ema(cell["avg_valence"], valence)
    cell["avg_dark"] = ema(cell["avg_dark"], v["darkness"])
    cell["avg_energy"] = ema(cell["avg_energy"], energy_delta)
    if b["touch"]:
        cell["touches"] += 1

# =====================================================
# RECALL + APPRAISAL
# =====================================================

def recall_key():
    b = st.session_state.body
    v = st.session_state.vision
    return f"{map_bin(b['x'])}|{round(v['darkness'],2)}"

def recall_update(k, valence):
    r = st.session_state.recall.setdefault(k, {"count": 0, "valence": 0.0})
    r["count"] += 1
    r["valence"] = ema(r["valence"], valence)

def appraise(energy_delta):
    b = st.session_state.body
    v = st.session_state.vision
    raw = (W_ENERGY * energy_delta) - (W_DARK * v["darkness"]) - (W_TOUCH * (1 if b["touch"] else 0))
    return max(-1, min(1, raw * 2.5))

# =====================================================
# EMOTION
# =====================================================

def update_emotion(valence):
    e = st.session_state.emotion
    s = st.session_state.sound

    e["arousal"] = clamp(e["arousal"] + 0.1 * s["disruption"])
    e["arousal"] = max(MIN_AROUSAL, e["arousal"])
    e["confidence"] = clamp(e["confidence"] + 0.03 * (1 - clamp(s["disruption"] / 2)))
    e["valence"] = valence

# =====================================================
# CHOICE
# =====================================================

def choose_action():
    b = st.session_state.body
    v = st.session_state.vision

    if b["investigating"]:
        return "MOVE"

    if b["energy"] < 0.35:
        return "REST"

    cell = st.session_state.map_memory.get(map_bin(b["x"]))
    if cell and cell["avg_valence"] < -0.25:
        b["dir"] *= -1
        return "MOVE"

    if v["grad"] * b["dir"] > 0.1 and v["darkness"] > 0.55:
        b["dir"] *= -1
        return "MOVE"

    if v["light"] > 0.9 and random.random() < 0.3:
        return "REST"

    return "MOVE"

# =====================================================
# CONTROLS
# =====================================================

c1, c2, c3 = st.columns(3)
with c1:
    step = st.button("▶ Advance Event")
with c2:
    auto = st.toggle("Auto-run (10 steps)")
with c3:
    if st.button("⟲ Rebirth (keep memory)"):
        init_state()
        st.rerun()

# =====================================================
# EVENT LOOP
# =====================================================

def run_step():
    st.session_state.event += 1
    action = choose_action()
    update_body(action)
    update_touch()
    update_vision_and_attention()
    update_sound()
    energy_before = st.session_state.body["energy"]
    energy_delta = apply_field_energy()
    val = appraise(energy_delta)
    recall_update(recall_key(), val)
    update_map(val, energy_delta)
    update_emotion(val)
    save_memory()

    b = st.session_state.body
    v = st.session_state.vision
    s = st.session_state.sound

    st.session_state.ledger.append({
        "event": st.session_state.event,
        "x": round(b["x"], 2),
        "energy": round(b["energy"], 2),
        "touch": b["touch"],
        "investigating": b["investigating"],
        "dark": round(v["darkness"], 3),
        "light": round(v["light"], 3),
        "grad": round(v["grad"], 3),
        "attn": v["attn_timer"],
        "heart": s["heart"],
        "rhythm": s["rhythm"],
        "disruption": s["disruption"],
        "valence": round(val, 3),
    })

if step:
    run_step()
if auto:
    for _ in range(10):
        run_step()

# =====================================================
# DISPLAY
# =====================================================

st.subheader("🧍 Body")
st.json(st.session_state.body)

st.subheader("👁️ Vision + Attention")
st.json(st.session_state.vision)

st.subheader("🔊 Sound")
st.json(st.session_state.sound)

st.subheader("❤️ Emotion")
st.json(st.session_state.emotion)

st.subheader("🗺️ MAP Memory")
for k in sorted(st.session_state.map_memory, key=lambda x: float(x)):
    st.write(k, st.session_state.map_memory[k])

with st.expander("📜 Ledger (Last 15)"):
    for row in st.session_state.ledger[-15:]:
        st.write(row)