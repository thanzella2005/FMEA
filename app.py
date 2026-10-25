"""FMEA & Defect Pareto Analyzer.

Run locally:  streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import fmea_charts as ch
import fmea_logic as fl

ROOT = Path(__file__).parent
SAMPLE_DEFECTS = ROOT / "sample_data" / "sample_defects.csv"
SAMPLE_FMEA = ROOT / "sample_data" / "sample_fmea.csv"

st.set_page_config(page_title="FMEA & Pareto Analyzer", layout="wide")

# Streamlit renamed use_container_width to width="stretch" in 1.50; support both.
_ver = tuple(int(p) for p in st.__version__.split(".")[:2] if p.isdigit())
STRETCH = {"width": "stretch"} if _ver >= (1, 50) else {"use_container_width": True}

BAND_CSS = {
    "High": "background-color:#f8d7da;color:#842029",
    "Medium": "background-color:#fff3cd;color:#664d03",
    "Low": "background-color:#d1e7dd;color:#0f5132",
}


# ------------------------------------------------------------------ session state
def set_fmea(df: pd.DataFrame) -> None:
    """Replace the worksheet. Bumping the version gives the editor a fresh key so it shows the new rows."""
    df = fl.normalize_fmea(df)
    st.session_state["fmea_base"] = df
    st.session_state["fmea"] = df
    st.session_state["fmea_ver"] += 1


if "fmea" not in st.session_state:
    _empty = fl.normalize_fmea(pd.DataFrame(columns=fl.FMEA_COLS))
    st.session_state["fmea"] = _empty  # latest edited worksheet, used by every tab
    st.session_state["fmea_base"] = _empty  # what the editor was last loaded with
    st.session_state["fmea_ver"] = 0


def load_sample_fmea() -> None:
    set_fmea(pd.read_csv(SAMPLE_FMEA))


def clear_fmea() -> None:
    set_fmea(pd.DataFrame(columns=fl.FMEA_COLS))


def add_vital_few(modes: list[str]) -> None:
    current = st.session_state["fmea"]
    have = set(current["Failure Mode"].str.strip().str.lower())
    rows = [
        {"Failure Mode": m, "Sev": 5, "Occ": 5, "Det": 5}
        for m in modes
        if m.strip().lower() not in have
    ]
    if not rows:
        st.toast("Those defects are already in the FMEA worksheet.")
        return
    new = pd.DataFrame(rows)
    set_fmea(new if current.empty else pd.concat([current, new], ignore_index=True))
    st.toast(f"Added {len(rows)} row(s) with placeholder scores of 5. Edit them on the FMEA tab.")


def style_results(df: pd.DataFrame, hi: float, med: float):
    def band_rpn(v):
        return BAND_CSS.get(fl.risk_band(v, hi, med), "")

    return (
        df.style.map(band_rpn, subset=["RPN", "New RPN"])
        .map(lambda name: BAND_CSS.get(name, ""), subset=["Risk"])
        .format({"RPN": "{:.0f}", "New RPN": "{:.0f}", "Reduction %": "{:.0f}%"}, na_rep="–")
    )


def score_col(label: str, help_text: str):
    return st.column_config.NumberColumn(label, help=help_text, min_value=1, max_value=10, step=1, format="%d")


FMEA_CONFIG = {
    "Failure Mode": st.column_config.TextColumn("Failure Mode", width="medium"),
    "Effect": st.column_config.TextColumn("Effect", width="medium"),
    "Cause": st.column_config.TextColumn("Cause", width="medium"),
    "Current Controls": st.column_config.TextColumn("Current Controls", width="medium"),
    "Sev": score_col("Sev", "Severity of the effect: 1 = negligible, 10 = hazardous"),
    "Occ": score_col("Occ", "Occurrence: 1 = very unlikely, 10 = almost certain"),
    "Det": score_col("Det", "Detection: 1 = almost certain to be caught, 10 = cannot be detected"),
    "Recommended Action": st.column_config.TextColumn("Recommended Action", width="medium"),
    "Owner": st.column_config.TextColumn("Owner"),
    "New Sev": score_col("New Sev", "Severity after the action (leave blank if unchanged)"),
    "New Occ": score_col("New Occ", "Occurrence after the action (leave blank if unchanged)"),
    "New Det": score_col("New Det", "Detection after the action (leave blank if unchanged)"),
}

# ------------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Settings")
    hi = st.number_input("High risk when RPN is at least", min_value=1, max_value=1000, value=150, step=10)
    med = st.number_input("Medium risk when RPN is at least", min_value=1, max_value=1000, value=100, step=10)
    med = min(med, hi)
    st.divider()
    st.caption(
        "**RPN = Severity × Occurrence × Detection**, each scored 1–10. "
        "Pareto charts show which defects matter by frequency; the FMEA shows which matter by risk."
    )

st.title("FMEA & Defect Pareto Analyzer")

# Shared values, filled in by the tabs below (tabs run top to bottom on every rerun).
defects = pd.DataFrame(columns=["defect_type", "count"])
agg = fl.aggregate_defects(defects)
cutoff = 80
calc = fl.compute_rpn(st.session_state["fmea"], hi, med)

tab_pareto, tab_fmea, tab_impact, tab_export = st.tabs(
    ["1 · Pareto", "2 · FMEA worksheet", "3 · Impact", "4 · Export"]
)

# ------------------------------------------------------------------------- Pareto
with tab_pareto:
    st.subheader("Defect Pareto")
    source = st.radio("Data source", ["Sample data", "Upload CSV", "Manual entry"], horizontal=True)

    raw = None
    try:
        if source == "Sample data":
            raw = fl.clean_defects(pd.read_csv(SAMPLE_DEFECTS))
            st.caption(
                "Synthetic sample data (12 weeks of defects on a fabricated-steel line) so you can try the app. "
                "Switch to Upload CSV to use your own."
            )
        elif source == "Upload CSV":
            uploaded = st.file_uploader("CSV with columns: defect_type, count (optional: date)", type="csv")
            if uploaded is not None:
                raw = fl.clean_defects(pd.read_csv(uploaded))
        else:
            blank = pd.DataFrame(
                {"defect_type": pd.Series(dtype="object"), "count": pd.Series(dtype="float64")}
            )
            typed = st.data_editor(
                blank, num_rows="dynamic", hide_index=True, key="manual_defects", **STRETCH
            )
            raw = fl.clean_defects(typed)
    except Exception as exc:  # bad file, missing columns, ...
        st.error(f"Could not read the data: {exc}")

    if raw is None or raw.empty:
        st.info("Add defect data to see the Pareto chart.")
    else:
        if "date" in raw.columns and raw["date"].notna().any():
            first_day, last_day = raw["date"].min().date(), raw["date"].max().date()
            span = st.date_input("Date range", (first_day, last_day), min_value=first_day, max_value=last_day)
            if isinstance(span, (tuple, list)) and len(span) == 2:
                start = pd.Timestamp(span[0])
                end = pd.Timestamp(span[1]) + pd.Timedelta(days=1)
                raw = raw[raw["date"].between(start, end, inclusive="left") | raw["date"].isna()]

        defects = raw
        agg = fl.aggregate_defects(defects)
        cutoff = st.slider("Vital-few cutoff (% of all defects)", 50, 95, 80, step=5)
        table = fl.pareto_table(agg["defect_type"], agg["count"], cutoff)
        vital = table[table["vital_few"]]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total defects", f"{table['value'].sum():,.0f}")
        m2.metric("Defect types", len(table))
        m3.metric("Vital few", f"{len(vital)} of {len(table)}")
        m4.metric("Share they cover", f"{vital['share_%'].sum():.0f}%")

        st.plotly_chart(ch.pareto_figure(table, "Defect count", cutoff), key="pareto_defects", **STRETCH)
        st.caption("Red bars are the vital few: fixing these removes most of the defects.")

        st.button(
            f"Add the {len(vital)} vital-few defects to the FMEA worksheet",
            on_click=add_vital_few,
            args=(vital["label"].tolist(),),
        )

        with st.expander("Pareto table"):
            shown = table.rename(
                columns={
                    "label": "Defect",
                    "value": "Count",
                    "share_%": "Share %",
                    "cum_%": "Cumulative %",
                    "vital_few": "Vital few",
                }
            ).round({"Share %": 1, "Cumulative %": 1})
            st.dataframe(shown, hide_index=True, **STRETCH)

        if "date" in defects.columns and defects["date"].notna().any():
            with st.expander("Trend over time"):
                st.plotly_chart(ch.trend_figure(defects), key="trend_defects", **STRETCH)

# --------------------------------------------------------------------------- FMEA
with tab_fmea:
    st.subheader("FMEA worksheet")
    st.caption(
        "Score Severity (Sev), Occurrence (Occ) and Detection (Det) from 1 to 10. "
        "Fill in the action columns to see the improvement on the Impact tab; "
        "a blank New score means that score does not change."
    )
    b1, b2, _spacer = st.columns([1, 1, 3])
    b1.button("Load sample FMEA", on_click=load_sample_fmea)
    b2.button("Clear worksheet", on_click=clear_fmea)

    with st.expander("Import an FMEA from CSV"):
        fmea_file = st.file_uploader(
            "A CSV exported from this app, or one with the same column names", type="csv", key="fmea_upload"
        )
        if fmea_file is not None and st.button("Replace the worksheet with this file"):
            imported = False
            try:
                set_fmea(pd.read_csv(fmea_file))
                imported = True
            except Exception as exc:
                st.error(f"Could not import that file: {exc}")
            if imported:
                st.rerun()

    base = st.session_state["fmea_base"]
    edited = st.data_editor(
        base,
        key=f"fmea_editor_{st.session_state['fmea_ver']}",
        num_rows="dynamic",
        hide_index=True,
        column_config=FMEA_CONFIG,
        **STRETCH,
    )
    working = fl.clean_fmea(fl.normalize_fmea(fl.merge_edit(edited, base)))
    st.session_state["fmea"] = working
    calc = fl.compute_rpn(working, hi, med)

    scored = calc.dropna(subset=["RPN"])
    if scored.empty:
        st.info(
            "No scored rows yet. Click Load sample FMEA, add the vital-few defects from the Pareto tab, "
            "or type a row above (a failure mode plus Sev, Occ and Det)."
        )
    else:
        st.markdown("##### Calculated risk (highest RPN first)")
        results = calc.sort_values("RPN", ascending=False, na_position="last")[fl.RESULT_COLS]
        st.dataframe(style_results(results.reset_index(drop=True), hi, med), hide_index=True, **STRETCH)
        st.caption(f"Risk bands: High ≥ {hi}, Medium ≥ {med}, otherwise Low. Change them in the sidebar.")

# ------------------------------------------------------------------------- Impact
with tab_impact:
    st.subheader("Impact of the recommended actions")
    stats = fl.summary_stats(calc, hi)
    if stats is None:
        st.info("Score some failure modes on the FMEA tab first (or click Load sample FMEA).")
    else:
        scored = calc.dropna(subset=["RPN"])
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total RPN before", f"{stats['before']:,.0f}")
        k2.metric(
            "Total RPN after",
            f"{stats['after']:,.0f}",
            f"-{stats['reduction_pct']:.0f}%" if stats["reduction_pct"] >= 0.5 else None,
            delta_color="inverse",
        )
        k3.metric("High-risk failure modes", f"{stats['high_before']} → {stats['high_after']}")
        k4.metric(f"Top {stats['n_top']} share of RPN", f"{stats['top_share_pct']:.0f}%")

        st.caption("Summary line (use the copy button):")
        st.code(fl.headline(stats), language=None)

        left, right = st.columns(2)
        with left:
            st.markdown("##### RPN Pareto")
            rpn_table = fl.pareto_table(scored["Failure Mode"], scored["RPN"], 80)
            st.plotly_chart(ch.pareto_figure(rpn_table, "RPN", 80), key="pareto_rpn", **STRETCH)
        with right:
            st.markdown("##### RPN before vs after actions")
            st.plotly_chart(ch.before_after_figure(scored), key="before_after", **STRETCH)

        st.markdown("##### Frequency vs risk")
        if agg.empty:
            st.caption("Add defect data on the Pareto tab to compare how often a defect occurs with how risky it is.")
        else:
            merged = fl.freq_vs_risk(agg, calc)
            if merged.empty:
                st.caption(
                    "No failure mode matches a defect name. Use the same names in both places "
                    "(the button on the Pareto tab copies them across)."
                )
            else:
                st.plotly_chart(ch.freq_risk_figure(merged, hi, med), key="freq_risk", **STRETCH)
                most_often = merged.loc[merged["count"].idxmax()]
                riskiest = merged.loc[merged["RPN"].idxmax()]
                if most_often["Failure Mode"] != riskiest["Failure Mode"]:
                    st.caption(
                        f"The most frequent defect is {most_often['Failure Mode']} "
                        f"(RPN {most_often['RPN']:.0f}), but the riskiest is {riskiest['Failure Mode']} "
                        f"(RPN {riskiest['RPN']:.0f}, only {riskiest['Share of defects %']:.1f}% of defects). "
                        "Fixing the most frequent defect first would not address the biggest risk."
                    )

# ------------------------------------------------------------------------- Export
with tab_export:
    st.subheader("Export")
    st.write("The Excel report has four sheets: Summary, Defects, Pareto and FMEA (RPN cells colour-coded).")
    try:
        report = fl.build_excel(defects, agg, calc, hi, med, cutoff)
        st.download_button(
            "Download Excel report",
            report,
            file_name="fmea_pareto_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as exc:
        st.error(f"Could not build the Excel report: {exc}")
    st.download_button(
        "Download FMEA worksheet (CSV, can be re-imported)",
        fl.fmea_to_csv(st.session_state["fmea"]),
        file_name="fmea_worksheet.csv",
        mime="text/csv",
    )
