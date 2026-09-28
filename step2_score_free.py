# STEP 2 (FREE VERSION): score every Fed statement from -1 (dovish) to +1 (hawkish) using Google's free Gemini API
# Test on 3 statements first:   python3 step2_score_free.py test
# Run everything:               python3 step2_score_free.py
import os, sys, json, time
import pandas as pd
from google import genai
from google.genai import types

OUT = "data/scores.csv"
TEST = len(sys.argv) > 1 and sys.argv[1] == "test"

SYSTEM = """You are a macro analyst at a hedge fund. You read Federal Reserve (FOMC) policy statements and score the monetary policy STANCE.

Scale:
-1.0 = very dovish (cutting rates, easing, emergency support)
 0.0 = neutral / on hold with balanced outlook
+1.0 = very hawkish (hiking rates, tightening, strong inflation concern)

Rules:
- Judge ONLY from the text of this statement. Do not use any knowledge of what happened in markets or the economy afterwards.
- Focus on the rate decision, forward guidance, and how the Committee describes inflation and growth risks.
- Reply with ONLY a JSON object, nothing else: {"score": <number between -1 and 1>, "reason": "<one sentence>"}"""

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Pick a free "flash-lite" model automatically (model names change often)
MODEL = os.environ.get("GEMINI_MODEL")
if not MODEL:
    names = []
    for m in client.models.list():
        n = m.name.replace("models/", "")
        acts = getattr(m, "supported_actions", None) or []
        bad = any(x in n for x in ["preview", "image", "tts", "live", "embedding", "audio", "exp", "vision", "thinking"])
        if "flash-lite" in n and not bad and (not acts or "generateContent" in acts):
            names.append(n)
    if not names:
        sys.exit("Could not find a flash-lite model. Run: python3 step2_score_free.py list")
    MODEL = sorted(names)[-1]
print("Using model:", MODEL)

st = pd.read_csv("data/statements.csv", parse_dates=["Date"])
if TEST:
    st = st.iloc[[0, len(st) // 2, len(st) - 1]]
path = "data/scores_test.csv" if TEST else OUT

done = {}
if os.path.exists(path) and not TEST:
    old = pd.read_csv(path, parse_dates=["Date"])
    done = {d: (s, r) for d, s, r in zip(old["Date"], old["score"], old["reason"])}

rows = []
for _, row in st.iterrows():
    d = row["Date"]
    if d in done:
        rows.append({"Date": d, "score": done[d][0], "reason": done[d][1]})
        continue
    text = str(row["Text"])[:12000]
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents="FOMC statement:\n\n" + text,
                config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0),
            )
            raw = resp.text
            js = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
            score = max(-1.0, min(1.0, float(js["score"])))
            rows.append({"Date": d, "score": score, "reason": js["reason"]})
            print(f"{d.date()}  score={score:+.2f}  {js['reason'][:90]}")
            break
        except Exception as e:
            print(f"  retry {attempt + 1} for {d.date()} ({str(e)[:120]})")
            time.sleep(20 * (attempt + 1))
    pd.DataFrame(rows).to_csv(path, index=False)
    time.sleep(7)  # stay under the free rate limit

pd.DataFrame(rows).to_csv(path, index=False)
print("DONE. Step 2 complete.")
