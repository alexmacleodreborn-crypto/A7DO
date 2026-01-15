import streamlit as st
import random
import copy

# =====================================================
# A7DO — BORN INTELLIGENCE (SINGLE FILE)
# Embodiment • Vision • Touch • Recall • Valence • Choice
# =====================================================

st.set_page_config(page_title="A7DO", layout="wide")
st.title("🧠 A7DO — Born Intelligence")
st.caption("Persistence • Competition • Shock • Decay • Curiosity • Choice • Body • Vision • Touch • Recall")

# =====================================================
# CONSTANTS
# =====================================================

GRID_SIZE = 8
WORLD_LIMIT = 20.0

MAX_CONCEPTS = 6
DECOHERENCE_THRESHOLD = 3
REPLACEMENT_THRESHOLD = 5

SHOCK_PROBABILITY = 0.08
SHOCK_MAGNITUDE = 0.6

DECAY_RATE = 0.01
MIN_AROUSAL = 0.15

# Recall learning rates
RECALL_ALPHA = 0.20          # exponential moving average rate
CONF_LEARN_RATE = 0.06       # how fast confidence-floor increases with good predictions
CONF_FORGET_RATE = 0.03      # how fast confidence-floor decreases with bad predictions

# Appraisal weights (valence conversion)
W_K = 1.00   # stability prediction error weight
W_E = 0.35   # energy deviation weight
W_T = 0.60   # touch penalty weight
W_M = 0.25   # motion novelty reward weight

# =====================================================
# SESSION STATE (BIRTH)
# =====================================================

def init_state():
    st.session_state.event = 0

    # Environment
    st.session_state.square = [[random.random() for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    st.session_state.prev_square = copy.deepcopy(st.session_state.square)

    # Cognition
    st.session_state.patterns = {}
    st.session_state.concepts = set()
    st.session_state.ledger = []

    # Emotion
    st.session_state.emotion = {"arousal": 0.4, "valence": 0.0, "confidence": 0.3}

    # Body
    st.session_state.body = {"x": 0.0, "v": 0.0, "energy": 1.0, "touch": False}

    # Senses
    st.session_state.vision = {"motion": 0.0}

    # Recall memory (evaluated experience)
    # signature -> stats
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
# ENVIRONMENT DYNAMICS
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
            dist = abs(i - cx) + abs(j - cy)
            influence = max(0, SHOCK_MAGNITUDE - 0.15 * dist)
            if influence > 0:
                grid[i][j] = clamp(grid[i][j] + random.uniform(-influence, influence))
    return grid

def square_features(grid):
    flat = [v for r in grid for v in r]
    mean = sum(flat) / len(flat)
    var = sum((v - mean) ** 2 for v in flat) / len(flat)
    return mean, var

# =====================================================
# VISION (MOTION PERCEPTION)
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

# =====================================================
# TOUCH (BOUNDARY PERCEPTION)
# =====================================================

def update_touch():
    b = st.session_state.body
    if b["x"] <= 0:
        b["x"] = 0.0
        b["touch"] = True
        b["v"] = 0.0
    elif b["x"] >= WORLD_LIMIT:
        b["x"] = WORLD_LIMIT
        b["touch"] = True
        b["v"] = 0.0
    else:
        b["touch"] = False

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

    p = patterns.setdefault(signature, {"count": 0.0, "decohered": False})

    if regime == "CLASSICAL":
        p["count"] += 1.0

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
# BODY DYNAMICS (REST BASIN FIX)
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
        b["energy"] = min(1.0, b["energy"] + 0.10)

    b["x"] += b["v"]

# =====================================================
# RECALL — EXPECTATION & EVALUATION MEMORY
# =====================================================

def recall_get(signature):
    r = st.session_state.recall.get(signature)
    if r is None:
        # sensible defaults (neutral expectations)
        r = {
            "count": 0,
            "expected_K": 0.30,
            "expected_energy": 0.80,
            "expected_motion": 0.10,
            "touch_rate": 0.0,
            "valence": 0.0,
            "conf_floor": 0.20
        }
        st.session_state.recall[signature] = r
    return r

def recall_update(signature, actual_K, energy, motion, touch_flag):
    r = recall_get(signature)
    r["count"] += 1

    # Update expectations
    r["expected_K"] = ema(r["expected_K"], actual_K)
    r["expected_energy"] = ema(r["expected_energy"], energy)
    r["expected_motion"] = ema(r["expected_motion"], motion)
    r["touch_rate"] = ema(r["touch_rate"], 1.0 if touch_flag else 0.0)

def appraisal_valence(signature, actual_K, energy, motion, touch_flag):
    r = recall_get(signature)

    # Lower K is "better" (more stable). So improvement is expected_K - actual_K
    dK = (r["expected_K"] - actual_K)
    dE = (energy - r["expected_energy"])
    dM = (motion - r["expected_motion"])
    t = 1.0 if touch_flag else 0.0

    raw = (W_K * dK) + (W_E * dE) + (W_M * dM) - (W_T * t)

    # squash into [-1, +1] softly
    val = max(-1.0, min(1.0, raw * 2.5))
    return val, abs(actual_K - r["expected_K"])

def recall_update_valence_and_conf(signature, valence, pred_err):
    r = recall_get(signature)

    # valence stored as EMA
    r["valence"] = ema(r["valence"], valence)

    # Confidence floor increases when prediction error is small, decreases when large
    # pred_err ~0.0 good, >0.15 poor (tunable)
    good = max(0.0, 0.15 - pred_err) / 0.15   # 1 when err=0, 0 when err>=0.15
    bad = max(0.0, pred_err - 0.15) / 0.35    # grows after 0.15

    r["conf_floor"] = clamp(
        r["conf_floor"] + CONF_LEARN_RATE * good - CONF_FORGET_RATE * bad,
        0.0, 1.0
    )

# =====================================================
# EMOTION REGULATION + PROPRIOCEPTION + SENSES + RECALL CONSOLIDATION
# =====================================================

def update_emotion(regime, shocked, signature):
    e = st.session_state.emotion
    b = st.session_state.body
    v = st.session_state.vision
    r = recall_get(signature)

    # Regime-driven updates
    if shocked:
        e["arousal"] = clamp(e["arousal"] + 0.25)
        e["confidence"] = max(0.0, e["confidence"] - 0.25)

    elif regime == "CLASSICAL":
        e["confidence"] = clamp(e["confidence"] + 0.03)
        e["arousal"] = max(0.0, e["arousal"] - 0.02)

    elif regime == "TRANSITION":
        e["arousal"] = clamp(e["arousal"] + 0.06)
        e["confidence"] = max(0.0, e["confidence"] - 0.05)

    elif regime == "ZENO":
        e["arousal"] = clamp(e["arousal"] + 0.12)
        e["confidence"] = max(0.0, e["confidence"] - 0.15)

    # Proprioception (body → mind)
    e["arousal"] = clamp(e["arousal"] + 0.10 * b["v"])
    e["confidence"] = max(0.0, e["confidence"] - 0.10 * (1.0 - b["energy"]))

    # Vision (motion) contributes to curiosity
    e["arousal"] = clamp(e["arousal"] + 0.40 * v["motion"])

    # Touch contributes to caution
    if b["touch"]:
        e["arousal"] = clamp(e["arousal"] + 0.20)
        e["confidence"] = max(0.0, e["confidence"] - 0.10)

    # Curiosity floor
    e["arousal"] = max(MIN_AROUSAL, e["arousal"])

    # Recall consolidation: confidence cannot fall below learned conf_floor for known signatures
    e["confidence"] = max(e["confidence"], r["conf_floor"])

# =====================================================
# CHOICE ENGINE (PREDICTIVE + MEMORY-BIASED)
# =====================================================

def predict_action_K(action, grid):
    test = copy.deepcopy(grid)

    if action == "OBSERVE":
        test = square_step(test, scale=0.5)
    elif action == "EXPLORE":
        test = square_step(test, scale=1.2)
    elif action == "HOLD":
        pass

    mean, var = square_features(test)
    _, _, K, regime = trap_state(mean, var)

    penalty = 0.0
    if regime == "ZENO":
        penalty = 2.0
    elif regime == "TRANSITION":
        penalty = 0.5

    return K + penalty

def choose_action(signature, grid):
    b = st.session_state.body
    r = recall_get(signature)

    actions = ["OBSERVE", "EXPLORE", "HOLD"]
    scored = {}

    for a in actions:
        base = predict_action_K(a, grid)

        # Embodied preference: if energy low, prefer HOLD/OBSERVE
        energy_bias = 0.0
        if b["energy"] < 0.35:
            if a == "EXPLORE":
                energy_bias += 0.35
            elif a == "HOLD":
                energy_bias -= 0.10

        # Memory bias: if signature has negative valence, damp EXPLORE
        mem_bias = 0.0
        if r["valence"] < -0.15 and a == "EXPLORE":
            mem_bias += 0.25
        if r["valence"] > 0.15 and a == "OBSERVE":
            mem_bias += 0.05  # small push to act when it's historically good

        scored[a] = base + energy_bias + mem_bias

    return min(scored, key=scored.get), scored

# =====================================================
# CONTROLS
# =====================================================

cA, cB, cC = st.columns(3)
with cA:
    force_shock = st.button("⚡ Force Shock")
with cB:
    step_btn = st.button("▶ Advance Event")
with cC:
    if st.button("⟲ Rebirth"):
        st.session_state.clear()
        init_state()
        st.experimental_rerun()

# =====================================================
# EVENT STEP
# =====================================================

if step_btn:
    st.session_state.event += 1

    shocked = False

    # Environment update
    st.session_state.square = square_step(st.session_state.square)
    if force_shock or random.random() < SHOCK_PROBABILITY:
        st.session_state.square = apply_shock(st.session_state.square)
        shocked = True

    # Vision update (motion)
    update_vision()

    # Trap + signature
    mean, var = square_features(st.session_state.square)
    Z, sigma, K, regime = trap_state(mean, var)
    signature = f"{round(mean,2)}|{round(var,2)}"

    # Decay + pattern update
    decay_patterns()
    update_patterns(signature, regime)

    # Choose action using current signature + memory bias
    action, action_scores = choose_action(signature, st.session_state.square)

    # Body update and touch
    update_body(action)
    update_touch()

    # Appraisal (convert sensation → valence) and update recall
    motion = st.session_state.vision["motion"]
    energy = st.session_state.body["energy"]
    touch_flag = st.session_state.body["touch"]

    valence, pred_err = appraisal_valence(signature, K, energy, motion, touch_flag)
    recall_update(signature, K, energy, motion, touch_flag)
    recall_update_valence_and_conf(signature, valence, pred_err)

    # Emotion update (now includes recall confidence floor)
    st.session_state.emotion["valence"] = valence
    update_emotion(regime, shocked, signature)

    # Log
    st.session_state.ledger.append({
        "event": st.session_state.event,
        "signature": signature,
        "regime": regime,
        "shock": shocked,
        "Z": round(Z, 3),
        "Σ": round(sigma, 3),
        "K": round(K, 3),
        "motion": round(motion, 3),
        "touch": touch_flag,
        "action": action,
        "action_scores": {k: round(v, 3) for k, v in action_scores.items()},
        "valence": round(valence, 3),
        "pred_err": round(pred_err, 3),
        "conf_floor": round(recall_get(signature)["conf_floor"], 3),
        "body": dict(st.session_state.body),
        "emotion": dict(st.session_state.emotion)
    })

# =====================================================
# DISPLAY
# =====================================================

st.subheader("📌 Current State")

if st.session_state.ledger:
    last = st.session_state.ledger[-1]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("K (Portal)", last["K"])
    c2.metric("Regime", last["regime"])
    c3.metric("Valence", last["valence"])
    c4.metric("Pred Error", last["pred_err"])

    st.write("**Signature:**", last["signature"])
    st.write("**Action:**", last["action"], " | scores:", last["action_scores"])
    st.write("**Shock:**", "YES ⚡" if last["shock"] else "No")
else:
    st.info("Press ▶ Advance Event to begin.")

st.subheader("❤️ Emotion")
st.json(st.session_state.emotion)

st.subheader("🧍 Body Awareness")
st.json(st.session_state.body)

st.subheader("👁️ Vision")
st.json(st.session_state.vision)

st.subheader("🧠 Active Concepts (Competitive)")
for c in sorted(list(st.session_state.concepts)):
    st.write(c, "→ persistence:", round(st.session_state.patterns[c]["count"], 2))

# Recall summary: show top learned signatures by count
st.subheader("🗃️ Recall (Evaluated Memory)")
recall_items = list(st.session_state.recall.items())
recall_items.sort(key=lambda kv: kv[1]["count"], reverse=True)
for sig, r in recall_items[:8]:
    st.write(
        f"**{sig}** | n={r['count']} | expK={r['expected_K']:.3f} | "
        f"val={r['valence']:.3f} | conf_floor={r['conf_floor']:.3f} | "
        f"touch_rate={r['touch_rate']:.2f} | exp_motion={r['expected_motion']:.3f}"
    )

with st.expander("📜 Ledger (Last 15 Events)"):
    for row in st.session_state.ledger[-15:]:
        st.write(row)