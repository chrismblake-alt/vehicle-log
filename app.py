import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Vehicle Checkout Log",
    page_icon="🚗",
    layout="wide"
)

# Google Sheet URL - public CSV export
SHEET_ID = "1wu21NBekBxmPlhyh6dcIS-ANnUEupuZnn0hQtyNX6tA"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_data():
    """Load data from Google Sheet"""
    try:
        df = pd.read_csv(CSV_URL)
        # Rename columns for easier handling
        df.columns = [
            'checkout_time', 'vehicle', 'first_name', 'last_name', 
            'mileage', 'destination', 'expected_back', 'email', 'submission_id'
        ]
        # Parse datetime
        df['checkout_time'] = pd.to_datetime(df['checkout_time'], errors='coerce')
        # Combine name
        df['staff_name'] = df['first_name'].fillna('') + ' ' + df['last_name'].fillna('')
        df['staff_name'] = df['staff_name'].str.strip()
        # Sort by most recent
        df = df.sort_values('checkout_time', ascending=False)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

st.title("🚗 Vehicle Checkout Log")

# Load data
df = load_data()

if df.empty:
    st.warning("No checkout data found. Make sure the Google Sheet is shared publicly.")
    st.stop()

# Refresh button
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# --- Current Vehicle Status ---
st.subheader("Current Vehicle Status")

vehicles = df['vehicle'].dropna().unique()

status_cols = st.columns(len(vehicles) if len(vehicles) > 0 else 1)

for i, vehicle in enumerate(vehicles):
    vehicle_df = df[df['vehicle'] == vehicle]
    if not vehicle_df.empty:
        last_checkout = vehicle_df.iloc[0]
        checkout_time = last_checkout['checkout_time']
        
        # Determine if likely still out
        hours_ago = (datetime.now() - checkout_time).total_seconds() / 3600 if pd.notna(checkout_time) else 0
        
        with status_cols[i]:
            st.markdown(f"**{vehicle}**")
            st.caption(f"Last checkout: {checkout_time.strftime('%m/%d %I:%M %p') if pd.notna(checkout_time) else 'Unknown'}")
            st.write(f"**{last_checkout['staff_name']}**")
            st.caption(f"→ {last_checkout['destination']}")
            if pd.notna(last_checkout['expected_back']):
                st.caption(f"Expected: {last_checkout['expected_back']}")

st.divider()

# --- Filters ---
st.subheader("Checkout History")

col1, col2, col3 = st.columns(3)

with col1:
    vehicle_filter = st.selectbox(
        "Vehicle",
        options=["All"] + list(vehicles),
        index=0
    )

with col2:
    staff_list = df['staff_name'].dropna().unique()
    staff_filter = st.selectbox(
        "Staff",
        options=["All"] + sorted(list(staff_list)),
        index=0
    )

with col3:
    date_range = st.selectbox(
        "Time Period",
        options=["Last 7 days", "Last 30 days", "All time"],
        index=0
    )

# Apply filters
filtered_df = df.copy()

if vehicle_filter != "All":
    filtered_df = filtered_df[filtered_df['vehicle'] == vehicle_filter]

if staff_filter != "All":
    filtered_df = filtered_df[filtered_df['staff_name'] == staff_filter]

if date_range == "Last 7 days":
    cutoff = datetime.now() - timedelta(days=7)
    filtered_df = filtered_df[filtered_df['checkout_time'] >= cutoff]
elif date_range == "Last 30 days":
    cutoff = datetime.now() - timedelta(days=30)
    filtered_df = filtered_df[filtered_df['checkout_time'] >= cutoff]

# Display table
display_df = filtered_df[['checkout_time', 'vehicle', 'staff_name', 'destination', 'mileage', 'expected_back']].copy()
display_df.columns = ['Checkout Time', 'Vehicle', 'Staff', 'Destination', 'Mileage', 'Expected Back']

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

st.caption(f"Showing {len(display_df)} entries")

st.divider()

# --- Quick Stats ---
st.subheader("Quick Stats")

col1, col2, col3, col4 = st.columns(4)

# Stats for selected time period
with col1:
    st.metric("Total Checkouts", len(filtered_df))

with col2:
    unique_staff = filtered_df['staff_name'].nunique()
    st.metric("Unique Staff", unique_staff)

with col3:
    most_used = filtered_df['vehicle'].value_counts()
    if not most_used.empty:
        st.metric("Most Used", most_used.index[0])
    else:
        st.metric("Most Used", "N/A")

with col4:
    # Checkouts this week
    week_ago = datetime.now() - timedelta(days=7)
    this_week = df[df['checkout_time'] >= week_ago]
    st.metric("This Week", len(this_week))
