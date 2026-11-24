"""Plotly figure builders. One measure per chart, one y-axis, thin marks,
recessive grid, hover on every mark. Colours come from config.COLORS."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import config as C

K = C.COLORS
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def _layout(fig: go.Figure, title: str, height: int = 340, y_pct: bool = False) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 15, "color": K["text_primary"]}},
        font={"family": FONT, "size": 12, "color": K["text_secondary"]},
        plot_bgcolor=K["surface"], paper_bgcolor=K["surface"],
        height=height, margin={"l": 8, "r": 24, "t": 48, "b": 8},
        showlegend=False, hoverlabel={"font": {"family": FONT}},
    )
    fig.update_xaxes(showgrid=False, linecolor=K["axis"], tickcolor=K["axis"], ticks="outside")
    fig.update_yaxes(gridcolor=K["grid"], zeroline=False, linecolor=K["axis"],
                     tickformat=".0%" if y_pct else None)
    return fig


def war_line(war: pd.DataFrame) -> go.Figure:
    d = war[war.complete]
    fig = go.Figure(go.Scatter(
        x=d.week_start, y=d.share, mode="lines+markers",
        line={"color": K["series_1"], "width": 2}, marker={"size": 8, "color": K["series_1"],
                                                            "line": {"color": K["surface"], "width": 2}},
        customdata=np.stack([d.active_reviewers, d.installed_base], axis=-1) if len(d) else None,
        hovertemplate="Week of %{x|%d %b}<br><b>%{y:.0%}</b> weekly active reviewers"
                      "<br>%{customdata[0]} of %{customdata[1]} installed users<extra></extra>",
    ))
    fig.add_hline(y=C.NORTH_STAR_TARGET, line={"color": K["muted"], "width": 1, "dash": "dash"},
                  annotation_text=f"Target {C.NORTH_STAR_TARGET:.0%}", annotation_position="top left",
                  annotation_font={"color": K["text_secondary"], "size": 11})
    _layout(fig, "Weekly Active Reviewers (share of installed users, complete weeks)", y_pct=True)
    fig.update_yaxes(rangemode="tozero")
    return fig


def funnel_bars(f: pd.DataFrame) -> go.Figure:
    d = f.iloc[::-1]
    label = [f"{u} ({p:.0%})" for u, p in zip(d.users, d.pct_of_installed)]
    prev = ["—" if np.isnan(x) else f"{x:.0%}" for x in d.pct_of_previous]
    fig = go.Figure(go.Bar(
        y=d.step, x=d.users, orientation="h", marker={"color": K["series_1"], "cornerradius": 4},
        text=label, textposition="outside", textfont={"color": K["text_primary"]}, cliponaxis=False,
        customdata=prev, hovertemplate="%{y}<br><b>%{x} users</b><br>%{customdata} of previous step<extra></extra>",
    ))
    _layout(fig, f"Activation funnel (all steps within {C.ACTIVATION_WINDOW_HOURS}h of install)", height=300)
    fig.update_xaxes(showgrid=True, gridcolor=K["grid"], showticklabels=False, ticks="",
                     range=[0, max(f.users.max(), 1) * 1.25])
    fig.update_yaxes(showgrid=False)
    return fig


def cohort_heatmap(m: pd.DataFrame) -> go.Figure:
    weeks = [c for c in m.columns if isinstance(c, (int, np.integer))]
    z = m[weeks].to_numpy(dtype=float)
    text = [["" if np.isnan(v) else f"{v:.0%}" for v in row] for row in z]
    ylab = [f"{w:%d %b} (n={n})" for w, n in zip(m.install_week, m.activated)]
    scale = [[i / (len(C.SEQUENTIAL_BLUE) - 1), c] for i, c in enumerate(C.SEQUENTIAL_BLUE)]
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"Week {w}" for w in weeks], y=ylab, zmin=0, zmax=1, colorscale=scale,
        text=text, texttemplate="%{text}", xgap=2, ygap=2,
        colorbar={"tickformat": ".0%", "thickness": 10, "outlinewidth": 0},
        hovertemplate="Installed week of %{y}<br>%{x} after install<br><b>%{z:.0%}</b> reviewed<extra></extra>",
    ))
    _layout(fig, "Review retention by install week (activated users)", height=60 + 44 * max(len(m), 3))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


def recall_paired(per_user: pd.DataFrame, means: dict) -> go.Figure:
    fig = go.Figure()
    xs = ["Unflagged topics", "Flagged topics"]
    for uid, r in per_user.iterrows():
        fig.add_trace(go.Scatter(x=xs, y=[r.unflagged, r.flagged], mode="lines+markers",
                                 line={"color": K["axis"], "width": 1}, marker={"size": 6, "color": K["axis"]},
                                 hovertemplate=f"{uid}: %{{y:.0f}} pts<extra></extra>"))
    fig.add_trace(go.Scatter(x=xs, y=[means["unflagged"], means["flagged"]], mode="lines+markers+text",
                             line={"color": K["series_1"], "width": 2},
                             marker={"size": 12, "color": K["series_1"], "line": {"color": K["surface"], "width": 2}},
                             text=[f"{means['unflagged']:.0f}", f"{means['flagged']:.0f}"],
                             textposition=["middle left", "middle right"], textfont={"color": K["text_primary"]},
                             hovertemplate="Average: %{y:.1f} pts<extra></extra>"))
    _layout(fig, "Recall test score per volunteer (grey) and average (blue), out of 100", height=380)
    fig.update_yaxes(range=[-5, 105])
    fig.update_xaxes(range=[-0.4, 1.4])
    return fig


def share_bars(labels, shares, title: str, height: int = 300) -> go.Figure:
    fig = go.Figure(go.Bar(
        y=labels, x=shares, orientation="h", marker={"color": K["series_1"], "cornerradius": 4},
        text=[f"{s:.0%}" for s in shares], textposition="outside", cliponaxis=False,
        textfont={"color": K["text_primary"]}, hovertemplate="%{y}<br><b>%{x:.0%}</b><extra></extra>",
    ))
    _layout(fig, title, height=height)
    fig.update_xaxes(range=[0, 1.1], tickformat=".0%", showgrid=True, gridcolor=K["grid"])
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig
