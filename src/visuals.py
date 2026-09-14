import pandas as pd
import plotly.express as px
import plotly.graph_objects as go   #for subplots in overview tab
from plotly.subplots import make_subplots
import streamlit as st
from datetime import date

#--------------------------------------------------------------------
# PAGE CONFIG (must be the very first Streamlit call)
#--------------------------------------------------------------------
st.set_page_config(
    page_title="HKIA Cargo Flight Dashboard",
    layout="wide",
)

#--------------------------------------------------------------------
# COLOR PALETTE (validated categorical/status palette - CVD-safe)
#--------------------------------------------------------------------
COLOR_GOOD = "#0ca30c"        #flown
COLOR_CRITICAL = "#d03b3b"    #cancelled
COLOR_MUTED = "#898781"       #reference line
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"]   #for tree map
STATUS_COLOR_MAP = {"Cancelled": COLOR_CRITICAL, "Flown": COLOR_GOOD}
TEMPLATE = "plotly_dark" 
DATA_DIR = "/Users/fionaleong/HKIA_flight_monitor/data"

#--------------------------------------------------------------------
# LOAD + ENRICH DATA
#--------------------------------------------------------------------
@st.cache_data
def load_data():
    df_ports = pd.read_csv(f"{DATA_DIR}/online_ports.csv")
    #prev historical + today plus future flights
    df1 = pd.read_csv(f"{DATA_DIR}/HKIA_merged.csv", header=0)
    df2  = pd.read_csv(f"{DATA_DIR}/HKIA_upcoming.csv", header=0)
    df= pd.concat([df1,df2], ignore_index=True)
    df = pd.merge(df, df_ports, how="inner", left_on="port", right_on="ports")  # strictly online (CX) ports

    df["status"] = df["status"].fillna("")
    df["is_cancelled"] = (df["status"].str.strip() == "Cancelled").astype(int)
    df["date"] = pd.to_datetime(df["date"])

    return df


df = load_data()

#--------------------------------------------------------------------
# SIDEBAR FILTERS (apply to every chart)
#--------------------------------------------------------------------
st.title("HKIA Cargo Flight Dashboard")
st.caption("Competitor analysis exclusive to CX online ports")
st.caption(f"Latest Data Load: {pd.Timestamp.now().date()}")     #add latest date of refresh: will be today()

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

#--------------------------------------------------------------------
# KPI ROW
#--------------------------------------------------------------------
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
#Total flights 
k1.metric("Total Flights", f"{total_flights:,}", border=True)
#Cancellation rate
k2.metric(
    "Cancellation Rate",
    f"{cancel_rate_overall:.1f}%",
    delta=f"{weekly_delta:.1f} pts vs prior week" if weekly_delta is not None else None,
    delta_color="inverse",  #increase cancellation indicated red, green otherwise
    border=True,
)
#latest data available: D+2 for cargo 
k3.metric("Latest Data Available", df["date"].max().strftime("%Y-%m-%d"), border=True) 

#--------------------------------------------------------------------
# UPCOMING FLIGHTS
#--------------------------------------------------------------------
st.divider()
st.subheader('Upcoming Flights')
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
    display_df = future_df.loc[future_df["is_cancelled"] == selected_status]

    st.dataframe(
            display_df.drop(columns=["ports", "status_code","flight_id"]),
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


#--------------------------------------------------------------------
# CANCELLATION LEADERBOARD (by airline / by port, toggle-able)
#--------------------------------------------------------------------

st.divider()
st.subheader("Historical Analysis")

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

MIN_SAMPLE = 200  # ignore airlines/ports with too few flights for cancellation%
cancel_airline_sample = cancel_airline[cancel_airline["total_flights"] > MIN_SAMPLE]
cancel_port_sample = cancel_port[cancel_port["total_flights"] > MIN_SAMPLE]
top_airline_per = cancel_airline_sample.sort_values("cancel%", ascending=False).iloc[0]
top_port_per = cancel_port_sample.sort_values("cancel%", ascending=False).iloc[0]

with st.container(border=True):
    st.subheader("Cancellation Leaderboard")
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
    col1.metric("Highest Cancellation Rate", f"{top_per[dim_key]} : {top_per['cancel%']}%", border=True)
    col2.metric("Most Cancelled Flights", f"{top_count[dim_key]} : {int(top_count['count'])}", border=True)

    col3, col4 = st.columns(2, gap="small")
    with col3:
        st.caption("Top 5 by cancellation rate")
        st.dataframe(
            top_per_5[[dim_key, "cancel%"]],        #display the dimension and cancellation%
            width='stretch',
            hide_index=True,    #hide the index
            column_config={
                dim_key: st.column_config.TextColumn(selected_dim),
                "cancel%": st.column_config.ProgressColumn(     #create percentage bar 
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


#--------------------------------------------------------------------
# TABS
#--------------------------------------------------------------------
tab_overview, tab_airline, tab_port = st.tabs(
    ["Overview", "By Airline", "By Port"]
)

#---------------------------- Overview -------------------------------
with tab_overview:
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
        #daily flight count (active/non cancelled)
        daily = past_df.groupby(past_df["date"].dt.date).agg(
            total=("flight_id", "count"), cancelled=("is_cancelled", "sum")
        ).reset_index()
        daily["cancel_rate"] = (daily["cancelled"] / daily["total"] * 100).round(1)
        daily["rolling_rate"] = daily["cancel_rate"].rolling(7, min_periods=1).mean().round(1) #rolling 7 days average 

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
        fig_trend.update_yaxes(title_text="Flights", row=1, col=1) #1st y axis
        fig_trend.update_yaxes(title_text="Cancel %", row=2, col=1) #2nd y axis
        fig_trend.update_layout(template=TEMPLATE, height=520, margin=dict(t=60), hovermode="x unified")
        st.plotly_chart(fig_trend, width='stretch')

        
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        past_df["weekday"] = past_df["date"].dt.day_name()
        wk = past_df.groupby("weekday").agg(
            total=("flight_id", "count"), cancelled=("is_cancelled", "sum")
        ).reindex(weekday_order).reset_index()
        wk["cancel_rate"] = (wk["cancelled"] / wk["total"] * 100).round(1)

        fig_weekday = px.bar(
            wk, x="weekday", y="cancel_rate", title='Cancellation pattern by day of the week', text="cancel_rate",
            color_discrete_sequence=[COLOR_CRITICAL], template=TEMPLATE,
            hover_data={"total": True, "cancelled": True, "weekday": False},
        )
        fig_weekday.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_weekday.update_xaxes(title_text="")
        fig_weekday.update_yaxes(title_text="Cancellation Rate (%)")
        st.plotly_chart(fig_weekday, width='stretch')

n=20       #range for the range slider 
#---------------------------- By Airline ------------------------------
with tab_airline:
    grouped_airline = past_df.groupby(["airline", "is_cancelled"]).agg(count=("flight_id", "count")).reset_index()
    grouped_airline["status_label"] = grouped_airline["is_cancelled"].map({1: "Cancelled", 0: "Flown"})
    non_cancelled = grouped_airline[grouped_airline["is_cancelled"] == 0]
    sorted_airlines = non_cancelled.sort_values("count", ascending=True)["airline"].tolist()

    length=len(sorted_airlines)
    start_idx= length - n -0.5
    end_idx= length + 0.5
    fig_airline = px.bar(
        grouped_airline, x="airline", y="count", color="status_label", barmode="group", text="count",
        title="Flight Volume by Airline", 
        subtitle="Segregated by flight status, sorted by non-cancelled flight volume",
        color_discrete_map=STATUS_COLOR_MAP, category_orders={"airline": sorted_airlines},
        template=TEMPLATE,
    )
    fig_airline.update_traces(textposition="outside")
    fig_airline.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.1, title_text="Airline", range=[start_idx,end_idx])
    fig_airline.update_yaxes(title_text="Flights", range=[0, grouped_airline["count"].max() * 1.1])
    fig_airline.update_layout(legend_title_text="")
    st.plotly_chart(fig_airline, width='stretch')

#---------------------------- By Port ------------------------------
with tab_port:
    grouped_port = past_df.groupby(["port", "is_cancelled"]).agg(count=("flight_id", "count")).reset_index()
    grouped_port["status_label"] = grouped_port["is_cancelled"].map({1: "Cancelled", 0: "Flown"})
    non_cancelled_port = grouped_port[grouped_port["is_cancelled"] == 0]
    sorted_ports = non_cancelled_port.sort_values("count", ascending=True)["port"].tolist()

    fig_port = px.bar(
        grouped_port, x="port", y="count", color="status_label", barmode="group", text="count",
        title="Flight Volume by Port",
        subtitle="Segregated by flight status, sorted by non-cancelled flight volume",
        color_discrete_map=STATUS_COLOR_MAP, category_orders={"port": sorted_ports},
        template=TEMPLATE,
    )

    length=len(sorted_ports)
    start_idx= length - n -0.5
    end_idx= length + 0.5
    fig_port.update_traces(textposition="outside")
    fig_port.update_xaxes(title_text="Port", rangeslider_visible=True, rangeslider_thickness= 0.1, range=[start_idx, end_idx])
    fig_port.update_yaxes(title_text="Flights", range=[0, grouped_port["count"].max() * 1.1])
    fig_port.update_layout(legend_title_text="")
    st.plotly_chart(fig_port, width='stretch')

    #why is tree map only consider top 40
    port_summary = past_df.groupby("port").agg(
        total=("flight_id", "count"), cancelled=("is_cancelled", "sum")
    ).reset_index()
    port_summary["cancel_rate"] = (port_summary["cancelled"] / port_summary["total"] * 100).round(1)
    port_summary = port_summary.sort_values("total", ascending=False)
    print(port_summary["cancel_rate"].head(5).tolist())
    treemap_data = port_summary.copy()

    fig_treemap = px.treemap(
        treemap_data, path=["port"], values="total", color="cancel_rate",
        color_continuous_scale=SEQUENTIAL_BLUE,
        title="Flight Volume by Port",
        subtitle= 'Colored by cancellation rate',
        template=TEMPLATE,
    )
    fig_treemap.update_traces(
        texttemplate="<b>%{label}</b><br>%{value} flights<br>%{color:.1f}% cancelled"
    )
    fig_treemap.update_layout(coloraxis_colorbar_title="Cancel %")
    st.plotly_chart(fig_treemap, width='stretch')

