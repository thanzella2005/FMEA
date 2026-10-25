"""Plotly figures for the FMEA + Pareto analyzer."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

RED, AMBER, GREEN, GREY, BLUE = "#C0392B", "#E0A526", "#2E8B57", "#9AA5B1", "#2F6DB5"
RISK_COLOR = {"High": RED, "Medium": AMBER, "Low": GREEN}

_MARGIN = dict(l=10, r=10, t=30, b=10)


def pareto_figure(table: pd.DataFrame, value_label: str, cutoff: float = 80) -> go.Figure:
    """Bars (vital few in red) plus a cumulative % line and a cutoff line. `table` comes from pareto_table()."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=table["label"],
            y=table["value"],
            marker_color=[RED if v else GREY for v in table["vital_few"]],
            texttemplate="%{y:,.0f}",
            textposition="outside",
            cliponaxis=False,
            name=value_label,
            hovertemplate="%{x}<br>" + value_label + ": %{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=table["label"],
            y=table["cum_%"],
            mode="lines+markers",
            line=dict(color=BLUE, width=2),
            marker=dict(size=7),
            name="Cumulative %",
            hovertemplate="%{x}<br>Cumulative: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=table["label"],
            y=[cutoff] * len(table),
            mode="lines",
            line=dict(color=GREY, dash="dot", width=1.5),
            name=f"{cutoff:g}% cutoff",
            hoverinfo="skip",
        ),
        secondary_y=True,
    )
    fig.update_yaxes(title_text=value_label, rangemode="tozero", secondary_y=False)
    fig.update_yaxes(title_text="Cumulative %", range=[0, 105], ticksuffix="%", showgrid=False, secondary_y=True)
    fig.update_xaxes(tickangle=-30)
    fig.update_layout(height=440, margin=_MARGIN, bargap=0.25, legend=dict(orientation="h", y=1.1, x=0))
    return fig


def before_after_figure(scored: pd.DataFrame) -> go.Figure:
    """Grouped bars of RPN before vs after actions, highest current RPN first."""
    d = scored.sort_values("RPN", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="RPN before", x=d["Failure Mode"], y=d["RPN"], marker_color=RED))
    fig.add_trace(go.Bar(name="RPN after actions", x=d["Failure Mode"], y=d["New RPN"], marker_color=BLUE))
    fig.update_yaxes(title_text="RPN", rangemode="tozero")
    fig.update_xaxes(tickangle=-30)
    fig.update_layout(
        barmode="group", height=440, margin=_MARGIN, legend=dict(orientation="h", y=1.1, x=0)
    )
    return fig


def freq_risk_figure(merged: pd.DataFrame, hi: float, med: float) -> go.Figure:
    """Share of all defects (x) against RPN (y); dots are coloured by risk band."""
    fig = go.Figure(
        go.Scatter(
            x=merged["Share of defects %"],
            y=merged["RPN"],
            mode="markers+text",
            text=merged["Failure Mode"],
            textposition="top center",
            marker=dict(size=14, color=[RISK_COLOR.get(r, GREY) for r in merged["Risk"]]),
            hovertemplate="%{text}<br>Share of defects: %{x:.1f}%<br>RPN: %{y:.0f}<extra></extra>",
        )
    )
    fig.add_hline(y=hi, line_dash="dot", line_color=RED, annotation_text=f"High >= {hi:g}")
    fig.add_hline(y=med, line_dash="dot", line_color=AMBER, annotation_text=f"Medium >= {med:g}")
    fig.update_xaxes(title_text="Share of all defects (%)", rangemode="tozero")
    fig.update_yaxes(title_text="RPN", range=[0, max(float(merged["RPN"].max()), float(hi)) * 1.2])
    fig.update_layout(height=460, margin=_MARGIN, showlegend=False)
    return fig


def trend_figure(defects: pd.DataFrame) -> go.Figure:
    """Weekly defect totals."""
    weekly = defects.dropna(subset=["date"]).set_index("date")["count"].resample("W").sum().reset_index()
    fig = go.Figure(
        go.Scatter(x=weekly["date"], y=weekly["count"], mode="lines+markers", line=dict(color=BLUE, width=2))
    )
    fig.update_yaxes(title_text="Defects per week", rangemode="tozero")
    fig.update_layout(height=320, margin=_MARGIN)
    return fig
