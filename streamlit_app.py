import streamlit as st
import random
import json
import os
import math

# =====================================================
# A7DO — Born Intelligence (Current Full Build)
# Vision: contrast gradients (no lights needed)
# Sound: heartbeat + footsteps (rhythm)
# Touch: edge-trigger + latch
# Memory: MAP + ATTENTION + persistent save
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Embodied • Remembering • Spatially aware • Attentive (Vision/Sound gradients)")

SAVE_FILE = "a7do_memory.json"

# -------------------------
# CONSTANTS
# -------------------------
WORLD_LIMIT = 20.0
MAP_BIN_SIZE = 2.0

TOUCH_PERSIST = 3
ATTENTION_PERSIST = 6

RECALL_ALPHA = 0.2
MIN_AROUSAL = 0.15

# movement / energy
MIN_MOVE_V = 0.25
MOVE_ACCEL = 0.10
MOVE_COST = 0.04
REST_GAIN = 0.07

# vision field sampling
GRAD_EPS = 0.35

# field → energy coupling
DARK_DRAIN_THRESHOLD = 0.65
LIGHT_GAIN_THRESHOLD = 0.75

# sound model
BASE_HEART = 0.8
HEART_AROUSAL_GAIN = 1.8
FOOTSTEP_GAIN = 1.2
DISRUPTION_GAIN = 1.0

# appraisal weights
W_ENERGY = 0.9
W_TOUCH = 0.8
W_DARK = 0.5

# -------------------------
# UTIL
# -------------------------
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def ema(old, new, a=RECALL_ALPHA):
    return (1 - a) * old + a * new

def map_bin(x):
    start = float(int(x // MAP_BIN_SIZE) * MAP_BIN_SIZE)
    return f"{start:.1f}"

# -------------------------
# SAVE / LOAD (backward compatible)
# -------------------------
def load_memory():
    """
    New format: {"recall": {...}, "map": {...}}
    Old format: {...}  (treated as recall-only)
    """
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)

        if isinstance(data, dict) and "recall" in data:
            if "map" not in data:
                data["map"] = {}
            return data

        return {"recall": data if isinstance(data, dict) else {}, "map": {}}

    return {"recall": {}, "map": {}}

def save_memory():
    with open(SAVE_FILE, "w") as f:
        json.dump(
            {"recall": st.session_state.recall, "map": st.session_state.map_memory},
            f,
            indent=2,
        )

# -------------------------
# WORLD FIELD (Vision = contrast)
# -------------------------
def boundary_darkness(x: float) -> float:
    # darker near edges, lighter near middle
    center = WORLD_LIMIT / 2.0
    d = abs(x - center) / center
    return clamp(d ** 1.6)

def mass_darkness(x: float, masses) -> float:
    total = 0.0
    for m in masses:
        dx = abs(x - m["x"])
        r = max(0.2, m["radius"])
        bump = math.exp(- (dx / r) ** 2)
        total += m["strength"] * bump
    return clamp(total)

def light_well(x: float, wells) -> float:
    total = 0.0
    for w in wells:
        dx = abs(x - w["x"])
        r = max(0.2, w["radius"])
        bump = math.exp(- (dx / r) ** 2)
        total += w["strength"] * bump
    return clamp(total)

def vision_field(x: float, masses, wells):
    darkness = clamp(boundary_darkness(x) + mass_darkness(x, masses))
    light = clamp((1.0 - darkness) + light_well(x, wells))
    return darkness, light

def vision_gradient(x: float, masses, wells):
    x1 = clamp(x - GRAD_EPS, 0.0, WORLD_LIMIT)
    x2 = clamp(x + GRAD_EPS, 0.0, WORLD_LIMIT)
    d1, _ = vision_field(x1, masses, wells)
    d2, _ = vision_field(x2, masses, wells)
    return (d2 - d1) / max(1e-6, (x2 - x1))

# -------------------------
# INIT
# -------------------------
def init_state():
    mem = load_memory()

    st.session_state.event = 0

    st.session_state.emotion = {"arousal": 0.4, "valence": 0.0, "confidence": 0.3}

    st.session_state.body = {
        "x": random.uniform(3.0, WORLD_LIMIT - 3.0),
        "v": 0.0,
        "dir": random.choice([-1, 1]),
        "energy": 1.0,
        "touch": False,
        "touch_timer": 0,
        "was_touching": False,
    }

    # "Mass" (darker) and "Open/light" (lighter) regions
    st.session_state.masses = [
        {"x": 14.0, "radius": 1.6, "strength": 0.75},  # dark / mass region
    ]
    st.session_state.wells = [
        {"x": 5.0, "radius": 2.2, "strength": 0.55},   # light / recovery region
    ]

    st.session_state.vision = {
        "darkness": 0.0,
        "light": 1.0,
        "darkness_grad": 0.0,
        "delta_darkness": 0.0,
        "attn_darkness": None,
        "attn_grad": None,
        "attn_timer": 0,
    }
    st.session_state.prev_darkness = None

    st.session_state.sound = {
        "heart_rate": 0.0,
        "footsteps": 0.0,
        "rhythm": 0.0,
        "disruption": 0.0,
    }
    st.session_state.prev_rhythm = None

    st.session_state.recall = mem["recall"]
    st.session_state.map_memory = mem["map"]

    st.session_state.ledger = []

if "event" not in st.session_state:
    init_state()

# -------------------------
# TOUCH (edge-triggered + latched)
# -------------------------
def update_touch():
    b = st.session_state.body
    touching_now = False

    if b["x"] <= 0.0:
        b["x"] = 0.0
        b["dir"] = 1
        touching_now = True
    elif b["x"] >= WORLD_LIMIT:
        b["x"] = WORLD_LIMIT
        b["dir"] = -1
        touching_now = True

    if touching_now and not b["was_touching"]:
        b["touch_timer"] = TOUCH_PERSIST

    if b["touch_timer"] > 0:
        b["touch"] = True
        b["touch_timer"] -= 1
    else:
        b["touch"] = False

    b["was_touching"] = touching_now

# -------------------------
# VISION + ATTENTION
# -------------------------
def update_vision_and_attention():
    b = st.session_state.body
    v = st.session_state.vision

    d, l = vision_field(b["x"], st.session_state.masses, st.session_state.wells)
    g = vision_gradient(b["x"], st.session_state.masses, st.session_state.wells)

    prev_d = st.session_state.prev_darkness
    v["delta_darkness"] = 0.0 if prev_d is None else (d - prev_d)
    st.session_state.prev_darkness = d

    v["darkness"] = d
    v["light"] = l
    v["darkness_grad"] = g

    salient = (d > 0.65) or (abs(g) > 0.10)
    if salient:
        v["attn_darkness"] = d
        v["attn_grad"] = g
        v["attn_timer"] = ATTENTION_PERSIST
    else:
        if v["attn_timer"] > 0:
            v["attn_timer"] -= 1
        else:
            v["attn_darkness"] = None
            v["attn_grad"] = None

# -------------------------
# SOUND (heartbeat + footsteps + disruption)
# -------------------------
def update_sound():
    e = st.session_state.emotion
    b = st.session_state.body
    v = st.session_state.vision
    s = st.session_state.sound

    heart = BASE_HEART + HEART_AROUSAL_GAIN * e["arousal"]
    foot = FOOTSTEP_GAIN * abs(b["v"])
    rhythm = heart + foot

    prev_r = st.session_state.prev_rhythm
    dr = 0.0 if prev_r is None else abs(rhythm - prev_r)
    st.session_state.prev_rhythm = rhythm

    disruption = DISRUPTION_GAIN * (dr + abs(v["delta_darkness"])) + (0.7 if b["touch"] else 0.0)

    s["heart_rate"] = round(heart, 3)
    s["footsteps"] = round(foot, 3)
    s["rhythm"] = round(rhythm, 3)
    s["disruption"] = round(disruption, 3)

# -------------------------
# BODY UPDATE
# -------------------------
def update_body(action: str):
    b = st.session_state.body

    if action == "MOVE":
        b["v"] = min(1.0, max(MIN_MOVE_V, b["v"] + MOVE_ACCEL))
        b["energy"] = max(0.0, b["energy"] - MOVE_COST)
    elif action == "REST":
        b["v"] = 0.0
        b["energy"] = min(1.0, b["energy"] + REST_GAIN)

    b["x"] += b["v"] * b["dir"]

# -------------------------
# ENERGY FROM FIELD (light recovers, dark drains)
# -------------------------
def apply_field_energy():
    b = st.session_state.body
    v = st.session_state.vision

    before = b["energy"]

    if v["darkness"] > DARK_DRAIN_THRESHOLD:
        drain = (v["darkness"] - DARK_DRAIN_THRESHOLD) * 0.12
        b["energy"] = clamp(b["energy"] - drain)

    if v["light"] > LIGHT_GAIN_THRESHOLD:
        gain = (v["light"] - LIGHT_GAIN_THRESHOLD) * 0.10
        b["energy"] = clamp(b["energy"] + gain)

    return b["energy"] - before

# -------------------------
# MAP MEMORY
# -------------------------
def update_map(valence, energy_delta):
    b = st.session_state.body
    v = st.session_state.vision
    key = map_bin(b["x"])

    if key not in st.session_state.map_memory:
        st.session_state.map_memory[key] = {
            "visits": 0,
            "avg_valence": 0.0,
            "avg_darkness": 0.0,
            "avg_energy_delta": 0.0,
            "touches": 0,
        }

    cell = st.session_state.map_memory[key]
    cell["visits"] += 1
    cell["avg_valence"] = ema(cell["avg_valence"], valence)
    cell["avg_darkness"] = ema(cell["avg_darkness"], v["darkness"])
    cell["avg_energy_delta"] = ema(cell["avg_energy_delta"], energy_delta)
    if b["touch"]:
        cell["touches"] += 1

# -------------------------
# RECALL (lightweight)
# -------------------------
def recall_key():
    b = st.session_state.body
    v = st.session_state.vision
    dk = round(v["darkness"], 2)
    return f"{map_bin(b['x'])}|D{dk}"

def recall_get(k):
    r = st.session_state.recall
    if k not in r:
        r[k] = {"count": 0, "valence": 0.0, "expected_dark": 0.5}
    return r[k]

def recall_update(k, valence):
    rec = recall_get(k)
    rec["count"] += 1
    rec["valence"] = ema(rec["valence"], valence)
    rec["expected_dark"] = ema(rec["expected_dark"], st.session_state.vision["darkness"])

# -------------------------
# APPRAISAL → VALENCE
# -------------------------
def appraise(energy_delta):
    b = st.session_state.body
    v = st.session_state.vision
    raw = (W_ENERGY * energy_delta) - (W_DARK * v["darkness"]) - (W_TOUCH * (1.0 if b["touch"] else 0.0))
    return max(-1.0, min(1.0, raw * 2.5))

# -------------------------
# EMOTION UPDATE
# -------------------------
def update_emotion(valence):
    e = st.session_state.emotion
    s = st.session_state.sound

    e["arousal"] = clamp(e["arousal"] + 0.10 * s["disruption"])
    e["arousal"] = max(MIN_AROUSAL, e["arousal"])

    e["confidence"] = clamp(e["confidence"] + 0.03 * (1.0 - clamp(s["disruption"] / 2.0)))
    e["valence"] = valence

# -------------------------
# CHOICE (MAP + ATTENTION + GRADIENT)
# -------------------------
def choose_action():
    b = st.session_state.body
    v = st.session_state.vision

    # survival: rest if low energy
    if b["energy"] < 0.35:
        return "REST"

    # map-based avoidance
    cell = st.session_state.map_memory.get(map_bin(b["x"]))
    if cell and cell["avg_valence"] < -0.25:
        b["dir"] *= -1
        return "MOVE"

    # if moving forward gets darker (grad * dir > 0), reverse
    if (v["darkness_grad"] * b["dir"] > 0.10) and (v["darkness"] > 0.55):
        b["dir"] *= -1
        return "MOVE"

    # attention: if we recently sensed "dangerous dark", keep moving away from gradient
    if v["attn_timer"] > 0 and v["attn_darkness"] is not None:
        if v["attn_darkness"] > 0.70:
            # move opposite direction of increasing darkness
            if v["attn_grad"] is not None and v["attn_grad"] != 0:
                b["dir"] = -1 if v["attn_grad"] > 0 else 1
            return "MOVE"

    # otherwise: explore with slight bias toward light
    # if current area is very light, rest sometimes (enjoy stability)
    if v["light"] > 0.90 and random.random() < 0.35:
        return "REST"

    return "MOVE"

# -------------------------
# CONTROLS
# -------------------------
c1, c2, c3 = st.columns(3)
with c1:
    step = st.button("▶ Advance Event")
with c2:
    auto = st.toggle("Auto-run (10 steps)", value=False)
with c3:
    if st.button("⟲ Rebirth (keep memory)"):
        init_state()
        st.rerun()

# -------------------------
# EVENT LOOP
# -------------------------
def do_one_step():
    st.session_state.event += 1

    action = choose_action()
    update_body(action)
    update_touch()
    update_vision_and_attention()
    update_sound()

    energy_before = st.session_state.body["energy"]
    energy_delta_field = apply_field_energy()
    energy_delta = st.session_state.body["energy"] - energy_before

    val = appraise(energy_delta)
    rk = recall_key()
    recall_update(rk, val)
    update_map(val, energy_delta)
    update_emotion(val)

    save_memory()

    b = st.session_state.body
    v = st.session_state.vision
    s = st.session_state.sound

    st.session_state.ledger.append({
        "event": st.session_state.event,
        "x": round(b["x"], 2),
        "bin": map_bin(b["x"]),
        "dir": b["dir"],
        "v": round(b["v"], 2),
        "energy": round(b["energy"], 2),
        "touch": b["touch"],
        "touch_timer": b["touch_timer"],
        "dark": round(v["darkness"], 3),
        "light": round(v["light"], 3),
        "grad": round(v["darkness_grad"], 3),
        "attn_timer": v["attn_timer"],
        "valence": round(val, 3),
        "heart": s["heart_rate"],
        "rhythm": s["rhythm"],
        "disruption": s["disruption"],
    })

if step:
    do_one_step()

if auto:
    # do a small batch without needing rerun loops
    for _ in range(10):
        do_one_step()

# -------------------------
# DISPLAY
# -------------------------
st.subheader("🧍 Body")
st.json(st.session_state.body)

st.subheader("👁️ Vision + Attention (gradients)")
st.json(st.session_state.vision)

st.subheader("🔊 Sound (heartbeat + footsteps)")
st.json(st.session_state.sound)

st.subheader("❤️ Emotion")
st.json(st.session_state.emotion)

st.subheader("🗺️ MAP Memory (bins)")
# show only sorted bins for readability
for k in sorted(st.session_state.map_memory.keys(), key=lambda x: float(x)):
    st.write(k, st.session_state.map_memory[k])

with st.expander("📜 Ledger (Last 15)"):
    for row in st.session_state.ledger[-15:]:
        st.write(row)