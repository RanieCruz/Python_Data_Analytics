from pathlib import Path
import html

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Retail Analytics Command Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BLUE = "#44AFF2"
ORANGE = "#F47A2A"

PALETTE = [
    "#023059",
    "#1462A6",
    "#44AFF2",
    "#ACD7F2",
    "#E4EDF2",
    ]


# ============================================================
# 2. MODERN DASHBOARD STYLING
# ============================================================

st.markdown(
    f"""
    <style>
        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 2rem;
        }}

        .hero {{
            border: 1px solid #44AFF2;
            border-radius: 20px;
            padding: 1.35rem 1.55rem;
            background:
                linear-gradient(
                    135deg,
                    rgba(2,71,183,0.10),
                    rgba(56,163,255,0.03)
                );
            margin-bottom: .9rem;
        }}

        .hero-kicker {{
            color: #FFFFFF;
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .09em;
            text-transform: capitalize;
        }}

        .hero-title {{
            color: #FFFFFF;
            font-size: 2.15rem;
            font-weight: 800;
            margin-top: .15rem;
            margin-bottom: .2rem;
        }}

        .hero-sub {{
            color: #FFFFFF;
            font-size: .98rem;
        }}

        .chips {{
            display: flex;
            flex-wrap: wrap;
            gap: .4rem;
            margin: .25rem 0 1rem 0;
        }}

        .chip {{
            background: #1462A6;
            border: 1px solid #44AFF2;
            color: #E4EDF2;
            border-radius: 999px;
            padding: .28rem .62rem;
            font-size: .8rem;
            font-weight: 650;
        }}

        div[data-testid="stMetric"] {{
            padding-top: .25rem;
            padding-bottom: .25rem;
        }}

        .section-note {{
            color: #FFFFFF;
            font-size: .86rem;
            margin-top: -.4rem;
            margin-bottom: .8rem;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)



# ============================================================
# 3. HELPERS
# ============================================================

def compact_number(value, decimals=2):
    if pd.isna(value):
        return "0"

    value = float(value)
    absolute = abs(value)

    if absolute >= 1_000_000_000:
        number = value / 1_000_000_000
        suffix = "B"
    elif absolute >= 1_000_000:
        number = value / 1_000_000
        suffix = "M"
    elif absolute >= 1_000:
        number = value / 1_000
        suffix = "K"
    else:
        return f"{value:,.0f}"

    text = f"{number:.{decimals}f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def clean_money(series):
    return pd.to_numeric(
        series.astype("string")
        .str.replace("₱", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def find_data_file(candidates):
    roots = [
        Path("data"),
        Path("."),
        Path("/mnt/data"),
    ]

    for root in roots:
        for name in candidates:
            path = root / name
            if path.exists():
                return path

    raise FileNotFoundError(
        "Could not find: " + ", ".join(candidates)
    )


def style_figure(fig, height=410):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(
            l=20,
            r=20,
            t=62,
            b=30,
        ),
        font=dict(
            family="Inter, Segoe UI, sans-serif",
            size=12,
            color="#E4EDF2",
        ),
        title=dict(
            font=dict(
                size=17,
                color="#E4EDF2",
            ),
            x=.01,
            xanchor="left",
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
        ),
    )
    return fig


def chart_card(fig):
    with st.container(border=True):
        st.plotly_chart(
            fig,
            width="stretch",
        )


def filter_sales(
    dataframe,
    start_date,
    end_date,
    regions,
    channels,
    categories,
    shipping_methods,
):
    result = dataframe[
        dataframe["order_date"].notna()
    ].copy()

    result = result[
        result["order_date"].dt.date.between(
            start_date,
            end_date,
        )
    ]

    if regions:
        result = result[
            result["region_name"].isin(regions)
        ]

    if channels:
        result = result[
            result["sales_channel"].isin(channels)
        ]

    if categories:
        result = result[
            result["category_clean"].isin(categories)
        ]

    if shipping_methods:
        result = result[
            result["shipping_method"].isin(shipping_methods)
        ]

    return result.copy()


def make_filter_chips(
    start_date,
    end_date,
    regions,
    channels,
    categories,
):
    values = [
        f"{start_date:%d %b %Y} – {end_date:%d %b %Y}",
        f"Regions: {len(regions)}",
        f"Channels: {len(channels)}",
        f"Categories: {len(categories)}",
    ]

    tags = "".join(
        (
            '<span class="chip">'
            f"{html.escape(v)}"
            "</span>"
        )
        for v in values
    )

    st.markdown(
        f'<div class="chips">{tags}</div>',
        unsafe_allow_html=True,
    )

def get_pct_change(current, previous):
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def format_sales(val):
        if val >= 1_000_000:
            return f"₱{val / 1_000_000:,.1f}M"
        elif val >= 1_000:
            return f"₱{val / 1_000:,.1f}K"
        else:
            return f"₱{val:,.0f}"
    
# ============================================================
# 4. LOAD + CLEAN ALL SEVEN DATASETS
# ============================================================

@st.cache_data
def load_data():
    customer_file = find_data_file(
        [
            "customers.csv",
            "customers(20261017-082937).csv",
        ]
    )

    product_file = find_data_file(
        [
            "products.csv",
            "products(1).csv",
        ]
    )

    order_file = find_data_file(
        [
            "orders.csv",
            "orders(1).csv",
        ]
    )

    item_file = find_data_file(
        [
            "order_items.csv",
            "order_items(1).csv",
        ]
    )

    payment_file = find_data_file(
        [
            "payments.csv",
            "payments(1).csv",
        ]
    )

    shipment_file = find_data_file(
        [
            "shipments.csv",
            "shipments(1).csv",
        ]
    )

    return_file = find_data_file(
        [
            "returns.csv",
            "returns(1).csv",
        ]
    )

    # --------------------------------------------------------
    # READ RAW FILES
    # --------------------------------------------------------

    customers_raw = pd.read_csv(customer_file)
    products_raw = pd.read_csv(product_file)
    orders_raw = pd.read_csv(order_file)
    items_raw = pd.read_csv(item_file)
    payments_raw = pd.read_csv(payment_file)
    shipments_raw = pd.read_csv(shipment_file)
    returns_raw = pd.read_csv(return_file)

    raw_counts = {
        "Customers": len(customers_raw),
        "Products": len(products_raw),
        "Orders": len(orders_raw),
        "Order Items": len(items_raw),
        "Payments": len(payments_raw),
        "Shipments": len(shipments_raw),
        "Returns": len(returns_raw),
    }

    # --------------------------------------------------------
    # DUPLICATES
    # --------------------------------------------------------

    customers = customers_raw.drop_duplicates().copy()
    products = products_raw.drop_duplicates().copy()
    orders = orders_raw.drop_duplicates().copy()
    items = items_raw.drop_duplicates().copy()
    payments = payments_raw.drop_duplicates().copy()
    shipments = shipments_raw.drop_duplicates().copy()
    returns = returns_raw.drop_duplicates().copy()

    # --------------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------------

    customers["customer_name"] = (
        customers["first_name"]
        .fillna("")
        .astype(str)
        .str.strip()
        + " "
        + customers["last_name"]
        .fillna("")
        .astype(str)
        .str.strip()
    ).str.strip()

    gender_map = {
        "m": "Male",
        "male": "Male",
        "f": "Female",
        "female": "Female",
    }

    customers["gender_clean"] = (
        customers["gender"]
        .astype("string")
        .str.strip()
        .str.lower()
        .replace(gender_map)
        .fillna("Unknown")
    )

    customers["age_clean"] = pd.to_numeric(
        customers["age"],
        errors="coerce",
    )

    customers.loc[
        ~customers["age_clean"].between(
            18,
            100,
        ),
        "age_clean",
    ] = pd.NA

    customers["signup_date_clean"] = pd.to_datetime(
        customers["signup_date"],
        format="mixed",
        errors="coerce",
    )

    # --------------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------------

    category_map = {
        "electronics": "Electronics",
        "elec": "Electronics",
        "home & kitchen": "Home & Kitchen",
        "home and kitchen": "Home & Kitchen",
        "books": "Books",
        "book": "Books",
        "groceries": "Groceries",
        "grocery": "Groceries",
        "toys": "Toys",
        "toy": "Toys",
        "beauty": "Beauty",
        "beauty & care": "Beauty",
        "fashion": "Fashion",
        "fashon": "Fashion",
        "sports": "Sports",
        "sports & outdoor": "Sports",
    }

    products["category_clean"] = (
        products["category"]
        .astype("string")
        .str.strip()
        .str.lower()
        .replace(category_map)
        .fillna("Unknown")
    )

    products["unit_cost_clean"] = clean_money(
        products["unit_cost"]
    )

    products["list_price_clean"] = clean_money(
        products["unit_price"]
    )

    products["stock_qty_clean"] = pd.to_numeric(
        products["stock_qty"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # ORDERS
    # --------------------------------------------------------

    orders["order_date"] = pd.to_datetime(
        orders["order_datetime"],
        format="mixed",
        errors="coerce",
    )

    orders["discount_pct_clean"] = pd.to_numeric(
        orders["discount_pct"],
        errors="coerce",
    ).fillna(0)

    orders.loc[
        ~orders["discount_pct_clean"].between(
            0,
            1,
        ),
        "discount_pct_clean",
    ] = 0

    orders["shipping_fee_clean"] = clean_money(
        orders["shipping_fee"]
    ).fillna(0)

    # Referential integrity: valid customer
    orders = orders[
        orders["customer_id"].isin(
            customers["customer_id"]
        )
    ].copy()

    # --------------------------------------------------------
    # ORDER ITEMS
    # --------------------------------------------------------

    items["quantity_clean"] = pd.to_numeric(
        items["quantity"],
        errors="coerce",
    )

    items["unit_price_clean"] = clean_money(
        items["unit_price_at_purchase"]
    )

    items = items[
        (items["quantity_clean"] > 0)
        & items["unit_price_clean"].notna()
        & items["product_id"].isin(
            products["product_id"]
        )
        & items["order_id"].isin(
            orders["order_id"]
        )
    ].copy()

    # --------------------------------------------------------
    # SALES ANALYSIS - ITEM LEVEL
    # --------------------------------------------------------

    sales_all = (
        items
        .merge(
            orders[
                [
                    "order_id",
                    "customer_id",
                    "order_date",
                    "order_status",
                    "sales_channel",
                    "shipping_method",
                    "discount_pct_clean",
                    "shipping_fee_clean",
                ]
            ],
            on="order_id",
            how="inner",
            validate="many_to_one",
        )
        .merge(
            products[
                [
                    "product_id",
                    "product_name",
                    "brand",
                    "category_clean",
                    "unit_cost_clean",
                    "list_price_clean",
                    "stock_qty_clean",
                ]
            ],
            on="product_id",
            how="inner",
            validate="many_to_one",
        )
        .merge(
            customers[
                [
                    "customer_id",
                    "customer_name",
                    "gender_clean",
                    "age_clean",
                    "region_name",
                    "city",
                    "barangay",
                    "loyalty_tier",
                ]
            ],
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
    )

    sales_all["gross_sales"] = (
        sales_all["quantity_clean"]
        * sales_all["unit_price_clean"]
    )

    sales_all["net_sales"] = (
        sales_all["gross_sales"]
        * (
            1
            - sales_all["discount_pct_clean"]
        )
    )

    sales_all["discount_amount"] = (
        sales_all["gross_sales"]
        - sales_all["net_sales"]
    )

    sales_all["estimated_cost"] = (
        sales_all["quantity_clean"]
        * sales_all["unit_cost_clean"]
    )

    sales_all["estimated_profit"] = (
        sales_all["net_sales"]
        - sales_all["estimated_cost"]
    )

    sales_all["month"] = (
        sales_all["order_date"]
        .dt.to_period("M")
        .astype("string")
    )

    sales_all["weekday"] = (
        sales_all["order_date"]
        .dt.day_name()
    )

    sales_all["hour"] = (
        sales_all["order_date"]
        .dt.hour
    )

    # --------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------

    payments["amount_paid_clean"] = clean_money(
        payments["amount_paid"]
    )

    payments["payment_date_clean"] = pd.to_datetime(
        payments["payment_date"],
        format="mixed",
        errors="coerce",
    )

    # --------------------------------------------------------
    # SHIPMENTS
    # --------------------------------------------------------

    shipments["ship_date_clean"] = pd.to_datetime(
        shipments["ship_date"],
        format="mixed",
        errors="coerce",
    )

    shipments["delivered_date_clean"] = pd.to_datetime(
        shipments["delivered_date"],
        format="mixed",
        errors="coerce",
    )

    shipments["delivery_days"] = (
        shipments["delivered_date_clean"]
        - shipments["ship_date_clean"]
    ).dt.days

    shipments.loc[
        shipments["delivery_days"] < 0,
        "delivery_days",
    ] = pd.NA

    # --------------------------------------------------------
    # RETURNS
    # --------------------------------------------------------

    returns["return_request_date_clean"] = pd.to_datetime(
        returns["return_request_date"],
        format="mixed",
        errors="coerce",
    )

    returns["refund_amount_clean"] = clean_money(
        returns["refund_amount"]
    ).fillna(0)

    returns["refunded_flag_clean"] = (
        returns["refunded_flag"]
        .astype("string")
        .str.strip()
        .str.title()
        .fillna("Unknown")
    )

    # --------------------------------------------------------
    # ORDER-LEVEL SUMMARY
    # --------------------------------------------------------

    order_summary = (
        sales_all
        .groupby(
            "order_id",
            as_index=False,
        )
        .agg(
            customer_id=("customer_id", "first"),
            customer_name=("customer_name", "first"),
            order_date=("order_date", "first"),
            order_status=("order_status", "first"),
            sales_channel=("sales_channel", "first"),
            shipping_method=("shipping_method", "first"),
            region_name=("region_name", "first"),
            city=("city", "first"),
            loyalty_tier=("loyalty_tier", "first"),
            discount_pct=(
                "discount_pct_clean",
                "first",
            ),
            shipping_fee=(
                "shipping_fee_clean",
                "first",
            ),
            gross_order_value=(
                "gross_sales",
                "sum",
            ),
            net_order_value=(
                "net_sales",
                "sum",
            ),
            discount_amount=(
                "discount_amount",
                "sum",
            ),
            estimated_cost=(
                "estimated_cost",
                "sum",
            ),
            estimated_profit=(
                "estimated_profit",
                "sum",
            ),
            units=("quantity_clean", "sum"),
            line_items=("order_item_id", "nunique"),
        )
    )

    order_summary["profit_margin_pct"] = (
        order_summary["estimated_profit"]
        / order_summary["net_order_value"]
        * 100
    )

    order_summary["month"] = (
        order_summary["order_date"]
        .dt.to_period("M")
        .astype("string")
    )

    order_summary["weekday"] = (
        order_summary["order_date"]
        .dt.day_name()
    )

    order_summary["hour"] = (
        order_summary["order_date"]
        .dt.hour
    )

    clean_counts = {
        "Customers": len(customers),
        "Products": len(products),
        "Orders": len(orders),
        "Order Items": len(items),
        "Payments": len(payments),
        "Shipments": len(shipments),
        "Returns": len(returns),
    }

    return {
        "customers": customers,
        "products": products,
        "sales_all": sales_all,
        "order_summary": order_summary,
        "payments": payments,
        "shipments": shipments,
        "returns": returns,
        "raw_counts": raw_counts,
        "clean_counts": clean_counts,
    }


# ============================================================
# 5. LOAD DATA
# ============================================================

try:
    data = load_data()

except FileNotFoundError as error:
    st.error(
        "One or more retail CSV files could not be found."
    )
    st.exception(error)
    st.stop()


customers = data["customers"]
products = data["products"]
sales_all = data["sales_all"]
order_summary = data["order_summary"]
payments = data["payments"]
shipments = data["shipments"]
returns = data["returns"]
raw_counts = data["raw_counts"]
clean_counts = data["clean_counts"]


# ============================================================
# 6. FILTER STATE
# ============================================================

date_series = sales_all["order_date"].dropna()

min_date = date_series.min().date()
max_date = date_series.max().date()

all_regions = sorted(
    sales_all["region_name"]
    .dropna()
    .unique()
    .tolist()
)

all_channels = sorted(
    sales_all["sales_channel"]
    .dropna()
    .unique()
    .tolist()
)

all_categories = sorted(
    sales_all["category_clean"]
    .dropna()
    .unique()
    .tolist()
)

all_shipping_methods = sorted(
    sales_all["shipping_method"]
    .dropna()
    .unique()
    .tolist()
)


def reset_filters():
    st.session_state["date_range"] = (
        min_date,
        max_date,
    )
    st.session_state["regions"] = all_regions
    st.session_state["channels"] = all_channels
    st.session_state["categories"] = all_categories
    st.session_state["shipping_methods"] = all_shipping_methods


if "date_range" not in st.session_state:
    reset_filters()


# ============================================================
# 7. SIDEBAR
# ============================================================

with st.sidebar:
    st.header("Dashboard Filters")
    st.caption(
        "Filters apply across all analytical sections."
    )

    selected_dates = st.date_input(
        "Order date range",
        min_value=min_date,
        max_value=max_date,
        key="date_range",
    )

    if isinstance(selected_dates, (tuple, list)):
        if len(selected_dates) == 2:
            start_date = selected_dates[0]
            end_date = selected_dates[1]
        else:
            start_date = min_date
            end_date = max_date
    else:
        start_date = selected_dates
        end_date = selected_dates

    selected_regions = st.multiselect(
        "Region",
        all_regions,
        key="regions",
    )

    selected_channels = st.multiselect(
        "Sales Channel",
        all_channels,
        key="channels",
    )

    selected_categories = st.multiselect(
        "Product Category",
        all_categories,
        key="categories",
    )

    selected_shipping = st.multiselect(
        "Shipping Method",
        all_shipping_methods,
        key="shipping_methods",
    )

    st.button(
        "Reset Filters",
        width="stretch",
        type="primary",
        on_click=reset_filters,
    )

    st.divider()

    st.caption(
        "Sales KPIs use fulfilled orders: Completed + Shipped."
    )


# ============================================================
# 8. FILTER ANALYTICAL DATA
# ============================================================

filtered_all = filter_sales(
    sales_all,
    start_date,
    end_date,
    selected_regions,
    selected_channels,
    selected_categories,
    selected_shipping,
)

if filtered_all.empty:
    st.warning(
        "No records match the selected filters."
    )
    st.stop()


filtered_fulfilled = filtered_all[
    filtered_all["order_status"].isin(
        [
            "Completed",
            "Shipped",
        ]
    )
].copy()

matching_all_order_ids = (
    filtered_all["order_id"]
    .drop_duplicates()
    .tolist()
)

matching_fulfilled_order_ids = (
    filtered_fulfilled["order_id"]
    .drop_duplicates()
    .tolist()
)

filtered_orders_all = order_summary[
    order_summary["order_id"].isin(
        matching_all_order_ids
    )
].copy()

filtered_orders_fulfilled = order_summary[
    order_summary["order_id"].isin(
        matching_fulfilled_order_ids
    )
].copy()

payment_scope = payments[
    payments["order_id"].isin(
        matching_all_order_ids
    )
].copy()

shipment_scope = shipments[
    shipments["order_id"].isin(
        matching_all_order_ids
    )
].copy()

return_scope = returns[
    returns["order_id"].isin(
        matching_all_order_ids
    )
].copy()


# ============================================================
# 9. HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">DataSense Analytics Founders Mentoring Program Batch 04</div>
        <div class="hero-title">
            Executive Retail Intelligence Hub
        </div>
        <div class="hero-sub">
            Unified analytics across sales performance, customer growth, profitability, and logistics.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

make_filter_chips(
    start_date,
    end_date,
    selected_regions,
    selected_channels,
    selected_categories,
)


# ============================================================
# 10. EXECUTIVE KPI STRIP
# ============================================================

# ============================================================
# 6. FILTER STATE, DATES & METRIC CALCULATIONS (WITH "ALL YEARS")
# ============================================================

from datetime import date

date_series = sales_all["order_date"].dropna()
min_date = date_series.min().date()
max_date = date_series.max().date()

sales_all["year"] = sales_all["order_date"].dt.year
available_years = sorted(sales_all["year"].dropna().unique().astype(int).tolist())

if not available_years:
    available_years = [max_date.year]

# Add "All Years" to the dropdown options
all_years_options = ["All Years"] + available_years

all_regions = sorted(sales_all["region_name"].dropna().unique().tolist())
all_channels = sorted(sales_all["sales_channel"].dropna().unique().tolist())
all_categories = sorted(sales_all["category_clean"].dropna().unique().tolist())
all_shipping_methods = sorted(sales_all["shipping_method"].dropna().unique().tolist())

# Safely initialize session state keys BEFORE any widgets are rendered
if "selected_year" not in st.session_state:
    st.session_state["selected_year"] = "All Years"  # Default to All Years
if "regions" not in st.session_state:
    st.session_state["regions"] = all_regions
if "channels" not in st.session_state:
    st.session_state["channels"] = all_channels
if "categories" not in st.session_state:
    st.session_state["categories"] = all_categories
if "shipping_methods" not in st.session_state:
    st.session_state["shipping_methods"] = all_shipping_methods

# Render Year Selector Widget
selected_year = st.selectbox(
    "Select Year",
    options=all_years_options,
    key="selected_year"
)

# Derive date boundaries based on selection
if selected_year == "All Years":
    curr_start_date = min_date
    curr_end_date = max_date
    # Compare against the prior span of equivalent duration or shift back 1 full year block
    prev_start_date = curr_start_date.replace(year=curr_start_date.year - 1)
    prev_end_date = curr_end_date.replace(year=curr_end_date.year - 1)
else:
    curr_start_date = max(date(selected_year, 1, 1), min_date)
    curr_end_date = max_date if selected_year == max_date.year else date(selected_year, 12, 31)
    
    try:
        prev_start_date = curr_start_date.replace(year=curr_start_date.year - 1)
        prev_end_date = curr_end_date.replace(year=curr_end_date.year - 1)
    except ValueError:
        prev_start_date = curr_start_date.replace(year=curr_start_date.year - 1, day=28)
        prev_end_date = curr_end_date.replace(year=curr_end_date.year - 1, day=28)

# ------------------------------------------------------------
# FILTER DATA FOR CURRENT & PREVIOUS YEARS + SIDEBAR FILTERS
# ------------------------------------------------------------

def apply_filters(df, start_d, end_d):
    filtered = df[
        (df["order_date"].dt.date >= start_d) & 
        (df["order_date"].dt.date <= end_d)
    ].copy()
    
    if "order_status" in filtered.columns:
        valid_statuses = ["fulfilled", "completed", "delivered", "shipped"]
        status_filtered = filtered[filtered["order_status"].str.lower().isin(valid_statuses)]
        if not status_filtered.empty:
            filtered = status_filtered
            
    if "regions" in st.session_state and st.session_state["regions"] and "region_name" in filtered.columns:
        filtered = filtered[filtered["region_name"].isin(st.session_state["regions"])]
    if "channels" in st.session_state and st.session_state["channels"] and "sales_channel" in filtered.columns:
        filtered = filtered[filtered["sales_channel"].isin(st.session_state["channels"])]
    if "categories" in st.session_state and st.session_state["categories"] and "category_clean" in filtered.columns:
        filtered = filtered[filtered["category_clean"].isin(st.session_state["categories"])]
    if "shipping_methods" in st.session_state and st.session_state["shipping_methods"] and "shipping_method" in filtered.columns:
        filtered = filtered[filtered["shipping_method"].isin(st.session_state["shipping_methods"])]
        
    return filtered

filtered_fulfilled = apply_filters(sales_all, curr_start_date, curr_end_date)
filtered_prev_fulfilled = apply_filters(sales_all, prev_start_date, prev_end_date)

filtered_orders_fulfilled = apply_filters(order_summary, curr_start_date, curr_end_date)
filtered_orders_prev_fulfilled = apply_filters(order_summary, prev_start_date, prev_end_date)

# ------------------------------------------------------------
# CALCULATE METRICS (CURRENT & PREVIOUS)
# ------------------------------------------------------------

gross_sales = filtered_fulfilled["gross_sales"].sum() if not filtered_fulfilled.empty else 0
prev_gross_sales = filtered_prev_fulfilled["gross_sales"].sum() if not filtered_prev_fulfilled.empty else 0

net_sales = filtered_fulfilled["net_sales"].sum() if not filtered_fulfilled.empty else 0
prev_net_sales = filtered_prev_fulfilled["net_sales"].sum() if not filtered_prev_fulfilled.empty else 0

discount_value = filtered_fulfilled["discount_amount"].sum() if not filtered_fulfilled.empty else 0
prev_discount_value = filtered_prev_fulfilled["discount_amount"].sum() if not filtered_prev_fulfilled.empty else 0

estimated_profit = filtered_fulfilled["estimated_profit"].sum() if not filtered_fulfilled.empty else 0
prev_estimated_profit = filtered_prev_fulfilled["estimated_profit"].sum() if not filtered_prev_fulfilled.empty else 0

units_sold = filtered_fulfilled["quantity_clean"].sum() if not filtered_fulfilled.empty else 0
prev_units_sold = filtered_prev_fulfilled["quantity_clean"].sum() if not filtered_prev_fulfilled.empty else 0

fulfilled_orders = filtered_fulfilled["order_id"].nunique() if not filtered_fulfilled.empty else 0
prev_fulfilled_orders = filtered_prev_fulfilled["order_id"].nunique() if not filtered_prev_fulfilled.empty else 0

unique_customers = filtered_fulfilled["customer_id"].nunique() if not filtered_fulfilled.empty else 0
prev_unique_customers = filtered_prev_fulfilled["customer_id"].nunique() if not filtered_prev_fulfilled.empty else 0

aov = (
    filtered_orders_fulfilled["net_order_value"].mean()
    if not filtered_orders_fulfilled.empty and "net_order_value" in filtered_orders_fulfilled.columns
    else 0
)
prev_aov = (
    filtered_orders_prev_fulfilled["net_order_value"].mean()
    if not filtered_orders_prev_fulfilled.empty and "net_order_value" in filtered_orders_prev_fulfilled.columns
    else 0
)

profit_margin = (
    estimated_profit / net_sales * 100
    if net_sales != 0
    else 0
)
prev_profit_margin = (
    prev_estimated_profit / prev_net_sales * 100
    if prev_net_sales != 0
    else 0
)

# ------------------------------------------------------------
# RENDER KPIS: Total, Total %, YoY Change, & YoY % with Icon
# ------------------------------------------------------------

def render_kpi_card(col, label, curr_val, prev_val, baseline_total=None, is_currency=True, is_pct=False):
    abs_diff = curr_val - prev_val
    pct_change = ((curr_val - prev_val) / abs(prev_val) * 100) if prev_val != 0 else 0
    
    if is_pct:
        val_str = f"{curr_val:.1f}%"
        point_diff = curr_val - prev_val
        col.metric(
            label=label,
            value=val_str,
            delta=f"{pct_change:+.1f}% YoY"
        )
        col.caption(f"YoY Pts Change: {point_diff:+.1f}% pts | Abs Diff: {abs_diff:+.1f}%")
    else:
        val_str = f"₱{compact_number(curr_val)}" if is_currency else f"{curr_val:,.0f}"
        
        col.metric(
            label=label,
            value=val_str,
            delta=f"{pct_change:+.1f}% YoY"
        )
        
        abs_display = f"₱{compact_number(abs_diff)}" if is_currency else f"{abs_diff:+,.0f}"
        if abs_diff >= 0 and is_currency:
            abs_display = f"+₱{compact_number(abs_diff)}"
            
        if baseline_total and baseline_total > 0 and curr_val != baseline_total:
            total_pct = (curr_val / baseline_total) * 100
            col.caption(f"Share: {total_pct:.1f}% | YoY Chg: {abs_display}")
        else:
            col.caption(f"YoY Absolute Change: {abs_display}")


k1, k2, k3, k4 = st.columns(4, border=True)

with k1:
    render_kpi_card(k1, "Gross Sales", gross_sales, prev_gross_sales, baseline_total=None, is_currency=True)
with k2:
    render_kpi_card(k2, "Net Sales", net_sales, prev_net_sales, baseline_total=None, is_currency=True)
with k3:
    render_kpi_card(k3, "Fulfilled Orders", fulfilled_orders, prev_fulfilled_orders, is_currency=False)
with k4:
    render_kpi_card(k4, "Average Order Value", aov, prev_aov, is_currency=True)

k5, k6, k7, k8 = st.columns(4, border=True)

with k5:
    render_kpi_card(k5, "Units Sold", units_sold, prev_units_sold, is_currency=False)
with k6:
    render_kpi_card(k6, "Unique Customers", unique_customers, prev_unique_customers, is_currency=False)
with k7:
    render_kpi_card(k7, "Estimated Profit", estimated_profit, prev_estimated_profit, baseline_total=net_sales, is_currency=True)
with k8:
    render_kpi_card(k8, "Estimated Margin", profit_margin, prev_profit_margin, is_currency=False, is_pct=True)


# ============================================================
# 11. DASHBOARD TABS
# ============================================================

(
    executive_tab,
    sales_tab,
    products_tab,
    customers_tab,
    profitability_tab,
    payments_tab,
    logistics_tab,
    data_tab,    
) = st.tabs(
    [
        "Executive",
        "Sales",
        "Products",
        "Customers",
        "Profit & Discounts",
        "Payments",
        "Logistics & Returns",
        "Data Explorer",        
    ]
)


# ============================================================
# 12. EXECUTIVE TAB
# ============================================================

with executive_tab:
    st.subheader("Executive Overview")
    st.markdown(
        '<div class="section-note">'
        'High-level indicators for fulfilled sales plus operational order mix.'
        '</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Monthly gross vs net sales
    # --------------------------------------------------------

    monthly_revenue = (
        filtered_fulfilled
        .groupby(
            "month",
            as_index=False,
        )
        .agg(
            Gross_Sales=("gross_sales", "sum"),
            Net_Sales=("net_sales", "sum"),
        )
        .sort_values("month")
    )

    fig = px.line(
        monthly_revenue,
        x="month",
        y=[
            "Gross_Sales",
            "Net_Sales",
        ],
        markers=True,
        title="Monthly Gross vs Net Sales",
        labels={
            "month": "",
            "value": "",
            "variable": "Measure",
        },
        color_discrete_sequence=[
            BLUE,
            ORANGE,
        ],
    )
    # Added subtitle and set the Net_Sales line to dotted
    fig.update_layout(
        title=dict(
            text="Monthly Gross vs Net Sales",
            subtitle=dict(
                text="How have monthly gross and net sales trended overtime?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        hovermode="x unified",
        yaxis_tickprefix="₱",
        yaxis_tickformat=",.0f",
    )

    fig.update_traces(
        line=dict(dash="dot"),
        selector=dict(name="Net_Sales"),
    )

    chart_card(
        style_figure(
            fig,
            height=440,
        )
    )
# Added key insight section below the chart
    st.markdown(
        """
        <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
            📌 <b>Key Insight:</b> Gross and net sales track closely together with consistent margins, peaking strongly around April and July across the fiscal timeline.
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns(
        2,
        gap="medium",
    )
##########################################################################################################    
      # Order status
    status_df = (
        filtered_orders_all[
            "order_status"
        ]
        .value_counts()
        .rename_axis("order_status")
        .reset_index(name="orders")
    )

    fig_status = px.pie(
        status_df,
        names="order_status",
        values="orders",
        hole=.58,
        title="Order Status Mix",
        color_discrete_sequence=PALETTE,
    )

    fig_status.update_layout(
        title=dict(
            text="Order Status Mix",
            subtitle=dict(
                text="What is the distribution of fulfillment statuses?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    fig_status = style_figure(
        fig_status,
        height=420,
    )

    with left:
        chart_card(fig_status)
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Fulfilled orders comprise the vast majority of total volume, reflecting a high completion rate.
            </div>
            """,
            unsafe_allow_html=True,
        )

# Sales channel
    channel_df = (
        filtered_fulfilled
        .groupby(
            "sales_channel",
            as_index=False,
        )["gross_sales"]
        .sum()
        .sort_values(
            "gross_sales",
            ascending=False,
        )
    )

    fig_channel = px.pie(
        channel_df,
        names="sales_channel",
        values="gross_sales",
        hole=.58,
        title="Gross Sales Share by Channel",
        color_discrete_sequence=PALETTE,
    )

    fig_channel.update_layout(
        title=dict(
            text="Gross Sales Share by Channel",
            subtitle=dict(
                text="Which channels drive the highest revenue share?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    fig_channel = style_figure(
        fig_channel,
        height=420,
    )

    with right:
        chart_card(fig_channel)
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Online channels account for the dominant share of total gross sales, outperforming other distribution paths.
            </div>
            """,
            unsafe_allow_html=True,
        )

    left2, right2 = st.columns(
        2,
        gap="medium",
    )

# Gross sales by category
    category_df = (
        filtered_fulfilled
        .groupby(
            "category_clean",
            as_index=False,
        )["gross_sales"]
        .sum()
        .sort_values("gross_sales")
    )

    max_sales = category_df["gross_sales"].max()
    category_df["formatted_text"] = category_df["gross_sales"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig_category = px.bar(
        category_df,
        x="gross_sales",
        y="category_clean",
        orientation="h",
        title="Gross Sales by Category",
        labels={
            "gross_sales": "",
            "category_clean": "",
        },
        color="gross_sales",
        color_continuous_scale=[
            "#DBEAFE",
            BLUE,
        ],
        text="formatted_text",
    )

    fig_category.update_traces(
        texttemplate="%{text}",
        textposition="auto",
    )

    fig_category.update_layout(
        title=dict(
            text="Gross Sales by Category",
            subtitle=dict(
                text="What are the top-performing product categories?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
        uniformtext_minsize=8,
        uniformtext_mode="hide",
    )

    with left2:
        chart_card(
            style_figure(
                fig_category,
                height=450,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #ffffff; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Top product categories lead revenue contribution by a wide margin over secondary items.
            </div>
            """,
            unsafe_allow_html=True,
        )

# Gross Sales by region
    region_df = (
        filtered_fulfilled
        .groupby(
            "region_name",
            as_index=False,
        )["gross_sales"]
        .sum()
        .sort_values("gross_sales")
    )

    max_sales = region_df["gross_sales"].max()
    region_df["formatted_text"] = region_df["gross_sales"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig_region = px.bar(
        region_df,
        x="gross_sales",
        y="region_name",
        orientation="h",
        title="Gross Sales by Region",
        labels={
            "gross_sales": "",
            "region_name": "",
        },
        color="gross_sales",
        color_continuous_scale=[
            "#E0F2FE",
            BLUE,
        ],
          text="formatted_text",
    )

    fig_region.update_traces(
        texttemplate="%{text}",
        textposition="auto",
    )


    fig_region.update_layout(
        title=dict(
            text="Gross Sales by Region",
            subtitle=dict(
                text="Which regions generate the most sales volume?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
    )

    with right2:
        chart_card(
            style_figure(
                fig_region,
                height=450,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #ffffff; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Major metropolitan regions drive the highest share of regional gross revenue.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# 13. SALES TAB
# ============================================================

with sales_tab:
    st.subheader("Sales Performance")

    row1a, row1b = st.columns(
        2,
        gap="medium",
    )

    # Orders by month
    monthly_orders = (
        filtered_orders_fulfilled
        .groupby(
            "month",
            as_index=False,
        )["order_id"]
        .nunique()
        .rename(
            columns={
                "order_id": "orders"
            }
        )
        .sort_values("month")
    )

    fig = px.line(
        monthly_orders,
        x="month",
        y="orders",
        markers=True,
        title="Fulfilled Orders by Month",
        labels={
            "month": "",
            "orders": "",
        },
        color_discrete_sequence=[
            BLUE
        ],
    )

    fig.update_layout(
        title=dict(
            text="Fulfilled Orders by Month",
            subtitle=dict(
                text="How has monthly order volume evolved?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    with row1a:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Order volume shows active growth periods with seasonal peaks during specific quarters.
            </div>
            """,
            unsafe_allow_html=True,
        )

   # AOV by month
    monthly_aov = (
        filtered_orders_fulfilled
        .groupby(
            "month",
            as_index=False,
        )["net_order_value"]
        .mean()
        .rename(
            columns={
                "net_order_value": "aov"
            }
        )
        .sort_values("month")
    )

    fig = px.line(
        monthly_aov,
        x="month",
        y="aov",
        markers=True,
        title="Average Order Value by Month",
        labels={
            "month": "",
            "aov": "",
        },
        color_discrete_sequence=[
            ORANGE
        ],
    )

    fig.update_layout(
        title=dict(
            text="Average Order Value by Month",
            subtitle=dict(
                text="What is the trend in average basket size?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        yaxis_tickprefix="₱",
        yaxis_tickformat=",.0f",
    )

    fig.update_traces(
        line=dict(dash="dot"),
        selector=dict(name="aov"),
    )

    with row1b:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Average order value remains relatively stable, reflecting consistent customer purchasing power.
            </div>
            """,
            unsafe_allow_html=True,
        )

    row2a, row2b = st.columns(
        2,
        gap="medium",
    )

# Sales by weekday
    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    weekday_df = (
        filtered_fulfilled
        .groupby(
            "weekday",
            as_index=False,
        )["gross_sales"]
        .sum()
    )

    weekday_df["weekday"] = pd.Categorical(
        weekday_df["weekday"],
        categories=weekday_order,
        ordered=True,
    )

    weekday_df = weekday_df.sort_values(
        "weekday"
    )

    fig = px.bar(
        weekday_df,
        x="weekday",
        y="gross_sales",
        title="Gross Sales by Day of Week",
        labels={
            "weekday": "",
            "gross_sales": "",
        },
        color="gross_sales",
        color_continuous_scale=[
            "#DBEAFE",
            BLUE,
        ],
    )

    # Add data labels to the bars
    fig.update_traces(
        texttemplate="₱%{y:,.0f}",
        textposition="inside"
    )

    fig.update_layout(
        title=dict(
            text="Gross Sales by Day of Week",
            subtitle=dict(
                text="Which days drive the highest revenue?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        yaxis_tickprefix="₱",
        yaxis_tickformat=",.0f",
    )

    with row2a:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Sales activity stays active across weekdays with predictable weekend fluctuations.
            </div>
            """,
            unsafe_allow_html=True,
        )
  # Sales by hour
    hourly_df = (
        filtered_fulfilled
        .groupby(
            "hour",
            as_index=False,
        )["gross_sales"]
        .sum()
        .sort_values("hour")
    )

    fig = px.line(
        hourly_df,
        x="hour",
        y="gross_sales",
        markers=True,
        title="Gross Sales by Hour of Day",
        labels={
            "hour": "",
            "gross_sales": "",
        },
        color_discrete_sequence=[
            BLUE
        ],
    )

    fig.update_layout(
        title=dict(
            text="Gross Sales by Hour of Day",
            subtitle=dict(
                text="At what times do customers purchase most?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        yaxis_tickprefix="₱",
        yaxis_tickformat=",.0f",
    )

    with row2b:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Purchases peak heavily during standard daytime and evening operating hours.
            </div>
            """,
            unsafe_allow_html=True,
        )

    row3a, row3b = st.columns(
        2,
        gap="medium",
    )
    
  # Order value distribution
    fig = px.histogram(
        filtered_orders_fulfilled,
        x="net_order_value",
        nbins=35,
        title="Net Order Value Distribution",
        labels={
            "net_order_value": "",
        },
        color_discrete_sequence=[
            BLUE
        ],
    )

    fig.update_layout(
        title=dict(
            text="Net Order Value Distribution",
            subtitle=dict(
                text="What is the spread of order transaction values?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
        yaxis_title="",
        bargap=0.15,  # Adds space between the bars (adjust between 0.05 and 0.3 as needed)
    )

    with row3a:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Order distribution is right-skewed, with the majority concentrated in lower-to-mid ticket sizes.
            </div>
            """,
            unsafe_allow_html=True,
        )

# Shipping method sales
    ship_method_df = (
        filtered_fulfilled
        .groupby(
            "shipping_method",
            as_index=False,
        )["gross_sales"]
        .sum()
        .sort_values(
            "gross_sales",
            ascending=False,
        )
    )

    fig = px.bar(
        ship_method_df,
        x="shipping_method",
        y="gross_sales",
        title="Gross Sales by Shipping Method",
        labels={
            "shipping_method": "",
            "gross_sales": "",
        },
        color="shipping_method",
        color_discrete_sequence=PALETTE,
    )

    fig.update_layout(
        title=dict(
            text="Gross Sales by Shipping Method",
            subtitle=dict(
                text="Which fulfillment methods drive total revenue?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        showlegend=False,
        yaxis_tickprefix="₱",
        yaxis_tickformat=",.0f",
    )

# Add data labels to the bars
    fig.update_traces(
        texttemplate="₱%{y:,.0f}",
        textposition="inside"
    )
    with row3b:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Standard shipping methods account for the majority of total order revenue.
            </div>
            """,
            unsafe_allow_html=True,
        )

# ============================================================
# 14. PRODUCTS TAB
# ============================================================

####Top Products
with products_tab:
    st.subheader("Product & Category Analytics")

    p1, p2 = st.columns(
        2,
        gap="medium",
    )

    top_products = (
        filtered_fulfilled
        .groupby(
            "product_name",
            as_index=False,
        )
        .agg(
            gross_sales=("gross_sales", "sum"),
            units=("quantity_clean", "sum"),
        )
        .sort_values(
            "gross_sales",
            ascending=False,
        )
        .head(15)
        .sort_values("gross_sales")
    )
        
    max_sales = top_products["gross_sales"].max()
    top_products["formatted_text"] = top_products["gross_sales"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig = px.bar(
        top_products,
        x="gross_sales",
        y="product_name",
        orientation="h",
        title="Top 15 Products by Gross Sales",
        labels={
            "gross_sales": "",
            "product_name": "",
        },
        color="gross_sales",
        color_continuous_scale=[
            "#DBEAFE",
            BLUE,
        ],
        text="formatted_text",  
    )
    
    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Top 15 Products by Gross Sales",
            subtitle=dict(
                text="Which items generate the highest total revenue?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
    )

    with p1:
        chart_card(
            style_figure(
                fig,
                height=540,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Top-selling products drive a disproportionate share of total revenue compared to the tail.
            </div>
            """,
            unsafe_allow_html=True,
        )
##### Top Brands
    
    top_brands = (
        filtered_fulfilled
        .groupby(
            "brand",
            as_index=False,
        )["gross_sales"]
        .sum()
        .sort_values(
            "gross_sales",
            ascending=False,
        )
        .head(12)
        .sort_values("gross_sales")
    )

    max_sales = top_brands["gross_sales"].max()
    top_brands["formatted_text"] = top_brands["gross_sales"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )
    
    fig = px.bar(
        top_brands,
        x="gross_sales",
        y="brand",
        orientation="h",
        title="Top Brands by Gross Sales",
        labels={
            "gross_sales": "",
            "brand": "",
        },
        color="gross_sales",
        color_continuous_scale=[
            "#DFF8F3",
            "#00A6A6",
        ],
        text="formatted_text", 
    )
    
    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Top Brands by Gross Sales",
            subtitle=dict(
                text="Which brands lead overall marketplace performance?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
    )

    with p2:
        chart_card(
            style_figure(
                fig,
                height=540,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Leading brands capture the majority of category-wide sales volume.
            </div>
            """,
            unsafe_allow_html=True,
        )

####### Unit Sold by Category
    p3, p4 = st.columns(
        2,
        gap="medium",
    )

    category_units = (
        filtered_fulfilled
        .groupby(
            "category_clean",
            as_index=False,
        )["quantity_clean"]
        .sum()
        .sort_values("quantity_clean")
    )
    max_sales = category_units["quantity_clean"].max()
    category_units["formatted_text"] = category_units["quantity_clean"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig = px.bar(
        category_units,
        x="quantity_clean",
        y="category_clean",
        orientation="h",
        title="Units Sold by Category",
        labels={
            "quantity_clean": "",
            "category_clean": "",
        },
        color="quantity_clean",
        color_continuous_scale=[
            "#EDE9FE",
            "#5B6CFF",
        ],
        text="formatted_text",
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Units Sold by Category",
            subtitle=dict(
                text="What are the highest-volume product categories?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
    )

    with p3:
        chart_card(
            style_figure(
                fig,
                height=430,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Core product categories move the highest total unit volume across the catalog.
            </div>
            """,
            unsafe_allow_html=True,
        )

    product_relationship = (
        filtered_fulfilled
        .groupby(
            [
                "product_name",
                "category_clean",
            ],
            as_index=False,
        )
        .agg(
            units=("quantity_clean", "sum"),
            average_price=(
                "unit_price_clean",
                "mean",
            ),
            gross_sales=("gross_sales", "sum"),
        )
    )

    fig = px.scatter(
        product_relationship,
        x="average_price",
        y="units",
        size="gross_sales",
        color="category_clean",
        hover_name="product_name",
        title="Product Price vs Units Sold",
        labels={
            "average_price": "",
            "units": "",
            "category_clean": "",
        },
        color_discrete_sequence=PALETTE,
    )

    fig.update_layout(
        title=dict(
            text="Product Price vs Units Sold",
            subtitle=dict(
                text="How do pricing and volume correlate across items?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
    )

    with p4:
        chart_card(
            style_figure(
                fig,
                height=430,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Lower-priced items generally achieve higher turnover volumes, while premium products rely on higher margins.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.subheader("Product Performance Table")

        product_table = (
            filtered_fulfilled
            .groupby(
                [
                    "product_name",
                    "brand",
                    "category_clean",
                ],
                as_index=False,
            )
            .agg(
                Units=("quantity_clean", "sum"),
                Orders=("order_id", "nunique"),
                Gross_Sales=("gross_sales", "sum"),
                Net_Sales=("net_sales", "sum"),
                Estimated_Profit=(
                    "estimated_profit",
                    "sum",
                ),
            )
            .sort_values(
                "Gross_Sales",
                ascending=False,
            )
        )

        st.dataframe(
            product_table,
            width="stretch",
            hide_index=True,
            column_config={
                "product_name": st.column_config.TextColumn(
                    "Product",
                    width="large",
                ),
                "brand": "Brand",
                "category_clean": "Category",
                "Units": st.column_config.NumberColumn(
                    "Units",
                    format="%d",
                ),
                "Orders": st.column_config.NumberColumn(
                    "Orders",
                    format="%d",
                ),
                "Gross_Sales": st.column_config.NumberColumn(
                    "Gross Sales",
                    format="₱ %.2f",
                ),
                "Net_Sales": st.column_config.NumberColumn(
                    "Net Sales",
                    format="₱ %.2f",
                ),
                "Estimated_Profit": st.column_config.NumberColumn(
                    "Est. Profit",
                    format="₱ %.2f",
                ),
            },
        )


# ============================================================
# 15. CUSTOMERS TAB
# ============================================================

with customers_tab:
    st.subheader("Customer Analytics")

    unique_customer_scope = (
        filtered_fulfilled[
            [
                "customer_id",
                "customer_name",
                "gender_clean",
                "age_clean",
                "region_name",
                "city",
                "loyalty_tier",
            ]
        ]
        .drop_duplicates(
            "customer_id"
        )
    )

    c1, c2 = st.columns(
        2,
        gap="medium",
    )

    loyalty_df = (
        unique_customer_scope[
            "loyalty_tier"
        ]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("loyalty_tier")
        .reset_index(name="customers")
    )

    fig = px.pie(
        loyalty_df,
        names="loyalty_tier",
        values="customers",
        hole=.58,
        title="Customer Mix by Loyalty Tier",
        color_discrete_sequence=PALETTE,
    )

    fig.update_layout(
        title=dict(
            text="Customer Mix by Loyalty Tier",
            subtitle=dict(
                text="How is the customer base distributed across tiers?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    with c1:
        chart_card(
            style_figure(
                fig,
                height=420,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> The customer base is heavily weighted toward standard tiers, indicating growth potential for upper loyalty levels.
            </div>
            """,
            unsafe_allow_html=True,
        )

##### Net Sales by Loyalty
    
    loyalty_sales = (
        filtered_fulfilled
        .groupby(
            "loyalty_tier",
            as_index=False,
            dropna=False,
        )["net_sales"]
        .sum()
        .sort_values(
            "net_sales",
            ascending=False,
        )
    )

    loyalty_sales["loyalty_tier"] = (
        loyalty_sales["loyalty_tier"]
        .fillna("Unknown")
    )
    max_sales = loyalty_sales["net_sales"].max()
    loyalty_sales["formatted_text"] = loyalty_sales["net_sales"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig = px.bar(
        loyalty_sales,
        x="loyalty_tier",
        y="net_sales",
        title="Net Sales by Loyalty Tier",
        labels={
            "loyalty_tier": "",
            "net_sales": "",
        },
        color="loyalty_tier",
        color_discrete_sequence=PALETTE,
        text="formatted_text", 
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        showlegend=False,
        yaxis_tickprefix="₱",
        yaxis_tickformat=",.0f",
    )

    fig.update_layout(
        title=dict(
            text="Customer Mix by Loyalty Tier",
            subtitle=dict(
                text="Which tiers contribute the highest net sales?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )
    with c2:
        chart_card(
            style_figure(
                fig,
                height=420,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Higher loyalty tiers drive a significant portion of total net revenue relative to their member share.
            </div>
            """,
            unsafe_allow_html=True,
        )

    c3, c4 = st.columns(
        2,
        gap="medium",
    )

##### Cities by Gross sales
    
    city_df = (
        filtered_fulfilled
        .groupby(
            "city",
            as_index=False,
        )["gross_sales"]
        .sum()
        .sort_values(
            "gross_sales",
            ascending=False,
        )
        .head(12)
        .sort_values("gross_sales")
    )

    max_sales = city_df["gross_sales"].max()
    city_df["formatted_text"] = city_df["gross_sales"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig = px.bar(
        city_df,
        x="gross_sales",
        y="city",
        orientation="h",
        title="Top Cities by Gross Sales",
        labels={
            "gross_sales": "Gross Sales (PHP)",
            "city": "City",
        },
        color="gross_sales",
        color_continuous_scale=[
            "#DBEAFE",
            BLUE,
        ],
        text="formatted_text", 
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Top Cities by Gross Sales",
            subtitle=dict(
                text="Which metropolitan areas generate the highest revenue?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
    )

    with c3:
        chart_card(
            style_figure(
                fig,
                height=470,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Top tier metropolitan cities dominate gross sales volume across regional markets.
            </div>
            """,
            unsafe_allow_html=True,
        )

    ##### uniqe customer by region
    region_customers = (
        unique_customer_scope
        .groupby(
            "region_name",
            as_index=False,
        )["customer_id"]
        .nunique()
        .rename(
            columns={
                "customer_id": "customers"
            }
        )
        .sort_values("customers")
    )

    fig = px.bar(
        region_customers,
        x="customers",
        y="region_name",
        orientation="h",
        title="Unique Customers by Region",
        labels={
            "customers": "",
            "region_name": "",
        },
        color="customers",
        color_continuous_scale=[
            "#E0F2FE",
            BLUE,
        ],
        text="customers", 
    )

    fig.update_layout(
        title=dict(
            text="Unique Customers by Region",
            subtitle=dict(
                text="How is customer acquisition distributed geographically?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
    )

    with c4:
        chart_card(
            style_figure(
                fig,
                height=470,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Customer concentration aligns closely with high-density population centers.
            </div>
            """,
            unsafe_allow_html=True,
        )
    c5, c6 = st.columns(
        2,
        gap="medium",
    )

###### customer Spend ######
    customer_summary = (
        filtered_fulfilled
        .groupby(
            [
                "customer_id",
                "customer_name",
                "loyalty_tier",
                "region_name",
            ],
            as_index=False,
        )
        .agg(
            Orders=("order_id", "nunique"),
            Spend=("net_sales", "sum"),
        )
    )

    fig = px.histogram(
        customer_summary,
        x="Spend",
        nbins=30,
        title="Customer Spend Distribution",
        labels={
            "Spend": "",
        },
        color_discrete_sequence=[
            BLUE
        ],
    )

    fig.update_layout(
        title=dict(
            text="Customer Spend Distribution",
            subtitle=dict(
                text="What is the spread of total net spend per customer?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
        yaxis_title="",
        bargap=0.15,  # Adds space between the bars (adjust between 0.05 and 0.3 as needed)
    )

    with c5:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Most customers fall into low-to-mid spend brackets, with a long tail of high-value spenders.
            </div>
            """,
            unsafe_allow_html=True,
        )
   
    fig = px.histogram(
        customer_summary,
        x="Orders",
        nbins=20,
        title="Customer Order Frequency",
        labels={
            "Orders": "",
        },
        color_discrete_sequence=[
            ORANGE
        ],
    )

    fig.update_layout(
        title=dict(
            text="Customer Order Frequency",
            subtitle=dict(
                text="How many orders do customers place on average?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        yaxis_title="",
        bargap=0.00,  # Adds space between the bars (adjust between 0.05 and 0.3 as needed)
    )
        
    with c6:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Single and double orders account for the majority of customer activity, highlighting retention opportunities.
            </div>
            """,
            unsafe_allow_html=True,
        )

    
    with st.container(border=True):
        st.subheader("Top Customers")

        top_customers = (
            customer_summary
            .sort_values(
                "Spend",
                ascending=False,
            )
            .head(25)
        )

        st.dataframe(
            top_customers,
            width="stretch",
            hide_index=True,
            column_config={
                "customer_id": "Customer ID",
                "customer_name": st.column_config.TextColumn(
                    "Customer",
                    width="large",
                ),
                "loyalty_tier": "Loyalty Tier",
                "region_name": "Region",
                "Orders": st.column_config.NumberColumn(
                    "Orders",
                    format="%d",
                ),
                "Spend": st.column_config.NumberColumn(
                    "Net Spend",
                    format="₱ %.2f",
                ),
            },
        )


# ============================================================
# 16. PROFITABILITY + DISCOUNTS TAB
# ============================================================

with profitability_tab:
    st.subheader("Profitability & Discount Analytics")

    d1, d2, d3, d4 = st.columns(
        4,
        border=True,
    )

    avg_discount = (
        filtered_orders_fulfilled[
            "discount_pct"
        ].mean() * 100
        if not filtered_orders_fulfilled.empty
        else 0
    )

    median_order = (
        filtered_orders_fulfilled[
            "net_order_value"
        ].median()
        if not filtered_orders_fulfilled.empty
        else 0
    )

    d1.metric(
        "Discount Value",
        f"₱{compact_number(discount_value)}",
    )

    d2.metric(
        "Average Discount",
        f"{avg_discount:.1f}%",
    )

    d3.metric(
        "Median Order Value",
        f"₱{median_order:,.2f}",
    )

    d4.metric(
        "Estimated Margin",
        f"{profit_margin:.1f}%",
    )

    pr1, pr2 = st.columns(
        2,
        gap="medium",
    )

    # Profit by category
    profit_category = (
        filtered_fulfilled
        .groupby(
            "category_clean",
            as_index=False,
        )
        .agg(
            estimated_profit=(
                "estimated_profit",
                "sum",
            ),
            net_sales=("net_sales", "sum"),
        )
    )

    profit_category["margin_pct"] = (
        profit_category["estimated_profit"]
        / profit_category["net_sales"]
        * 100
    )

    profit_category = profit_category.sort_values(
        "estimated_profit"
    )

    max_sales = profit_category["net_sales"].max()
    profit_category["formatted_text"] = profit_category["net_sales"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig = px.bar(
        profit_category,
        x="estimated_profit",
        y="category_clean",
        orientation="h",
        title="Estimated Profit by Category",
        labels={
            "estimated_profit": "",
            "category_clean": "",
        },
        color="estimated_profit",
        color_continuous_scale=[
            "#DCFCE7",
            "#16A34A",
        ],
        text="formatted_text", 
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Estimated Profit by Category",
            subtitle=dict(
                text="Which categories generate the highest estimated profit?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
    )

    with pr1:
        chart_card(
            style_figure(
                fig,
                height=440,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Certain core product categories drive the majority of profitability, providing clear focus for margin optimization.
            </div>
            """,
            unsafe_allow_html=True,
        )

#######  Margin by category #########
    
    margin_df = profit_category.sort_values(
        "margin_pct"
    )

    max_margin = margin_df["margin_pct"].max()
    margin_df["formatted_text"] = margin_df["margin_pct"].apply(
        lambda x: f"<b>{x:.2f}%</b>" if x == max_margin else f"{x:.2f}%"
    )

    fig = px.bar(
        margin_df,
        x="margin_pct",
        y="category_clean",
        orientation="h",
        title="Estimated Profit Margin by Category",
        labels={
            "margin_pct": "",
            "category_clean": "",
        },
        color="margin_pct",
        color_continuous_scale=[
            "#EDE9FE",
            "#7C3AED",
        ],
        text="formatted_text",         
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )
 

    fig.update_layout(
        title=dict(
            text="Estimated Profit Margin by Category",
            subtitle=dict(
                text="Which product categories deliver the highest percentage margins?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
    )

    with pr2:
        chart_card(
            style_figure(
                fig,
                height=440,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Profitability percentages vary widely across categories, highlighting opportunities to pivot marketing toward high-margin items.
            </div>
            """,
            unsafe_allow_html=True,
        )

    pr3, pr4 = st.columns(
        2,
        gap="medium",
    )

###### monthly net sales profit and discount #######
    
    
    fig = px.histogram(
        filtered_orders_fulfilled,
        x="discount_pct",
        nbins=25,
        title="Order Discount Distribution",
        labels={
            "discount_pct": "",
        },
        color_discrete_sequence=[
            ORANGE
        ],
    )

    fig.update_layout(
        title=dict(
            text="Order Discount Distribution",
            subtitle=dict(
                text="What is the distribution of discount percentages applied to orders?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        xaxis_tickformat=".0%",
        yaxis_title="Orders",
        bargap=0.15,  # Adds space between the bars (adjust between 0.05 and 0.3 as needed)
    )

    with pr3:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Promotional discounts cluster around specific thresholds, revealing the heavy reliance on standard discount tiers.
            </div>
            """,
            unsafe_allow_html=True,
        )

    
    fig = px.scatter(
        filtered_orders_fulfilled,
        x="discount_pct",
        y="net_order_value",
        color="sales_channel",
        hover_data=[
            "order_id",
            "region_name",
        ],
        title="Discount Rate vs Net Order Value",
        labels={
            "discount_pct": "",
            "net_order_value": "",
            "sales_channel": "",
        },
        color_discrete_sequence=PALETTE,
    )

    fig.update_layout(
        title=dict(
            text="Discount Rate vs Net Order Value",
            subtitle=dict(
                text="Does higher discounting drive larger net basket sizes across sales channels?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        xaxis_tickformat=".0%",
        yaxis_tickprefix="₱",
        yaxis_tickformat=",.0f",
    )

    with pr4:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Higher discount rates do not consistently translate to larger order values, pointing to potential over-discounting on standard basket sizes.
            </div>
            """,
            unsafe_allow_html=True,
        )

    monthly_profit = (
        filtered_orders_fulfilled
        .groupby(
            "month",
            as_index=False,
        )
        .agg(
            Net_Sales=(
                "net_order_value",
                "sum",
            ),
            Estimated_Profit=(
                "estimated_profit",
                "sum",
            ),
            Discount_Value=(
                "discount_amount",
                "sum",
            ),
        )
        .sort_values("month")
    )

    fig = px.line(
        monthly_profit,
        x="month",
        y=[
            "Net_Sales",
            "Estimated_Profit",
            "Discount_Value",
        ],
        markers=True,
        title="Monthly Net Sales, Profit and Discount Value",
        labels={
            "month": "",
            "value": "",
            "variable": "",
        },
        color_discrete_sequence=[
            BLUE,
            "#16A34A",
            ORANGE,
        ],
    )

    fig.update_layout(
        title=dict(
            text="Monthly Net Sales, Profit and Discount Value",
            subtitle=dict(
                text="How do net sales, profit, and discount values trend over time?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        hovermode="x unified",
        yaxis_tickprefix="₱",
        yaxis_tickformat=",.0f",
    )

    chart_card(
        style_figure(
            fig,
            height=440,
        )
    )
    st.markdown(
        """
        <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
            📌 <b>Key Insight:</b> Revenue and profit track closely month-over-month, while promotional discount values scale proportionally with sales volume surges.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 17. PAYMENTS TAB
# ============================================================

with payments_tab:
    st.subheader("Payment Analytics")

    paid_rows = payment_scope[
        payment_scope["payment_status"]
        .astype("string")
        .str.strip()
        .str.lower()
        .eq("paid")
    ]

    total_paid = paid_rows[
        "amount_paid_clean"
    ].sum()

    failed_payments = (
        payment_scope["payment_status"]
        .astype("string")
        .str.strip()
        .str.lower()
        .eq("failed")
        .sum()
    )

    refunded_payments = (
        payment_scope["payment_status"]
        .astype("string")
        .str.strip()
        .str.lower()
        .eq("refunded")
        .sum()
    )

    pay1, pay2, pay3, pay4 = st.columns(
        4,
        border=True,
    )

    pay1.metric(
        "Payment Records",
        f"{len(payment_scope):,}",
    )

    pay2.metric(
        "Paid Amount",
        f"₱{compact_number(total_paid)}",
    )

    pay3.metric(
        "Failed Payments",
        f"{failed_payments:,}",
    )

    pay4.metric(
        "Refunded Payments",
        f"{refunded_payments:,}",
    )

    py1, py2 = st.columns(
        2,
        gap="medium",
    )

####### Payment Status ######
    
    payment_status_df = (
        payment_scope[
            "payment_status"
        ]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("payment_status")
        .reset_index(name="count")
    )

    fig = px.pie(
        payment_status_df,
        names="payment_status",
        values="count",
        hole=.58,
        title="Payment Status",
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(
        title=dict(
            text="Payment Status",
            subtitle=dict(
                text="What is the distribution of successful versus failed or pending payments?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    with py1:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> The vast majority of payment transactions complete successfully, with minimal leakage from failures or refunds.
            </div>
            """,
            unsafe_allow_html=True,
        )

 ###### Payment Method ######    
    payment_method_df = (
        payment_scope[
            "payment_method"
        ]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("payment_method")
        .reset_index(name="count")
        .sort_values("count")
    )

    max_margin = payment_method_df["count"].max()
    payment_method_df["formatted_text"] = payment_method_df["count"].apply(
        lambda x: f"<b>{x:.0f}</b>" if x == max_margin else f"{x:.0f}"
    )

    fig = px.bar(
        payment_method_df,
        x="count",
        y="payment_method",
        orientation="h",
        title="Payment Method Usage",
        labels={
            "count": "",
            "payment_method": "",
        },
        color="count",
        color_continuous_scale=[
            "#DBEAFE",
            BLUE,
        ],
        text="formatted_text",
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Payment Method Usage",
            subtitle=dict(
                text="Which payment channels are preferred by customers?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
    )

    with py2:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Digital wallets and specific gateway options drive the highest volume of transaction checkouts.
            </div>
            """,
            unsafe_allow_html=True,
        )

    py3, py4 = st.columns(
        2,
        gap="medium",
    )


    
 #### Amount by Method ####

    
    amount_method = (
        payment_scope
        .groupby(
            "payment_method",
            as_index=False,
        )["amount_paid_clean"]
        .sum()
        .sort_values("amount_paid_clean")
    )

    max_sales = amount_method["amount_paid_clean"].max()
    amount_method["formatted_text"] = amount_method["amount_paid_clean"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig = px.bar(
        amount_method,
        x="amount_paid_clean",
        y="payment_method",
        orientation="h",
        title="Recorded Payment Amount by Method",
        labels={
            "amount_paid_clean": "",
            "payment_method": "",
        },
        color="amount_paid_clean",
        color_continuous_scale=[
            "#DFF8F3",
            "#00A6A6",
        ],
        text="formatted_text", 
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Recorded Payment Amount by Method",
            subtitle=dict(
                text="How do total monetary volumes break down across payment methods?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
    )

    with py3:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Revenue totals mirror transaction volume distribution, confirming consistent average order values across channels.
            </div>
            """,
            unsafe_allow_html=True,
        )

    ###### Method Status
    method_status = (
        payment_scope
        .groupby(
            [
                "payment_method",
                "payment_status",
            ],
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "count"
            }
        )
    )

    fig = px.bar(
        method_status,
        x="payment_method",
        y="count",
        color="payment_status",
        barmode="stack",
        title="Payment Status by Method",
        labels={
            "payment_method": "",
            "count": "",
            "payment_status": "",
        },
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(
        title=dict(
            text="Payment Status by Method",
            subtitle=dict(
                text="What is the success and failure breakdown per individual payment gateway?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    with py4:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Gateway reliability remains stable, with failure rates proportional to channel usage volume.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# 18. LOGISTICS + RETURNS TAB
# ============================================================

with logistics_tab:
    st.subheader("Logistics & Returns")

    delivered_days = shipment_scope[
        "delivery_days"
    ].dropna()

    
    median_delivery = (
        delivered_days.median()
        if not delivered_days.empty
        else pd.NA
    )

    returned_orders = (
        return_scope["order_id"]
        .nunique()
    )

    return_rate = (
        returned_orders
        / len(filtered_orders_all)
        * 100
        if len(filtered_orders_all) > 0
        else 0
    )

    total_refunds = (
        return_scope[
            "refund_amount_clean"
        ].sum()
    )

    lost_shipments = (
        shipment_scope["shipment_status"]
        .astype("string")
        .str.strip()
        .str.lower()
        .eq("lost")
        .sum()
    )

    lg1, lg2, lg3, lg4 = st.columns(
        4,
        border=True,
    )

    lg1.metric(
        "Median Delivery",
        (
            f"{median_delivery:.0f} days"
            if pd.notna(median_delivery)
            else "—"
        ),
    )

    lg2.metric(
        "Return Rate",
        f"{return_rate:.1f}%",
    )

    lg3.metric(
        "Refund Amount",
        f"₱{compact_number(total_refunds)}",
    )

    lg4.metric(
        "Lost Shipments",
        f"{lost_shipments:,}",
    )

    lgrow1a, lgrow1b = st.columns(
        2,
        gap="medium",
    )

    ####### Shipment status ######
    
    shipment_status_df = (
        shipment_scope[
            "shipment_status"
        ]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("shipment_status")
        .reset_index(name="count")
    )

    fig = px.pie(
        shipment_status_df,
        names="shipment_status",
        values="count",
        hole=.58,
        title="Shipment Status",
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(
        title=dict(
            text="Shipment Status",
            subtitle=dict(
                text="What is the proportion of delivered versus pending or delayed shipments?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    with lgrow1a:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> The vast majority of shipments are successfully delivered, with minor shares in transit or exceptions.
            </div>
            """,
            unsafe_allow_html=True,
        )

#### Volume by courier
    
    courier_df = (
        shipment_scope[
            "courier"
        ]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("courier")
        .reset_index(name="shipments")
        .sort_values("shipments")
    )

    max_margin = courier_df["shipments"].max()
    courier_df["formatted_text"] = courier_df["shipments"].apply(
        lambda x: f"<b>{x:.0f}</b>" if x == max_margin else f"{x:.0f}"
    )

    fig = px.bar(
        courier_df,
        x="shipments",
        y="courier",
        orientation="h",
        title="Shipment Volume by Courier",
        labels={
            "shipments": "",
            "courier": "",
        },
        color="shipments",
        color_continuous_scale=[
            "#DBEAFE",
            BLUE,
        ],
        text="formatted_text",
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Shipment Volume by Courier",
            subtitle=dict(
                text="How are delivery volumes distributed across third-party logistics partners?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
    )

    with lgrow1b:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Primary courier partners handle the bulk of fulfillment volume, showing high vendor concentration.
            </div>
            """,
            unsafe_allow_html=True,
        )

    lgrow2a, lgrow2b = st.columns(
        2,
        gap="medium",
    )


    ###### Delivery by Courier ######
    delivery_by_courier = (
        shipment_scope
        .groupby(
            "courier",
            as_index=False,
        )["delivery_days"]
        .median()
        .dropna()
        .sort_values("delivery_days")
    )

    max_margin = delivery_by_courier["delivery_days"].max()
    delivery_by_courier["formatted_text"] = delivery_by_courier["delivery_days"].apply(
        lambda x: f"<b>{x:.0f}</b>" if x == max_margin else f"{x:.0f}"
    )

    fig = px.bar(
        delivery_by_courier,
        x="delivery_days",
        y="courier",
        orientation="h",
        title="Median Delivery Days by Courier",
        labels={
            "delivery_days": "",
            "courier": "",
        },
        color="delivery_days",
        color_continuous_scale=[
            "#ECFDF5",
            "#16A34A",
        ],
        text="formatted_text", 
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Median Delivery Days by Courier",
            subtitle=dict(
                text="How do delivery turnaround times compare across couriers?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
    )

    with lgrow2a:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Median transit durations vary across couriers, identifying opportunities to optimize fulfillment SLAs.
            </div>
            """,
            unsafe_allow_html=True,
        )
##### DIstribution ####
    
    fig = px.histogram(
        shipment_scope.dropna(
            subset=[
                "delivery_days"
            ]
        ),
        x="delivery_days",
        nbins=20,
        title="Delivery Time Distribution",
        labels={
            "delivery_days": "Delivery Days",
        },
        color_discrete_sequence=[
            BLUE
        ],
    )

    fig.update_layout(
        title=dict(
            text="Delivery Time Distribution",
            subtitle=dict(
                text="What is the frequency spread of order delivery timelines?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        yaxis_title="Shipments",
    )

    with lgrow2b:
        chart_card(
            style_figure(
                fig,
                height=410,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Most shipments cluster tightly around standard delivery windows, with a slight tail for remote regions.
            </div>
            """,
            unsafe_allow_html=True,
        )

    lgrow3a, lgrow3b = st.columns(
        2,
        gap="medium",
    )

    ##### Return reason ######
    return_reason_df = (
        return_scope[
            "reason"
        ]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("reason")
        .reset_index(name="returns")
        .sort_values("returns")
    )
    
    max_margin = return_reason_df["returns"].max()
    return_reason_df["formatted_text"] = return_reason_df["returns"].apply(
        lambda x: f"<b>{x:.0f}</b>" if x == max_margin else f"{x:.0f}"
    )

    fig = px.bar(
        return_reason_df,
        x="returns",
        y="reason",
        orientation="h",
        title="Return Reasons",
        labels={
            "returns": "Return Requests",
            "reason": "Reason",
        },
        color="returns",
        color_continuous_scale=[
            "#FFEDD5",
            ORANGE,
        ],
        text="formatted_text", 
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )


    fig.update_layout(
        title=dict(
            text="Return Reasons",
            subtitle=dict(
                text="What are the primary drivers behind customer product returns?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
    )

    with lgrow3a:
        chart_card(
            style_figure(
                fig,
                height=430,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Sizing and product defects account for the highest proportion of return requests.
            </div>
            """,
            unsafe_allow_html=True,
        )
###Refund Status
    refund_flag_df = (
        return_scope[
            "refunded_flag_clean"
        ]
        .value_counts()
        .rename_axis("refund_status")
        .reset_index(name="count")
    )

    fig = px.pie(
        refund_flag_df,
        names="refund_status",
        values="count",
        hole=.58,
        title="Return Refund Status",
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(
        title=dict(
            text="Return Refund Status",
            subtitle=dict(
                text="What proportion of returned items have been fully refunded?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    with lgrow3b:
        chart_card(
            style_figure(
                fig,
                height=430,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Refund processing rates remain prompt, with closed refund requests clearing the majority queue.
            </div>
            """,
            unsafe_allow_html=True,
        )
###### refund reason
    refund_reason_df = (
        return_scope
        .groupby(
            "reason",
            as_index=False,
        )["refund_amount_clean"]
        .sum()
        .sort_values("refund_amount_clean")
    )
    
    max_sales = refund_reason_df["refund_amount_clean"].max()
    refund_reason_df["formatted_text"] = refund_reason_df["refund_amount_clean"].apply(
        lambda x: f"<b>{format_sales(x)}</b>" if x == max_sales else format_sales(x)
    )

    fig = px.bar(
        refund_reason_df,
        x="refund_amount_clean",
        y="reason",
        orientation="h",
        title="Refund Amount by Return Reason",
        labels={
            "refund_amount_clean": "Refund Amount (PHP)",
            "reason": "Return Reason",
        },
        color="refund_amount_clean",
        color_continuous_scale=[
            "#FFE4E6",
            "#E11D48",
        ],
        text="formatted_text", 
    )

    fig.update_traces(
        texttemplate="%{text}",
        textposition="auto",  
    )

    fig.update_layout(
        title=dict(
            text="Refund Amount by Return Reason",
            subtitle=dict(
                text="Which return categories represent the highest monetary refunds?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
        coloraxis_showscale=False,
        xaxis_tickprefix="₱",
        xaxis_tickformat=",.0f",
    )

    chart_card(
        style_figure(
            fig,
            height=430,
        )
    )
    st.markdown(
        """
        <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
            📌 <b>Key Insight:</b> Monetary losses from refunds correlate directly with high-frequency return categories, emphasizing product quality controls.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 19. DATA EXPLORER + QUALITY TAB
# ============================================================

with data_tab:
    st.subheader("Data Explorer & Quality Checks")

    dq1, dq2 = st.columns(
        2,
        gap="medium",
    )

    count_rows = []

    for dataset_name in raw_counts:
        count_rows.append(
            {
                "Dataset": dataset_name,
                "Raw Rows": raw_counts[
                    dataset_name
                ],
                "Clean Rows": clean_counts[
                    dataset_name
                ],
            }
        )

    count_df = pd.DataFrame(
        count_rows
    )

    count_long = count_df.melt(
        id_vars="Dataset",
        var_name="Stage",
        value_name="Rows",
    )

    fig = px.bar(
        count_long,
        x="Dataset",
        y="Rows",
        color="Stage",
        barmode="group",
        title="Raw vs Clean Row Counts",
        color_discrete_sequence=[
            "#94A3B8",
            BLUE,
        ],
    )
    fig.update_layout(
        title=dict(
            text="Raw vs Clean Row Counts",
            subtitle=dict(
                text="How do dataset volumes compare before and after data cleaning?",
                font=dict(size=12, color="#FFFFFF"),
            ),
        ),
    )

    with dq1:
        chart_card(
            style_figure(
                fig,
                height=430,
            )
        )
        st.markdown(
            """
            <div style="background-color: #023059; padding: 0.75rem 1rem; border-radius: 0 0 12px 12px; color: #FFFFFF; font-size: 0.85rem; margin-top: -0.9rem; margin-bottom: 0.9rem;">
                📌 <b>Key Insight:</b> Data cleaning removes duplicate and invalid rows cleanly while retaining the vast majority of original records.
            </div>
            """,
            unsafe_allow_html=True,
        )

    quality_summary = pd.DataFrame(
        {
            "Metric": [
                "Filtered item rows",
                "Filtered all orders",
                "Filtered fulfilled orders",
                "Payment records",
                "Shipment records",
                "Return records",
            ],
            "Value": [
                len(filtered_all),
                len(filtered_orders_all),
                len(
                    filtered_orders_fulfilled
                ),
                len(payment_scope),
                len(shipment_scope),
                len(return_scope),
            ],
        }
    )

    with dq2:
        with st.container(border=True):
            st.markdown(
                "#### Current Filter Scope"
            )
            st.dataframe(
                quality_summary,
                width="stretch",
                hide_index=True,
                column_config={
                    "Metric": "Metric",
                    "Value": st.column_config.NumberColumn(
                        "Records",
                        format="%d",
                    ),
                },
            )

    with st.container(border=True):
        st.subheader(
            "Filtered Transaction Details"
        )

        detail_columns = [
            "order_id",
            "order_date",
            "customer_name",
            "product_name",
            "brand",
            "category_clean",
            "quantity_clean",
            "unit_price_clean",
            "sales_channel",
            "shipping_method",
            "region_name",
            "city",
            "discount_pct_clean",
            "gross_sales",
            "net_sales",
            "estimated_profit",
        ]

        detail = (
            filtered_all[
                detail_columns
            ]
            .sort_values(
                "order_date",
                ascending=False,
            )
            .copy()
        )

        detail[
            "discount_percent"
        ] = (
            detail[
                "discount_pct_clean"
            ]
            * 100
        )

        detail = detail.drop(
            columns=[
                "discount_pct_clean"
            ]
        )

        st.dataframe(
            detail,
            width="stretch",
            hide_index=True,
            column_config={
                "order_id": st.column_config.TextColumn(
                    "Order ID",
                    pinned=True,
                ),
                "order_date": st.column_config.DatetimeColumn(
                    "Order Date",
                    format="DD MMM YYYY, hh:mm a",
                ),
                "customer_name": st.column_config.TextColumn(
                    "Customer",
                    width="medium",
                ),
                "product_name": st.column_config.TextColumn(
                    "Product",
                    width="large",
                ),
                "brand": "Brand",
                "category_clean": "Category",
                "quantity_clean": st.column_config.NumberColumn(
                    "Qty",
                    format="%d",
                ),
                "unit_price_clean": st.column_config.NumberColumn(
                    "Unit Price",
                    format="₱ %.2f",
                ),
                "sales_channel": "Channel",
                "shipping_method": "Shipping",
                "region_name": "Region",
                "city": "City",
                "discount_percent": st.column_config.NumberColumn(
                    "Discount",
                    format="%.1f%%",
                ),
                "gross_sales": st.column_config.NumberColumn(
                    "Gross Sales",
                    format="₱ %.2f",
                ),
                "net_sales": st.column_config.NumberColumn(
                    "Net Sales",
                    format="₱ %.2f",
                ),
                "estimated_profit": st.column_config.NumberColumn(
                    "Est. Profit",
                    format="₱ %.2f",
                ),
            },
        )

        st.download_button(
            "Download Filtered Transactions",
            data=detail.to_csv(
                index=False
            ).encode("utf-8"),
            file_name=(
                "retail_filtered_transactions.csv"
            ),
            mime="text/csv",
            width="stretch",
        )

    with st.expander(
        "Cleaning rules used by this dashboard"
    ):
        st.markdown(
            """
            - Exact duplicate rows are removed.
            - Product category variants are standardized.
            - Currency-like values are converted to numeric.
            - Non-positive item quantities are excluded.
            - Mixed date formats are parsed with `format="mixed"`.
            - Missing order discounts are treated as zero.
            - Invalid discount rates are reset to zero.
            - Orders must reference an existing customer.
            - Order items must reference existing orders and products.
            - Sales KPIs use **Completed** and **Shipped** orders.
            - Estimated profit is `net sales - estimated product cost`.
            - Shipping fee is not included in net sales.
            """
        )


