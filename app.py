from __future__ import annotations

from copy import deepcopy
from datetime import date
import html
import math

import pandas as pd
import streamlit as st

from engine import PlanError, build_plan, rebuild_plan
from explainer import explain_plan
from helplines import get_financial_support_resources, get_wellbeing_support
from profiles import get_stacked_profile


st.set_page_config(
    page_title="DebtPilot",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------- Visual system ----------------
st.markdown(
    """
    <style>
      #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
        visibility: hidden !important;
        height: 0 !important;
      }

      .block-container {
        max-width: 1320px;
        padding-top: 1.15rem;
        padding-bottom: 3rem;
      }

      :root {
        --bg: #0b1220;
        --panel: #111827;
        --panel-soft: #0f172a;
        --border: #263244;
        --muted: #94a3b8;
        --text: #f8fafc;
        --blue: #2563eb;
        --blue-soft: rgba(37,99,235,.12);
        --green: #22c55e;
        --green-soft: rgba(34,197,94,.10);
        --amber: #f59e0b;
        --amber-soft: rgba(245,158,11,.10);
        --red: #ef4444;
        --red-soft: rgba(239,68,68,.10);
      }

      [data-testid="stAppViewContainer"] {
        background: var(--bg);
      }

      .dp-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: .35rem 0 1rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.35rem;
      }

      .dp-brand {
        font-size: 1.62rem;
        font-weight: 800;
        letter-spacing: -.035em;
        color: var(--text);
      }

      .dp-subbrand {
        color: var(--muted);
        font-size: .85rem;
        margin-top: .15rem;
      }

      .dp-tag {
        border: 1px solid var(--border);
        color: #cbd5e1;
        padding: .38rem .68rem;
        border-radius: 999px;
        font-size: .72rem;
        font-weight: 700;
        background: rgba(255,255,255,.02);
        white-space: nowrap;
      }

      .dp-section-title {
        color: var(--text);
        font-size: 1.08rem;
        font-weight: 800;
        margin: 0 0 .15rem 0;
      }

      .dp-section-note {
        color: var(--muted);
        font-size: .78rem;
        margin: 0 0 .8rem 0;
      }

      .dp-card {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: .95rem 1rem;
      }

      .dp-safe {
        background: var(--green-soft);
        border: 1px solid rgba(34,197,94,.42);
        border-radius: 12px;
        padding: .85rem .95rem;
        margin: .8rem 0 1rem 0;
      }

      .dp-distress {
        background: var(--red-soft);
        border: 1px solid rgba(239,68,68,.46);
        border-radius: 12px;
        padding: .95rem 1rem;
        margin: .8rem 0 1rem 0;
      }

      .dp-warning {
        background: var(--amber-soft);
        border: 1px solid rgba(245,158,11,.42);
        border-radius: 12px;
        padding: .85rem .95rem;
        margin: .8rem 0;
      }

      .dp-status-title {
        font-weight: 850;
        letter-spacing: -.01em;
      }

      .dp-muted { color: var(--muted); }

      .dp-plan-row {
        padding: .82rem .1rem;
        border-bottom: 1px solid rgba(148,163,184,.14);
      }

      .dp-plan-row:last-child {
        border-bottom: none;
      }

      .dp-plan-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
      }

      .dp-rank {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.7rem;
        height: 1.7rem;
        border-radius: 50%;
        background: var(--blue-soft);
        color: #bfdbfe;
        border: 1px solid rgba(37,99,235,.45);
        font-weight: 800;
        margin-right: .55rem;
        font-size: .78rem;
      }

      .dp-money {
        font-size: 1.18rem;
        font-weight: 800;
        white-space: nowrap;
      }

      .dp-caption {
        color: var(--muted);
        font-size: .75rem;
        line-height: 1.45;
        margin-top: .2rem;
      }

      .dp-proof-item {
        display: flex;
        gap: .55rem;
        padding: .52rem 0;
        border-bottom: 1px solid rgba(148,163,184,.10);
      }

      .dp-proof-item:last-child {
        border-bottom: none;
      }

      .dp-check {
        color: var(--green);
        font-weight: 900;
      }

      .dp-support {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: .85rem .9rem;
        margin-bottom: .65rem;
      }

      .dp-phone {
        font-size: 1.12rem;
        font-weight: 800;
        margin: .18rem 0;
      }

      .dp-footer {
        border-top: 1px solid var(--border);
        margin-top: 1.6rem;
        padding-top: .8rem;
        color: var(--muted);
        font-size: .72rem;
      }

      div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: .68rem .78rem;
      }

      div[data-testid="stDataEditor"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
      }

      div[data-testid="stTabs"] button {
        font-weight: 700;
      }

      div.stButton > button,
      div[data-testid="stLinkButton"] a {
        border-radius: 9px !important;
        font-weight: 750 !important;
        min-height: 2.55rem;
      }

      /* Make currency inputs look cleaner; users can type directly. */
      button[aria-label="Increment"],
      button[aria-label="Decrement"] {
        display: none !important;
      }

      /* Reduce unused padding around number-input controls. */
      div[data-baseweb="input"] input {
        padding-right: .7rem !important;
      }

      @media (max-width: 900px) {
        .dp-topbar {
          align-items: flex-start;
          flex-direction: column;
        }
        .block-container {
          padding-left: .75rem;
          padding-right: .75rem;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- State ----------------
def _init_state():
    if "profile" not in st.session_state:
        st.session_state.profile = get_stacked_profile()
    if "plan" not in st.session_state:
        st.session_state.plan = None
    if "explanation" not in st.session_state:
        st.session_state.explanation = None
    if "rebuild" not in st.session_state:
        st.session_state.rebuild = None
    if "rebuild_explanation" not in st.session_state:
        st.session_state.rebuild_explanation = None
    if "editor_version" not in st.session_state:
        st.session_state.editor_version = 1

    profile = st.session_state.profile
    defaults = {
        "income_input": float(profile["income"]),
        "rent_input": float(profile["essential_expenses"]["rent"]),
        "food_input": float(profile["essential_expenses"]["food"]),
        "transport_input": float(profile["essential_expenses"]["transport"]),
        "other_input": float(profile["essential_expenses"]["other_essentials"]),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_demo():
    """Safe Streamlit callback: runs before widgets are rebuilt."""
    profile = get_stacked_profile()
    st.session_state.profile = profile
    st.session_state.plan = None
    st.session_state.explanation = None
    st.session_state.rebuild = None
    st.session_state.rebuild_explanation = None
    st.session_state.editor_version += 1
    st.session_state.income_input = float(profile["income"])
    st.session_state.rent_input = float(profile["essential_expenses"]["rent"])
    st.session_state.food_input = float(profile["essential_expenses"]["food"])
    st.session_state.transport_input = float(profile["essential_expenses"]["transport"])
    st.session_state.other_input = float(profile["essential_expenses"]["other_essentials"])


def _debts_to_df(debts):
    rows = []
    for debt in debts:
        rows.append(
            {
                "Debt": debt["name"],
                "Type": debt["type"],
                "Balance (₹)": debt["balance"],
                "Min due (₹)": debt["minimum_due"],
                "APR (%)": debt["interest_rate"],
                "Due date": debt["due_date"] or "",
            }
        )
    return pd.DataFrame(rows)


def _df_to_debts(df):
    debts = []
    for index, row in df.iterrows():
        name = str(row.get("Debt", "") or "").strip()
        if not name:
            continue

        apr = row.get("APR (%)")
        if apr is None or (isinstance(apr, float) and math.isnan(apr)):
            apr = None

        due = str(row.get("Due date", "") or "").strip()
        if due.lower() in {"nan", "nat", "none"}:
            due = ""

        debts.append(
            {
                "id": f"debt_{index + 1}",
                "name": name,
                "type": str(row.get("Type", "Other") or "Other"),
                "balance": row.get("Balance (₹)", 0),
                "minimum_due": row.get("Min due (₹)", 0),
                "interest_rate": apr,
                "due_date": due or None,
                # Manual overdue control removed from UI.
                # Engine still marks debts overdue automatically when due_date is in the past.
                "overdue": False,
            }
        )
    return debts


def _build_current_profile(edited_df):
    return {
        "profile_name": "Current profile",
        "as_of_date": date.today().isoformat(),
        "income": st.session_state.income_input,
        "essential_expenses": {
            "rent": st.session_state.rent_input,
            "food": st.session_state.food_input,
            "transport": st.session_state.transport_input,
            "other_essentials": st.session_state.other_input,
        },
        "debts": _df_to_debts(edited_df),
    }


_init_state()

# ---------------- Header ----------------
st.markdown(
    """
    <div class="dp-topbar">
      <div>
        <div class="dp-brand">🧭 DebtPilot</div>
        <div class="dp-subbrand">Monthly debt planning</div>
      </div>
      <div>
        <span class="dp-tag">Advisory only</span>
        <span class="dp-tag">No payments collected</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

profile = st.session_state.profile

# ---------------- Step 1: Profile ----------------
st.markdown('<div class="dp-section-title">1 · Financial profile</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="dp-section-note">Income and protected monthly essentials.</div>',
    unsafe_allow_html=True,
)

i1, i2, i3, i4, i5 = st.columns([1.1, 1, 1, 1, 1])
with i1:
    st.number_input("Monthly income (₹)", min_value=0.0, step=500.0, key="income_input")
with i2:
    st.number_input("Rent / housing", min_value=0.0, step=250.0, key="rent_input")
with i3:
    st.number_input("Food", min_value=0.0, step=250.0, key="food_input")
with i4:
    st.number_input("Transport", min_value=0.0, step=250.0, key="transport_input")
with i5:
    st.number_input("Other essentials", min_value=0.0, step=250.0, key="other_input")

st.markdown('<div style="height:.35rem"></div>', unsafe_allow_html=True)
st.markdown('<div class="dp-section-title">Debts</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="dp-section-note">APR can be left blank when unknown. Past due dates are detected automatically.</div>',
    unsafe_allow_html=True,
)

debt_df = _debts_to_df(profile["debts"])
edited_df = st.data_editor(
    debt_df,
    key=f"debt_editor_{st.session_state.editor_version}",
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    column_config={
        "Debt": st.column_config.TextColumn("Debt", required=True, width="medium"),
        "Type": st.column_config.SelectboxColumn(
            "Type",
            width="medium",
            options=[
                "Credit card",
                "Consumer / personal loan",
                "BNPL",
                "Money owed to friend",
                "Other",
            ],
        ),
        "Balance (₹)": st.column_config.NumberColumn(
            "Balance (₹)", min_value=0.0, format="₹%.0f", width="small"
        ),
        "Min due (₹)": st.column_config.NumberColumn(
            "Min due (₹)", min_value=0.0, format="₹%.0f", width="small"
        ),
        "APR (%)": st.column_config.NumberColumn(
            "APR (%)", min_value=0.0, format="%.2f", width="small"
        ),
        "Due date": st.column_config.TextColumn(
            "Due date", help="YYYY-MM-DD; leave blank if unknown", width="small"
        ),
    },
)

a1, a2, spacer = st.columns([1.2, 1, 3.5])
with a1:
    generate_clicked = st.button(
        "Generate plan",
        type="primary",
        use_container_width=True,
    )
with a2:
    st.button(
        "Reload demo",
        use_container_width=True,
        on_click=_load_demo,
    )

if generate_clicked:
    try:
        current_profile = _build_current_profile(edited_df)
        plan = build_plan(current_profile)

        st.session_state.profile = deepcopy(current_profile)
        st.session_state.plan = plan
        st.session_state.explanation = explain_plan(plan)
        st.session_state.rebuild = None
        st.session_state.rebuild_explanation = None
        st.rerun()
    except PlanError as exc:
        st.error(str(exc))


# ---------------- Step 2: Verified plan ----------------
plan = st.session_state.plan
if plan is not None:
    st.markdown("---")
    st.markdown('<div class="dp-section-title">2 · Verified plan</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dp-section-note">Calculated from the supplied profile.</div>',
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Income", f"₹{plan['income']:,.0f}")
    m2.metric("Essentials", f"₹{plan['essential_total']:,.0f}")
    m3.metric("Safe debt budget", f"₹{plan['safe_debt_budget']:,.0f}")
    m4.metric("Minimum dues", f"₹{plan['minimum_required']:,.0f}")
    m5.metric("Surplus", f"₹{plan['surplus_after_minimums']:,.0f}")

    if plan["status"] == "safe":
        st.markdown(
            f"""
            <div class="dp-safe">
              <span class="dp-status-title">✓ Safe plan</span>
              <span class="dp-muted"> · ₹{plan['surplus_after_minimums']:,.0f} remains after all supplied minimum dues.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="dp-distress">
              <span class="dp-status-title">⚠ Financial distress</span><br>
              <span class="dp-muted">{html.escape(plan["distress"]["message"])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    plan_left, plan_right = st.columns([1.35, .85], gap="large")

    with plan_left:
        st.markdown("**Payment plan**")

        if plan["status"] == "distress":
            st.markdown(
                """
                <div class="dp-warning">
                  <b>Normal payment allocation paused.</b>
                  <span class="dp-muted"> The supplied minimum dues do not fit safely after essential expenses.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        payment_by_id = {item["debt_id"]: item for item in plan["payments"]}

        for ranked in plan["ranking"]:
            payment = payment_by_id.get(ranked["id"], {})
            amount = payment.get("payment", 0)
            evidence = " · ".join(ranked["evidence"])

            amount_html = (
                f'<span class="dp-money">₹{amount:,.0f}</span>'
                if plan["status"] == "safe"
                else '<span class="dp-muted">Allocation paused</span>'
            )

            st.markdown(
                f"""
                <div class="dp-plan-row">
                  <div class="dp-plan-header">
                    <div>
                      <span class="dp-rank">{ranked["rank"]}</span>
                      <b>{html.escape(ranked["name"])}</b>
                    </div>
                    {amount_html}
                  </div>
                  <div class="dp-caption">{html.escape(evidence)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with plan_right:
        st.markdown("**Plan proof**")
        proof = plan["plan_proof"]
        st.caption(f'{proof["passed_count"]}/{proof["total_count"]} checks passed')

        for item in proof["checks"]:
            st.markdown(
                f"""
                <div class="dp-proof-item">
                  <span class="dp-check">✓</span>
                  <div>
                    <b>{html.escape(item["name"])}</b><br>
                    <span class="dp-caption">{html.escape(item["detail"])}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    explanation = st.session_state.explanation
    if explanation:
        st.markdown('<div style="height:.65rem"></div>', unsafe_allow_html=True)
        with st.expander("Explanation"):
            source = explanation["source"]
            model = explanation.get("model", "")
            if model:
                st.caption(f"{source} · {model}")
            else:
                st.caption(source)
            st.write(explanation["text"])

    # ---------------- Step 3: Income shock ----------------
    st.markdown("---")
    st.markdown('<div class="dp-section-title">3 · Income shock</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dp-section-note">Rebuild the same month at a lower income.</div>',
        unsafe_allow_html=True,
    )

    base_profile = deepcopy(st.session_state.profile)
    current_income = int(float(base_profile["income"]))
    default_new_income = min(current_income, 16000)

    shock_left, shock_mid, shock_right = st.columns([1.2, .7, 1.8], gap="large")

    with shock_left:
        new_income = st.slider(
            "New monthly income (₹)",
            min_value=0,
            max_value=max(30000, current_income),
            value=default_new_income,
            step=500,
        )

    with shock_mid:
        st.metric(
            "Change",
            f"₹{new_income - current_income:,.0f}",
        )
        rebuild_clicked = st.button(
            "Rebuild plan",
            type="primary",
            use_container_width=True,
        )

    if rebuild_clicked:
        try:
            rebuilt = rebuild_plan(base_profile, new_income)
            st.session_state.rebuild = rebuilt
            st.session_state.rebuild_explanation = explain_plan(rebuilt["after"])
            st.rerun()
        except PlanError as exc:
            st.error(str(exc))

    rebuild = st.session_state.rebuild

    with shock_right:
        if rebuild is not None:
            before = rebuild["before"]
            after = rebuild["after"]

            status_color = "#22c55e" if after["status"] == "safe" else "#ef4444"
            st.markdown(
                f"""
                <div class="dp-card">
                  <div class="dp-caption">Status</div>
                  <div style="font-size:1.15rem;font-weight:800;color:{status_color};">
                    {before["status"].upper()} → {after["status"].upper()}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if rebuild is not None:
        before = rebuild["before"]
        after = rebuild["after"]

        st.markdown("**What changed**")
        wc_cols = st.columns(4)
        for col, row in zip(wc_cols, rebuild["what_changed"]["rows"]):
            with col:
                st.metric(
                    row["label"],
                    f"₹{row['after']:,.0f}",
                    delta=f"₹{row['change']:,.0f}",
                )

        if after["status"] == "distress":
            extra_line = ""
            if after["distress"]["essential_gap"] > 0:
                extra_line = (
                    f" Essential-expense gap: ₹{after['distress']['essential_gap']:,.0f}."
                )

            st.markdown(
                f"""
                <div class="dp-distress">
                  <span class="dp-status-title">⚠ Financial distress mode</span><br>
                  <span class="dp-muted">
                    Minimum-payment shortfall: ₹{after["distress"]["payment_shortfall"]:,.0f}.
                    {html.escape(extra_line)}
                    Normal payment optimisation is paused.
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("**Support**")
            support_financial, support_wellbeing = st.columns([1.15, .85], gap="large")

            with support_financial:
                st.caption("Financial / consumer support")
                for resource in get_financial_support_resources():
                    alt = (
                        f" · {resource['alternate_phone']}"
                        if resource.get("alternate_phone")
                        else ""
                    )
                    st.markdown(
                        f"""
                        <div class="dp-support">
                          <b>{html.escape(resource["name"])}</b>
                          <div class="dp-phone">{html.escape(resource["phone"])}{html.escape(alt)}</div>
                          <div class="dp-caption">
                            {html.escape(resource["category"])} · {html.escape(resource["availability"])}
                          </div>
                          <div class="dp-muted" style="margin-top:.45rem;font-size:.82rem;">
                            {html.escape(resource["description"])}
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.link_button(
                        f'Official source',
                        resource["source_url"],
                        use_container_width=True,
                    )

            with support_wellbeing:
                wellbeing = get_wellbeing_support()
                st.caption("If stress is affecting wellbeing")
                st.markdown(
                    f"""
                    <div class="dp-support">
                      <b>{html.escape(wellbeing["name"])}</b>
                      <div class="dp-phone">{html.escape(wellbeing["phone"])}</div>
                      <div class="dp-caption">
                        {html.escape(wellbeing["availability"])} · {html.escape(wellbeing["category"])}
                      </div>
                      <div class="dp-muted" style="margin-top:.45rem;font-size:.82rem;">
                        {html.escape(wellbeing["description"])}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.link_button(
                    "Official source",
                    wellbeing["source_url"],
                    use_container_width=True,
                )

            if st.session_state.rebuild_explanation:
                with st.expander("Rebuilt-plan explanation"):
                    info = st.session_state.rebuild_explanation
                    if info.get("model"):
                        st.caption(f'{info["source"]} · {info["model"]}')
                    else:
                        st.caption(info["source"])
                    st.write(info["text"])

        else:
            st.markdown(
                """
                <div class="dp-safe">
                  <span class="dp-status-title">✓ Rebuilt plan remains feasible</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


st.markdown(
    """
    <div class="dp-footer">
      Advisory planning only · Uses user-supplied financial data · No payment collection
    </div>
    """,
    unsafe_allow_html=True,
)
