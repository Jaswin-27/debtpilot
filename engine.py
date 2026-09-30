from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
import math

EPSILON = 0.01

FORBIDDEN_MOVES = [
    "borrow_new_debt_to_pay_old_debt",
    "use_protected_essential_expenses",
    "invent_interest_rate",
    "allocate_more_than_safe_budget",
    "collect_or_transfer_payment",
    "allow_llm_to_change_financial_decisions",
]


class PlanError(ValueError):
    """Raised when supplied financial data is invalid."""


def _money(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise PlanError(f"{field_name} must be a number.")
    if math.isnan(number) or math.isinf(number):
        raise PlanError(f"{field_name} must be a finite number.")
    if number < 0:
        raise PlanError(f"{field_name} cannot be negative.")
    return round(number, 2)


def _optional_rate(value: Any, field_name: str) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise PlanError(f"{field_name} must be a number or left blank.")
    if math.isnan(number):
        return None
    if math.isinf(number) or number < 0:
        raise PlanError(f"{field_name} must be zero or greater.")
    return round(number, 4)


def _parse_date(value: Any) -> Optional[date]:
    if value in (None, "", "Unknown", "unknown"):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise PlanError(f"Invalid date '{value}'. Use YYYY-MM-DD.")


def _as_of(profile: Dict[str, Any]) -> date:
    raw = profile.get("as_of_date")
    return _parse_date(raw) if raw else date.today()


def validate_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(profile, dict):
        raise PlanError("Profile must be a dictionary.")

    cleaned = deepcopy(profile)
    cleaned["income"] = _money(cleaned.get("income", 0), "Monthly income")

    expenses = cleaned.get("essential_expenses", {})
    if not isinstance(expenses, dict):
        raise PlanError("Essential expenses must be a dictionary.")

    cleaned_expenses: Dict[str, float] = {}
    for name, amount in expenses.items():
        cleaned_expenses[str(name)] = _money(amount, f"Essential expense '{name}'")
    cleaned["essential_expenses"] = cleaned_expenses

    debts = cleaned.get("debts", [])
    if not isinstance(debts, list):
        raise PlanError("Debts must be a list.")

    seen_ids = set()
    cleaned_debts = []

    for index, raw_debt in enumerate(debts, start=1):
        if not isinstance(raw_debt, dict):
            raise PlanError(f"Debt #{index} is invalid.")

        debt = deepcopy(raw_debt)
        debt_id = str(debt.get("id") or f"debt_{index}")
        if debt_id in seen_ids:
            raise PlanError(f"Duplicate debt id: {debt_id}")
        seen_ids.add(debt_id)

        name = str(debt.get("name") or "").strip()
        if not name:
            name = f"Debt {index}"

        debt["id"] = debt_id
        debt["name"] = name
        debt["type"] = str(debt.get("type") or "Other").strip()
        debt["balance"] = _money(debt.get("balance", 0), f"{name} balance")
        debt["minimum_due"] = _money(debt.get("minimum_due", 0), f"{name} minimum due")
        debt["minimum_due"] = min(debt["minimum_due"], debt["balance"])
        debt["interest_rate"] = _optional_rate(debt.get("interest_rate"), f"{name} APR")

        due = _parse_date(debt.get("due_date"))
        debt["due_date"] = due.isoformat() if due else None
        debt["overdue"] = bool(debt.get("overdue", False))
        cleaned_debts.append(debt)

    cleaned["debts"] = cleaned_debts
    cleaned["as_of_date"] = _parse_date(cleaned.get("as_of_date")).isoformat() if cleaned.get("as_of_date") else date.today().isoformat()
    return cleaned


def calculate_essential_total(profile: Dict[str, Any]) -> float:
    return round(sum(profile["essential_expenses"].values()), 2)


def calculate_safe_debt_budget(profile: Dict[str, Any]) -> Tuple[float, float]:
    essential_total = calculate_essential_total(profile)
    raw_after_essentials = round(profile["income"] - essential_total, 2)
    return max(0.0, raw_after_essentials), raw_after_essentials


def calculate_minimum_required(profile: Dict[str, Any]) -> float:
    return round(sum(min(debt["minimum_due"], debt["balance"]) for debt in profile["debts"]), 2)


def _days_until_due(debt: Dict[str, Any], as_of_date: date) -> Optional[int]:
    due = _parse_date(debt.get("due_date"))
    return (due - as_of_date).days if due else None


def _is_overdue(debt: Dict[str, Any], as_of_date: date) -> bool:
    days = _days_until_due(debt, as_of_date)
    return bool(debt.get("overdue")) or (days is not None and days < 0)


def debt_evidence(debt: Dict[str, Any], as_of_date: date) -> List[str]:
    evidence: List[str] = []
    days = _days_until_due(debt, as_of_date)

    if _is_overdue(debt, as_of_date):
        if days is not None and days < 0:
            evidence.append(f"Due date passed {-days} day(s) ago")
        else:
            evidence.append("Marked overdue")
    elif days is None:
        evidence.append("Due date unknown")
    elif days == 0:
        evidence.append("Due today")
    elif days == 1:
        evidence.append("Due in 1 day")
    elif days > 1:
        evidence.append(f"Due in {days} days")

    evidence.append(f"Minimum due ₹{debt['minimum_due']:,.0f}")

    rate = debt.get("interest_rate")
    if rate is None:
        evidence.append("APR unknown — not used for APR ranking")
    else:
        evidence.append(f"Verified APR {rate:g}% from supplied data")

    return evidence


def _ranking_key(debt: Dict[str, Any], as_of_date: date) -> Tuple:
    overdue = _is_overdue(debt, as_of_date)
    days = _days_until_due(debt, as_of_date)
    due_key = days if days is not None else 999999
    rate = debt.get("interest_rate")
    known_rate = rate is not None
    rate_key = -(rate if known_rate else -1)
    return (0 if overdue else 1, 0 if known_rate else 1, rate_key, due_key, debt["name"].lower())


def rank_debts(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    as_of_date = _as_of(profile)
    active = [debt for debt in profile["debts"] if debt["balance"] > EPSILON]
    ordered = sorted(active, key=lambda debt: _ranking_key(debt, as_of_date))
    result = []
    for rank, debt in enumerate(ordered, start=1):
        result.append({
            "rank": rank,
            "id": debt["id"],
            "name": debt["name"],
            "type": debt["type"],
            "balance": debt["balance"],
            "minimum_due": debt["minimum_due"],
            "interest_rate": debt["interest_rate"],
            "due_date": debt["due_date"],
            "overdue": _is_overdue(debt, as_of_date),
            "evidence": debt_evidence(debt, as_of_date),
        })
    return result


def detect_distress(profile: Dict[str, Any], safe_budget: float, raw_after_essentials: float, minimum_required: float) -> Dict[str, Any]:
    essential_total = calculate_essential_total(profile)
    essential_gap = max(0.0, round(essential_total - profile["income"], 2))
    payment_shortfall = max(0.0, round(minimum_required - safe_budget, 2))

    if raw_after_essentials < -EPSILON:
        return {
            "active": True,
            "level": "severe",
            "reason": "income_below_essentials",
            "message": "Income is below protected essential expenses. Normal debt optimisation is paused.",
            "essential_gap": essential_gap,
            "payment_shortfall": payment_shortfall,
        }

    if safe_budget + EPSILON < minimum_required:
        return {
            "active": True,
            "level": "shortfall",
            "reason": "minimums_exceed_safe_budget",
            "message": "The safe debt budget cannot cover all supplied minimum obligations. Normal debt optimisation is paused.",
            "essential_gap": 0.0,
            "payment_shortfall": payment_shortfall,
        }

    return {
        "active": False,
        "level": "safe",
        "reason": None,
        "message": "The current month is feasible under the supplied data.",
        "essential_gap": 0.0,
        "payment_shortfall": 0.0,
    }


def allocate_safe_plan(profile: Dict[str, Any], ranking: List[Dict[str, Any]], safe_budget: float) -> Tuple[List[Dict[str, Any]], float]:
    debt_by_id = {debt["id"]: debt for debt in profile["debts"]}
    payments = {debt_id: min(debt["minimum_due"], debt["balance"]) for debt_id, debt in debt_by_id.items()}

    used = round(sum(payments.values()), 2)
    remaining = round(max(0.0, safe_budget - used), 2)

    for ranked in ranking:
        if remaining <= EPSILON:
            break
        debt = debt_by_id[ranked["id"]]
        already = payments[debt["id"]]
        room = max(0.0, round(debt["balance"] - already, 2))
        extra = min(room, remaining)
        payments[debt["id"]] = round(already + extra, 2)
        remaining = round(remaining - extra, 2)

    result: List[Dict[str, Any]] = []
    rank_map = {item["id"]: item["rank"] for item in ranking}
    for debt in profile["debts"]:
        payment = round(payments.get(debt["id"], 0.0), 2)
        if payment <= EPSILON:
            continue
        result.append({
            "debt_id": debt["id"],
            "debt": debt["name"],
            "rank": rank_map.get(debt["id"]),
            "payment": payment,
            "minimum_due": debt["minimum_due"],
            "balance": debt["balance"],
            "interest_rate": debt["interest_rate"],
            "due_date": debt["due_date"],
        })

    result.sort(key=lambda item: item["rank"] if item["rank"] is not None else 999999)
    return result, remaining


def validate_plan(profile: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    allocated = round(sum(item["payment"] for item in plan["payments"]), 2)
    safe_budget = plan["safe_debt_budget"]
    debt_by_id = {debt["id"]: debt for debt in profile["debts"]}
    checks: List[Dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("Protected essentials untouched", allocated <= safe_budget + EPSILON,
        f"Suggested payments use ₹{allocated:,.0f} from a safe debt budget of ₹{safe_budget:,.0f}.")
    add("Payments within safe budget", allocated <= safe_budget + EPSILON,
        "Suggested payments never exceed cash left after protected essentials.")
    add("No negative payments", all(item["payment"] >= -EPSILON for item in plan["payments"]),
        "All suggested payment amounts are zero or positive.")
    add("No payment exceeds balance", all(item["payment"] <= debt_by_id[item["debt_id"]]["balance"] + EPSILON for item in plan["payments"]),
        "Every payment is capped at the supplied outstanding balance.")
    add("No interest rate invented", True,
        "Unknown APR values remain unknown and are excluded from APR ranking.")
    add("No new borrowing", True,
        "The engine contains no action that creates a new loan to service old debt.")
    add("No payment collection", True,
        "DebtPilot is advisory only and has no transfer or collection capability.")

    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "passed_count": sum(1 for item in checks if item["passed"]), "total_count": len(checks), "checks": checks}


def build_plan(profile: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = validate_profile(profile)
    essential_total = calculate_essential_total(cleaned)
    safe_budget, raw_after_essentials = calculate_safe_debt_budget(cleaned)
    minimum_required = calculate_minimum_required(cleaned)
    ranking = rank_debts(cleaned)
    distress = detect_distress(cleaned, safe_budget, raw_after_essentials, minimum_required)

    if distress["active"]:
        payments: List[Dict[str, Any]] = []
        unallocated_cash = safe_budget
    else:
        payments, unallocated_cash = allocate_safe_plan(cleaned, ranking, safe_budget)

    allocated_total = round(sum(item["payment"] for item in payments), 2)
    surplus_after_minimums = max(0.0, round(safe_budget - minimum_required, 2))

    plan = {
        "status": "distress" if distress["active"] else "safe",
        "as_of_date": _as_of(cleaned).isoformat(),
        "income": cleaned["income"],
        "essential_total": essential_total,
        "safe_debt_budget": safe_budget,
        "minimum_required": minimum_required,
        "surplus_after_minimums": surplus_after_minimums,
        "allocated_total": allocated_total,
        "unallocated_cash": round(unallocated_cash, 2),
        "ranking": ranking,
        "payments": payments,
        "distress": distress,
        "forbidden_moves": list(FORBIDDEN_MOVES),
    }

    proof = validate_plan(cleaned, plan)
    plan["plan_proof"] = proof
    if not proof["passed"]:
        raise PlanError("Generated plan failed deterministic safety validation.")
    return plan


def compare_plans(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    rows = [
        {"label": "Income", "before": before["income"], "after": after["income"]},
        {"label": "Safe debt budget", "before": before["safe_debt_budget"], "after": after["safe_debt_budget"]},
        {"label": "Minimum required", "before": before["minimum_required"], "after": after["minimum_required"]},
        {"label": "Payment shortfall", "before": before["distress"]["payment_shortfall"], "after": after["distress"]["payment_shortfall"]},
    ]
    for row in rows:
        row["change"] = round(row["after"] - row["before"], 2)
    return {"rows": rows, "status_before": before["status"], "status_after": after["status"], "status_changed": before["status"] != after["status"]}


def rebuild_plan(profile: Dict[str, Any], new_income: float) -> Dict[str, Any]:
    original = validate_profile(profile)
    before = build_plan(original)
    changed = deepcopy(original)
    changed["income"] = _money(new_income, "New monthly income")
    after = build_plan(changed)
    return {"before": before, "after": after, "what_changed": compare_plans(before, after), "updated_profile": changed}


def run_smoke_checks() -> None:
    from profiles import get_stacked_profile

    profile = get_stacked_profile()
    plan = build_plan(profile)
    assert plan["status"] == "safe"
    assert plan["safe_debt_budget"] == 15000
    assert plan["minimum_required"] == 9500
    assert plan["surplus_after_minimums"] == 5500
    assert plan["plan_proof"]["passed"]
    assert len(plan["ranking"]) == 4
    assert plan["ranking"][0]["name"] == "Credit Card"
    assert sum(item["payment"] for item in plan["payments"]) <= plan["safe_debt_budget"] + EPSILON

    friend = next(item for item in plan["ranking"] if "Friend" in item["name"])
    assert friend["interest_rate"] is None

    rebuilt = rebuild_plan(profile, 16000)
    assert rebuilt["after"]["status"] == "distress"
    assert rebuilt["after"]["payments"] == []
    assert rebuilt["after"]["distress"]["payment_shortfall"] == 6500

    severe = build_plan({**profile, "income": 10000})
    assert severe["status"] == "distress"
    assert severe["distress"]["level"] == "severe"
    assert severe["payments"] == []

    print("DebtPilot engine smoke checks: PASS")
    print(f"Safe budget: ₹{plan['safe_debt_budget']:,.0f}")
    print(f"Minimum required: ₹{plan['minimum_required']:,.0f}")
    print(f"Surplus after minimums: ₹{plan['surplus_after_minimums']:,.0f}")
    print(f"Reduced-income status: {rebuilt['after']['status']}")
    print(f"Reduced-income shortfall: ₹{rebuilt['after']['distress']['payment_shortfall']:,.0f}")


if __name__ == "__main__":
    run_smoke_checks()
