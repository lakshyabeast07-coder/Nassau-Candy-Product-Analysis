import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nassau Candy — Product Profitability",
    page_icon="🍬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
C = {
    "navy":   "#1F3864", "green":  "#375623", "brown":  "#843C0C",
    "purple": "#4A235A", "blue":   "#2E75B6", "amber":  "#EF9F27",
    "red":    "#E24B4A", "teal":   "#1D9E75", "gray":   "#888780",
    "light":  "#EBF3FB",
}
DIV_COLORS = {"Chocolate": "#843C0C", "Other": "#888780", "Sugar": "#EF9F27"}
FLAG_COLORS = {
    "High-Profit / High-Margin":  "#375623",
    "High-Sales / Low-Margin":    "#EF9F27",
    "Low-Sales / Low-Profit":     "#E24B4A",
}
ACTION_COLORS = {
    "🔴 URGENT": "#E24B4A", "🔴 HIGH": "#E24B4A",
    "🟡 MEDIUM": "#EF9F27", "🟡 LOW": "#EF9F27",
    "🟢 MAINTAIN": "#375623", "🟢 MAINTAIN & EXPAND": "#1D9E75",
    "🟢 BUNDLE / PROMOTE": "#1D9E75",
}

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────
FILE = "Nassau_Candy_Distributor_Work_Product.xlsx"

@st.cache_data
def load_data():
    # ── Main transactions ──────────────────────────────────────
    df = pd.read_excel(FILE, sheet_name="Nassau Candy Distributor")
    df["Order Date"]  = pd.to_datetime(df["Order Date"])
    df["Ship Date"]   = pd.to_datetime(df["Ship Date"])
    df["Margin (%)"]  = (df["Gross Profit"] / df["Sales"] * 100).round(2)
    df["Cost Ratio (%)"] = (df["Cost"] / df["Sales"] * 100).round(2)

    # ── Profitability metrics (pre-computed) ───────────────────
    pm = pd.read_excel(FILE, sheet_name="Profitability Metrics", header=3)
    pm.columns = [c.strip() for c in pm.columns]
    # Drop rows where Product ID is NaN or is the literal header string
    pm = pm[pd.to_numeric(pm["Gross Margin (%)"], errors="coerce").notna()].copy()
    pm["Gross Margin (%)"] = pd.to_numeric(pm["Gross Margin (%)"], errors="coerce")
    pm["Gross Margin (%)"] = (pm["Gross Margin (%)"] * 100).round(2)

    # ── Product-level analysis ────────────────────────────────
    pl_raw = pd.read_excel(FILE, sheet_name="Product-Level Analysis", header=None)
    pl_cols = ["Rank", "Tier", "Product Name", "Total Revenue ($)",
               "Total Gross Profit ($)", "Gross Margin (%)", "Profit per Unit ($)",
               "Units Sold", "Category"]
    pl = pl_raw.iloc[8:23, :9].copy()
    pl.columns = pl_cols
    # Keep only rows where Rank is a real number (drops stray header rows)
    pl["Rank"] = pd.to_numeric(pl["Rank"], errors="coerce")
    pl = pl.dropna(subset=["Rank"]).copy()
    for col in ["Total Revenue ($)", "Total Gross Profit ($)", "Gross Margin (%)",
                "Profit per Unit ($)", "Units Sold"]:
        pl[col] = pd.to_numeric(pl[col], errors="coerce")
    pl["Gross Margin (%)"]    = (pl["Gross Margin (%)"] * 100).round(2)
    pl["Rank"]                = pl["Rank"].astype("Int64")
    pl["Units Sold"]          = pl["Units Sold"].astype("Int64")

    # ── Division performance ───────────────────────────────────
    dp_raw = pd.read_excel(FILE, sheet_name="Division Performance", header=None)
    dp_cols = ["Division", "SKUs", "Transactions", "Units Sold", "Total Revenue ($)",
               "Total Cost ($)", "Gross Profit ($)", "Gross Margin (%)",
               "Revenue Share (%)", "Profit Share (%)", "Profit per Unit ($)"]
    dp = dp_raw.iloc[4:9, :11].copy()
    dp.columns = dp_cols
    # Drop header echo rows and TOTAL row
    dp = dp[dp["Division"].notna()].copy()
    dp = dp[~dp["Division"].astype(str).str.contains("Division|TOTAL", na=False)].copy()
    dp["Division"] = dp["Division"].astype(str).str.replace(r"^[^\w]+", "", regex=True).str.strip()
    for col in dp.columns[1:]:
        dp[col] = pd.to_numeric(dp[col], errors="coerce")
    dp = dp.dropna(subset=["Gross Margin (%)"]).copy()
    dp["Gross Margin (%)"]   = (dp["Gross Margin (%)"]   * 100).round(2)
    dp["Revenue Share (%)"]  = (dp["Revenue Share (%)"]  * 100).round(2)
    dp["Profit Share (%)"]   = (dp["Profit Share (%)"]   * 100).round(2)

    # Imbalance table (rows 17-20)
    imb_raw = dp_raw.iloc[17:21, :9].copy()
    imb_raw.columns = ["Division", "Revenue Share (%)", "Profit Share (%)", "Imbalance (pp)",
                        "Imbalance Signal", "Revenue ($)", "Gross Profit ($)",
                        "Revenue-Profit Gap ($)", "Interpretation"]
    imb = imb_raw[imb_raw["Division"].notna()].copy()
    imb = imb[~imb["Division"].astype(str).str.contains("Division", na=False)].copy()
    imb["Division"] = imb["Division"].astype(str).str.replace(r"^[^\w]+", "", regex=True).str.strip()
    for col in ["Revenue Share (%)", "Profit Share (%)", "Imbalance (pp)",
                "Revenue ($)", "Gross Profit ($)", "Revenue-Profit Gap ($)"]:
        imb[col] = pd.to_numeric(imb[col], errors="coerce")
    imb = imb.dropna(subset=["Revenue Share (%)"]).copy()
    imb["Revenue Share (%)"] = (imb["Revenue Share (%)"] * 100).round(2)
    imb["Profit Share (%)"]  = (imb["Profit Share (%)"]  * 100).round(2)

    # ── Pareto & cost diagnostics ─────────────────────────────
    pc_raw = pd.read_excel(FILE, sheet_name="Pareto & Cost Diagnostics", header=None)
    pareto_cols = ["Rank", "Product Name", "Division", "Revenue ($)", "Rev Share (%)",
                   "Cum Rev (%)", "80% Line", "Gross Profit ($)", "Prof Share (%)",
                   "Cum Prof (%)", "Gross Margin (%)", "Pareto Category"]
    pareto = pc_raw.iloc[4:20, :12].copy()
    pareto.columns = pareto_cols
    # Keep only numeric-rank rows (drops header echo and PORTFOLIO TOTAL)
    pareto["Rank"] = pd.to_numeric(pareto["Rank"], errors="coerce")
    pareto = pareto.dropna(subset=["Rank"]).copy()
    for col in ["Revenue ($)", "Rev Share (%)", "Cum Rev (%)", "Gross Profit ($)",
                "Prof Share (%)", "Cum Prof (%)", "Gross Margin (%)"]:
        pareto[col] = pd.to_numeric(pareto[col], errors="coerce")
    pareto["Rev Share (%)"]   = (pareto["Rev Share (%)"]   * 100).round(2)
    pareto["Cum Rev (%)"]     = (pareto["Cum Rev (%)"]     * 100).round(2)
    pareto["Prof Share (%)"]  = (pareto["Prof Share (%)"]  * 100).round(2)
    pareto["Cum Prof (%)"]    = (pareto["Cum Prof (%)"]    * 100).round(2)
    pareto["Gross Margin (%)"]= (pareto["Gross Margin (%)"]* 100).round(2)

    # Cost diagnostics rows 47-62
    cost_cols = ["Rank", "Product Name", "Division", "Revenue ($)", "Total Cost ($)",
                 "Cost Ratio (%)", "Gross Profit ($)", "Margin (%)", "Profit/Unit ($)",
                 "Cost/Unit ($)", "Diagnosis", "Action Flag"]
    cost_diag = pc_raw.iloc[47:63, :12].copy()
    cost_diag.columns = cost_cols
    # Keep only rows with a real product name and numeric cost ratio
    cost_diag = cost_diag[cost_diag["Product Name"].notna()].copy()
    cost_diag = cost_diag[~cost_diag["Product Name"].astype(str).str.contains("Product Name|#", na=False)].copy()
    for col in ["Revenue ($)", "Total Cost ($)", "Cost Ratio (%)",
                "Gross Profit ($)", "Margin (%)", "Profit/Unit ($)", "Cost/Unit ($)"]:
        cost_diag[col] = pd.to_numeric(cost_diag[col], errors="coerce")
    cost_diag = cost_diag.dropna(subset=["Cost Ratio (%)"]).copy()
    cost_diag["Cost Ratio (%)"] = (cost_diag["Cost Ratio (%)"] * 100).round(2)
    cost_diag["Margin (%)"]     = (cost_diag["Margin (%)"]     * 100).round(2)

    return df, pm, pl, dp, imb, pareto, cost_diag


df, pm, pl, dp, imb, pareto, cost_diag = load_data()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/emoji/96/candy.png", width=58)
st.sidebar.title("🍬 Nassau Candy")
st.sidebar.markdown("**Product Profitability Dashboard**")
st.sidebar.divider()
st.sidebar.header("🔎 Filters")

# Date range
min_d, max_d = df["Order Date"].min().date(), df["Order Date"].max().date()
date_range = st.sidebar.date_input("Order Date Range", [min_d, max_d],
                                   min_value=min_d, max_value=max_d)

# Division filter
all_divs = sorted(df["Division"].unique())
sel_divs = st.sidebar.multiselect("Division", all_divs, default=all_divs)

# Margin threshold
margin_thresh = st.sidebar.slider(
    "Min Gross Margin (%)", min_value=0, max_value=100, value=0, step=5,
    help="Show only products/orders at or above this margin threshold"
)

# Product search
search_q = st.sidebar.text_input("🔍 Product Search", placeholder="Type product name...")

st.sidebar.divider()
st.sidebar.caption(f"Dataset: {len(df):,} transactions · {df['Product Name'].nunique()} SKUs · {df['Division'].nunique()} Divisions")

# ─────────────────────────────────────────────────────────────────────────────
# APPLY FILTERS TO MAIN DF
# ─────────────────────────────────────────────────────────────────────────────
fdf = df.copy()
if len(date_range) == 2:
    fdf = fdf[(fdf["Order Date"].dt.date >= date_range[0]) &
              (fdf["Order Date"].dt.date <= date_range[1])]
fdf = fdf[fdf["Division"].isin(sel_divs)]
fdf = fdf[fdf["Margin (%)"] >= margin_thresh]
if search_q.strip():
    fdf = fdf[fdf["Product Name"].str.contains(search_q.strip(), case=False, na=False)]

# Filtered product-level aggregation (live, from raw transactions)
prod_agg = fdf.groupby(["Product ID", "Product Name", "Division"]).agg(
    Transactions  = ("Row ID",       "count"),
    Units_Sold    = ("Units",        "sum"),
    Total_Revenue = ("Sales",        "sum"),
    Total_Cost    = ("Cost",         "sum"),
    Total_Profit  = ("Gross Profit", "sum"),
).reset_index()
prod_agg["Margin (%)"]       = (prod_agg["Total_Profit"] / prod_agg["Total_Revenue"] * 100).round(2)
prod_agg["Cost Ratio (%)"]   = (prod_agg["Total_Cost"]   / prod_agg["Total_Revenue"] * 100).round(2)
prod_agg["Profit per Unit"]  = (prod_agg["Total_Profit"] / prod_agg["Units_Sold"]).round(2)
prod_agg["Revenue per Unit"] = (prod_agg["Total_Revenue"]/ prod_agg["Units_Sold"]).round(2)
prod_agg["Profit Share (%)"] = (prod_agg["Total_Profit"] / prod_agg["Total_Profit"].sum() * 100).round(2)
prod_agg["Revenue Share (%)"]= (prod_agg["Total_Revenue"]/ prod_agg["Total_Revenue"].sum() * 100).round(2)
prod_agg["Cum Rev (%)"]      = prod_agg.sort_values("Total_Revenue", ascending=False)["Revenue Share (%)"].cumsum().round(2)
prod_agg["Rank"]             = prod_agg["Total_Profit"].rank(ascending=False, method="first").astype(int)
prod_agg = prod_agg.sort_values("Total_Profit", ascending=False).reset_index(drop=True)

# Filtered division aggregation
div_agg = fdf.groupby("Division").agg(
    Transactions  = ("Row ID",       "count"),
    Units_Sold    = ("Units",        "sum"),
    Total_Revenue = ("Sales",        "sum"),
    Total_Cost    = ("Cost",         "sum"),
    Total_Profit  = ("Gross Profit", "sum"),
).reset_index()
div_agg["Margin (%)"]      = (div_agg["Total_Profit"] / div_agg["Total_Revenue"] * 100).round(2)
div_agg["Revenue Share (%)"] = (div_agg["Total_Revenue"] / div_agg["Total_Revenue"].sum() * 100).round(2)
div_agg["Profit Share (%)"]  = (div_agg["Total_Profit"]  / div_agg["Total_Profit"].sum()  * 100).round(2)

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.title("🍬 Nassau Candy — Product Profitability Dashboard")
if search_q.strip():
    st.info(f"🔍 Filtering by: **\"{search_q}\"** · {len(fdf):,} matching transactions")
else:
    st.caption(f"Showing **{len(fdf):,}** of {len(df):,} transactions · {prod_agg.shape[0]} products · Filters active")
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# TOP KPIs
# ─────────────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
tot_rev  = fdf["Sales"].sum()
tot_cost = fdf["Cost"].sum()
tot_prof = fdf["Gross Profit"].sum()
tot_marg = (tot_prof / tot_rev * 100) if tot_rev > 0 else 0
n_skus   = fdf["Product Name"].nunique()
n_orders = len(fdf)

k1.metric("Total Revenue",    f"${tot_rev:,.0f}")
k2.metric("Total Cost",       f"${tot_cost:,.0f}")
k3.metric("Gross Profit",     f"${tot_prof:,.0f}")
k4.metric("Portfolio Margin", f"{tot_marg:.1f}%")
k5.metric("Active SKUs",      str(n_skus))
k6.metric("Transactions",     f"{n_orders:,}")
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 1 — PRODUCT PROFITABILITY OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
st.header("📦 Module 1 — Product Profitability Overview")

tab1a, tab1b, tab1c = st.tabs(["🏆 Margin Leaderboard", "💰 Profit Contribution", "📋 Full Product Table"])

with tab1a:
    st.subheader("Product Margin Leaderboard")
    col1, col2 = st.columns(2)

    # Margin bar
    sorted_margin = prod_agg.sort_values("Margin (%)", ascending=True)
    bar_colors = [DIV_COLORS.get(d, C["gray"]) for d in sorted_margin["Division"]]
    fig_margin = go.Figure(go.Bar(
        y=sorted_margin["Product Name"],
        x=sorted_margin["Margin (%)"],
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v:.1f}%" for v in sorted_margin["Margin (%)"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Margin: %{x:.1f}%<extra></extra>",
    ))
    avg_margin = prod_agg["Margin (%)"].mean()
    fig_margin.add_vline(x=avg_margin, line_dash="dash", line_color=C["red"],
                          annotation_text=f"Avg: {avg_margin:.1f}%",
                          annotation_position="top right")
    fig_margin.update_layout(
        title="Gross Margin (%) — All Products", height=420,
        xaxis_title="Gross Margin (%)", yaxis_title="",
        showlegend=False, margin=dict(t=40, b=20, l=10, r=80),
    )
    col1.plotly_chart(fig_margin, use_container_width=True)

    # Profit per unit leaderboard
    sorted_ppu = prod_agg.sort_values("Profit per Unit", ascending=True)
    fig_ppu = go.Figure(go.Bar(
        y=sorted_ppu["Product Name"],
        x=sorted_ppu["Profit per Unit"],
        orientation="h",
        marker_color=[DIV_COLORS.get(d, C["gray"]) for d in sorted_ppu["Division"]],
        text=[f"${v:.2f}" for v in sorted_ppu["Profit per Unit"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Profit/Unit: $%{x:.2f}<extra></extra>",
    ))
    fig_ppu.update_layout(
        title="Profit per Unit ($) — All Products", height=420,
        xaxis_title="Profit per Unit ($)", yaxis_title="",
        showlegend=False, margin=dict(t=40, b=20, l=10, r=80),
    )
    col2.plotly_chart(fig_ppu, use_container_width=True)

    # Category badge summary
    st.subheader("Performance Category Classification")
    cat_col1, cat_col2, cat_col3 = st.columns(3)
    high_pm  = pl[pl["Category"] == "High-Profit / High-Margin"]
    high_slm = pl[pl["Category"] == "High-Sales / Low-Margin"]
    low_sl   = pl[pl["Category"] == "Low-Sales / Low-Profit"]

    with cat_col1:
        st.markdown("##### 🟢 High-Profit / High-Margin")
        for _, r in high_pm.iterrows():
            st.success(f"**{r['Product Name']}** — {r['Gross Margin (%)']:.1f}% margin")

    with cat_col2:
        st.markdown("##### 🟡 High-Sales / Low-Margin")
        for _, r in high_slm.iterrows():
            st.warning(f"**{r['Product Name']}** — {r['Gross Margin (%)']:.1f}% margin")

    with cat_col3:
        st.markdown("##### 🔴 Low-Sales / Low-Profit")
        for _, r in low_sl.iterrows():
            st.error(f"**{r['Product Name']}** — {r['Gross Margin (%)']:.1f}% margin")


with tab1b:
    st.subheader("Profit Contribution Analysis")
    col1, col2 = st.columns(2)

    # Waterfall: profit contribution
    sorted_contrib = prod_agg.sort_values("Total_Profit", ascending=False)
    fig_wf = go.Figure(go.Waterfall(
        name="Profit",
        orientation="v",
        measure=["relative"] * len(sorted_contrib) + ["total"],
        x=list(sorted_contrib["Product Name"]) + ["TOTAL"],
        y=list(sorted_contrib["Total_Profit"]) + [0],
        text=[f"${v:,.0f}" for v in sorted_contrib["Total_Profit"]] + [f"${tot_prof:,.0f}"],
        textposition="outside",
        connector={"line": {"color": "rgba(63,63,63,0.2)"}},
        increasing={"marker": {"color": C["green"]}},
        totals={"marker": {"color": C["navy"]}},
    ))
    fig_wf.update_layout(
        title="Gross Profit Contribution by Product (Waterfall)", height=420,
        yaxis_title="Gross Profit ($)",
        xaxis_tickangle=-35, margin=dict(t=40, b=80, l=10, r=10),
    )
    col1.plotly_chart(fig_wf, use_container_width=True)

    # Treemap: profit concentration
    fig_tree = px.treemap(
        prod_agg,
        path=["Division", "Product Name"],
        values="Total_Profit",
        color="Margin (%)",
        color_continuous_scale=["#E24B4A", "#EF9F27", "#1D9E75"],
        color_continuous_midpoint=prod_agg["Margin (%)"].median(),
        hover_data={"Total_Revenue": ":,.0f", "Margin (%)": ":.1f"},
        title="Profit Treemap — Size = Total Profit, Color = Margin %",
    )
    fig_tree.update_layout(height=420, margin=dict(t=40, b=10, l=10, r=10),
                            coloraxis_colorbar_title="Margin %")
    col2.plotly_chart(fig_tree, use_container_width=True)

    # Bubble chart: revenue vs profit vs margin
    fig_bubble = px.scatter(
        prod_agg,
        x="Total_Revenue", y="Total_Profit",
        size="Units_Sold", color="Division",
        color_discrete_map=DIV_COLORS,
        hover_name="Product Name",
        hover_data={"Margin (%)": ":.1f", "Units_Sold": ":,",
                    "Total_Revenue": ":,.0f", "Total_Profit": ":,.0f"},
        text="Product Name",
        title="Revenue vs Profit vs Volume (bubble = units sold)",
        size_max=60,
    )
    fig_bubble.update_traces(textposition="top center", textfont_size=9)
    fig_bubble.update_layout(height=450, xaxis_title="Total Revenue ($)",
                              yaxis_title="Total Gross Profit ($)",
                              margin=dict(t=40, b=20, l=10, r=10))
    st.plotly_chart(fig_bubble, use_container_width=True)


with tab1c:
    st.subheader("Full Product Profitability Table")

    # Margin risk badge
    def margin_flag(m):
        if m >= 65: return "🟢 Strong"
        if m >= 50: return "🟡 Moderate"
        if m >= 40: return "🟠 At Risk"
        return "🔴 Critical"

    display_df = prod_agg[[
        "Rank", "Product Name", "Division", "Transactions", "Units_Sold",
        "Total_Revenue", "Total_Cost", "Total_Profit",
        "Margin (%)", "Profit per Unit", "Profit Share (%)"
    ]].copy()
    display_df["Margin Flag"] = display_df["Margin (%)"].apply(margin_flag)
    display_df.columns = [
        "Rank", "Product", "Division", "Orders", "Units",
        "Revenue ($)", "Cost ($)", "Profit ($)",
        "Margin (%)", "Profit/Unit ($)", "Profit Share (%)", "Flag"
    ]
    display_df = display_df.sort_values("Rank")
    st.dataframe(
        display_df.style
            .format({
                "Revenue ($)": "${:,.2f}", "Cost ($)": "${:,.2f}",
                "Profit ($)": "${:,.2f}", "Profit/Unit ($)": "${:,.2f}",
                "Margin (%)": "{:.1f}%", "Profit Share (%)": "{:.1f}%",
                "Units": "{:,}", "Orders": "{:,}",
            })
            .background_gradient(subset=["Margin (%)"], cmap="RdYlGn", vmin=0, vmax=100)
            .background_gradient(subset=["Profit ($)"], cmap="Blues"),
        use_container_width=True, height=460,
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 2 — DIVISION PERFORMANCE DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
st.header("🏢 Module 2 — Division Performance Dashboard")

tab2a, tab2b, tab2c = st.tabs(["📊 Revenue vs Profit", "📈 Margin Distribution", "⚖️ Imbalance Analysis"])

with tab2a:
    col1, col2 = st.columns(2)

    # Grouped bar: Revenue vs Profit per division
    fig_rvp = go.Figure()
    fig_rvp.add_trace(go.Bar(
        name="Revenue", x=div_agg["Division"],
        y=div_agg["Total_Revenue"],
        marker_color=[DIV_COLORS.get(d, C["gray"]) for d in div_agg["Division"]],
        opacity=0.9,
        text=[f"${v:,.0f}" for v in div_agg["Total_Revenue"]],
        textposition="outside",
    ))
    fig_rvp.add_trace(go.Bar(
        name="Profit", x=div_agg["Division"],
        y=div_agg["Total_Profit"],
        marker_color=[DIV_COLORS.get(d, C["gray"]) for d in div_agg["Division"]],
        opacity=0.5,
        text=[f"${v:,.0f}" for v in div_agg["Total_Profit"]],
        textposition="outside",
    ))
    fig_rvp.update_layout(
        barmode="group", title="Revenue vs Gross Profit by Division",
        yaxis_title="Amount ($)", height=380,
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=60, b=20, l=10, r=10),
    )
    col1.plotly_chart(fig_rvp, use_container_width=True)

    # Stacked bar: revenue/cost/profit breakdown per division
    fig_stack = go.Figure()
    fig_stack.add_trace(go.Bar(
        name="Gross Profit", x=div_agg["Division"],
        y=div_agg["Total_Profit"],
        marker_color=C["green"],
        text=[f"${v:,.0f}" for v in div_agg["Total_Profit"]],
        textposition="inside",
        insidetextanchor="middle",
    ))
    fig_stack.add_trace(go.Bar(
        name="Total Cost", x=div_agg["Division"],
        y=div_agg["Total_Cost"],
        marker_color=C["brown"],
        text=[f"${v:,.0f}" for v in div_agg["Total_Cost"]],
        textposition="inside",
        insidetextanchor="middle",
    ))
    fig_stack.update_layout(
        barmode="stack", title="Revenue Composition (Profit + Cost)",
        yaxis_title="Amount ($)", height=380,
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=60, b=20, l=10, r=10),
    )
    col2.plotly_chart(fig_stack, use_container_width=True)

    # Revenue & Profit share donut side by side
    col3, col4 = st.columns(2)
    fig_rev_pie = px.pie(div_agg, values="Total_Revenue", names="Division",
                          color="Division", color_discrete_map=DIV_COLORS,
                          title="Revenue Share by Division", hole=0.5)
    fig_rev_pie.update_layout(height=320, margin=dict(t=40, b=10, l=10, r=10))
    col3.plotly_chart(fig_rev_pie, use_container_width=True)

    fig_prof_pie = px.pie(div_agg, values="Total_Profit", names="Division",
                           color="Division", color_discrete_map=DIV_COLORS,
                           title="Profit Share by Division", hole=0.5)
    fig_prof_pie.update_layout(height=320, margin=dict(t=40, b=10, l=10, r=10))
    col4.plotly_chart(fig_prof_pie, use_container_width=True)


with tab2b:
    col1, col2 = st.columns(2)

    # Box plot: margin distribution by division
    fig_box = px.box(
        fdf, x="Division", y="Margin (%)",
        color="Division", color_discrete_map=DIV_COLORS,
        points="all",
        title="Gross Margin Distribution by Division (all transactions)",
    )
    fig_box.add_hline(y=fdf["Margin (%)"].mean(), line_dash="dash", line_color=C["red"],
                       annotation_text=f"Portfolio avg: {fdf['Margin (%)'].mean():.1f}%")
    fig_box.update_layout(showlegend=False, height=400,
                           yaxis_title="Gross Margin (%)",
                           margin=dict(t=40, b=20, l=10, r=10))
    col1.plotly_chart(fig_box, use_container_width=True)

    # Violin: margin distribution
    fig_violin = px.violin(
        fdf, x="Division", y="Margin (%)",
        color="Division", color_discrete_map=DIV_COLORS,
        box=True, points="outliers",
        title="Margin Distribution Density (Violin)",
    )
    fig_violin.update_layout(showlegend=False, height=400,
                              yaxis_title="Gross Margin (%)",
                              margin=dict(t=40, b=20, l=10, r=10))
    col2.plotly_chart(fig_violin, use_container_width=True)

    # Margin histogram faceted by division
    fig_hist = px.histogram(
        fdf, x="Margin (%)", color="Division",
        facet_col="Division", color_discrete_map=DIV_COLORS,
        nbins=30, title="Margin Frequency Distribution by Division",
        marginal="box",
    )
    fig_hist.update_layout(height=380, showlegend=False,
                            margin=dict(t=60, b=20, l=10, r=10))
    st.plotly_chart(fig_hist, use_container_width=True)


with tab2c:
    st.subheader("Revenue vs Profit Share Imbalance")

    col1, col2 = st.columns(2)

    # Grouped bar: revenue vs profit share %
    fig_imb = go.Figure()
    fig_imb.add_trace(go.Bar(
        name="Revenue Share (%)", x=div_agg["Division"],
        y=div_agg["Revenue Share (%)"],
        marker_color=C["blue"], opacity=0.85,
        text=[f"{v:.1f}%" for v in div_agg["Revenue Share (%)"]],
        textposition="outside",
    ))
    fig_imb.add_trace(go.Bar(
        name="Profit Share (%)", x=div_agg["Division"],
        y=div_agg["Profit Share (%)"],
        marker_color=C["green"], opacity=0.85,
        text=[f"{v:.1f}%" for v in div_agg["Profit Share (%)"]],
        textposition="outside",
    ))
    fig_imb.update_layout(
        barmode="group",
        title="Revenue Share vs Profit Share by Division",
        yaxis_title="Share (%)", height=380,
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=60, b=20, l=10, r=10),
    )
    col1.plotly_chart(fig_imb, use_container_width=True)

    # Imbalance waterfall
    imb_data_live = div_agg.copy()
    imb_data_live["Imbalance (pp)"] = imb_data_live["Profit Share (%)"] - imb_data_live["Revenue Share (%)"]
    fig_gap = go.Figure(go.Bar(
        x=imb_data_live["Division"],
        y=imb_data_live["Imbalance (pp)"],
        marker_color=[C["green"] if v >= 0 else C["red"] for v in imb_data_live["Imbalance (pp)"]],
        text=[f"{'+' if v >= 0 else ''}{v:.2f}pp" for v in imb_data_live["Imbalance (pp)"]],
        textposition="outside",
    ))
    fig_gap.add_hline(y=0, line_color="black", line_width=1)
    fig_gap.update_layout(
        title="Profit-Revenue Share Imbalance (pp) — Positive = Profit-Rich",
        yaxis_title="Imbalance (percentage points)", height=380,
        margin=dict(t=40, b=20, l=10, r=10),
    )
    col2.plotly_chart(fig_gap, use_container_width=True)

    # Assessment cards
    st.subheader("Division Financial Efficiency Assessment")
    assessments = [
        ("Chocolate", "✅ STRONG FINANCIAL EFFICIENCY",
         "Gross Margin ~67.4% — highest in the portfolio. Profit share (95.1%) exceeds revenue share (92.9%) by +2.1pp. 5 SKUs generating $88,824 gross profit. **Strategic Action: Protect pricing power; expand distribution.**",
         "success"),
        ("Other", "⚠️ STRUCTURAL MARGIN ISSUE",
         "Gross Margin ~44.8% — lowest, 22.9pp below Chocolate. Revenue-heavy division. Kazookles skews metrics at 7.7% margin. **Strategic Action: Investigate Kazookles; reprice or discontinue.**",
         "warning"),
        ("Sugar", "🔵 MODERATE — NEGLIGIBLE SCALE",
         "Gross Margin ~66.6% — comparable to Chocolate. Revenue & profit shares near-identical (~0.3%). 7 SKUs, only $285 gross profit total. **Strategic Action: Bundle Sugar products; evaluate promotional strategy.**",
         "info"),
    ]
    for div, title, body, badge_type in assessments:
        if div in sel_divs:
            with st.expander(f"**{title}** — {div}", expanded=True):
                if badge_type == "success":
                    st.success(body)
                elif badge_type == "warning":
                    st.warning(body)
                else:
                    st.info(body)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 3 — COST VS MARGIN DIAGNOSTICS
# ─────────────────────────────────────────────────────────────────────────────
st.header("🔬 Module 3 — Cost vs Margin Diagnostics")

tab3a, tab3b = st.tabs(["📉 Cost-Sales Scatter", "⚑ Margin Risk Flags"])

with tab3a:
    col1, col2 = st.columns(2)

    # Cost ratio scatter: cost % vs margin %
    fig_cs1 = px.scatter(
        prod_agg,
        x="Cost Ratio (%)", y="Margin (%)",
        size="Total_Revenue", color="Division",
        color_discrete_map=DIV_COLORS,
        hover_name="Product Name",
        hover_data={"Total_Revenue": ":,.0f", "Total_Cost": ":,.0f", "Units_Sold": ":,"},
        text="Product Name",
        title="Cost Ratio (%) vs Gross Margin (%) — Size = Revenue",
        size_max=55,
    )
    fig_cs1.add_hline(y=65, line_dash="dot", line_color=C["amber"],
                       annotation_text="Target margin: 65%")
    fig_cs1.add_vline(x=35, line_dash="dot", line_color=C["amber"],
                       annotation_text="Target cost ratio: 35%")
    fig_cs1.update_traces(textposition="top center", textfont_size=8)
    fig_cs1.update_layout(height=460, margin=dict(t=40, b=20, l=10, r=10),
                           xaxis_title="Cost Ratio (% of Revenue)",
                           yaxis_title="Gross Margin (%)")
    col1.plotly_chart(fig_cs1, use_container_width=True)

    # Revenue vs Cost scatter
    fig_cs2 = px.scatter(
        prod_agg,
        x="Total_Revenue", y="Total_Cost",
        size="Total_Profit", color="Division",
        color_discrete_map=DIV_COLORS,
        hover_name="Product Name",
        hover_data={"Margin (%)": ":.1f", "Total_Profit": ":,.0f"},
        text="Product Name",
        title="Total Revenue vs Total Cost — Size = Gross Profit",
        size_max=55,
    )
    max_val = max(prod_agg["Total_Revenue"].max(), prod_agg["Total_Cost"].max())
    fig_cs2.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                       line=dict(dash="dash", color=C["red"], width=1.5))
    fig_cs2.add_annotation(x=max_val * 0.6, y=max_val * 0.65,
                             text="Cost = Revenue (0% margin)", showarrow=False,
                             font=dict(size=9, color=C["red"]))
    fig_cs2.update_traces(textposition="top center", textfont_size=8)
    fig_cs2.update_layout(height=460, margin=dict(t=40, b=20, l=10, r=10),
                           xaxis_title="Total Revenue ($)", yaxis_title="Total Cost ($)")
    col2.plotly_chart(fig_cs2, use_container_width=True)

    # Cost per unit vs revenue per unit
    fig_cs3 = px.scatter(
        prod_agg,
        x="Revenue per Unit", y=prod_agg["Total_Cost"] / prod_agg["Units_Sold"],
        size="Units_Sold", color="Division",
        color_discrete_map=DIV_COLORS,
        hover_name="Product Name",
        hover_data={"Margin (%)": ":.1f", "Profit per Unit": ":,.2f"},
        text="Product Name",
        title="Revenue per Unit vs Cost per Unit — Size = Units Sold",
        size_max=45,
    )
    max_u = max(prod_agg["Revenue per Unit"].max(),
                (prod_agg["Total_Cost"] / prod_agg["Units_Sold"]).max())
    fig_cs3.add_shape(type="line", x0=0, y0=0, x1=max_u, y1=max_u,
                       line=dict(dash="dash", color=C["red"], width=1.5))
    fig_cs3.update_traces(textposition="top center", textfont_size=8)
    fig_cs3.update_layout(height=400, margin=dict(t=40, b=20, l=10, r=10),
                           xaxis_title="Revenue per Unit ($)",
                           yaxis_title="Cost per Unit ($)")
    st.plotly_chart(fig_cs3, use_container_width=True)


with tab3b:
    st.subheader("Margin Risk Flag Analysis")

    # Risk classification from pre-computed cost diagnostics
    # Apply division filter
    cd_filt = cost_diag[cost_diag["Division"].isin(sel_divs)].copy() if not cost_diag.empty else cost_diag

    # Heatmap: product × metric
    col1, col2 = st.columns([2, 1])

    fig_risk_bar = go.Figure()
    risk_colors = []
    for _, row in cd_filt.iterrows():
        flag = str(row.get("Action Flag", ""))
        if "🔴" in flag:      risk_colors.append(C["red"])
        elif "🟡" in flag:    risk_colors.append(C["amber"])
        else:                  risk_colors.append(C["green"])

    fig_risk_bar.add_trace(go.Bar(
        y=cd_filt["Product Name"],
        x=cd_filt["Cost Ratio (%)"],
        orientation="h",
        marker_color=risk_colors,
        text=[f"{v:.1f}%" for v in cd_filt["Cost Ratio (%)"]],
        textposition="outside",
        customdata=cd_filt[["Margin (%)", "Diagnosis", "Action Flag"]].values,
        hovertemplate="<b>%{y}</b><br>Cost Ratio: %{x:.1f}%<br>Margin: %{customdata[0]:.1f}%<br>%{customdata[1]}<br>%{customdata[2]}<extra></extra>",
    ))
    fig_risk_bar.add_vline(x=35, line_dash="dash", line_color=C["amber"],
                            annotation_text="Target ≤35%")
    fig_risk_bar.update_layout(
        title="Cost Ratio (%) by Product — Red = Urgent, Amber = Monitor, Green = Healthy",
        height=480, xaxis_title="Cost as % of Revenue",
        yaxis_title="", margin=dict(t=40, b=20, l=10, r=80),
    )
    col1.plotly_chart(fig_risk_bar, use_container_width=True)

    with col2:
        st.markdown("##### Risk Summary")
        urgent  = cd_filt[cd_filt["Action Flag"].astype(str).str.contains("🔴", na=False)]
        medium  = cd_filt[cd_filt["Action Flag"].astype(str).str.contains("🟡", na=False)]
        healthy = cd_filt[cd_filt["Action Flag"].astype(str).str.contains("🟢", na=False)]
        st.metric("🔴 Urgent / High", len(urgent))
        st.metric("🟡 Medium / Monitor", len(medium))
        st.metric("🟢 Healthy", len(healthy))
        st.divider()
        if not urgent.empty:
            st.markdown("**🔴 Urgent Actions:**")
            for _, r in urgent.iterrows():
                st.error(f"**{r['Product Name']}** — {r['Diagnosis']}")

    # Detailed risk flags table
    st.subheader("Cost Diagnostics Detail Table")
    flag_display = cd_filt[[
        "Product Name", "Division", "Revenue ($)", "Total Cost ($)",
        "Cost Ratio (%)", "Margin (%)", "Profit/Unit ($)", "Cost/Unit ($)",
        "Diagnosis", "Action Flag"
    ]].copy()
    flag_display = flag_display.sort_values("Cost Ratio (%)", ascending=False)

    def color_flag_row(row):
        flag = str(row.get("Action Flag", ""))
        if "🔴" in flag:   return ["background-color: #fcebeb"] * len(row)
        elif "🟡" in flag: return ["background-color: #faeeda"] * len(row)
        elif "🟢" in flag: return ["background-color: #eaf3de"] * len(row)
        return [""] * len(row)

    st.dataframe(
        flag_display.style
            .apply(color_flag_row, axis=1)
            .format({
                "Revenue ($)": "${:,.2f}", "Total Cost ($)": "${:,.2f}",
                "Cost Ratio (%)": "{:.1f}%", "Margin (%)": "{:.1f}%",
                "Profit/Unit ($)": "${:,.2f}", "Cost/Unit ($)": "${:,.2f}",
            }),
        use_container_width=True, height=420,
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MODULE 4 — PROFIT CONCENTRATION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
st.header("📊 Module 4 — Profit Concentration Analysis")

tab4a, tab4b, tab4c = st.tabs(["📉 Pareto Chart", "🔗 Dependency Indicators", "🗺️ Geographic Concentration"])

with tab4a:
    st.subheader("Pareto Analysis — Revenue & Profit Concentration")

    # Recompute from filtered data
    pareto_live = prod_agg.sort_values("Total_Revenue", ascending=False).copy()
    pareto_live["Cum Rev (%)"]  = (pareto_live["Total_Revenue"].cumsum() / pareto_live["Total_Revenue"].sum() * 100).round(2)
    pareto_live["Cum Prof (%)"] = pareto_live.sort_values("Total_Profit", ascending=False)["Total_Profit"].cumsum() / pareto_live["Total_Profit"].sum() * 100
    pareto_live["Rev Share (%)"]= (pareto_live["Total_Revenue"] / pareto_live["Total_Revenue"].sum() * 100).round(2)

    # Pareto bar + cumulative line
    fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
    fig_pareto.add_trace(go.Bar(
        x=pareto_live["Product Name"],
        y=pareto_live["Rev Share (%)"],
        name="Revenue Share (%)",
        marker_color=[DIV_COLORS.get(d, C["gray"]) for d in pareto_live["Division"]],
        opacity=0.85,
    ), secondary_y=False)
    fig_pareto.add_trace(go.Scatter(
        x=pareto_live["Product Name"],
        y=pareto_live["Cum Rev (%)"],
        name="Cumulative Revenue (%)",
        mode="lines+markers",
        line=dict(color=C["navy"], width=2.5),
        marker=dict(size=7),
    ), secondary_y=True)
    fig_pareto.add_hline(y=80, secondary_y=True, line_dash="dash",
                          line_color=C["red"],
                          annotation_text="80% threshold", annotation_position="right")
    fig_pareto.update_layout(
        title="Pareto Chart — Revenue Concentration (80/20 Rule)",
        height=440, barmode="group",
        xaxis_tickangle=-35,
        legend=dict(orientation="h", y=1.05),
        margin=dict(t=60, b=100, l=10, r=10),
    )
    fig_pareto.update_yaxes(title_text="Revenue Share (%)", secondary_y=False)
    fig_pareto.update_yaxes(title_text="Cumulative Revenue (%)", secondary_y=True, range=[0, 105])
    st.plotly_chart(fig_pareto, use_container_width=True)

    # Pareto for PROFIT
    pareto_profit = prod_agg.sort_values("Total_Profit", ascending=False).copy()
    pareto_profit["Cum Prof (%)"]   = (pareto_profit["Total_Profit"].cumsum() / pareto_profit["Total_Profit"].sum() * 100).round(2)
    pareto_profit["Prof Share (%)"] = (pareto_profit["Total_Profit"] / pareto_profit["Total_Profit"].sum() * 100).round(2)

    fig_pareto2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig_pareto2.add_trace(go.Bar(
        x=pareto_profit["Product Name"],
        y=pareto_profit["Prof Share (%)"],
        name="Profit Share (%)",
        marker_color=[DIV_COLORS.get(d, C["gray"]) for d in pareto_profit["Division"]],
        opacity=0.85,
    ), secondary_y=False)
    fig_pareto2.add_trace(go.Scatter(
        x=pareto_profit["Product Name"],
        y=pareto_profit["Cum Prof (%)"],
        name="Cumulative Profit (%)",
        mode="lines+markers",
        line=dict(color=C["green"], width=2.5),
        marker=dict(size=7),
    ), secondary_y=True)
    fig_pareto2.add_hline(y=80, secondary_y=True, line_dash="dash", line_color=C["red"],
                           annotation_text="80% threshold")
    fig_pareto2.update_layout(
        title="Pareto Chart — Profit Concentration (80/20 Rule)",
        height=440, xaxis_tickangle=-35,
        legend=dict(orientation="h", y=1.05),
        margin=dict(t=60, b=100, l=10, r=10),
    )
    fig_pareto2.update_yaxes(title_text="Profit Share (%)", secondary_y=False)
    fig_pareto2.update_yaxes(title_text="Cumulative Profit (%)", secondary_y=True, range=[0, 105])
    st.plotly_chart(fig_pareto2, use_container_width=True)

    # Pareto insight banner
    top4_rev  = pareto_live.head(4)["Cum Rev (%)"].max()
    top4_prof = pareto_profit.head(4)["Cum Prof (%)"].max()
    st.info(
        f"📌 **Pareto Insight:** Top 4 products ({round(4/prod_agg.shape[0]*100,0):.0f}% of SKUs) "
        f"drive **{top4_rev:.1f}% of revenue** and **{top4_prof:.1f}% of profit**. "
        f"The Chocolate division IS the business."
    )


with tab4b:
    st.subheader("Product & Division Dependency Indicators")
    col1, col2 = st.columns(2)

    # Dependency gauge: top-1 product profit share
    top1_share = pareto_profit.iloc[0]["Prof Share (%)"] if len(pareto_profit) > 0 else 0
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=top1_share,
        title={"text": f"Top Product Profit Dependency<br><span style='font-size:12px'>{pareto_profit.iloc[0]['Product Name'] if len(pareto_profit)>0 else ''}</span>"},
        number={"suffix": "%", "font": {"size": 36}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": C["navy"]},
            "steps": [
                {"range": [0, 25],  "color": "#D5EDCD"},
                {"range": [25, 50], "color": "#FFF2CC"},
                {"range": [50, 75], "color": "#FFD9B3"},
                {"range": [75, 100],"color": "#FFBBBB"},
            ],
            "threshold": {"line": {"color": C["red"], "width": 3}, "value": 50},
        },
    ))
    fig_gauge.update_layout(height=320, margin=dict(t=80, b=20, l=40, r=40))
    col1.plotly_chart(fig_gauge, use_container_width=True)

    # Division concentration gauge
    top_div_share = div_agg.sort_values("Profit Share (%)", ascending=False).iloc[0]["Profit Share (%)"] if len(div_agg) > 0 else 0
    top_div_name  = div_agg.sort_values("Profit Share (%)", ascending=False).iloc[0]["Division"] if len(div_agg) > 0 else ""
    fig_gauge2 = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=top_div_share,
        title={"text": f"Top Division Profit Dependency<br><span style='font-size:12px'>{top_div_name} Division</span>"},
        number={"suffix": "%", "font": {"size": 36}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": C["brown"]},
            "steps": [
                {"range": [0, 40],  "color": "#D5EDCD"},
                {"range": [40, 70], "color": "#FFF2CC"},
                {"range": [70, 90], "color": "#FFD9B3"},
                {"range": [90, 100],"color": "#FFBBBB"},
            ],
            "threshold": {"line": {"color": C["red"], "width": 3}, "value": 80},
        },
    ))
    fig_gauge2.update_layout(height=320, margin=dict(t=80, b=20, l=40, r=40))
    col2.plotly_chart(fig_gauge2, use_container_width=True)

    # Concentration risk bars
    st.subheader("Concentration Metrics — Dependency Table")
    n_prod = prod_agg.shape[0]
    pareto_sorted = prod_agg.sort_values("Total_Profit", ascending=False).copy()
    pareto_sorted["Cum Prof (%)"] = (pareto_sorted["Total_Profit"].cumsum() / pareto_sorted["Total_Profit"].sum() * 100).round(1)
    milestone_rows = []
    for pct in [25, 50, 75, 80, 90]:
        sub = pareto_sorted[pareto_sorted["Cum Prof (%)"] >= pct]
        n   = len(pareto_sorted) - len(sub) + 1 if not sub.empty else n_prod
        milestone_rows.append({
            "Profit Threshold": f"{pct}%",
            "# Products Required": n,
            "% of Total SKUs": f"{n/n_prod*100:.1f}%",
            "Concentration Level": "🔴 Critical" if pct>=80 and n<=3 else ("🟡 High" if pct>=80 and n<=6 else "🟢 Healthy"),
        })
    st.dataframe(pd.DataFrame(milestone_rows), use_container_width=True, hide_index=True)

    # Strategic action summary
    st.subheader("📋 Strategic Action Summary")
    actions = [
        ("🔴 URGENT",   "Cost Renegotiate / Discontinue", "Kazookles (OTH-KAZ-38000)",       "Cost ratio 92.3%. Renegotiate factory pricing or remove from portfolio."),
        ("🔴 HIGH",     "Reprice Upward",                  "Fun Dip, SweeTARTS, Nerds",        "Margins 40–47%. Prices set too low. Benchmark against Chocolate margins (65%+)."),
        ("🟡 MEDIUM",   "Factory Cost Review",             "Lickable Wallpaper",               "50% margin on $7,860 revenue. Cost equals profit — factory cost renegotiation needed."),
        ("🟡 MEDIUM",   "Discontinuation Review",          "Fizzy Lifting Drinks, Laffy Taffy, Wonka Gum", "Combined revenue <$730. Administrative burden may exceed marginal profit."),
        ("🟢 GROW",     "Promote High-Margin Sugar SKUs",  "Everlasting Gobstopper, Hair Toffee", "Margins 78–80% — highest in portfolio. Bundle with Chocolate bars to drive volume."),
        ("🟢 PROTECT",  "Maintain & Expand Chocolate",     "All 5 Chocolate Wonka Bars",       "$88,824 gross profit, 95% of portfolio profit. Protect pricing power and supply."),
    ]
    for priority, action, products, detail in actions:
        col_p, col_a, col_pr, col_d = st.columns([1.2, 1.8, 2.2, 4])
        col_p.markdown(f"**{priority}**")
        col_a.write(action)
        col_pr.write(products)
        col_d.write(detail)
        st.markdown("<hr style='margin:4px 0; border-color:#e0e0e0'>", unsafe_allow_html=True)


with tab4c:
    st.subheader("Geographic Revenue Concentration")

    geo_data = [
        ("California",   "Pacific",   27917.40, 2001, 0.197, 0.197, "🔴 HIGH DEPENDENCY"),
        ("New York",     "Atlantic",  15541.03, 1128, 0.110, 0.307, "🔴 HIGH DEPENDENCY"),
        ("Texas",        "Interior",  13416.09,  985, 0.095, 0.401, "🔴 HIGH DEPENDENCY"),
        ("Pennsylvania", "Atlantic",   8027.03,  587, 0.057, 0.458, "🟡 MODERATE"),
        ("Washington",   "Pacific",    6921.15,  506, 0.049, 0.507, "🟡 MODERATE"),
        ("Illinois",     "Interior",   6898.96,  492, 0.049, 0.555, "🟡 MODERATE"),
        ("Ohio",         "Atlantic",   6768.95,  469, 0.048, 0.603, "🟡 MODERATE"),
        ("Florida",      "Gulf",       4804.02,  383, 0.034, 0.637, "🟢 NORMAL"),
        ("Arizona",      "Pacific",    3587.55,  224, 0.025, 0.662, "🟢 NORMAL"),
        ("North Carolina","Gulf",      3450.86,  249, 0.024, 0.686, "🟢 NORMAL"),
        ("Michigan",     "Interior",   3331.00,  255, 0.023, 0.710, "🟢 NORMAL"),
        ("Virginia",     "Gulf",       3177.84,  224, 0.022, 0.732, "🟢 NORMAL"),
        ("Georgia",      "Gulf",       2692.84,  184, 0.019, 0.751, "🟢 NORMAL"),
        ("Colorado",     "Pacific",    2544.91,  182, 0.018, 0.769, "🟢 NORMAL"),
        ("Tennessee",    "Gulf",       2383.56,  183, 0.017, 0.786, "🟢 NORMAL"),
        ("Indiana",      "Interior",   2002.78,  149, 0.014, 0.800, "🟢 NORMAL"),
    ]
    geo_df = pd.DataFrame(geo_data, columns=[
        "State", "Region", "Revenue ($)", "Transactions",
        "Rev Share", "Cum Rev", "Dependency Flag"
    ])
    geo_df["Rev Share (%)"]  = (geo_df["Rev Share"] * 100).round(1)
    geo_df["Cum Rev (%)"]    = (geo_df["Cum Rev"]   * 100).round(1)

    dep_colors = {"🔴 HIGH DEPENDENCY": C["red"], "🟡 MODERATE": C["amber"], "🟢 NORMAL": C["green"]}

    col1, col2 = st.columns(2)

    fig_geo_bar = go.Figure(go.Bar(
        x=geo_df["State"], y=geo_df["Rev Share (%)"],
        marker_color=[dep_colors.get(f, C["gray"]) for f in geo_df["Dependency Flag"]],
        text=[f"{v:.1f}%" for v in geo_df["Rev Share (%)"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Share: %{y:.1f}%<extra></extra>",
    ))
    fig_geo_bar.update_layout(
        title="Top 16 States — Revenue Share (%)",
        height=380, xaxis_tickangle=-40,
        yaxis_title="Revenue Share (%)",
        margin=dict(t=40, b=100, l=10, r=10),
    )
    col1.plotly_chart(fig_geo_bar, use_container_width=True)

    # Cumulative line (Pareto for states)
    fig_geo_cum = make_subplots(specs=[[{"secondary_y": True}]])
    fig_geo_cum.add_trace(go.Bar(
        x=geo_df["State"], y=geo_df["Rev Share (%)"],
        marker_color=[dep_colors.get(f, C["gray"]) for f in geo_df["Dependency Flag"]],
        name="Rev Share (%)", opacity=0.8,
    ), secondary_y=False)
    fig_geo_cum.add_trace(go.Scatter(
        x=geo_df["State"], y=geo_df["Cum Rev (%)"],
        mode="lines+markers", name="Cumulative (%)",
        line=dict(color=C["navy"], width=2.5), marker=dict(size=7),
    ), secondary_y=True)
    fig_geo_cum.add_hline(y=80, secondary_y=True, line_dash="dash",
                           line_color=C["red"], annotation_text="80% line")
    fig_geo_cum.update_layout(
        title="Geographic Revenue Concentration (Pareto)",
        height=380, xaxis_tickangle=-40,
        legend=dict(orientation="h", y=1.05),
        margin=dict(t=60, b=100, l=10, r=10),
    )
    fig_geo_cum.update_yaxes(title_text="Rev Share (%)", secondary_y=False)
    fig_geo_cum.update_yaxes(title_text="Cumulative (%)", secondary_y=True, range=[0, 105])
    col2.plotly_chart(fig_geo_cum, use_container_width=True)

    st.warning(
        "🌎 **Geographic Risk:** California (19.7%), New York (10.9%), Texas (9.5%) = **40.1% of revenue in 3 states**. "
        "Top 7 states = 60.3%. Only 16 of 59 states needed to reach 80% revenue. "
        "**Recommendation:** Prioritize sales growth in Midwest and Gulf states."
    )

    st.dataframe(
        geo_df[["State", "Region", "Revenue ($)", "Transactions", "Rev Share (%)", "Cum Rev (%)", "Dependency Flag"]]
        .style.format({"Revenue ($)": "${:,.2f}", "Rev Share (%)": "{:.1f}%", "Cum Rev (%)": "{:.1f}%"})
        .apply(lambda row: [
            f"background-color: {dep_colors.get(row['Dependency Flag'], '#fff')}22" if col == "Dependency Flag"
            else "" for col in row.index
        ], axis=1),
        use_container_width=True, hide_index=True,
    )

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='text-align:center; color:#888; font-size:12px; padding:12px 0;'>
    🍬 Nassau Candy Distributor · Product Profitability Analytics ·
    Built with <strong>Streamlit</strong> & <strong>Plotly</strong>
    </div>
    """,
    unsafe_allow_html=True,
)
