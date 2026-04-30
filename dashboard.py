#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 22 09:02:57 2024

@author: and
"""

import os
import re
import time

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from cachelib import SimpleCache
from dash import Input, Output, State, dcc, html, no_update
from dash_extensions.enrich import (
    DashProxy,
    Serverside,
    ServersideBackend,
    ServersideOutputTransform,
)
from plotly.subplots import make_subplots
from plotly_resampler import FigureResampler

# %%
datapath = "data"
mar = 10  # margin

# Graph IDs for resampled figures
RESAMPLED_GRAPH_IDS = [
    "graph-heat-power",
    "graph-heating-temps",
    "graph-hotwater-temps",
    "graph-ambient-temps",
    "graph-defrost",
]

# %% plot functions


def plot_temperatures(df, prefix):
    fig = FigureResampler(go.Figure())

    for colname in [x for x in df.columns if x.startswith(prefix)]:
        fig.add_trace(
            go.Scattergl(
                hovertemplate=" %{y:2.2f}°C",
                name=colname,
            ),
            hf_x=df.index,
            hf_y=df.loc[:, colname],
        )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=mar, r=mar, t=mar, b=mar),
    )
    fig.update_yaxes(automargin="left+top")

    return fig


def plot_heat_power(df):
    fig = FigureResampler(go.Figure())

    colors = {
        "Leistung Heizen": "Blue",
        "Leistung Warmwasser": "Green",
        "Leistung Abtauen": "Red",
        "Leistungsaufnahme": "Black",
    }

    df["Leistung Heizen"] = df["Heizleistung Ist"].where(
        df["Betriebszustand"] == "Heizen", 0
    )
    df["Leistung Warmwasser"] = df["Heizleistung Ist"].where(
        df["Betriebszustand"] == "WW", 0
    )
    for colname in [
        "Leistung Heizen",
        "Leistung Warmwasser",
        "Leistung Abtauen",
        "Leistungsaufnahme",
    ]:
        if colname in df.columns:
            fig.add_trace(
                go.Scattergl(
                    line=dict(color=colors[colname], width=1),
                    fill="tozeroy",
                    hovertemplate=" %{y:2.2f}kW",
                    name=colname,
                ),
                hf_x=df.index,
                hf_y=df.loc[:, colname],
            )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=mar, r=mar, t=mar, b=mar),
    )
    fig.update_yaxes(automargin="left+top")
    return fig


def plot_defrost(df):
    fig = FigureResampler(go.Figure())

    for colname in ["Abtaubedarf"]:
        fig.add_trace(
            go.Scattergl(
                hovertemplate=" %{y:2.2f}%",
                name=colname,
            ),
            hf_x=df.index,
            hf_y=df.loc[:, colname],
        )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=mar, r=mar, t=mar, b=mar),
    )
    fig.update_yaxes(automargin="left+top")
    return fig


def plot_flow(df):
    fig = FigureResampler(go.Figure())

    for colname in ["Durchfluss"]:
        fig.add_trace(
            go.Scattergl(
                hovertemplate=" %{y:2.2f}%",
                name=colname,
            ),
            hf_x=df.index,
            hf_y=df.loc[:, colname],
        )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=mar, r=mar, t=mar, b=mar),
    )
    fig.update_yaxes(automargin="left+top")
    return fig


def plot_energies(data_df):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for i, colname in enumerate(["Eingesetzte Energie_Heizung", "Wärmemenge_Heizung"]):
        fig.add_trace(
            go.Bar(
                x=data_df.index,
                y=data_df.loc[:, colname],
                offsetgroup=i,
                hovertemplate=" %{y:2.2f} kWh",
                name=colname,
            )
        )
    for i, (colname, color) in enumerate(
        zip(
            ["Eingesetzte Energie_Warmwasser", "Wärmemenge_Warmwasser"],
            ["maroon", "darkblue"],
        )
    ):
        fig.add_trace(
            go.Bar(
                x=data_df.index,
                y=data_df.loc[:, colname],
                marker=dict(color=color),
                offsetgroup=i,
                hovertemplate=" %{y:2.2f} kWh",
                name=colname,
            )
        )
    colors = {
        "COP_Heizung": "Green",
        "COP_Warmwasser": "darkgreen",
    }
    for colname in ["COP_Heizung", "COP_Warmwasser"]:
        fig.add_trace(
            go.Scatter(
                x=data_df.index,
                y=data_df.loc[:, colname],
                mode="markers",
                marker=dict(
                    color=colors[colname], size=20, line=dict(color="Yellow", width=2)
                ),
                hovertemplate=" %{y:2.2f} X",
                name=colname,
            ),
            secondary_y=True,
        )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=mar, r=mar, t=mar, b=mar),
    )
    fig.update_yaxes(automargin="left+top")
    return fig


# %% Layout


def sidebar_content():
    day_regex = re.compile(r"log_(.*).csv(?:.gz)?")
    days = [m.group(1) for f in os.scandir(datapath) if (m := day_regex.match(f.name))]
    days = sorted(days)
    content = html.Div(
        children=[
            dcc.Dropdown(
                days,
                days[-1],
                id="day_dropdown",
            ),
            html.Div(id="sidebar_content"),
        ]
    )

    return content


def construct_layout():
    print("constructing layout")
    store_components = [
        dcc.Store(id=gid.replace("graph-", "store-")) for gid in RESAMPLED_GRAPH_IDS
    ]
    layout = html.Div(
        [
            dbc.Row(html.Div(html.H1("Heatpump Dashboard"))),
            dbc.Row(
                [
                    dbc.Col(
                        sidebar_content(),
                        width=2,
                        style={
                            "background-color": "#ADD8E6",
                        },
                    ),
                    dbc.Col(
                        dcc.Loading(
                            [
                                html.H4("Heat Output"),
                                dcc.Graph(id="graph-heat-power"),
                                html.H4("Heating temperatures"),
                                dcc.Graph(
                                    id="graph-heating-temps", style={"height": "50vh"}
                                ),
                                html.H4("Hot water temperatures"),
                                dcc.Graph(
                                    id="graph-hotwater-temps", style={"height": "50vh"}
                                ),
                                html.H4("Ambient temperature"),
                                dcc.Graph(
                                    id="graph-ambient-temps", style={"height": "50vh"}
                                ),
                                html.H4("Defreezing share"),
                                dcc.Graph(id="graph-defrost"),
                                html.H4("Energy input/output"),
                                dcc.Graph(
                                    id="graph-energies", style={"height": "50vh"}
                                ),
                            ]
                        )
                    ),
                ]
            ),
            dcc.Interval(id="interval-component", interval=60 * 1000, n_intervals=0),
            *store_components,
        ]
    )

    return layout


# %% App setup


class MemoryBackend(SimpleCache, ServersideBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, key, ignore_expired=False):
        if key is None:
            return None
        return super().get(key)


serverside_cache = MemoryBackend(default_timeout=30 * 60)

app = DashProxy(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    transforms=[ServersideOutputTransform(backends=[serverside_cache])],
)
app.layout = construct_layout

# %% Content


@app.callback(
    output=[
        Output("graph-heat-power", "figure"),
        Output("store-heat-power", "data"),
        Output("graph-heating-temps", "figure"),
        Output("store-heating-temps", "data"),
        Output("graph-hotwater-temps", "figure"),
        Output("store-hotwater-temps", "data"),
        Output("graph-ambient-temps", "figure"),
        Output("store-ambient-temps", "data"),
        Output("graph-defrost", "figure"),
        Output("store-defrost", "data"),
        Output("graph-energies", "figure"),
        Output("sidebar_content", "children"),
    ],
    inputs=[
        Input("day_dropdown", "value"),
    ],
)
def update_content(day_dropdown):
    # load data
    filepath = os.path.join(datapath, "log_" + day_dropdown + ".csv")
    if not os.path.exists(filepath):
        filepath += ".gz"
    print(filepath)
    tt = time.time()
    df = pd.read_csv(
        filepath,
        index_col=0,
    )
    print(f"File loaded in {time.time() - tt}s")

    tt = time.time()

    today = pd.Timestamp.now().floor("d")
    data_date = pd.to_datetime(day_dropdown, format="%y-%m-%d")

    delta_time = today - data_date

    df.index = pd.DatetimeIndex(df.index) - delta_time
    # df = df.resample('1min').first()
    print(f"Data processed in {time.time() - tt}s")

    data_df = (
        df[
            [
                "Eingesetzte Energie_Heizung",
                "Wärmemenge_Heizung",
                "Wärmemenge_Warmwasser",
                "Eingesetzte Energie_Warmwasser",
            ]
        ]
        .resample("60min")
        .first()
        .diff()
    )

    data_df["COP_Heizung"] = (
        data_df["Wärmemenge_Heizung"] / data_df["Eingesetzte Energie_Heizung"]
    )
    data_df["COP_Warmwasser"] = (
        data_df["Wärmemenge_Warmwasser"] / data_df["Eingesetzte Energie_Warmwasser"]
    )

    # Build resampled figures
    fig_heat_power = plot_heat_power(df)
    fig_heating_temps = plot_temperatures(df, prefix="Th")
    fig_hotwater_temps = plot_temperatures(df, prefix="Tw")
    fig_ambient_temps = plot_temperatures(df, prefix="Ta")
    fig_defrost = plot_defrost(df)
    fig_energies = plot_energies(data_df)

    # Sidebar statistics
    total_heat_output = (
        data_df["Wärmemenge_Warmwasser"].sum() + data_df["Wärmemenge_Heizung"].sum()
    )
    total_heating_output = data_df["Wärmemenge_Heizung"].sum()
    total_hotwater_output = data_df["Wärmemenge_Warmwasser"].sum()

    total_heat_input = (
        data_df["Eingesetzte Energie_Warmwasser"].sum()
        + data_df["Eingesetzte Energie_Heizung"].sum()
    )
    total_heating_input = data_df["Eingesetzte Energie_Heizung"].sum()
    total_hotwater_input = data_df["Wärmemenge_Warmwasser"].sum()

    overall_COP = total_heat_output / total_heat_input

    hours_running = (~df["Betriebszustand"].isna()).sum() / 60
    sidebar_content = html.Div(
        children=[
            html.B("Overview :"),
            html.P(f"Time heating: {hours_running:2.2f} h"),
            html.P(f"COP: {overall_COP:2.2f}"),
            html.B("Thermal heat output :"),
            html.P(f"Total output: {total_heat_output:2.2f} kWh"),
            html.P(f"Total heating: {total_heating_output:2.2f} kWh"),
            html.P(f"Total hotwater: {total_hotwater_output:2.2f} kWh"),
            html.B("Electric input :"),
            html.P(f"Total input: {total_heat_input:2.2f} kWh"),
            html.P(f"Total heating: {total_heating_input:2.2f} kWh"),
            html.P(f"Total hotwater: {total_hotwater_input:2.2f} kWh"),
        ]
    )

    return (
        fig_heat_power,
        Serverside(fig_heat_power),
        fig_heating_temps,
        Serverside(fig_heating_temps),
        fig_hotwater_temps,
        Serverside(fig_hotwater_temps),
        fig_ambient_temps,
        Serverside(fig_ambient_temps),
        fig_defrost,
        Serverside(fig_defrost),
        fig_energies,
        sidebar_content,
    )


# Register relayout callbacks for each resampled graph
def _make_relayout_callback(graph_id):
    store_id = graph_id.replace("graph-", "store-")

    @app.callback(
        Output(graph_id, "figure", allow_duplicate=True),
        Input(graph_id, "relayoutData"),
        State(store_id, "data"),
        prevent_initial_call=True,
    )
    def _update_on_relayout(relayoutdata, fig):
        if fig is None:
            return no_update
        return fig.construct_update_data_patch(relayoutdata)

    _update_on_relayout.__name__ = f"relayout_{graph_id}"
    return _update_on_relayout


for _gid in RESAMPLED_GRAPH_IDS:
    _make_relayout_callback(_gid)


@app.callback(
    Output("day_dropdown", "options"),
    Input("interval-component", "n_intervals"),
    prevent_initial_call=True,
)
def update(val):
    days = [f.name[4:-4] for f in os.scandir(datapath)]
    days = sorted(days)
    print("Updating options")
    return days


if __name__ == "__main__":
    app.run(
        debug=False,
        port=8887,
        host="0.0.0.0",
    )
