from __future__ import annotations

from datetime import date, timedelta
from copy import deepcopy


def _future(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def get_stacked_profile():
    return {
        "profile_name": "Stacked debt demo",
        "as_of_date": date.today().isoformat(),
        "income": 28000,
        "essential_expenses": {
            "rent": 7000,
            "food": 3500,
            "transport": 1500,
            "other_essentials": 1000,
        },
        "debts": [
            {"id": "credit_card", "name": "Credit Card", "type": "Credit card", "balance": 32000, "minimum_due": 2800, "interest_rate": 39, "due_date": _future(3), "overdue": False},
            {"id": "personal_loan", "name": "Personal Loan", "type": "Consumer / personal loan", "balance": 45000, "minimum_due": 4200, "interest_rate": 16, "due_date": _future(8), "overdue": False},
            {"id": "bnpl", "name": "BNPL", "type": "BNPL", "balance": 8000, "minimum_due": 1500, "interest_rate": 0, "due_date": _future(5), "overdue": False},
            {"id": "friend", "name": "Friend / Informal", "type": "Money owed to friend", "balance": 5000, "minimum_due": 1000, "interest_rate": None, "due_date": _future(14), "overdue": False},
        ],
    }


def get_reduced_income_profile():
    profile = deepcopy(get_stacked_profile())
    profile["profile_name"] = "Reduced-income demo"
    profile["income"] = 16000
    return profile
