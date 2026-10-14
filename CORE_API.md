# ParkFlow — Core API (Ali)

Run the app: `pip install -r requirements.txt` then `streamlit run main.py`
Run core tests: `python -m unittest discover -s tests -v`

## For Ziad (dashboard.py)

`parking_system` that main.py passes to your functions is a `core.ParkingSystem` (20 slots, 5 per zone).
Actions **never raise**; they return a dict with `success` and `message`:

```python
res = parking_system.park_vehicle(plate, vehicle_type)      # vehicle_type in core.VEHICLE_TYPES
st.success(res["message"]) if res["success"] else st.error(res["message"])
```

| need | call |
|---|---|
| entry / exit | `park_vehicle(plate, vehicle_type="Car")`, `exit_vehicle(plate)` → has `fee`, `duration_minutes`, `served_from_queue` |
| fee before exit | `quote_fee(plate)` |
| KPIs | `get_parking_status()` → total, available, occupied, waiting, occupancy_rate, by_zone, by_size · `get_summary()` adds revenue + average duration |
| parking map | `get_slot_grid()` (2D list of slot dicts) or `get_occupancy_matrix()` (2D 0/1 for a heatmap) |
| slot lists | `get_available_slots()`, `get_occupied_slots()` → `ParkingSlot` objects (`.to_dict()`) |
| waiting queue | `get_waiting_vehicles()` → `Vehicle` objects (`.to_record()`), `remove_from_waiting(plate)` |
| search | `find_vehicle(plate)` → Vehicle or None (hash table) · `search_vehicles(text)` partial · `find_record_by_id("V0003")` (binary search) |
| sort | `sort_records(by="fee", descending=True)` (merge sort) |
| tables | `get_records()` → list of dicts → `pd.DataFrame(...)` |
| history / undo | `get_history()` (oldest first), `undo_last_operation()` |
| roles | `st.session_state.role` + `core.can(role, "park")` to show/hide controls |

Actions per role: Driver → view_status, search · Gate Operator → + park, exit, manage_waiting, view_history · Admin → all.

## Record schema (`get_records()`)

`vehicle_id, plate_number, slot_id, entry_time, exit_time, status, parking_duration` (shared schema, duration in minutes)
+ `vehicle_type, zone, fee, from_waiting`. Status: waiting / parked / exited / cancelled.
Vehicle types, slot sizes (Compact / Standard / Oversized) and zones (Zone A…) use the same names as the dataset.

## For Ibrahim (structures_and_algorithms.py)

Keep the names and signatures from the skeleton. core.py tests each one when it loads and uses it if it works;
otherwise a temporary version is used. The sidebar → "Algorithms status" must show ✅ for all before submission.
`binary_search` may return the item **or** its index (-1/None when missing). `greedy_slot_allocation(available_slots, vehicle)`
receives only free slots that fit the vehicle; useful fields: `slot.size_rank`, `slot.index` (0 = nearest to gate), `slot.zone`.

## For Arwa (analytics.py)

main.py needs `analytics.py` with:
```python
def load_parking_data(path) -> pd.DataFrame: ...
def clean_parking_data(df) -> pd.DataFrame: ...
```
(the notebook can stay as the analysis evidence, but Streamlit can't import a .ipynb).
