from __future__ import annotations
import json
import os
from dataclasses import dataclass
from typing import Dict, Any, Tuple

import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL", "https://script.google.com/macros/s/AKfycbyduzh-CH2VlqZ8rxmnWvn8wwJegsklEw4T6R_KZnApZKoZm5VpczktitvIUoEFgAnx/exec")  # Web app URL
APPS_SCRIPT_TOKEN = os.environ.get("APPS_SCRIPT_TOKEN", "CHANGE_ME_TO_A_LONG_RANDOM_STRING")  # same as API_TOKEN in Apps Script


@dataclass
class QuizData:
    personas: Dict[str, Dict[str, Any]]
    questions: list[Dict[str, Any]]


def load_quiz_data(path: str = "personas.json") -> QuizData:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return QuizData(personas=raw["personas"], questions=raw["questions"])


QUIZ = load_quiz_data()


def compute_result(answers: Dict[str, int]) -> Tuple[str, Dict[str, int]]:
    scores = {k: 0 for k in QUIZ.personas.keys()}
    q_map = {q["id"]: q for q in QUIZ.questions}

    for qid, opt_idx in answers.items():
        q = q_map.get(qid)
        if not q:
            continue
        options = q.get("options", [])
        if opt_idx < 0 or opt_idx >= len(options):
            continue
        weights = options[opt_idx].get("weights", {})
        for persona_key, w in weights.items():
            if persona_key in scores:
                scores[persona_key] += int(w)

    winner = max(scores.items(), key=lambda kv: (kv[1], kv[0]))[0]
    return winner, scores


def call_apps_script(payload: dict) -> dict:
    if not APPS_SCRIPT_URL or not APPS_SCRIPT_TOKEN:
        raise RuntimeError("Missing APPS_SCRIPT_URL or APPS_SCRIPT_TOKEN env vars")

    payload = {**payload, "token": APPS_SCRIPT_TOKEN}
    resp = requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
    # Apps Script always returns JSON body; treat non-200 as error too
    data = resp.json() if resp.content else {}
    if not data.get("ok"):
        # include status code in error for debugging
        data["_http_status"] = resp.status_code
    return data


def require_verified_email():
    email = session.get("email")
    return email if email else None


@app.route("/")
def index():
    session.pop("answers", None)
    session.pop("email", None)
    return render_template("index.html")


@app.route("/start")
def start():
    # email gate entry
    return render_template("email.html", error=None)


@app.route("/verify_email", methods=["POST"])
def verify_email():
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        return render_template("email.html", error="Please enter your email.")

    try:
        res = call_apps_script({"action": "verify_email", "email": email})
    except Exception as e:
        return render_template("email.html", error=f"Verification service error: {e}")

    if res.get("ok") is True:
        session["email"] = email
        # clear any old result
        session.pop("answers", None)
        session.pop("winner", None)
        session.pop("readonly", None)
        return redirect(url_for("quiz"))

    # Not ok
    err = res.get("error")
    if err == "already_submitted" and res.get("result"):
        session["email"] = email
        session["readonly"] = True

        # Stored results from sheet
        session["winner"] = res["result"].get("persona")
        # answers are keyed by q1..qN in Apps Script helper above
        # convert to your internal qid format if needed
        session["answers"] = res["result"].get("answers", {})

        return redirect(url_for("result"))

    msg_map = {
        "invalid_email": "That email format looks invalid.",
        "not_allowed": "Your email is not in the allowed list.",
        "already_submitted": "You have already submitted. (Result not found in sheet.)"
    }
    return render_template("email.html", error=msg_map.get(err, f"Verification failed: {err}"))



@app.route("/quiz")
def quiz():
    if not require_verified_email():
        return redirect(url_for("start"))
    return render_template("quiz.html", questions=QUIZ.questions)


@app.route("/submit", methods=["POST"])
def submit():
    if not require_verified_email():
        return {"ok": False, "error": "not_verified"}, 401

    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers", {})

    # Validate
    cleaned: Dict[str, int] = {}
    valid_qids = [q["id"] for q in QUIZ.questions]
    valid_set = set(valid_qids)

    for qid, idx in answers.items():
        if qid in valid_set:
            try:
                cleaned[qid] = int(idx)
            except Exception:
                pass

    # Compute result
    winner, _scores = compute_result(cleaned)

    # Save locally in session
    session["answers"] = cleaned
    session["winner"] = winner

    # Persist to Google Sheet (first-write wins)
    email = session["email"]
    try:
        res = call_apps_script({
            "action": "submit_result",
            "email": email,
            "persona": winner,
            "answers": cleaned,
            "question_order": valid_qids
        })
        if not res.get("ok"):
            # If duplicate, block
            if res.get("error") == "already_submitted":
                return {"ok": False, "error": "already_submitted"}, 409
            return {"ok": False, "error": res.get("error", "save_failed")}, 500
    except Exception as e:
        return {"ok": False, "error": f"save_failed: {e}"}, 500

    return {"ok": True}


@app.route("/result")
def result():
    if not require_verified_email():
        return redirect(url_for("start"))

    winner_key = session.get("winner")
    answers = session.get("answers", {})
    readonly = bool(session.get("readonly", False))

    if not winner_key:
        # If user somehow navigated here without a stored result
        return redirect(url_for("quiz"))

    winner = QUIZ.personas.get(winner_key)
    if not winner:
        return render_template("result.html", winner_key="unknown", winner={
            "title": "Unknown",
            "tagline": "",
            "description": "Could not find persona configuration for this result.",
            "traits": {}
        }, scores={}, score_pct={}, personas=QUIZ.personas, readonly=readonly)

    # Optional: recompute scores if you want to show breakdown
    # Only works if answers are indices and match your quiz question IDs.
    scores = {k: 0 for k in QUIZ.personas.keys()}
    try:
        # Convert answers values to int indices when possible
        cleaned = {}
        for k, v in answers.items():
            try:
                cleaned[k] = int(v)
            except Exception:
                pass
        winner2, scores = compute_result(cleaned)
        # winner2 should match winner_key if consistent
    except Exception:
        pass

    max_score = max(scores.values()) if scores else 1
    score_pct = {k: int((v / max_score) * 100) if max_score > 0 else 0 for k, v in scores.items()}

    return render_template(
        "result.html",
        winner_key=winner_key,
        winner=winner,
        scores=scores,
        score_pct=score_pct,
        personas=QUIZ.personas,
        readonly=readonly
    )



import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
