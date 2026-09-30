from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"

SYSTEM_INSTRUCTIONS = """
You are the explanation layer of DebtPilot, a hackathon debt-management prototype.

A deterministic Python engine has already made every financial decision.
You have LANGUAGE AUTHORITY ONLY, not financial authority.

You may explain only the structured plan provided to you.

You MUST NOT:
- change any amount, rank, APR, due date, balance, status or safety check
- invent an APR, fee, saving, legal consequence or financial fact
- recommend taking a new loan to repay an old debt
- recommend skipping protected essential expenses
- invent a helpline or phone number
- claim DebtPilot can collect or transfer money
- override the distress gate
- calculate new financial figures that are not in the structured plan

If information is unknown, say it is unknown.
If status is distress, state that normal debt optimisation is paused.
Tone: calm, specific, concise and non-judgmental.
Use 4–7 short sentences.
""".strip()


def deterministic_explanation(plan: Dict[str, Any]) -> str:
    safe_budget = plan["safe_debt_budget"]
    minimums = plan["minimum_required"]
    lines = [
        f"After protected essential expenses, ₹{safe_budget:,.0f} is available for debt payments.",
        f"The supplied minimum obligations total ₹{minimums:,.0f}.",
    ]

    if plan["status"] == "distress":
        shortfall = plan["distress"]["payment_shortfall"]
        lines.append(f"The current numbers show a minimum-payment shortfall of ₹{shortfall:,.0f}, so normal debt optimisation is paused.")
        if plan["distress"]["essential_gap"] > 0:
            lines.append(f"Income is also ₹{plan['distress']['essential_gap']:,.0f} below the protected essential-expense total.")
        lines.append("DebtPilot does not use essential-expense money or recommend new borrowing to fill the gap.")
    else:
        lines.append(f"All supplied minimums fit inside the safe debt budget, leaving ₹{plan['surplus_after_minimums']:,.0f} for additional repayment.")
        if plan["ranking"]:
            first = plan["ranking"][0]
            lines.append(f"{first['name']} is priority #1 under the deterministic ranking rules.")

    unknown = [item["name"] for item in plan.get("ranking", []) if item.get("interest_rate") is None]
    if unknown:
        lines.append(f"The APR for {', '.join(unknown)} is unknown, so it is not used for APR ranking.")

    lines.append(f"The plan passed {plan['plan_proof']['passed_count']}/{plan['plan_proof']['total_count']} deterministic safety checks.")
    return " ".join(lines)


def _normalize_model_name(model: str) -> str:
    model = (model or "").strip()
    if not model:
        return ""
    return model if model.startswith("models/") else f"models/{model}"


def _discover_model(api_key: str) -> Optional[str]:
    response = requests.get(f"{API_ROOT}/models", params={"key": api_key}, timeout=12)
    response.raise_for_status()
    models = response.json().get("models", [])
    usable = []
    for model in models:
        methods = model.get("supportedGenerationMethods", [])
        name = model.get("name", "")
        if "generateContent" in methods and name:
            usable.append(name)
    if not usable:
        return None

    for candidate in ["models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-flash"]:
        if candidate in usable:
            return candidate

    stable_flash = [name for name in usable if "gemini" in name.lower() and "flash" in name.lower() and "preview" not in name.lower() and "exp" not in name.lower()]
    if stable_flash:
        return sorted(stable_flash, reverse=True)[0]
    flash = [name for name in usable if "flash" in name.lower()]
    if flash:
        return sorted(flash, reverse=True)[0]
    gemini = [name for name in usable if "gemini" in name.lower()]
    return sorted(gemini, reverse=True)[0] if gemini else usable[0]


def _safe_payload(plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": plan["status"],
        "income": plan["income"],
        "essential_total": plan["essential_total"],
        "safe_debt_budget": plan["safe_debt_budget"],
        "minimum_required": plan["minimum_required"],
        "surplus_after_minimums": plan["surplus_after_minimums"],
        "ranking": plan["ranking"],
        "payments": plan["payments"],
        "distress": plan["distress"],
        "plan_proof": plan["plan_proof"],
    }


def explain_plan(plan: Dict[str, Any]) -> Dict[str, str]:
    fallback = deterministic_explanation(plan)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    requested_model = _normalize_model_name(os.getenv("GEMINI_MODEL", ""))

    if not api_key:
        return {"text": fallback, "source": "Deterministic fallback", "model": ""}

    try:
        model = requested_model or _discover_model(api_key)
        if not model:
            raise RuntimeError("No generateContent-capable Gemini model was found.")

        prompt = SYSTEM_INSTRUCTIONS + "\n\nVERIFIED STRUCTURED PLAN:\n" + json.dumps(_safe_payload(plan), ensure_ascii=False)
        response = requests.post(
            f"{API_ROOT}/{model}:generateContent",
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500},
            },
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise RuntimeError("Gemini returned no explanation text.")
        return {"text": text, "source": "Gemini", "model": model.replace("models/", "")}
    except Exception:
        return {"text": fallback, "source": "Deterministic fallback", "model": ""}
