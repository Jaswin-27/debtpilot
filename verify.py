from copy import deepcopy

from engine import PlanError, build_plan, rebuild_plan
from profiles import get_stacked_profile


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    profile = get_stacked_profile()

    # 1. Baseline
    plan = build_plan(profile)
    check(plan["status"] == "safe", "Baseline should be safe")
    check(plan["safe_debt_budget"] == 15000, "Safe debt budget should be 15000")
    check(plan["minimum_required"] == 9500, "Minimum required should be 9500")
    check(plan["surplus_after_minimums"] == 5500, "Surplus should be 5500")
    check(plan["plan_proof"]["passed"], "Plan proof should pass")
    check(plan["ranking"][0]["name"] == "Credit Card", "Credit card should rank first")
    check(sum(x["payment"] for x in plan["payments"]) <= 15000.01, "Payments exceed safe budget")

    # 2. Unknown APR preserved
    friend = next(x for x in plan["ranking"] if "Friend" in x["name"])
    check(friend["interest_rate"] is None, "Unknown APR was not preserved")

    # 3. Zero APR is valid known data
    bnpl = next(x for x in plan["ranking"] if x["name"] == "BNPL")
    check(bnpl["interest_rate"] == 0, "0% APR must not become unknown")

    # 4. Income shock
    rebuilt = rebuild_plan(profile, 16000)
    check(rebuilt["after"]["status"] == "distress", "Reduced income should trigger distress")
    check(rebuilt["after"]["distress"]["payment_shortfall"] == 6500, "Expected 6500 shortfall")
    check(rebuilt["after"]["payments"] == [], "Distress mode should pause normal payment allocation")

    # 5. Income below essentials
    severe = build_plan({**profile, "income": 10000})
    check(severe["status"] == "distress", "Income below essentials should be distress")
    check(severe["distress"]["level"] == "severe", "Expected severe distress")
    check(severe["distress"]["essential_gap"] == 3000, "Expected essential gap of 3000")

    # 6. No debts
    no_debts = deepcopy(profile)
    no_debts["debts"] = []
    empty = build_plan(no_debts)
    check(empty["minimum_required"] == 0, "No-debt minimums should be zero")
    check(empty["payments"] == [], "No-debt plan should contain no payments")
    check(empty["status"] == "safe", "No-debt profile should be safe if essentials fit")

    # 7. Overpay prevention
    tiny = deepcopy(profile)
    tiny["debts"][0]["balance"] = 1000
    tiny["debts"][0]["minimum_due"] = 2800
    tiny_plan = build_plan(tiny)
    card_payment = next(x for x in tiny_plan["payments"] if x["debt"] == "Credit Card")
    check(card_payment["payment"] <= 1000.01, "Payment exceeded outstanding balance")

    # 8. Negative values rejected
    bad = deepcopy(profile)
    bad["income"] = -1
    try:
        build_plan(bad)
        raise AssertionError("Negative income should have raised PlanError")
    except PlanError:
        pass

    # 9. Unknown due date accepted
    unknown_due = deepcopy(profile)
    unknown_due["debts"][3]["due_date"] = None
    unknown_due_plan = build_plan(unknown_due)
    check(unknown_due_plan["plan_proof"]["passed"], "Unknown due date should be accepted")

    # 10. Exact-budget case
    exact = deepcopy(profile)
    exact["income"] = 22500
    exact_plan = build_plan(exact)
    check(exact_plan["status"] == "safe", "Exact-budget case should be safe")
    check(exact_plan["surplus_after_minimums"] == 0, "Exact-budget surplus should be zero")

    print("DebtPilot final verification: PASS (10/10 scenarios)")


if __name__ == "__main__":
    main()
