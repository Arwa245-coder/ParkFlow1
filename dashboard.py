"""
ParkFlow - Dashboard (Owner: Ziad)

main.py calls one function per tab:
    show_parking_management(parking_system)   live lot: KPIs, parking map, entry / exit, queue
    show_vehicle_search(parking_system)       live records search
    show_parking_history(parking_system)      live operation log + session records
    show_dashboard(df)                        HISTORICAL CSV analytics (not the live lot)
"""

from html import escape

import pandas as pd
import streamlit as st

from core import VEHICLE_TYPES, can

# main.py imports this file without try/except, so optional imports are guarded here.
try:
    import plotly.express as px
except ImportError:
    px = None
try:
    import analytics
    ANALYTICS_IMPORT_ERROR = None
except Exception as error:  # analytics.py missing or being edited
    analytics = None
    ANALYTICS_IMPORT_ERROR = str(error)

CSS = """
<style>
div[data-testid="stMetric"] { border: 1px solid rgba(128,128,128,.25); border-radius: 12px;
    padding: 10px 14px; background: rgba(128,128,128,.06); }
.pf-lot { background: #1b2330; border: 1px solid #2d3748; border-radius: 16px; padding: 14px; color: #e2e8f0; }
.pf-head { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;
    font-size: .78rem; margin-bottom: 10px; opacity: .9; }
.pf-head i { display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin: 0 5px 0 12px; }
.pf-row { display: flex; align-items: stretch; }
.pf-zone { width: 54px; flex: none; display: flex; align-items: center; font-size: .7rem; font-weight: 700;
    letter-spacing: .06em; color: #94a3b8; }
.pf-bay { min-width: 0; height: 120px; display: flex; flex-direction: column; align-items: center;
    justify-content: space-between; padding: 6px 2px 4px; border-left: 2px solid rgba(226,232,240,.5); }
.pf-bay:last-child { border-right: 2px solid rgba(226,232,240,.5); }
.pf-row.down .pf-bay { border-top: 2px solid rgba(226,232,240,.5); }
.pf-row.up .pf-bay { border-bottom: 2px solid rgba(226,232,240,.5); }
.pf-bay.free { background: linear-gradient(180deg, rgba(20,184,166,.14), rgba(20,184,166,.04)); }
.pf-stage { flex: 1; display: flex; align-items: center; justify-content: center; min-height: 0; }
.pf-stage svg { height: 76px; width: auto; }
.pf-row.down .pf-stage svg { transform: rotate(180deg); }
.pf-car { animation: pf-in .45s ease-out; }
@keyframes pf-in { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: none; } }
.pf-hint { font-size: .6rem; letter-spacing: .14em; color: #5eead4; opacity: .8; }
.pf-sid { font-size: .72rem; font-weight: 700; }
.pf-lbl { font-size: .62rem; color: #94a3b8; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pf-bay.free .pf-lbl { color: #5eead4; }
.pf-aisle { position: relative; height: 54px; background: #131a24; display: flex; align-items: center;
    gap: 6px; padding-left: 54px; margin: 0; }
.pf-aisle:before { content: ""; position: absolute; left: 60px; right: 10px; top: 50%;
    border-top: 2px dashed rgba(250,204,21,.5); }
.pf-gate { position: relative; z-index: 1; font-size: .65rem; font-weight: 800; letter-spacing: .12em;
    background: #fbbf24; color: #111827; border-radius: 4px; padding: 2px 8px; }
.pf-q { position: relative; z-index: 1; width: 40px; height: 36px; display: flex; align-items: center;
    justify-content: center; background: #131a24; }
.pf-q svg { height: 34px; width: auto; transform: rotate(90deg); }
.pf-more { position: relative; z-index: 1; background: #131a24; font-size: .7rem; padding: 0 6px; color: #fbbf24; }
.pf-curb { height: 8px; margin: 8px 0; border-radius: 3px; opacity: .45;
    background: repeating-linear-gradient(90deg, #fbbf24 0 14px, #1b2330 14px 28px); }
section[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,.2); }
section[data-testid="stSidebar"] h1 { font-size: 1.2rem; letter-spacing: .1em; text-transform: uppercase;
    color: #14b8a6; padding: 0 0 .4rem; }
section[data-testid="stSidebar"] label p { font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; opacity: .7; }
section[data-testid="stSidebar"] div[data-testid="stMetric"] { padding: 8px 12px; }
section[data-testid="stSidebar"] details { border: 1px solid rgba(128,128,128,.2); border-radius: 10px; }
section[data-testid="stSidebar"] details > div p { font-size: .74rem; opacity: .7; margin: 0 0 2px; }
</style>
"""


TYPE_COLORS = {"Car": "#60a5fa", "Electric Vehicle": "#22d3ee", "Motorcycle": "#f59e0b", "Truck": "#a78bfa"}
WHEELS = '<g fill="#0b1220"><rect x="0" y="14" width="5" height="15" rx="2"/><rect x="35" y="14" width="5" height="15" rx="2"/><rect x="0" y="52" width="5" height="15" rx="2"/><rect x="35" y="52" width="5" height="15" rx="2"/></g>'
SHAPES = {  # top-down vehicles, nose at the top; COLOR is replaced per vehicle type
    "car": WHEELS + '<rect x="3" y="2" width="34" height="76" rx="12" fill="COLOR"/>'
           '<path d="M9 23h22l-3 11H12z" fill="#0f172a" opacity=".85"/>'
           '<rect x="11" y="37" width="18" height="14" rx="3" fill="#000" opacity=".16"/>'
           '<path d="M12 56h16l3 8H9z" fill="#0f172a" opacity=".85"/>'
           '<rect x="8" y="3" width="7" height="3" rx="1.5" fill="#fde68a"/><rect x="25" y="3" width="7" height="3" rx="1.5" fill="#fde68a"/>'
           '<rect x="8" y="74" width="7" height="3" rx="1.5" fill="#f87171"/><rect x="25" y="74" width="7" height="3" rx="1.5" fill="#f87171"/>',
    "bike": '<rect x="17" y="3" width="6" height="16" rx="3" fill="#0b1220"/><rect x="17" y="61" width="6" height="16" rx="3" fill="#0b1220"/>'
            '<rect x="15" y="12" width="10" height="56" rx="5" fill="COLOR"/><rect x="6" y="22" width="28" height="4" rx="2" fill="#0b1220"/>'
            '<circle cx="20" cy="42" r="8" fill="#0f172a" opacity=".85"/>',
    "truck": WHEELS + '<rect x="4" y="2" width="32" height="24" rx="9" fill="COLOR"/><path d="M9 11h22l-2 9H11z" fill="#0f172a" opacity=".85"/>'
             '<rect x="4" y="29" width="32" height="49" rx="3" fill="COLOR" opacity=".65"/>'
             '<path d="M8 36h24M8 48h24M8 60h24" stroke="#0f172a" stroke-opacity=".3"/>',
}
SIZE_GROW = {"Compact": .8, "Standard": 1, "Oversized": 1.3}  # wider bays for bigger slot sizes


# ------------------------------------------------------------------ helpers
def _css():
    st.markdown(CSS, unsafe_allow_html=True)


def _role():
    """main.py's sidebar stores the selected role here."""
    return st.session_state.get("role", "Gate Operator")


def _card():
    """Bordered box. Older Streamlit versions have no border option, so fall back to a plain container."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def _flash(key, res, extra=""):
    """Keep the result message, then rerun so main.py's sidebar counters refresh too."""
    st.session_state[key] = (bool(res.get("success")), res.get("message", "") + extra)
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # very old Streamlit
        st.experimental_rerun()


def _show_flash(key):
    flash = st.session_state.pop(key, None)
    if flash:
        (st.success if flash[0] else st.error)(flash[1])


# ------------------------------------------------------- 1. live parking map
def _vehicle_svg(vehicle_type):
    shape = {"Motorcycle": "bike", "Truck": "truck"}.get(vehicle_type, "car")
    color = TYPE_COLORS.get(vehicle_type, TYPE_COLORS["Car"])
    return '<svg viewBox="0 0 40 80">' + SHAPES[shape].replace("COLOR", color) + "</svg>"


def _bay(slot):
    if slot.is_occupied:
        plate = escape(slot.vehicle.plate_number)
        tip = escape(f"{slot.slot_id} | {slot.vehicle.plate_number} | {slot.vehicle.vehicle_type}")
        stage = f'<div class="pf-car">{_vehicle_svg(slot.vehicle.vehicle_type)}</div>'
        state, label = "occ", plate
    else:
        tip = escape(f"{slot.slot_id} | free | {slot.size}")
        stage, state, label = f'<div class="pf-hint">{escape(slot.size.upper())}</div>', "free", "FREE"
    return (f'<div class="pf-bay {state}" style="flex:{SIZE_GROW.get(slot.size, 1)}" title="{tip}">'
            f'<div class="pf-stage">{stage}</div><div class="pf-sid">{escape(slot.slot_id)}</div>'
            f'<div class="pf-lbl" dir="auto">{label}</div></div>')


def _aisle(waiting=None):
    """Driving lane. The first one has the entry gate and the waiting cars lined up behind it."""
    cells = ""
    if waiting is not None:
        cells = '<span class="pf-gate">ENTRY</span>'
        for vehicle in waiting[:6]:
            cells += f'<div class="pf-q" title="Waiting: {escape(vehicle.plate_number)}">{_vehicle_svg(vehicle.vehicle_type)}</div>'
        if len(waiting) > 6:
            cells += f'<span class="pf-more">+{len(waiting) - 6}</span>'
    return f'<div class="pf-aisle">{cells}</div>'


def _lot_html(parking_system, status, waiting):
    """The whole parking lot as ONE html block: rows of bays facing a driving lane."""
    rows = [row for row in parking_system.grid if row]
    blocks = []
    for first in range(0, len(rows), 2):  # two zones share one driving lane
        pair = rows[first:first + 2]
        html = ""
        for index, row in enumerate(pair):
            html += f'<div class="pf-row {"down" if index == 0 else "up"}"><div class="pf-zone">{escape(row[0].zone)}</div>'
            html += "".join(_bay(slot) for slot in row) + "</div>"
            if index == 0:
                html += _aisle(waiting if first == 0 else None)
        blocks.append(html)
    legend = "".join(f'<i style="background:{color}"></i>{name}' for name, color in TYPE_COLORS.items())
    head = (f'<div class="pf-head"><span><b>{status["available"]}</b> free &nbsp;/&nbsp; <b>{status["occupied"]}</b> occupied'
            f' &nbsp;/&nbsp; <b>{status["waiting"]}</b> waiting</span><span>{legend}</span></div>')
    return '<div class="pf-lot">' + head + '<div class="pf-curb"></div>'.join(blocks) + "</div>"


def _operations(parking_system, role, waiting):
    left, right = st.columns(2)
    with left, _card():
        st.markdown("**Vehicle entry**")
        if can(role, "park"):
            with st.form("park_form", clear_on_submit=True):
                plate = st.text_input("Plate number", placeholder="ABC 1234")
                vehicle_type = st.selectbox("Vehicle type", VEHICLE_TYPES)
                if st.form_submit_button("Park vehicle", type="primary"):
                    _flash("flash_manage", parking_system.park_vehicle(plate, vehicle_type))
        else:
            st.info(f"The {role} role cannot register entries.")

    with right, _card():
        st.markdown("**Vehicle exit**")
        if not can(role, "exit"):
            st.info(f"The {role} role cannot register exits.")
        elif not (parked := [s.vehicle.plate_number for s in parking_system.get_occupied_slots()]):
            st.caption("No parked vehicles.")
        else:
            plate = st.selectbox("Parked vehicle", parked)
            fee_col, exit_col = st.columns(2)
            if fee_col.button("Quote fee"):
                res = parking_system.quote_fee(plate)
                (st.info if res["success"] else st.error)(res["message"])
            if exit_col.button("Exit vehicle", type="primary"):
                res = parking_system.exit_vehicle(plate)
                moved = ", ".join(v["plate_number"] for v in res.get("served_from_queue") or [])
                _flash("flash_manage", res, f" Moved from queue: {moved}." if moved else "")

    if waiting:
        with st.expander(f"Waiting queue ({len(waiting)})", expanded=True):
            st.dataframe(pd.DataFrame([
                {"#": i, "plate_number": v.plate_number, "vehicle_type": v.vehicle_type}
                for i, v in enumerate(waiting, 1)]), hide_index=True)
            if can(role, "manage_waiting"):
                plate = st.selectbox("Remove from queue", [v.plate_number for v in waiting])
                if st.button("Remove from waiting queue"):
                    _flash("flash_manage", parking_system.remove_from_waiting(plate))


def show_parking_management(parking_system):
    _css()
    st.subheader("Live Parking")
    _show_flash("flash_manage")
    status = parking_system.get_parking_status()
    waiting = parking_system.get_waiting_vehicles()

    kpis = st.columns(4)
    kpis[0].metric("Available", status["available"])
    kpis[1].metric("Occupied", status["occupied"])
    kpis[2].metric("Waiting", status["waiting"])
    kpis[3].metric("Occupancy", f"{status['occupancy_rate']}%")

    st.markdown(_lot_html(parking_system, status, waiting), unsafe_allow_html=True)
    st.write("")
    _operations(parking_system, _role(), waiting)


# ------------------------------------------------------------ 2. live search
def show_vehicle_search(parking_system):
    _css()
    st.subheader("Vehicle Search")
    if not can(_role(), "search"):
        st.info("Your role cannot search vehicles.")
        return
    if not parking_system.get_records():
        st.info("No vehicles registered yet. Park a vehicle first.")
        return

    text_col, field_col = st.columns([3, 1])
    text = text_col.text_input("Search", placeholder="e.g. ABC, P03, Truck")
    field = field_col.selectbox("Field", ["plate_number", "slot_id", "vehicle_type", "status", "zone"])
    if text.strip():
        results = parking_system.search_vehicles(text, field)
        if results:
            st.caption(f"{len(results)} result(s)")
            st.dataframe(pd.DataFrame(results), hide_index=True)
        else:
            st.warning("No matching vehicles.")

    vehicle_id = st.text_input("Or find by vehicle ID", placeholder="V0001")
    if vehicle_id.strip():
        vehicle = parking_system.find_record_by_id(vehicle_id)
        if vehicle:
            st.dataframe(pd.DataFrame([vehicle.to_record()]), hide_index=True)
        else:
            st.warning("No vehicle with this ID.")


# ----------------------------------------------------------- 3. live history
def show_parking_history(parking_system):
    _css()
    st.subheader("History & Records")
    _show_flash("flash_history")
    role = _role()
    if not can(role, "view_history"):
        st.info(f"The {role} role cannot view history.")
        return

    summary = parking_system.get_summary()
    cards = st.columns(5)
    cards[0].metric("Sessions", summary["total_sessions"])
    cards[1].metric("Completed", summary["completed_sessions"])
    cards[2].metric("Revenue today", f"{summary['revenue_today']:.2f} EGP")
    cards[3].metric("Total revenue", f"{summary['total_revenue']:.2f} EGP")
    cards[4].metric("Avg duration", f"{summary['average_duration']} min")

    history = parking_system.get_history()
    st.markdown("**Operation log** (newest first)")
    if history:
        st.dataframe(pd.DataFrame(history[::-1]), hide_index=True)
    else:
        st.caption("No operations yet.")
    if can(role, "undo") and st.button("Undo last operation"):  # Admin only
        _flash("flash_history", parking_system.undo_last_operation())

    records = parking_system.get_records()
    if not records:
        return
    st.markdown("**Vehicle records**")
    f1, f2, f3 = st.columns([2, 2, 1])
    statuses = f1.multiselect("Status", ["waiting", "parked", "exited", "cancelled"],
                              default=["waiting", "parked", "exited", "cancelled"])
    by = f2.selectbox("Sort by", ["vehicle_id", "plate_number", "entry_time", "parking_duration", "fee"])
    rows = [r for r in parking_system.sort_records(by, f3.checkbox("Descending")) if r["status"] in statuses]
    table = pd.DataFrame(rows)
    st.dataframe(table, hide_index=True)
    if not table.empty:
        st.download_button("Download CSV", table.to_csv(index=False).encode("utf-8-sig"),
                           "parkflow_records.csv", "text/csv")


# --------------------------------------------------- 4. historical analytics
BUSY, OTHER = "#fb7185", "#14b8a6"
REQUIRED_ANALYTICS = (  # what show_dashboard needs from analytics.py
    "data_quality_summary", "filter_options", "apply_filters", "summary_metrics", "peak_entry_hours",
    "entry_hour_counts", "section_occupancy", "payment_summary", "vehicle_type_summary",
    "duration_distribution", "monthly_records", "generate_insights", "DATA_LIMITATIONS",
)


def _style(fig, title):
    fig.update_layout(title=title, height=330, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def _render_quality(df):
    """Data-quality panel. Uses the unfiltered data, so filters can't hide problems."""
    quality = analytics.data_quality_summary(df)
    c1, c2, c3 = st.columns(3)
    c1.metric("Complete records", f"{quality.get('complete_records_percent', 'n/a')}%")
    c2.metric("Possible overnight stays", quality.get("possible_overnight_records", "n/a"))
    date_range = quality.get("date_range")
    if date_range:
        c3.metric("Date range", f"{date_range[0]:%Y-%m} to {date_range[1]:%Y-%m}")
    issues = quality.get("issues") or []
    if issues:
        st.warning(f"{len(issues)} data-quality note(s). No rows were deleted; "
                   "impossible values were treated as missing.")
        with st.expander("Data-quality details"):
            for issue in issues:
                st.write(f"- {issue}")
    else:
        st.success("No data-quality issues found in the checked columns.")


def _read_filters(df):
    """Draw the filter widgets and return keyword arguments for analytics.apply_filters."""
    options = analytics.filter_options(df)
    filters = {}
    columns = st.columns(3)
    labels = {"sections": "Parking section", "vehicle_types": "Vehicle type", "payment_statuses": "Payment status"}
    for column, key in zip(columns, labels):
        chosen = column.multiselect(labels[key], options[key], default=options[key], key=f"hist_{key}")
        filters[key] = None if list(chosen) == list(options[key]) else list(chosen)  # None = filter off

    left, right = st.columns(2)
    first, last = options["hours"]
    if first < last:
        hours = left.slider("Entry hour", first, last, (first, last), key="hist_hours")
        filters["hour_range"] = None if tuple(hours) == (first, last) else tuple(hours)
    if options["dates"] and options["dates"][0] < options["dates"][1]:
        start, end = options["dates"]
        picked = right.date_input("Date range", value=(start, end), min_value=start, max_value=end, key="hist_dates")
        if isinstance(picked, (tuple, list)) and len(picked) == 2 and tuple(picked) != (start, end):
            filters["date_range"] = tuple(picked)
    return filters


def _chart_hours(df):
    hours = analytics.entry_hour_counts(df)
    top = hours["records"].max()
    hours["Hour type"] = ["Busiest hour" if r == top and top > 0 else "Other hours" for r in hours["records"]]
    fig = px.bar(hours, x="Entry_Time", y="records", color="Hour type",
                 color_discrete_map={"Busiest hour": BUSY, "Other hours": OTHER},
                 labels={"Entry_Time": "Entry hour (0-23)", "records": "Records"})
    fig.update_layout(showlegend=False, xaxis=dict(dtick=1))
    return _style(fig, "Entry-hour pattern")


def _chart_sections(df):
    sections = analytics.section_occupancy(df)
    sections["Parking_Lot_Section"] = sections["Parking_Lot_Section"].astype(str)
    fig = px.bar(sections, x="Parking_Lot_Section", y="occupied_share_percent", text="occupied_share_percent",
                 hover_data=["records", "occupied_records"], color_discrete_sequence=[OTHER],
                 labels={"Parking_Lot_Section": "Section", "occupied_share_percent": "Rows labelled Occupied (%)"})
    fig.update_layout(yaxis=dict(range=[0, 100]))
    return _style(fig, "Occupied-labelled share by section")


def _chart_payments(df):
    payments = analytics.payment_summary(df)
    payments["Payment_Status"] = payments["Payment_Status"].astype(str)
    fig = px.pie(payments, names="Payment_Status", values="records", hole=0.55,
                 hover_data=["total_amount"], color_discrete_sequence=[OTHER, "#fbbf24", BUSY])
    return _style(fig, "Records by payment status")


def _chart_vehicles(df):
    vehicles = analytics.vehicle_type_summary(df)
    vehicles["Vehicle_Type"] = vehicles["Vehicle_Type"].astype(str)
    fig = px.bar(vehicles, x="Vehicle_Type", y="average_duration", color="Vehicle_Type",
                 hover_data=["records", "average_payment"],
                 labels={"Vehicle_Type": "Vehicle type", "average_duration": "Average duration (dataset units)"})
    fig.update_layout(showlegend=False)
    return _style(fig, "Average parking duration by vehicle type")


def _chart_durations(df):
    durations = analytics.duration_distribution(df)
    fig = px.bar(durations, x="Parking_Duration", y="records", color_discrete_sequence=["#6366f1"],
                 labels={"Parking_Duration": "Parking duration (dataset units)", "records": "Records"})
    fig.update_layout(xaxis=dict(dtick=1))
    return _style(fig, "Parking-duration distribution")


def _chart_monthly(df):
    monthly = analytics.monthly_records(df)
    fig = px.line(monthly, x="Month", y="records", markers=True, color_discrete_sequence=[OTHER],
                  labels={"Month": "Month", "records": "Records"})
    return _style(fig, "Records per month")


def show_dashboard(df):
    """Historical analytics from the CSV. Nothing here is live data from ParkingSystem."""
    _css()
    st.subheader("Historical Analytics")
    st.info("📚 **Historical dataset** (IIoT Smart Parking, past records). It is not live sensor data and "
            "it does not describe the live lot managed in the other tabs.")
    if analytics is None:
        st.warning(f"analytics.py could not be imported: {ANALYTICS_IMPORT_ERROR}")
        return
    if px is None:
        st.error("Plotly is not installed, so the charts cannot be drawn. Run: pip install plotly")
        return
    if df is None or df.empty:
        st.warning("The dataset is empty.")
        return

    missing = [name for name in REQUIRED_ANALYTICS if not hasattr(analytics, name)]
    if missing:
        st.error("This analytics.py does not match dashboard.py. Missing: " + ", ".join(missing))
        return
    try:
        _render_analytics(df)
    except (KeyError, TypeError, AttributeError) as error:
        st.error(f"analytics.py returned something dashboard.py does not expect "
                 f"({type(error).__name__}: {error}). Both files must come from the same version.")


def _render_analytics(df):
    with st.expander("Data quality", expanded=False):
        _render_quality(df)

    filtered = analytics.apply_filters(df, **_read_filters(df))
    if filtered.empty:
        st.info("No records match the selected filters.")
        return
    st.caption(f"Showing {len(filtered)} of {len(df)} records.")

    # --- KPI cards (units are not confirmed by the dataset, so we say so)
    m = analytics.summary_metrics(filtered)
    row1 = st.columns(4)
    row1[0].metric("Records", m["total_records"])
    row1[1].metric("Labelled Occupied", f"{m['occupied_records'] / m['total_records'] * 100:.1f}%")
    row1[2].metric("Avg occupancy rate", f"{m['average_occupancy_rate_percent']}%")
    row1[3].metric("Avg duration (dataset units)", m["average_parking_duration"])
    row2 = st.columns(4)
    row2[0].metric("Avg payment (dataset units)", m["average_payment_amount"])
    row2[1].metric("Unpaid or overdue", f"{m['unpaid_or_overdue_percent']}%")
    row2[2].metric("Violation rate", f"{m['violation_rate_percent']}%")
    row2[3].metric("Busiest entry hour", f"{int(analytics.peak_entry_hours(filtered, 1).iloc[0]['Entry_Time']):02d}:00"
                   if len(analytics.peak_entry_hours(filtered, 1)) else "n/a")

    # --- charts (each one is built by a small function above)
    charts = [(_chart_hours, "hist_hours_chart"), (_chart_sections, "hist_sections_chart"),
              (_chart_payments, "hist_payments_chart"), (_chart_vehicles, "hist_vehicles_chart"),
              (_chart_durations, "hist_durations_chart"), (_chart_monthly, "hist_monthly_chart")]
    for i in range(0, len(charts), 2):
        for column, (build, key) in zip(st.columns(2), charts[i:i + 2]):
            try:
                column.plotly_chart(build(filtered), key=key)
            except Exception as error:  # one broken chart must not hide the others
                column.warning(f"Chart unavailable: {error}")

    with st.expander("Key insights", expanded=True):
        for line in analytics.generate_insights(filtered):
            st.markdown(f"- {line}")
    with st.expander("About this data"):
        for note in analytics.DATA_LIMITATIONS:
            st.markdown(f"- {note}")
    with st.expander("Show data table"):
        st.dataframe(filtered, hide_index=True)