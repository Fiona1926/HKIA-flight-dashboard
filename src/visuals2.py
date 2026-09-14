import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import date

# --------------------------------------------------------------------
# PAGE CONFIG (must be the very first Streamlit call)
# --------------------------------------------------------------------
st.set_page_config(
    page_title="HKIA Cargo Flight Dashboard",
    page_icon="✈️",
    layout="wide",
)

# --------------------------------------------------------------------
# COLOR PALETTE (validated categorical/status palette - CVD-safe)
# --------------------------------------------------------------------
COLOR_GOOD = "#0ca30c"        # flown / on-time
COLOR_CRITICAL = "#d03b3b"    # cancelled / bad
COLOR_MUTED = "#898781"       # secondary reference lines
COLOR_ACCENT = "#2a78d6"      # chrome accent - reuses the sequential blue base
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"]
STATUS_COLOR_MAP = {"Cancelled": COLOR_CRITICAL, "Flown": COLOR_GOOD}
TEMPLATE = "plotly_white"

TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
SURFACE_CARD = "#fcfcfb"
BORDER_HAIRLINE = "rgba(11,11,11,0.10)"

CHART_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color=TEXT_SECONDARY,
)

DATA_DIR = "/Users/fionaleong/HKIA_flight_monitor/data"


# --------------------------------------------------------------------
# MARKDOWN/CSS COMPONENTS
# --------------------------------------------------------------------
def inject_css():
    st.markdown(
        f"""
        <style>
        .hero {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem 1rem;
            padding: 1rem 1.25rem;
            background: {SURFACE_CARD};
            border: 1px solid {BORDER_HAIRLINE};
            border-left: 4px solid {COLOR_ACCENT};
            border-radius: 10px;
            margin-bottom: 1rem;
        }}
        .hero-title {{ font-size: 1.6rem; font-weight: 700; color: {TEXT_PRIMARY}; margin: 0; }}
        .hero-subtitle {{ font-size: 0.9rem; color: {TEXT_SECONDARY}; margin: 0.15rem 0 0 0; }}
        .hero-badge {{
            font-size: 0.8rem;
            font-weight: 600;
            color: {COLOR_ACCENT};
            background: rgba(42,120,214,0.10);
            border: 1px solid rgba(42,120,214,0.25);
            border-radius: 999px;
            padding: 0.3rem 0.75rem;
            white-space: nowrap;
        }}
        .stat-card {{
            background: {SURFACE_CARD};
            border: 1px solid {BORDER_HAIRLINE};
            border-left: 4px solid {COLOR_ACCENT};
            border-radius: 10px;
            padding: 0.85rem 1rem;
            height: 100%;
        }}
        .stat-card .stat-label {{
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            text-transform: uppercase;
            color: {TEXT_SECONDARY};
            margin: 0 0 0.3rem 0;
        }}
        .stat-card .stat-value {{
            font-size: 1.7rem;
            font-weight: 700;
            color: {TEXT_PRIMARY};
            margin: 0;
            line-height: 1.1;
        }}
        .stat-card .stat-delta {{
            display: inline-block;
            margin-top: 0.4rem;
            font-size: 0.78rem;
            font-weight: 600;
            border-radius: 999px;
            padding: 0.15rem 0.55rem;
        }}
        .stat-delta.up {{ color: {COLOR_CRITICAL}; background: rgba(208,59,59,0.10); }}
        .stat-delta.down {{ color: {COLOR_GOOD}; background: rgba(12,163,12,0.10); }}
        .badge {{
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 600;
            border-radius: 999px;
            padding: 0.15rem 0.6rem;
        }}
        .badge-good {{ color: {COLOR_GOOD}; background: rgba(12,163,12,0.12); }}
        .badge-critical {{ color: {COLOR_CRITICAL}; background: rgba(208,59,59,0.12); }}
        .accent-rule {{
            border: none;
            height: 3px;
            width: 48px;
            background: {COLOR_ACCENT};
            border-radius: 2px;
            margin: 0 0 0.75rem 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label, value, delta_text=None, delta_kind=None):
    delta_html = f'<div class="stat-delta {delta_kind}">{delta_text}</div>' if delta_text else ""
    st.markdown(
        f"""
        <div class="stat-card">
            <p class="stat-label">{label}</p>
            <p class="stat-value">{value}</p>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_badge(text, kind):
    return f'<span class="badge badge-{kind}">{text}</span>'


def section_header(icon, text):
    st.markdown(f"### {icon} {text}")
    st.markdown('<hr class="accent-rule">', unsafe_allow_html=True)


inject_css()

# --------------------------------------------------------------------
# LOAD + ENRICH DATA
# --------------------------------------------------------------------
@st.cache_data
def load_data():
    df_ports = pd.read_csv(f"{DATA_DIR}/online_ports.csv")
    df = pd.read_csv(f"{DATA_DIR}/HKIA_merged.csv", header=0)
    df = pd.merge(df, df_ports, how="inner", left_on="port", right_on="ports")  # strictly online (CX) ports

    df["status"] = df["status"].fillna("")
    df["is_cancelled"] = (df["status"].str.strip() == "Cancelled").astype(int)
    df["date"] = pd.to_datetime(df["date"])

    return df


df = load_data()

# --------------------------------------------------------------------
# SIDEBAR FILTERS (apply to every chart)
# --------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero">
        <div>
            <p class="hero-title">✈️ HKIA Cargo Flight Dashboard</p>
            <p class="hero-subtitle">Competitor analysis exclusive to CX online ports</p>
        </div>
        <span class="hero-badge">Data as of {pd.Timestamp.now().date()}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.header("Filters")

selected_type = st.sidebar.multiselect(
    "Select Flight Type(s):",
    options=sorted(df["flight_type"].unique()),
    default=sorted(df["flight_type"].unique()),
)
selected_airline = st.sidebar.multiselect(
    "Select Airline(s):",
    options=sorted(df["airline"].unique()),
    default=sorted(df["airline"].unique()),
)
selected_port = st.sidebar.multiselect(
    "Select Port(s):",
    options=sorted(df["port"].unique()),
    default=sorted(df["port"].unique()),
)

if not selected_type or not (selected_airline or selected_port):
    st.sidebar.warning("Please select at least one flight type and one airline/port.")
    st.stop()

mask = df["flight_type"].isin(selected_type)
if selected_airline:
    mask &= df["airline"].isin(selected_airline)
if selected_port:
    mask &= df["port"].isin(selected_port)
df = df.loc[mask]

if df.empty:
    st.sidebar.warning("No data available for the selected filters. Please broaden your selection.")
    st.stop()

st.divider()

#create a seperate copy for past and future data
past_df = df.loc[df["date"] < pd.Timestamp.today()].copy()   # exclude today + future -> historical only
future_df = df.loc[df["date"] >= pd.Timestamp.now().normalize()].copy()   #strips time, keep at midnight

# --------------------------------------------------------------------
# KPI ROW
# --------------------------------------------------------------------
total_flights = len(df)
total_cancelled = int(df["is_cancelled"].sum())
cancel_rate_overall = (total_cancelled / total_flights * 100) if total_flights else 0.0

# week-over-week cancellation trend, for a KPI delta
# must consider full week, hence rolling 7 days
if not past_df.empty:
    last_day = past_df["date"].max()
    recent_cut = last_day - pd.Timedelta(days=7)
    prev_cut = recent_cut - pd.Timedelta(days=7)
    last7 = past_df[past_df["date"] > recent_cut]
    prev7 = past_df[(past_df["date"] > prev_cut) & (past_df["date"] <= recent_cut)]
    rate_last7 = last7["is_cancelled"].mean() * 100 if len(last7) else None     #% of cancellation this week
    rate_prev7 = prev7["is_cancelled"].mean() * 100 if len(prev7) else None     #% of cancellaton the week before
    weekly_delta = (rate_last7 - rate_prev7) if (rate_last7 is not None and rate_prev7 is not None) else None
else:
    weekly_delta = None

k1, k2, k3 = st.columns(3, gap="small")
with k1:
    render_kpi_card("Total Flights", f"{total_flights:,}")
with k2:
    delta_text, delta_kind = None, None
    if weekly_delta is not None:
        delta_kind = "up" if weekly_delta > 0 else "down"     #up = cancellations rose = bad = red
        arrow = "▲" if weekly_delta > 0 else "▼"
        delta_text = f"{arrow} {abs(weekly_delta):.1f} pts vs prior week"
    render_kpi_card("Cancellation Rate", f"{cancel_rate_overall:.1f}%", delta_text, delta_kind)
with k3:
    render_kpi_card("Latest Data Available", df["date"].max().strftime("%Y-%m-%d"))

# --------------------------------------------------------------------
# CANCELLATION LEADERBOARD (by airline / by port, toggle-able)
# --------------------------------------------------------------------

#cancellation_summary based on the key dimension
def cancellation_summary(frame, key):
    grp = frame.groupby([key, "is_cancelled"]).agg(count=("flight_id", "count")).reset_index()
    grp = grp[grp["is_cancelled"] == 1]
    total = frame.groupby(key)["flight_id"].count().reset_index(name="total_flights")
    grp = pd.merge(grp, total, on=key, how="right").fillna({"count": 0})    #NA would be 0
    grp["cancel%"] = (grp["count"] / grp["total_flights"] * 100).round(2)
    return grp


cancel_airline = cancellation_summary(df, "airline")
cancel_port = cancellation_summary(df, "port")

top_airline_count = cancel_airline.sort_values("count", ascending=False).iloc[0]
top_port_count = cancel_port.sort_values("count", ascending=False).iloc[0]

MIN_SAMPLE = 100  # ignore airlines/ports with too few flights to be meaningful
cancel_airline_sample = cancel_airline[cancel_airline["total_flights"] > MIN_SAMPLE]
cancel_port_sample = cancel_port[cancel_port["total_flights"] > MIN_SAMPLE]
top_airline_per = cancel_airline_sample.sort_values("cancel%", ascending=False).iloc[0]
top_port_per = cancel_port_sample.sort_values("cancel%", ascending=False).iloc[0]

with st.container(border=True):
    section_header("🏆", "Cancellation Leaderboard")
    st.caption(f"Rate-based ranking only considers entries with more than {MIN_SAMPLE} flights.")
    selected_dim = st.selectbox("Dimension", options=["Airline", "Port"], key="selected_dim")
    dim_key = "airline" if selected_dim == "Airline" else "port"

    if selected_dim == "Airline":
        top_per, top_count = top_airline_per, top_airline_count
        top_per_5 = cancel_airline_sample.sort_values("cancel%", ascending=False).head(5)
        top_count_5 = cancel_airline.sort_values("count", ascending=False).head(5)
    else:
        top_per, top_count = top_port_per, top_port_count
        top_per_5 = cancel_port_sample.sort_values("cancel%", ascending=False).head(5)
        top_count_5 = cancel_port.sort_values("count", ascending=False).head(5)

    col1, col2 = st.columns(2, gap="small")
    with col1:
        render_kpi_card("🔻 Highest Cancellation Rate", f"{top_per[dim_key]} — {top_per['cancel%']}%")
    with col2:
        render_kpi_card("#️⃣ Most Cancelled Flights", f"{top_count[dim_key]} — {int(top_count['count'])}")

    col3, col4 = st.columns(2, gap="small")
    with col3:
        st.caption("Top 5 by cancellation rate")
        st.dataframe(
            top_per_5[[dim_key, "cancel%"]],        #display the dimension and cancellation%
            width='stretch',
            hide_index=True,    #hide the index
            column_config={
                dim_key: st.column_config.TextColumn(selected_dim),
                "cancel%": st.column_config.ProgressColumn(
                    "Cancellation Rate", format="%.1f%%", min_value=0, max_value=100
                ),
            },
        )
    with col4:
        st.caption("Top 5 by cancellation count")
        st.dataframe(
            top_count_5[[dim_key, "count"]],       #display the dimension and count
            width='stretch',
            hide_index=True,
            column_config={
                dim_key: st.column_config.TextColumn(selected_dim),
                "count": st.column_config.NumberColumn("Cancelled Flights"),
            },
        )

st.divider()

# --------------------------------------------------------------------
# TABS
# --------------------------------------------------------------------
tab_overview, tab_airline, tab_port, tab_upcoming = st.tabs(
    ["📊 Overview", "🏢 By Airline", "🗺️ By Port", "📅 Upcoming Flights"]
)

# ---------------------------- Overview -------------------------------
with tab_overview:
    section_header("📈", "Historical Trend")
    csv_past = past_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Historical Data as CSV",
        data=csv_past,
        file_name=f"HKIA_flight_data_{date.today()}.csv",
        mime="text/csv",
    )

    if past_df.empty:
        st.info("No historical data available for the selected filters.")
    else:
        daily = past_df.groupby(past_df["date"].dt.date).agg(
            total=("flight_id", "count"), cancelled=("is_cancelled", "sum")
        ).reset_index()
        daily["cancel_rate"] = (daily["cancelled"] / daily["total"] * 100).round(1)
        daily["rolling_rate"] = daily["cancel_rate"].rolling(7, min_periods=1).mean().round(1)

        fig_trend = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
            subplot_titles=("Daily Flight Volume", "Daily Cancellation Rate (%)"),
        )
        fig_trend.add_trace(
            go.Bar(x=daily["date"], y=daily["total"], marker_color=SEQUENTIAL_BLUE[3], name="Flights"),
            row=1, col=1,
        )
        fig_trend.add_trace(
            go.Scatter(x=daily["date"], y=daily["cancel_rate"], mode="markers", name="Daily rate",
                       marker=dict(color=COLOR_MUTED, size=5), opacity=0.6),
            row=2, col=1,
        )
        fig_trend.add_trace(
            go.Scatter(x=daily["date"], y=daily["rolling_rate"], mode="lines", name="7-day average",
                       line=dict(color=COLOR_CRITICAL, width=2)),
            row=2, col=1,
        )
        fig_trend.update_yaxes(title_text="Flights", row=1, col=1)
        fig_trend.update_yaxes(title_text="Cancel %", row=2, col=1)
        fig_trend.update_layout(template=TEMPLATE, height=520, margin=dict(t=60), hovermode="x unified")
        fig_trend.update_layout(**CHART_LAYOUT_DEFAULTS)
        st.plotly_chart(fig_trend, width='stretch')

        section_header("🗓️", "Cancellation Pattern by Day of Week")
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        past_df["weekday"] = past_df["date"].dt.day_name()
        wk = past_df.groupby("weekday").agg(
            total=("flight_id", "count"), cancelled=("is_cancelled", "sum")
        ).reindex(weekday_order).reset_index()
        wk["cancel_rate"] = (wk["cancelled"] / wk["total"] * 100).round(1)

        fig_weekday = px.bar(
            wk, x="weekday", y="cancel_rate", text="cancel_rate",
            color_discrete_sequence=[COLOR_CRITICAL], template=TEMPLATE,
            hover_data={"total": True, "cancelled": True, "weekday": False},
        )
        fig_weekday.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_weekday.update_xaxes(title_text="")
        fig_weekday.update_yaxes(title_text="Cancellation Rate (%)")
        fig_weekday.update_layout(**CHART_LAYOUT_DEFAULTS)
        st.plotly_chart(fig_weekday, width='stretch')

# ---------------------------- By Airline ------------------------------
with tab_airline:
    grouped_airline = past_df.groupby(["airline", "is_cancelled"]).agg(count=("flight_id", "count")).reset_index()
    grouped_airline["status_label"] = grouped_airline["is_cancelled"].map({1: "Cancelled", 0: "Flown"})
    non_cancelled = grouped_airline[grouped_airline["is_cancelled"] == 0]
    sorted_airlines = non_cancelled.sort_values("count", ascending=True)["airline"].tolist()

    fig_airline = px.bar(
        grouped_airline, x="airline", y="count", color="status_label", barmode="group", text="count",
        title="Flight Volume by Airline", subtitle="Sorted by non-cancelled flight volume",
        color_discrete_map=STATUS_COLOR_MAP, category_orders={"airline": sorted_airlines},
        template=TEMPLATE,
    )
    fig_airline.update_traces(textposition="inside")
    fig_airline.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.05, title_text="")
    fig_airline.update_yaxes(title_text="Flights", range=[0, grouped_airline["count"].max() * 1.1])
    fig_airline.update_layout(legend_title_text="")
    fig_airline.update_layout(**CHART_LAYOUT_DEFAULTS)
    st.plotly_chart(fig_airline, width='stretch')

# ---------------------------- By Port ------------------------------
with tab_port:
    TOP_N_BAR = 20
    top_ports_by_volume = past_df["port"].value_counts().head(TOP_N_BAR).index.tolist()
    grouped_port = past_df[past_df["port"].isin(top_ports_by_volume)]
    grouped_port = grouped_port.groupby(["port", "is_cancelled"]).agg(count=("flight_id", "count")).reset_index()
    grouped_port["status_label"] = grouped_port["is_cancelled"].map({1: "Cancelled", 0: "Flown"})
    non_cancelled_port = grouped_port[grouped_port["is_cancelled"] == 0]
    sorted_ports = non_cancelled_port.sort_values("count", ascending=True)["port"].tolist()

    fig_port = px.bar(
        grouped_port, x="port", y="count", color="status_label", barmode="group", text="count",
        title=f"Flight Volume by Port (Top {TOP_N_BAR} of {past_df['port'].nunique()} by volume)",
        subtitle="Sorted by non-cancelled flight volume",
        color_discrete_map=STATUS_COLOR_MAP, category_orders={"port": sorted_ports},
        template=TEMPLATE,
    )
    fig_port.update_traces(textposition="inside")
    fig_port.update_xaxes(title_text="")
    fig_port.update_yaxes(title_text="Flights", range=[0, grouped_port["count"].max() * 1.1])
    fig_port.update_layout(legend_title_text="")
    fig_port.update_layout(**CHART_LAYOUT_DEFAULTS)
    st.plotly_chart(fig_port, width='stretch')

    section_header("🌐", "Full Port Picture")
    TOP_N_TREEMAP = 40
    port_summary = past_df.groupby("port").agg(
        total=("flight_id", "count"), cancelled=("is_cancelled", "sum")
    ).reset_index()
    port_summary["cancel_rate"] = (port_summary["cancelled"] / port_summary["total"] * 100).round(1)
    port_summary = port_summary.sort_values("total", ascending=False)

    treemap_data = port_summary.head(TOP_N_TREEMAP).copy()
    remainder = port_summary.iloc[TOP_N_TREEMAP:]
    if not remainder.empty:
        other_total = remainder["total"].sum()
        other_cancelled = remainder["cancelled"].sum()
        other_row = pd.DataFrame([{
            "port": f"Other ({len(remainder)} ports)",
            "total": other_total,
            "cancelled": other_cancelled,
            "cancel_rate": round(other_cancelled / other_total * 100, 1) if other_total else 0,
        }])
        treemap_data = pd.concat([treemap_data, other_row], ignore_index=True)

    fig_treemap = px.treemap(
        treemap_data, path=["port"], values="total", color="cancel_rate",
        color_continuous_scale=SEQUENTIAL_BLUE,
        title="Flight Volume by Port, colored by Cancellation Rate",
        template=TEMPLATE,
    )
    fig_treemap.update_traces(
        texttemplate="<b>%{label}</b><br>%{value} flights<br>%{color:.1f}% cancelled"
    )
    fig_treemap.update_layout(coloraxis_colorbar_title="Cancel %")
    fig_treemap.update_layout(**CHART_LAYOUT_DEFAULTS)
    st.plotly_chart(fig_treemap, width='stretch')

# ---------------------------- Upcoming Flights ------------------------------
with tab_upcoming:
    if future_df.empty:
        st.info("No upcoming flights available for the selected filters.")
    else:
        future_df["date"] = future_df["date"].dt.date
        csv_future = future_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Upcoming Data as CSV",
            data=csv_future,
            file_name=f"HKIA_future_flight_data_{date.today()}.csv",
            mime="text/csv",
        )

        future_df["is_cancelled"] = future_df["is_cancelled"].map({1: "Cancelled", 0: "Scheduled"})
        status_options = future_df["is_cancelled"].unique().tolist()
        selected_status = st.selectbox("Status", options=status_options)
        badge_kind = "critical" if selected_status == "Cancelled" else "good"
        st.markdown(f"Showing: {render_badge(selected_status, badge_kind)}", unsafe_allow_html=True)
        display_df = future_df.loc[future_df["is_cancelled"] == selected_status]

        st.dataframe(
            display_df.drop(columns=["ports", "status_code"]),
            width='stretch',
            hide_index=True,
            column_config={
                "flight_no": st.column_config.TextColumn("Flight No."),
                "airline": st.column_config.TextColumn("Airline"),
                "date": st.column_config.DateColumn("Date"),
                "time": st.column_config.TextColumn("Scheduled Time"),
                "port": st.column_config.TextColumn("Port"),
                "status": st.column_config.TextColumn("Status"),
                "flight_type": st.column_config.TextColumn("Type"),
                "is_cancelled": st.column_config.TextColumn("Flight Status"),
            },
        )

st.divider()
st.caption(
    f"Data pipeline: HKIA public flight API · Filtered to CX online ports · "
    f"{len(df):,} flights shown for the current filter selection"
)
