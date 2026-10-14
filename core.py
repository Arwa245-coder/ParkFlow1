"""
ParkFlow - Core System (Owner: Ali - Core System + Integration)

Flow:  arrival -> validation -> allocation (greedy) -> waiting queue if full
       -> exit -> duration + fee -> slot released -> next waiting vehicle served

Data structures (from structures_and_algorithms.py - Ibrahim):
    waiting_queue  Queue      vehicles waiting when the lot is full (FIFO)
    history        Stack      every operation, used for undo
    vehicle_index  HashTable  plate -> vehicle currently in the system (O(1) gate lookup)
Core structures (Ali):
    slots          list       all ParkingSlot objects (P01, P02, ...)
    grid           2D list    grid[row][col] -> slot, one row per zone (Zone A, Zone B, ...)
    vehicles       dict       vehicle_id -> Vehicle (every session, ordered by id)

All public ParkingSystem actions return a dict:
    {"success": True/False, "message": "...", ...}
so the Streamlit UI never crashes on invalid input.
"""

import csv
import math
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Integration with Ibrahim's module.
# Each structure / algorithm is self-tested once at import. If it is not
# finished yet (still TODO) a small temporary version is used so the app can
# run. As soon as Ibrahim's version works, it is used automatically.
# Check get_algorithms_status() before submission: everything must be "team".
# ---------------------------------------------------------------------------
try:
    import structures_and_algorithms as _sa
except Exception:  # file missing or has a syntax error while being edited
    _sa = None

ALGORITHMS_STATUS = {}

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
GRACE_MINUTES = 15
DAILY_CAP_HOURS = 10


# =============================================================== exceptions
class ParkFlowError(Exception):
    """Base error with a user-friendly message."""


class ValidationError(ParkFlowError):
    pass


class DuplicateVehicleError(ParkFlowError):
    pass


class VehicleNotFoundError(ParkFlowError):
    pass


class SlotOccupiedError(ParkFlowError):
    pass


class InvalidOperationError(ParkFlowError):
    pass


# ======================================================== temporary fallbacks
class _FallbackStack:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        return self.items.pop() if self.items else None

    def peek(self):
        return self.items[-1] if self.items else None

    def is_empty(self):
        return len(self.items) == 0


class _FallbackQueue:
    def __init__(self):
        self.items = []

    def enqueue(self, item):
        self.items.append(item)

    def dequeue(self):
        return self.items.pop(0) if self.items else None

    def peek(self):
        return self.items[0] if self.items else None

    def is_empty(self):
        return len(self.items) == 0


class _FallbackHashTable:
    def __init__(self, capacity=101):
        self.capacity = capacity
        self.table = {}

    def insert(self, key, value):
        self.table[key] = value

    def search(self, key):
        return self.table.get(key)

    def delete(self, key):
        self.table.pop(key, None)


def _fallback_linear_search(data, target, key=None):
    for item in data:
        if (key(item) if key else item) == target:
            return item
    return None


def _fallback_binary_search(sorted_data, target, key=None):
    low, high = 0, len(sorted_data) - 1
    while low <= high:
        mid = (low + high) // 2
        value = key(sorted_data[mid]) if key else sorted_data[mid]
        if value == target:
            return sorted_data[mid]
        if value < target:
            low = mid + 1
        else:
            high = mid - 1
    return None


def _fallback_merge_sort(data, key=None):
    # simple insertion sort, temporary until Ibrahim's merge sort is ready
    key = key or (lambda x: x)
    result = []
    for item in data:
        i = len(result)
        while i > 0 and key(result[i - 1]) > key(item):
            i -= 1
        result.insert(i, item)
    return result


def _fallback_greedy(available_slots, vehicle):
    best = None
    for slot in available_slots:
        if best is None or (slot.size_rank, slot.index) < (best.size_rank, best.index):
            best = slot
    return best


# ------------------------------------------------------------ self-tests
def _test_stack(cls):
    s = cls()
    s.push(1)
    s.push(2)
    return (s.peek() == 2 and s.pop() == 2 and s.pop() == 1
            and s.pop() is None and s.is_empty() is True)


def _test_queue(cls):
    q = cls()
    q.enqueue("a")
    q.enqueue("b")
    return (q.peek() == "a" and q.dequeue() == "a" and q.dequeue() == "b"
            and q.dequeue() is None and q.is_empty() is True)


def _test_hash(cls):
    h = cls()
    h.insert("ABC 1", 1)
    h.insert("XYZ 2", 2)
    h.insert("ABC 1", 3)  # update
    ok = h.search("ABC 1") == 3 and h.search("XYZ 2") == 2 and h.search("NO") is None
    h.delete("ABC 1")
    return ok and h.search("ABC 1") is None and h.search("XYZ 2") == 2


def _test_linear(fn):
    data = [{"k": 5}, {"k": 2}, {"k": 9}]
    return fn(data, 2, key=lambda d: d["k"]) == {"k": 2} and fn(data, 7, key=lambda d: d["k"]) is None


def _bsearch_result(result, data):
    """Accept either the item or its index from binary_search."""
    if result is None or isinstance(result, bool):
        return None
    if isinstance(result, int):
        return data[result] if 0 <= result < len(data) else None
    return result


def _test_binary(fn):
    data = [{"k": 1}, {"k": 3}, {"k": 5}, {"k": 8}]
    return (_bsearch_result(fn(data, 5, key=lambda d: d["k"]), data) == {"k": 5}
            and _bsearch_result(fn(data, 4, key=lambda d: d["k"]), data) is None)


def _test_sort(fn):
    data = [{"k": 3}, {"k": 1}, {"k": 2}, {"k": 1}]
    result = fn(data, key=lambda d: d["k"])
    return [d["k"] for d in result] == [1, 1, 2, 3] and [d["k"] for d in data] == [3, 1, 2, 1]


def _load(name, fallback, test):
    obj = getattr(_sa, name, None) if _sa else None
    if obj is not None:
        try:
            if test is None or test(obj):
                ALGORITHMS_STATUS[name] = "team"
                return obj
        except Exception:
            pass
    ALGORITHMS_STATUS[name] = "temporary fallback"
    return fallback


Stack = _load("Stack", _FallbackStack, _test_stack)
Queue = _load("Queue", _FallbackQueue, _test_queue)
HashTable = _load("HashTable", _FallbackHashTable, _test_hash)
linear_search = _load("linear_search", _fallback_linear_search, _test_linear)
binary_search = _load("binary_search", _fallback_binary_search, _test_binary)
merge_sort = _load("merge_sort", _fallback_merge_sort, _test_sort)
# greedy is tested at the end of this file (needs ParkingSlot) and validated on every call
greedy_slot_allocation = getattr(_sa, "greedy_slot_allocation", None) if _sa else None


def get_algorithms_status():
    return dict(ALGORITHMS_STATUS)


# =============================================================== validation
_LETTERS = r"[A-Zء-ي]"
PLATE_PATTERN = re.compile(rf"^(?:({_LETTERS}{{1,3}})(\d{{1,4}})|(\d{{1,4}})({_LETTERS}{{1,3}}))$")
VEHICLE_ID_PATTERN = re.compile(r"^V\d{4,}$")
SLOT_ID_PATTERN = re.compile(r"^P\d{2,3}$")
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def normalize_plate(plate_number):
    """'abc-1234' -> 'ABC 1234',  'سصع٥٥٢' -> 'س ص ع 552'. Raises ValidationError."""
    if plate_number is None or not str(plate_number).strip():
        raise ValidationError("Plate number is required.")
    text = str(plate_number).translate(_ARABIC_DIGITS).upper()
    compact = re.sub(r"[\s\-_]", "", text)
    match = PLATE_PATTERN.match(compact)
    if not match:
        raise ValidationError(
            f"Invalid plate '{plate_number}'. Use 1-3 letters and 1-4 digits, e.g. ABC 1234 or س ص ع 552."
        )
    letters = match.group(1) or match.group(4)
    digits = match.group(2) or match.group(3)
    if re.match(r"[ء-ي]", letters):
        letters = " ".join(letters)
    return f"{letters} {digits}"


def parse_time(value=None):
    """None -> now. Accepts datetime or 'YYYY-MM-DD HH:MM[:SS]'."""
    if value is None:
        return datetime.now().replace(microsecond=0)
    if isinstance(value, datetime):
        return value.replace(microsecond=0)
    text = str(value).strip().replace("T", " ")
    for fmt in (DATETIME_FORMAT, "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            pass
    raise ValidationError(f"Invalid time '{value}'. Use YYYY-MM-DD HH:MM.")


def format_time(value):
    return value.strftime(DATETIME_FORMAT) if value else None


# ================================================================= vehicles
# Spot sizes and vehicle types use the same names as the dataset
SLOT_SIZES = {"Compact": 1, "Standard": 2, "Oversized": 3}


class Vehicle:
    """Base vehicle. Subclasses change the type, rate and allowed slot sizes."""

    VEHICLE_TYPE = "Car"
    HOURLY_RATE = 10.0
    ALLOWED_SIZES = ("Standard", "Oversized")

    def __init__(self, plate_number, vehicle_id=None):
        self.vehicle_id = vehicle_id
        self.plate_number = normalize_plate(plate_number)
        self.slot_id = None
        self.zone = None
        self.entry_time = None
        self.exit_time = None
        self.requested_at = None      # when it joined the waiting queue
        self.status = "waiting"       # waiting -> parked -> exited  (or cancelled)
        self.parking_duration = None  # minutes
        self.fee = 0.0
        self.from_waiting = False

    @property
    def vehicle_type(self):
        return self.VEHICLE_TYPE

    # ---- polymorphic behaviour
    def can_use(self, slot):
        return slot.size in self.ALLOWED_SIZES

    def billable_hours(self, minutes):
        if minutes <= GRACE_MINUTES:
            return 0
        hours = math.ceil(minutes / 60)
        days, rest = divmod(hours, 24)
        return days * DAILY_CAP_HOURS + min(rest, DAILY_CAP_HOURS)

    def calculate_fee(self, minutes):
        return round(self.billable_hours(minutes) * self.HOURLY_RATE, 2)

    # ---- lifecycle
    def record_entry(self, slot_id, entry_time=None, zone=None):
        if self.status == "parked":
            raise InvalidOperationError(f"{self.plate_number} is already parked at {self.slot_id}.")
        self.slot_id = slot_id
        self.zone = zone
        self.entry_time = parse_time(entry_time)
        self.exit_time = None
        self.parking_duration = None
        self.fee = 0.0
        self.status = "parked"

    def record_exit(self, exit_time=None):
        if self.status != "parked":
            raise InvalidOperationError(f"{self.plate_number} is not parked.")
        exit_time = parse_time(exit_time)
        if exit_time < self.entry_time:
            raise ValidationError("Exit time cannot be before entry time.")
        self.exit_time = exit_time
        self.parking_duration = int((exit_time - self.entry_time).total_seconds() // 60)
        self.fee = self.calculate_fee(self.parking_duration)
        self.status = "exited"
        return self.parking_duration

    def current_duration(self, now=None):
        if self.status == "exited":
            return self.parking_duration
        if self.status != "parked":
            return None
        return max(0, int((parse_time(now) - self.entry_time).total_seconds() // 60))

    def to_record(self):
        """Shared data schema (first 7 keys) + extra columns for the dashboard."""
        return {
            "vehicle_id": self.vehicle_id,
            "plate_number": self.plate_number,
            "slot_id": self.slot_id,
            "entry_time": format_time(self.entry_time),
            "exit_time": format_time(self.exit_time),
            "status": self.status,
            "parking_duration": self.parking_duration,
            "vehicle_type": self.vehicle_type,
            "zone": self.zone,
            "fee": self.fee,
            "from_waiting": self.from_waiting,
        }

    def __repr__(self):
        return f"{self.__class__.__name__}({self.plate_number!r}, {self.status})"


class Car(Vehicle):
    pass


class Motorcycle(Vehicle):
    VEHICLE_TYPE = "Motorcycle"
    HOURLY_RATE = 5.0
    ALLOWED_SIZES = ("Compact", "Standard", "Oversized")


class ElectricVehicle(Car):
    VEHICLE_TYPE = "Electric Vehicle"
    CHARGING_RATE = 5.0

    def calculate_fee(self, minutes):
        base = super().calculate_fee(minutes)
        return round(base + self.billable_hours(minutes) * self.CHARGING_RATE, 2)


class Truck(Vehicle):
    VEHICLE_TYPE = "Truck"
    HOURLY_RATE = 20.0
    ALLOWED_SIZES = ("Oversized",)


VEHICLE_CLASSES = {cls.VEHICLE_TYPE: cls for cls in (Car, Motorcycle, ElectricVehicle, Truck)}
VEHICLE_TYPES = list(VEHICLE_CLASSES)


def create_vehicle(plate_number, vehicle_type="Car", vehicle_id=None):
    for name, cls in VEHICLE_CLASSES.items():
        if str(vehicle_type).strip().lower() == name.lower():
            return cls(plate_number, vehicle_id)
    raise ValidationError(f"Invalid vehicle type '{vehicle_type}'. Choose one of: {', '.join(VEHICLE_TYPES)}.")


# ==================================================================== users
class User:
    ROLE = "user"
    PERMISSIONS = set()

    def __init__(self, name):
        self.name = name

    def can(self, action):
        return "all" in self.PERMISSIONS or action in self.PERMISSIONS


class Driver(User):
    ROLE = "Driver"
    PERMISSIONS = {"view_status", "search"}


class GateOperator(User):
    ROLE = "Gate Operator"
    PERMISSIONS = {"view_status", "search", "park", "exit", "manage_waiting", "view_history"}


class Admin(User):
    ROLE = "Admin"
    PERMISSIONS = {"all"}


ROLES = {cls.ROLE: cls for cls in (Driver, GateOperator, Admin)}


def can(role, action):
    """UI helper: can('Driver', 'park') -> False."""
    cls = ROLES.get(role)
    return bool(cls) and cls("").can(action)


# ==================================================================== slots
class ParkingSlot:
    def __init__(self, slot_id, size="Standard", zone="Zone A", row=0, col=0, index=0):
        if size not in SLOT_SIZES:
            raise ValidationError(f"Invalid slot size '{size}'.")
        self.slot_id = slot_id
        self.size = size
        self.size_rank = SLOT_SIZES[size]
        self.zone = zone
        self.row = row
        self.col = col
        self.index = index          # distance order from the gate (0 = nearest)
        self.is_occupied = False
        self.vehicle = None

    def occupy(self, vehicle):
        if self.is_occupied:
            raise SlotOccupiedError(f"Slot {self.slot_id} is already occupied by {self.vehicle.plate_number}.")
        if not vehicle.can_use(self):
            raise InvalidOperationError(f"A {vehicle.vehicle_type} cannot park in a {self.size} slot.")
        self.vehicle = vehicle
        self.is_occupied = True

    def release(self):
        previous = self.vehicle
        self.vehicle = None
        self.is_occupied = False
        return previous

    def to_dict(self):
        return {
            "slot_id": self.slot_id,
            "zone": self.zone,
            "size": self.size,
            "row": self.row,
            "col": self.col,
            "is_occupied": self.is_occupied,
            "plate_number": self.vehicle.plate_number if self.vehicle else None,
        }

    def __repr__(self):
        return f"ParkingSlot({self.slot_id}, {self.size}, {'occupied' if self.is_occupied else 'free'})"


def _test_greedy(fn):
    slots = [ParkingSlot("P02", "Oversized", index=1), ParkingSlot("P01", "Standard", index=0)]
    return fn(slots, Car("ABC 1")) in slots


try:
    _greedy_ok = greedy_slot_allocation is not None and _test_greedy(greedy_slot_allocation)
except Exception:
    _greedy_ok = False
if not _greedy_ok:
    greedy_slot_allocation = None
ALGORITHMS_STATUS["greedy_slot_allocation"] = "team" if _greedy_ok else "temporary fallback"


def _safe(method):
    """Turn ParkFlowError into {'success': False, 'message': ...} (no crash in the UI)."""
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except ParkFlowError as error:
            return {"success": False, "message": str(error)}
    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__
    return wrapper


# =========================================================== parking system
class ParkingSystem:
    def __init__(self, number_of_slots=10, slots_per_row=5, slot_sizes=None):
        if not isinstance(number_of_slots, int) or not 1 <= number_of_slots <= 500:
            raise ValidationError("Number of slots must be between 1 and 500.")
        if not isinstance(slots_per_row, int) or slots_per_row < 1:
            raise ValidationError("Slots per row must be a positive number.")
        if math.ceil(number_of_slots / slots_per_row) > 26:
            raise ValidationError("Too many rows (max 26 zones). Increase slots_per_row.")
        if slot_sizes is not None and len(slot_sizes) != number_of_slots:
            raise ValidationError("slot_sizes must have one size per slot.")

        self.slots = []
        self.grid = []                       # 2D: grid[row][col]
        for i in range(number_of_slots):
            row, col = divmod(i, slots_per_row)
            if col == 0:
                self.grid.append([])
            if slot_sizes:
                size = slot_sizes[i]
            elif col == 0 and slots_per_row > 2:
                size = "Compact"
            elif col == slots_per_row - 1 and slots_per_row > 2:
                size = "Oversized"
            else:
                size = "Standard"
            slot = ParkingSlot(f"P{i + 1:02d}", size, f"Zone {chr(65 + row)}", row, col, i)
            self.slots.append(slot)
            self.grid[row].append(slot)

        self.vehicles = {}                   # vehicle_id -> Vehicle (all sessions)
        self.waiting_queue = Queue()
        self.history = Stack()
        self.vehicle_index = HashTable()     # plate -> Vehicle (parked or waiting)
        self._next_id = 1

    # ------------------------------------------------------------ helpers
    def _new_vehicle(self, plate_number, vehicle_type):
        vehicle = create_vehicle(plate_number, vehicle_type, f"V{self._next_id:04d}")
        self._next_id += 1
        self.vehicles[vehicle.vehicle_id] = vehicle
        return vehicle

    def _queue_to_list(self):
        """Read the queue in order using only enqueue/dequeue, then restore it."""
        items = []
        while not self.waiting_queue.is_empty():
            items.append(self.waiting_queue.dequeue())
        for item in items:
            self.waiting_queue.enqueue(item)
        return items

    def _rebuild_queue(self, items):
        while not self.waiting_queue.is_empty():
            self.waiting_queue.dequeue()
        for item in items:
            self.waiting_queue.enqueue(item)

    def _stack_to_list(self):
        """Oldest first, stack restored after reading."""
        items = []
        while not self.history.is_empty():
            items.append(self.history.pop())
        for item in reversed(items):
            self.history.push(item)
        return list(reversed(items))

    def _log(self, action, vehicle, time, details=""):
        self.history.push({
            "time": format_time(time),
            "action": action,
            "vehicle_id": vehicle.vehicle_id,
            "plate_number": vehicle.plate_number,
            "slot_id": vehicle.slot_id,
            "details": details,
        })

    def _choose_slot(self, vehicle):
        candidates = [s for s in self.get_available_slots() if vehicle.can_use(s)]
        if not candidates:
            return None
        if greedy_slot_allocation is not None:
            try:
                slot = greedy_slot_allocation(candidates, vehicle)
                if slot in candidates:  # never trust a slot that is taken / wrong size
                    return slot
            except Exception:
                pass
        return _fallback_greedy(candidates, vehicle)

    def _park_in(self, vehicle, slot, now):
        slot.occupy(vehicle)
        vehicle.record_entry(slot.slot_id, now, slot.zone)
        self.vehicle_index.insert(vehicle.plate_number, vehicle)

    # ------------------------------------------------------- validation
    def validate_plate_number(self, plate_number):
        """Return the normalized plate or raise ValidationError."""
        return normalize_plate(plate_number)

    # ----------------------------------------------------------- arrival
    @_safe
    def park_vehicle(self, plate_number, vehicle_type="Car", now=None):
        """Validate, reject duplicates, allocate a slot or add to the waiting queue."""
        plate = self.validate_plate_number(plate_number)
        now = parse_time(now)
        create_vehicle(plate, vehicle_type)  # validate type before using an id
        current = self.find_vehicle(plate)
        if current is not None:
            where = f"parked at {current.slot_id}" if current.status == "parked" else "in the waiting queue"
            raise DuplicateVehicleError(f"Vehicle {plate} is already {where}.")

        vehicle = self._new_vehicle(plate, vehicle_type)
        slot = self._choose_slot(vehicle)
        if slot is None:
            vehicle.requested_at = now
            self.waiting_queue.enqueue(vehicle)
            self.vehicle_index.insert(plate, vehicle)
            position = len(self._queue_to_list())
            self._log("wait", vehicle, now, f"position {position}")
            return {"success": True, "status": "waiting", "position": position,
                    "vehicle": vehicle.to_record(),
                    "message": f"No suitable slot. {plate} added to the waiting queue (#{position})."}

        self._park_in(vehicle, slot, now)
        self._log("park", vehicle, now)
        return {"success": True, "status": "parked", "slot_id": slot.slot_id,
                "vehicle": vehicle.to_record(),
                "message": f"{plate} parked at {slot.slot_id} ({slot.zone})."}

    # -------------------------------------------------------------- exit
    @_safe
    def exit_vehicle(self, plate_number, now=None):
        """Validate, record exit, release slot, serve the waiting queue."""
        plate = self.validate_plate_number(plate_number)
        vehicle = self.find_vehicle(plate)
        if vehicle is None or vehicle.status != "parked":
            raise VehicleNotFoundError(f"Vehicle {plate} is not parked here.")
        now = parse_time(now)
        vehicle.record_exit(now)
        self._slot_by_id(vehicle.slot_id).release()
        self.vehicle_index.delete(plate)
        self._log("exit", vehicle, now, f"fee {vehicle.fee:.2f}")

        served = []
        while True:
            result = self.allocate_next_waiting_vehicle(now)
            if result is None:
                break
            served.append(result["vehicle"])
        return {"success": True, "vehicle": vehicle.to_record(), "fee": vehicle.fee,
                "duration_minutes": vehicle.parking_duration, "served_from_queue": served,
                "message": f"{plate} exited after {vehicle.parking_duration} min. Fee: {vehicle.fee:.2f} EGP."}

    @_safe
    def quote_fee(self, plate_number, now=None):
        vehicle = self.find_vehicle(self.validate_plate_number(plate_number))
        if vehicle is None or vehicle.status != "parked":
            raise VehicleNotFoundError(f"Vehicle {plate_number} is not parked here.")
        minutes = vehicle.current_duration(now)
        return {"success": True, "duration_minutes": minutes, "fee": vehicle.calculate_fee(minutes),
                "message": f"Current fee: {vehicle.calculate_fee(minutes):.2f} EGP ({minutes} min)."}

    # ------------------------------------------------------------ lookup
    def find_vehicle(self, plate_number):
        """HashTable lookup. Returns the Vehicle (parked or waiting) or None."""
        try:
            plate = self.validate_plate_number(plate_number)
        except ValidationError:
            return None
        return self.vehicle_index.search(plate)

    def _slot_by_id(self, slot_id):
        slot = linear_search(self.slots, str(slot_id).strip().upper(), key=lambda s: s.slot_id)
        if slot is None:
            raise ValidationError(f"Slot {slot_id} does not exist.")
        return slot

    def find_record_by_id(self, vehicle_id):
        """Binary search: vehicle ids are created in increasing order, so the list is sorted."""
        vid = str(vehicle_id).strip().upper()
        if not VEHICLE_ID_PATTERN.match(vid):
            return None
        records = list(self.vehicles.values())
        return _bsearch_result(binary_search(records, vid, key=lambda v: v.vehicle_id), records)

    def search_vehicles(self, text, field="plate_number"):
        """Sequential search (partial match) over all records."""
        if field not in ("plate_number", "slot_id", "vehicle_type", "status", "zone"):
            return []
        query = re.sub(r"\s", "", str(text or "")).lower()
        if not query:
            return []
        results = []
        for vehicle in self.vehicles.values():
            value = re.sub(r"\s", "", str(vehicle.to_record()[field] or "")).lower()
            if query in value:
                results.append(vehicle.to_record())
        return results

    def sort_records(self, by="entry_time", descending=False):
        """Merge sort (Ibrahim) on any record column."""
        records = self.get_records()
        numeric = by in ("parking_duration", "fee")

        def key(record):
            value = record.get(by)
            if numeric:
                return float(value or 0)
            return "" if value is None else str(value)

        result = merge_sort(records, key=key)
        if descending:
            result = [result[i] for i in range(len(result) - 1, -1, -1)]
        return result

    # ------------------------------------------------------------- slots
    def get_available_slots(self):
        return [slot for slot in self.slots if not slot.is_occupied]

    def get_occupied_slots(self):
        return [slot for slot in self.slots if slot.is_occupied]

    def get_slot_grid(self):
        """2D list of slot dicts (rows = zones) for the parking map."""
        return [[slot.to_dict() for slot in row] for row in self.grid]

    def get_occupancy_matrix(self):
        """2D list of 0 (free) / 1 (occupied) for a heatmap. Short rows padded with None."""
        width = max(len(row) for row in self.grid)
        return [[int(s.is_occupied) for s in row] + [None] * (width - len(row)) for row in self.grid]

    # ----------------------------------------------------------- waiting
    def get_waiting_vehicles(self):
        """Waiting vehicles in arrival order."""
        return self._queue_to_list()

    def allocate_next_waiting_vehicle(self, now=None):
        """
        Give a free slot to the first waiting vehicle that fits (FIFO).
        A vehicle that still does not fit keeps its place in the queue.
        Returns a result dict, or None if nobody could be served.
        """
        waiting = self._queue_to_list()
        for position, vehicle in enumerate(waiting):
            slot = self._choose_slot(vehicle)
            if slot is None:
                continue
            now = parse_time(now)
            self._rebuild_queue(waiting[:position] + waiting[position + 1:])
            vehicle.from_waiting = True
            self._park_in(vehicle, slot, now)
            self._log("park", vehicle, now, "from waiting queue")
            return {"success": True, "status": "parked", "slot_id": slot.slot_id,
                    "vehicle": vehicle.to_record(),
                    "message": f"{vehicle.plate_number} moved from the queue to {slot.slot_id}."}
        return None

    @_safe
    def remove_from_waiting(self, plate_number, now=None):
        plate = self.validate_plate_number(plate_number)
        waiting = self._queue_to_list()
        for position, vehicle in enumerate(waiting):
            if vehicle.plate_number == plate:
                self._rebuild_queue(waiting[:position] + waiting[position + 1:])
                self.vehicle_index.delete(plate)
                vehicle.status = "cancelled"
                self._log("leave_queue", vehicle, parse_time(now), f"position {position + 1}")
                return {"success": True, "message": f"{plate} removed from the waiting queue."}
        raise VehicleNotFoundError(f"Vehicle {plate} is not in the waiting queue.")

    # ------------------------------------------------------------ status
    def get_parking_status(self):
        total = len(self.slots)
        occupied = len(self.get_occupied_slots())
        by_zone, by_size = {}, {}
        for slot in self.slots:
            for groups, name in ((by_zone, slot.zone), (by_size, slot.size)):
                group = groups.setdefault(name, {"total": 0, "occupied": 0, "available": 0})
                group["total"] += 1
                group["occupied" if slot.is_occupied else "available"] += 1
        return {
            "total": total,
            "available": total - occupied,
            "occupied": occupied,
            "waiting": len(self._queue_to_list()),
            "occupancy_rate": round(occupied / total * 100, 1) if total else 0.0,
            "by_zone": by_zone,
            "by_size": by_size,
        }

    def get_records(self, status=None):
        """Every vehicle session as a dict -> pd.DataFrame(system.get_records())."""
        return [v.to_record() for v in self.vehicles.values() if status is None or v.status == status]

    def get_summary(self, now=None):
        """Live KPIs for the dashboard."""
        now = parse_time(now)
        exited = [v for v in self.vehicles.values() if v.status == "exited"]
        today = [v for v in exited if v.exit_time.date() == now.date()]
        return {
            **self.get_parking_status(),
            "total_sessions": len(self.vehicles),
            "completed_sessions": len(exited),
            "revenue_today": round(sum(v.fee for v in today), 2),
            "total_revenue": round(sum(v.fee for v in exited), 2),
            "average_duration": round(sum(v.parking_duration for v in exited) / len(exited), 1) if exited else 0,
        }

    # ----------------------------------------------------------- history
    def get_history(self):
        """Operation history, oldest first."""
        return self._stack_to_list()

    @_safe
    def undo_last_operation(self):
        """Undo the most recent operation using the history Stack."""
        operation = self.history.pop()
        if operation is None:
            raise InvalidOperationError("Nothing to undo.")
        try:
            message = self._undo(operation)
        except ParkFlowError:
            self.history.push(operation)
            raise
        return {"success": True, "message": message}

    def _undo(self, op):
        vehicle = self.vehicles.get(op["vehicle_id"])
        if vehicle is None:
            raise InvalidOperationError("Cannot undo: record not found.")
        action = op["action"]

        if action == "park":
            if vehicle.status != "parked" or vehicle.slot_id != op["slot_id"]:
                raise InvalidOperationError(f"Cannot undo: {vehicle.plate_number} is no longer in {op['slot_id']}.")
            self._slot_by_id(vehicle.slot_id).release()
            vehicle.slot_id, vehicle.zone, vehicle.entry_time = None, None, None
            if vehicle.from_waiting:   # return it to the front of the queue
                vehicle.status, vehicle.from_waiting = "waiting", False
                self._rebuild_queue([vehicle] + self._queue_to_list())
                return f"Undo: {vehicle.plate_number} returned to the front of the waiting queue."
            vehicle.status = "cancelled"
            self.vehicle_index.delete(vehicle.plate_number)
            return f"Undo: entry of {vehicle.plate_number} cancelled."

        if action == "exit":
            slot = self._slot_by_id(op["slot_id"])
            if vehicle.status != "exited" or slot.is_occupied or self.find_vehicle(vehicle.plate_number):
                raise InvalidOperationError(f"Cannot undo exit of {vehicle.plate_number}: slot or vehicle changed.")
            slot.occupy(vehicle)
            vehicle.status, vehicle.exit_time, vehicle.parking_duration, vehicle.fee = "parked", None, None, 0.0
            self.vehicle_index.insert(vehicle.plate_number, vehicle)
            return f"Undo: {vehicle.plate_number} is back in {slot.slot_id}."

        if action == "wait":
            waiting = self._queue_to_list()
            if vehicle not in waiting:
                raise InvalidOperationError(f"Cannot undo: {vehicle.plate_number} is no longer waiting.")
            self._rebuild_queue([v for v in waiting if v is not vehicle])
            self.vehicle_index.delete(vehicle.plate_number)
            vehicle.status = "cancelled"
            return f"Undo: {vehicle.plate_number} removed from the waiting queue."

        if action == "leave_queue":
            if self.find_vehicle(vehicle.plate_number):
                raise InvalidOperationError(f"Cannot undo: {vehicle.plate_number} is already in the system.")
            waiting = self._queue_to_list()
            position = int(op["details"].split()[-1]) - 1
            waiting.insert(min(position, len(waiting)), vehicle)
            self._rebuild_queue(waiting)
            vehicle.status = "waiting"
            self.vehicle_index.insert(vehicle.plate_number, vehicle)
            return f"Undo: {vehicle.plate_number} is back in the waiting queue."

        raise InvalidOperationError(f"Cannot undo '{action}'.")

    # ------------------------------------------------------------ export
    def export_records_csv(self, path):
        records = self.get_records()
        columns = list(Vehicle("AAA 1").to_record().keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(records)
        return len(records)

    def __repr__(self):
        s = self.get_parking_status()
        return f"ParkingSystem(total={s['total']}, occupied={s['occupied']}, waiting={s['waiting']})"
