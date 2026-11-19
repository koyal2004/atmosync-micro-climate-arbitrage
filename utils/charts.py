"""
AtmoSync - Interactive Data Visualizations & Mapping Suite
Plotly Express, Plotly Graph Objects, and PyDeck chart builders.
"""

import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from config.settings import COLORS

# Default Plotly Theme styling
THEME_LAYOUT = {
    "font": {"family": "Inter, sans-serif", "color": "#0F172A", "size": 12},
    "paper_bgcolor": "#FFFFFF",
    "plot_bgcolor": "#F8FAFC",
    "margin": {"l": 40, "r": 25, "t": 35, "b": 40},
    "hoverlabel": {"bgcolor": "#10243A", "font_size": 12, "font_color": "#FFFFFF"},
    "xaxis": {"showgrid": True, "gridcolor": "#E2E8F0", "linecolor": "#CBD5E1"},
    "yaxis": {"showgrid": True, "gridcolor": "#E2E8F0", "linecolor": "#CBD5E1"},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1}
}

def create_donut_chart(df: pd.DataFrame, names_col: str, values_col: Optional[str] = None, 
                        title: str = "", color_map: Optional[Dict[str, str]] = None) -> go.Figure:
    """Create a Bloomberg-style sleek donut chart."""
    if values_col:
        data_s = df.groupby(names_col)[values_col].sum()
    else:
        data_s = df[names_col].value_counts()

    labels = data_s.index.tolist()
    vals = data_s.values.tolist()

    colors = [color_map.get(lbl, COLORS["secondary"]) if color_map else None for lbl in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=vals,
        hole=0.55,
        marker={"colors": colors} if all(colors) else {},
        textinfo="percent+label",
        hoverinfo="label+value+percent",
        textposition="outside"
    )])
    fig.update_layout(title_text=title, **THEME_LAYOUT)
    return fig

def create_line_chart(df: pd.DataFrame, x_col: str, y_col: str, color_col: Optional[str] = None, 
                      title: str = "", y_title: str = "") -> go.Figure:
    """Line chart with markers."""
    fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title,
                  color_discrete_sequence=[COLORS["secondary"], COLORS["info"], COLORS["warning"], COLORS["critical"]])
    fig.update_layout(**THEME_LAYOUT)
    if y_title:
        fig.update_layout(yaxis_title=y_title)
    return fig

def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, color_col: Optional[str] = None, 
                     orientation: str = "v", title: str = "", color_map: Optional[Dict[str, str]] = None) -> go.Figure:
    """Create styled bar chart."""
    fig = px.bar(df, x=x_col, y=y_col, color=color_col, orientation=orientation, title=title,
                 color_discrete_map=color_map,
                 color_discrete_sequence=[COLORS["primary"], COLORS["secondary"], COLORS["info"]])
    fig.update_layout(**THEME_LAYOUT)
    return fig

def create_dual_axis_chart(df: pd.DataFrame, x_col: str, y1_col: str, y2_col: str,
                           y1_name: str, y2_name: str, title: str) -> go.Figure:
    """Dual axis line chart for Temperature vs Humidity."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df[y1_col], name=y1_name,
        line={"color": COLORS["critical"], "width": 2}
    ))
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df[y2_col], name=y2_name, yaxis="y2",
        line={"color": COLORS["secondary"], "width": 2, "dash": "dot"}
    ))
    fig.update_layout(
        title=title,
        yaxis={"title": y1_name, "title_font": {"color": COLORS["critical"]}},
        yaxis2={"title": y2_name, "title_font": {"color": COLORS["secondary"]}, "overlaying": "y", "side": "right"},
        **THEME_LAYOUT
    )
    return fig

def create_scatter_plot(df: pd.DataFrame, x_col: str, y_col: str, color_col: Optional[str] = None,
                        size_col: Optional[str] = None, title: str = "") -> go.Figure:
    """Scatter plot for environmental multi-variate analysis."""
    fig = px.scatter(df, x=x_col, y=y_col, color=color_col, size=size_col, title=title,
                     color_discrete_sequence=[COLORS["secondary"], COLORS["critical"], COLORS["info"]])
    fig.update_layout(**THEME_LAYOUT)
    return fig

def create_waterfall_chart(components: Dict[str, float], title: str = "Arbitrage Margin Waterfall (₹)") -> go.Figure:
    """Waterfall chart explaining revenue breakdown, logistics cost, and net arbitrage gain."""
    measures = []
    x_labels = list(components.keys())
    y_vals = list(components.values())

    for i, (k, v) in enumerate(components.items()):
        if i == 0:
            measures.append("absolute")
        elif i == len(components) - 1:
            measures.append("total")
        else:
            measures.append("relative")

    fig = go.Figure(go.Waterfall(
        name="Arbitrage Breakdown",
        orientation="v",
        measure=measures,
        x=x_labels,
        textposition="outside",
        text=[f"₹{abs(v):,.0f}" for v in y_vals],
        y=y_vals,
        connector={"line": {"color": "#94A3B8"}},
        decreasing={"marker": {"color": COLORS["critical"]}},
        increasing={"marker": {"color": COLORS["success"]}},
        totals={"marker": {"color": COLORS["primary"]}}
    ))
    fig.update_layout(title=title, **THEME_LAYOUT)
    return fig

def create_pydeck_route_map(
    source_lat: float, source_lon: float,
    dest_lat: float, dest_lon: float,
    source_name: str, dest_name: str,
    alt_lat: Optional[float] = None, alt_lon: Optional[float] = None,
    alt_name: Optional[str] = None
) -> pdk.Deck:
    """Generates PyDeck Arc and Scatterplot Map connecting transit hubs."""
    nodes = [
        {"name": f"Source: {source_name}", "lat": source_lat, "lon": source_lon, "color": [16, 36, 58, 220], "radius": 14000},
        {"name": f"Destination: {dest_name}", "lat": dest_lat, "lon": dest_lon, "color": [220, 38, 38, 220], "radius": 14000}
    ]
    arcs = [
        {
            "from_name": source_name, "to_name": dest_name,
            "from_lat": source_lat, "from_lon": source_lon,
            "to_lat": dest_lat, "to_lon": dest_lon,
            "color": [18, 184, 166, 200]
        }
    ]

    if alt_lat and alt_lon:
        nodes.append({
            "name": f"Alternative: {alt_name}", "lat": alt_lat, "lon": alt_lon,
            "color": [22, 163, 74, 220], "radius": 16000
        })
        arcs.append({
            "from_name": dest_name, "to_name": alt_name,
            "from_lat": dest_lat, "from_lon": dest_lon,
            "to_lat": alt_lat, "to_lon": alt_lon,
            "color": [22, 163, 74, 230]
        })

    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame(nodes),
        get_position=["lon", "lat"],
        get_color="color",
        get_radius="radius",
        pickable=True
    )

    arc_layer = pdk.Layer(
        "ArcLayer",
        data=pd.DataFrame(arcs),
        get_source_position=["from_lon", "from_lat"],
        get_target_position=["to_lon", "to_lat"],
        get_source_color="color",
        get_target_color="color",
        get_width=4,
        pickable=True
    )

    mid_lat = (source_lat + dest_lat) / 2.0
    mid_lon = (source_lon + dest_lon) / 2.0

    view_state = pdk.ViewState(
        latitude=mid_lat,
        longitude=mid_lon,
        zoom=5.0,
        pitch=35
    )

    return pdk.Deck(
        layers=[arc_layer, scatter_layer],
        initial_view_state=view_state,
        tooltip={"text": "{name}"},
        map_style="mapbox://styles/mapbox/light-v10"
    )

def create_state_market_map(markets_df: pd.DataFrame) -> go.Figure:
    """State-wise market geographical distribution bubble chart."""
    fig = px.scatter_geo(
        markets_df,
        lat="latitude",
        lon="longitude",
        hover_name="market_name",
        size="estimated_daily_capacity",
        color="state",
        scope="asia",
        title="Indian Agricultural Trading Hubs & Mandis"
    )
    fig.update_geos(
        center={"lat": 20.5937, "lon": 78.9629},
        projection_scale=3.8,
        showland=True, landcolor="#F8FAFC",
        showcountries=True, countrycolor="#CBD5E1"
    )
    fig.update_layout(margin={"l": 0, "r": 0, "t": 35, "b": 0}, paper_bgcolor="#FFFFFF")
    return fig
