"""
ParkFlow Core Engine: Fully Upgraded OOP Models, Data Structures, and Algorithms
Author: Ibrahim
Course: Samsung Innovation Campus (SIC 8) - Final Project
Description: Fully addresses validation, proper Stack/Queue classes, Custom Hash Table,
Linear Search, Binary Search with sort checks, Merge Sort with comparison/recursion counters,
size-aware Greedy Allocation, and algorithm statistics.
"""

from collections import deque
import re

# ==========================================
# PART 1: OBJECT-ORIENTED PROGRAMMING & VALIDATION
# ==========================================

class Vehicle:
    """Represents a vehicle with strict regex validation rejecting invalid formats."""
    def __init__(self, plate_number: str, vehicle_type: str, owner_name: str, phone: str):
        self.plate_number = self.validate_plate(plate_number)
        self.vehicle_type = vehicle_type  # 'Car', 'SUV', 'Motorcycle'
        self.owner_name = owner_name.strip()
        self.phone = self.validate_phone(phone)

    @staticmethod
    def validate_plate(plate: str) -> str:
        """Validates license plate format using strict Regex and raises ValueError if invalid."""
        if not plate or not isinstance(plate, str):
            raise ValueError("License plate cannot be empty.")
        clean_plate = plate.strip().upper()
        # Standard format: e.g., ABC-1234 or A12-345
        pattern = r"^[A-Z0-9]{2,4}[-\s]?[0-9]{2,4}$"
        if not re.match(pattern, clean_plate):
            raise ValueError(f"Invalid license plate format: '{plate}'. Expected format like 'ABC-1234'.")
        return clean_plate

    @staticmethod
    def validate_phone(phone: str) -> str:
        """Validates Egyptian mobile format completely via Regex (010, 011, 012, 015 + 8 digits)."""
        if not phone or not isinstance(phone, str):
            raise ValueError("Phone number cannot be empty.")
        clean_phone = phone.strip()
        pattern = r"^01[0125][0-9]{8}$"
        if not re.match(pattern, clean_phone):
            raise ValueError(f"Invalid phone number: '{phone}'. Must be a valid 11-digit Egyptian mobile number.")
        return clean_phone


class ParkingSpot:
    """Represents an individual parking spot inside the garage grid."""
    def __init__(self, spot_id: str, floor: int, size: str, hourly_rate: float):
        self.spot_id = spot_id            # e.g., "F1-01"
        self.floor = floor                
        self.size = size                  # 'Small', 'Medium', 'Large'
        self.hourly_rate = float(hourly_rate)    
        self.is_occupied = False          
        self.current_vehicle = None       

    def occupy(self, vehicle: Vehicle):
        self.is_occupied = True
        self.current_vehicle = vehicle

    def vacate(self):
        self.is_occupied = False
        vehicle_leaving = self.current_vehicle
        self.current_vehicle = None
        return vehicle_leaving


class Ticket:
    """Represents an active or closed parking session ticket."""
    def __init__(self, ticket_id: str, vehicle: Vehicle, spot: ParkingSpot, entry_time: float):
        self.ticket_id = ticket_id
        self.vehicle = vehicle
        self.spot = spot
        self.entry_time = entry_time
        self.exit_time = None
        self.total_fee = 0.0
        self.status = "Active"

    def close_ticket(self, exit_time: float):
        self.exit_time = exit_time
        duration_hours = max(1.0, (self.exit_time - self.entry_time) / 3600.0)
        self.total_fee = round(duration_hours * self.spot.hourly_rate, 2)
        self.status = "Closed"
        self.spot.vacate()
        return self.total_fee


# ==========================================
# PART 2: CUSTOM DATA STRUCTURES (Stack, Queue, Hash Table)
# ==========================================

class GarageQueue:
    """Dedicated FIFO Queue class for waiting vehicles."""
    def __init__(self):
        self.items = deque()

    def enqueue(self, vehicle: Vehicle):
        self.items.append(vehicle)

    def dequeue(self) -> Vehicle:
        if not self.is_empty():
            return self.items.popleft()
        return None

    def is_empty(self) -> bool:
        return len(self.items) == 0

    def size(self) -> int:
        return len(self.items)


class StateUndoStack:
    """LIFO Stack maintaining state-reverting actions for true Undo functionality."""
    def __init__(self):
        self.stack = []

    def push(self, action_name: str, undo_callback):
        """Pushes an action tuple: (description, function_to_reverse_it)"""
        self.stack.append((action_name, undo_callback))

    def pop_and_undo(self) -> str:
        """Pops the last action and executes its callback to reverse state."""
        if not self.stack:
            return "No actions available to undo."
        action_name, undo_callback = self.stack.pop()
        undo_callback()  # Executes state reversal
        return f"Successfully reverted action: {action_name}"

    def is_empty(self) -> bool:
        return len(self.stack) == 0


class CustomHashTable:
    """Custom Hash Table implemented from scratch using Chaining to handle collisions."""
    def __init__(self, capacity: int = 50):
        self.capacity = capacity
        self.buckets = [[] for _ in range(capacity)]
        self.size = 0

    def _hash_function(self, key: str) -> int:
        return sum(ord(char) for char in str(key)) % self.capacity

    def insert(self, key: str, value):
        index = self._hash_function(key)
        bucket = self.buckets[index]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        bucket.append((key, value))
        self.size += 1

    def get(self, key: str):
        index = self._hash_function(key)
        bucket = self.buckets[index]
        for k, v in bucket:
            if k == key:
                return v
        return None

    def remove(self, key: str) -> bool:
        index = self._hash_function(key)
        bucket = self.buckets[index]
        for i, (k, v) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self.size -= 1
                return True
        return False


# ==========================================
# PART 3: ALGORITHMS ENGINE & STATISTICS
# ==========================================

class GarageManager:
    """Core manager containing all requested search, sort, greedy allocation, and performance counters."""
    def __init__(self):
        self.spots = []
        self.waiting_queue = GarageQueue()
        self.action_stack = StateUndoStack()
        self.ticket_hash_table = CustomHashTable(100)
        
        # Statistics counters
        self.stats = {
            "merge_comparisons": 0,
            "merge_recursions": 0,
            "linear_searches_performed": 0,
            "binary_searches_performed": 0
        }

    def add_spot(self, spot: ParkingSpot):
        self.spots.append(spot)

    # --- 1. QUEUE & STACK OPERATIONS WITH REAL STATE REVERSAL ---
    def enqueue_vehicle(self, vehicle: Vehicle):
        self.waiting_queue.enqueue(vehicle)
        # Register Undo State Reversal Callback
        self.action_stack.push(
            f"Enqueue Vehicle {vehicle.plate_number}",
            lambda: self.waiting_queue.items.pop() if self.waiting_queue.items else None
        )

    def undo_last_system_action(self) -> str:
        return self.action_stack.pop_and_undo()

    # --- 2. LINEAR SEARCH ALGORITHM ---
    def linear_search_by_owner(self, owner_name: str) -> list:
        """Performs Linear Search on unsorted spot list with performance tracking."""
        self.stats["linear_searches_performed"] += 1
        results = []
        target = owner_name.strip().lower()
        for spot in self.spots:
            if spot.is_occupied and spot.current_vehicle:
                if target in spot.current_vehicle.owner_name.lower():
                    results.append((spot, spot.current_vehicle))
        return results

    # --- 3. SIZE-AWARE GREEDY ALLOCATION ALGORITHM ---
    def greedy_allocate_spot(self, vehicle: Vehicle) -> ParkingSpot:
        """
        Greedy Choice: Filters spots by vehicle size compatibility 
        and immediately selects the cheapest available spot.
        """
        # Size mapping hierarchy compatibility
        size_hierarchy = {'Small': 1, 'Medium': 2, 'Large': 3}
        v_size_val = size_hierarchy.get(vehicle.vehicle_type, 2) # Default Medium

        # Filter available spots matching size constraints
        compatible_spots = []
        for s in self.spots:
            if not s.is_occupied:
                s_size_val = size_hierarchy.get(s.size, 2)
                if s_size_val >= v_size_val:  # Spot can fit vehicle size
                    compatible_spots.append(s)

        if not compatible_spots:
            return None

        # Greedy choice: minimum hourly rate among compatible spots
        best_spot = min(compatible_spots, key=lambda s: s.hourly_rate)
        return best_spot

    # --- 4. MANUAL MERGE SORT ALGORITHM (WITH METRICS) ---
    def merge_sort_spots_by_rate(self, spot_list: list) -> list:
        """Manually sorts parking spots by hourly rate using Merge Sort, tracking comparisons."""
        self.stats["merge_recursions"] += 1
        if len(spot_list) <= 1:
            return spot_list

        mid = len(spot_list) // 2
        left_half = self.merge_sort_spots_by_rate(spot_list[:mid])
        right_half = self.merge_sort_spots_by_rate(spot_list[mid:])

        return self._merge(left_half, right_half)

    def _merge(self, left: list, right: list) -> list:
        sorted_result = []
        i = j = 0
        while i < len(left) and j < len(right):
            self.stats["merge_comparisons"] += 1
            if left[i].hourly_rate <= right[j].hourly_rate:
                sorted_result.append(left[i])
                i += 1
            else:
                sorted_result.append(right[j])
                j += 1
        sorted_result.extend(left[i:])
        sorted_result.extend(right[j:])
        return sorted_result

    # --- 5. BINARY SEARCH ALGORITHM (WITH SORT CHECK & SAFETY) ---
    def binary_search_spot_id(self, sorted_spot_ids: list, target_id: str) -> int:
        """
        Performs Binary Search on sorted spot IDs. 
        Ensures list is sorted beforehand to prevent incorrect results.
        """
        self.stats["binary_searches_performed"] += 1
        
        # Verify sort order invariant
        if sorted_spot_ids != sorted(sorted_spot_ids):
            sorted_spot_ids = sorted(sorted_spot_ids)  # Auto-correct safety guard

        left = 0
        right = len(sorted_spot_ids) - 1

        while left <= right:
            mid = (left + right) // 2
            if sorted_spot_ids[mid] == target_id:
                return mid
            elif sorted_spot_ids[mid] < target_id:
                left = mid + 1
            else:
                right = mid - 1
        return -1  # Not found indicator

    def get_performance_statistics(self) -> dict:
        """Returns algorithm performance counters and metrics for testing."""
        return self.stats



# ==========================================================
# COMPATIBILITY API FOR Ali's core.py
# The original Ibrahim classes and methods above are preserved.
# These adapters expose the names/signatures expected by core.py.
# ==========================================================

class Stack:
    """Compatibility Stack API expected by core.py."""
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


class Queue(GarageQueue):
    """Expose Ibrahim's FIFO queue under the name expected by core.py."""
    def peek(self):
        return self.items[0] if self.items else None


class HashTable(CustomHashTable):
    """Expose Ibrahim's custom hash table using core.py's expected API."""
    def search(self, key):
        return self.get(key)

    def delete(self, key):
        return self.remove(key)


def linear_search(data, target, key=None):
    """Return the matching item (not its index), or None if not found."""
    key_fn = key or (lambda item: item)
    for item in data:
        if key_fn(item) == target:
            return item
    return None


def binary_search(sorted_data, target, key=None):
    """Binary search on data already sorted ascending; return item or None."""
    key_fn = key or (lambda item: item)
    low, high = 0, len(sorted_data) - 1
    while low <= high:
        mid = (low + high) // 2
        value = key_fn(sorted_data[mid])
        if value == target:
            return sorted_data[mid]
        if value < target:
            low = mid + 1
        else:
            high = mid - 1
    return None


def merge_sort(data, key=None):
    """Stable Merge Sort wrapper using Ibrahim's existing merge-sort logic."""
    key_fn = key or (lambda item: item)
    manager = GarageManager()

    class _Sortable:
        def __init__(self, item):
            self.item = item
            self.sort_key = key_fn(item)

        @property
        def hourly_rate(self):
            return self.sort_key

    wrapped = [_Sortable(item) for item in data]
    sorted_wrapped = manager.merge_sort_spots_by_rate(wrapped)
    return [item.item for item in sorted_wrapped]


def greedy_slot_allocation(candidates, vehicle):
    """Compatibility signature expected by core.py; choose a suitable slot."""
    if not candidates:
        return None

    vehicle_type = str(getattr(vehicle, "vehicle_type", "")).strip().lower()
    vehicle_size = getattr(vehicle, "size_rank", None)
    if vehicle_size is None:
        if any(word in vehicle_type for word in ("truck", "bus", "large")):
            vehicle_size = 3
        elif any(word in vehicle_type for word in ("motorcycle", "bike", "compact", "small")):
            vehicle_size = 1
        else:
            vehicle_size = 2

    def slot_rank(slot):
        rank = getattr(slot, "size_rank", None)
        if rank is None:
            size = str(getattr(slot, "size", "Standard")).strip().lower()
            rank = 1 if size in ("compact", "small") else 3 if size in ("oversized", "large") else 2
        return rank, getattr(slot, "index", 0)

    compatible = [slot for slot in candidates if slot_rank(slot)[0] >= vehicle_size]
    return min(compatible, key=slot_rank) if compatible else None


__all__ = [
    "Vehicle", "ParkingSpot", "Ticket", "GarageQueue", "StateUndoStack",
    "CustomHashTable", "GarageManager", "Stack", "Queue", "HashTable",
    "linear_search", "binary_search", "merge_sort", "greedy_slot_allocation"
]
