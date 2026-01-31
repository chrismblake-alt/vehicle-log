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
MAINTENANCE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=338560830"

# Oil change thresholds (in miles)
OIL_CHANGE_INTERVAL = 5000
WARNING_THRESHOLD = 4000  # Yellow at 4000 miles
OVERDUE_THRESHOLD = 5000  # Red at 5000 miles

@st.cache_data(ttl=60)
def load_data():
    """Load checkout data from Google Sheet"""
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = [
            'checkout_time', 'vehicle', 'first_name', 'last_name', 
            'mileage', 'destination', 'expected_back', 'email', 'submission_id'
        ]
        df['checkout_time'] = pd.to_datetime(df['checkout_time'], errors='coerce')
        df['staff_name'] = df['first_name'].fillna('') + ' ' + df['last_name'].fillna('')
        df['staff_name'] = df['staff_name'].str.strip()
        df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce')
        df = df.sort_values('checkout_time', ascending=False)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_maintenance():
    """Load maintenance data from Google Sheet"""
    try:
        df = pd.read_csv(MAINTENANCE_URL)
        df.columns = ['vehicle', 'date', 'mileage', 'service_type']
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading maintenance data: {e}")
        return pd.DataFrame()

def get_oil_change_status(vehicle, current_mileage, maintenance_df):
    """Get oil change status for a vehicle"""
    # Filter for oil changes for this vehicle
    vehicle_oil = maintenance_df[
        (maintenance_df['vehicle'] == vehicle) & 
        (maintenance_df['service_type'].str.lower().str.contains('oil', na=False))
    ]
    
    if vehicle_oil.empty or pd.isna(current_mileage):
        return {
            'status': 'unknown',
            'color': '⚪',
            'message': 'No oil change on record',
            'miles_since': None,
            'last_mileage': None
        }
    
    # Get most recent oil change
    last_oil_change = vehicle_oil.sort_values('mileage', ascending=False).iloc[0]
    last_mileage = last_oil_change['mileage']
    miles_since = current_mileage - last_mileage
    
    if miles_since >= OVERDUE_THRESHOLD:
        return {
            'status': 'overdue',
            'color': '🔴',
            'message': f'{int(miles_since):,} miles since oil change - OVERDUE',
            'miles_since': miles_since,
            'last_mileage': last_mileage
        }
    elif miles_since >= WARNING_THRESHOLD:
        return {
            'status': 'warning',
            'color': '🟡',
            'message': f'{int(miles_since):,} miles since oil change - Due soon',
            'miles_since': miles_since,
            'last_mileage': last_mileage
        }
    else:
        return {
            'status': 'good',
            'color': '🟢',
            'message': f'{int(miles_since):,} miles since oil change',
            'miles_since': miles_since,
            'last_mileage': last_mileage
        }

st.title("🚗 Vehicle Checkout Log")

# Load data
df = load_data()
maintenance_df = load_maintenance()

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

for vehicle in vehicles:
    vehicle_df = df[df['vehicle'] == vehicle]
    if not vehicle_df.empty:
        last_checkout = vehicle_df.iloc[0]
        checkout_time = last_checkout['checkout_time']
        current_mileage = last_checkout['mileage']
        
        # Get oil change status
        oil_status = get_oil_change_status(vehicle, current_mileage, maintenance_df)
        
        with st.container():
            col1, col2, col3 = st.columns([2, 2, 2])
            
            with col1:
                st.markdown(f"### {vehicle}")
                st.caption(f"Last checkout: {checkout_time.strftime('%m/%d %I:%M %p') if pd.notna(checkout_time) else 'Unknown'}")
                st.write(f"**{last_checkout['staff_name']}** → {last_checkout['destination']}")
                if pd.notna(last_checkout['expected_back']):
                    st.caption(f"Expected back: {last_checkout['expected_back']}")
            
            with col2:
                if pd.notna(current_mileage):
                    st.metric("Current Mileage", f"{int(current_mileage):,}")
                else:
                    st.metric("Current Mileage", "Not recorded")
            
            with col3:
                st.markdown(f"**Oil Change Status**")
                st.markdown(f"{oil_status['color']} {oil_status['message']}")
                if oil_status['miles_since'] is not None:
                    miles_remaining = OVERDUE_THRESHOLD - oil_status['miles_since']
                    if miles_remaining > 0:
                        st.caption(f"{int(miles_remaining):,} miles until due")
            
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

# --- Maintenance History ---
st.subheader("Maintenance History")

if not maintenance_df.empty:
    maintenance_display = maintenance_df.sort_values('date', ascending=False).copy()
    maintenance_display.columns = ['Vehicle', 'Date', 'Mileage', 'Service Type']
    st.dataframe(
        maintenance_display,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No maintenance records yet. Add entries to the Maintenance tab in your Google Sheet.")

st.divider()

# --- Quick Stats ---
st.subheader("Quick Stats")

col1, col2, col3, col4 = st.columns(4)

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
    week_ago = datetime.now() - timedelta(days=7)
    this_week = df[df['checkout_time'] >= week_ago]
    st.metric("This Week", len(this_week))
