"""
ParkFlow - Streamlit entry point (Owner: Ali - Integration)

Run:   streamlit run main.py

Connects:
    core.py                        Ali      ParkingSystem (kept in st.session_state)
    structures_and_algorithms.py   Ibrahim  used inside core.py
    analytics.py                   Arwa     load_parking_data(path), clean_parking_data(df)
    dashboard.py                   Ziad     show_* functions
"""

from pathlib import Path

import streamlit as st

from core import ROLES, ParkingSystem, get_algorithms_status
from dashboard import (
    show_dashboard,
    show_parking_management,
    show_parking_history,
    show_vehicle_search,
)

try:
    from analytics import clean_parking_data, load_parking_data
    ANALYTICS_ERROR = None
except Exception as error:  # analytics.py missing or still being edited
    load_parking_data = clean_parking_data = None
    ANALYTICS_ERROR = str(error)

DATA_PATH = Path(__file__).parent / "data" / "IIoT_Smart_Parking_Management.csv"
DEFAULT_SLOTS = 20
SLOTS_PER_ROW = 5


def initialize_session_state():
    """Create the parking system once and keep it across reruns."""
    if "parking_system" not in st.session_state:
        st.session_state.parking_system = ParkingSystem(
            number_of_slots=DEFAULT_SLOTS, slots_per_row=SLOTS_PER_ROW
        )
    if "role" not in st.session_state:
        st.session_state.role = "Gate Operator"


@st.cache_data(show_spinner="Loading parking dataset...")
def load_clean_data(path):
    return clean_parking_data(load_parking_data(path))


def sidebar(parking_system):
    st.sidebar.title("ParkFlow")
    st.session_state.role = st.sidebar.selectbox(
        "Current user role", list(ROLES), index=list(ROLES).index(st.session_state.role)
    )

    status = parking_system.get_parking_status()
    st.sidebar.metric("Available slots", f"{status['available']} / {status['total']}")
    st.sidebar.metric("Waiting vehicles", status["waiting"])

    if st.session_state.role == "Admin":
        with st.sidebar.expander("Admin: reset lot"):
            slots = st.number_input("Number of slots", 1, 130, DEFAULT_SLOTS)
            per_row = st.number_input("Slots per row (zone)", 1, 20, SLOTS_PER_ROW)
            if st.button("Reset parking system"):
                st.session_state.parking_system = ParkingSystem(int(slots), int(per_row))
                st.rerun()

    with st.sidebar.expander("Algorithms status"):
        for name, source in get_algorithms_status().items():
            st.write(("✅ " if source == "team" else "⚠️ ") + f"{name}: {source}")


def main():
    st.set_page_config(page_title="ParkFlow", page_icon="🅿️", layout="wide")
    initialize_session_state()
    parking_system = st.session_state.parking_system
    sidebar(parking_system)

    st.title("🅿️ ParkFlow — Smart Parking Management")
    tab_manage, tab_search, tab_history, tab_dashboard = st.tabs(
        ["Parking Management", "Vehicle Search", "History", "Analytics Dashboard"]
    )

    with tab_manage:
        show_parking_management(parking_system)

    with tab_search:
        show_vehicle_search(parking_system)

    with tab_history:
        show_parking_history(parking_system)

    with tab_dashboard:
        if ANALYTICS_ERROR:
            st.warning(f"Analytics module not available yet: {ANALYTICS_ERROR}")
        elif not DATA_PATH.exists():
            st.warning(f"Dataset not found: {DATA_PATH.name}")
        else:
            try:
                df = load_clean_data(str(DATA_PATH))
            except Exception as error:
                st.error(f"Could not load the dataset: {error}")
            else:
                show_dashboard(df)


if __name__ == "__main__":
    main()
