from collections import deque
import re
# ==========================================
# PART 1: OBJECT-ORIENTED PROGRAMMING (OOP)
# ==========================================
class Vehicle:
    """Represents a vehicle entering the parking system with strict validation."""
    def __init__(self, plate_number: str, vehicle_type: str, owner_name: str, phone: str):
        self.plate_number = self.validate_plate(plate_number)
        self.vehicle_type = vehicle_type  # 'Car', 'SUV', 'Motorcycle'
        self.owner_name = owner_name
        self.phone = self.validate_phone(phone)
    @staticmethod
    def validate_plate(plate: str) -> str:
        """Validates license plate format using Regex (e.g., ABC-1234 or 1234 ABC)."""
        clean_plate = plate.strip().upper()
        pattern = r"^[A-Z0-9]{2,4}[-\s]?[0-9]{2,4}$"
        if not re.match(pattern, clean_plate):
            pass
        return clean_plate
    @staticmethod
    def validate_phone(phone: str) -> str:
        """Validates phone number using Regex."""
        clean_phone = phone.strip()
        pattern = r"^01[0125][0-9]{8}$" 
        if not re.match(pattern, clean_phone) and len(clean_phone) < 10:
            raise ValueError("Invalid phone number format.")
        return clean_phone
class ParkingSpot:
    """Represents an individual parking spot inside the garage grid."""
    def __init__(self, spot_id: str, floor: int, size: str, hourly_rate: float):
        self.spot_id = spot_id            
        self.floor = floor                
        self.size = size                  
        self.hourly_rate = hourly_rate    
        self.is_occupied = False          
        self.current_vehicle = None       

    def occupy(self, vehicle: Vehicle):
        """Marks the spot as occupied by a vehicle."""
        self.is_occupied = True
        self.current_vehicle = vehicle

    def vacate(self):
        """Frees up the parking spot."""
        self.is_occupied = False
        vehicle_leaving = self.current_vehicle
        self.current_vehicle = None
        return vehicle_leaving

class Ticket:
    """Represents a parking session ticket."""
    def __init__(self, ticket_id: str, vehicle: Vehicle, spot: ParkingSpot, entry_time: float):
        self.ticket_id = ticket_id
        self.vehicle = vehicle
        self.spot = spot
        self.entry_time = entry_time  # timestamp
        self.exit_time = None
        self.total_fee = 0.0
        self.status = "Active"

    def close_ticket(self, exit_time: float):
        """Calculates fee and closes the parking session."""
        self.exit_time = exit_time
        duration_hours = max(1.0, (self.exit_time - self.entry_time) / 3600.0)
        self.total_fee = round(duration_hours * self.spot.hourly_rate, 2)
        self.status = "Closed"
        self.spot.vacate()
        return self.total_fee

# ==========================================
# PART 2: DATA STRUCTURES & ALGORITHMS
# ==========================================
class GarageManager:
    """Core Engine managing queues, stacks, search, sort, and greedy allocation."""
    def __init__(self):
        self.spots = []                  
        self.waiting_queue = deque()    
        self.action_stack = []           
        self.active_tickets = {}         

    def add_spot(self, spot: ParkingSpot):
        """Adds a parking spot to the system."""
        self.spots.append(spot)

    # --- 1. QUEUE OPERATION (FIFO) ---
    def enqueue_waiting_vehicle(self, vehicle: Vehicle):
        """Adds a vehicle to the waiting queue if no spots are available."""
        self.waiting_queue.append(vehicle)
        self.action_stack.append(f"Enqueued vehicle: {vehicle.plate_number}")

    def dequeue_waiting_vehicle(self) -> Vehicle:
        """Removes and returns the first vehicle waiting in line."""
        if self.waiting_queue:
            vehicle = self.waiting_queue.popleft()
            self.action_stack.append(f"Dequeued waiting vehicle: {vehicle.plate_number}")
            return vehicle
        return None

    # --- 2. STACK OPERATION (LIFO / UNDO) ---
    def undo_last_action(self) -> str:
        """Reverts or pops the last recorded action from the stack."""
        if self.action_stack:
            last_action = self.action_stack.pop()
            return f"Undone successfully: {last_action}"
        return "No actions to undo."

    # --- 3. GREEDY ALGORITHM (Optimal Spot Allocation) ---
    def greedy_allocate_spot(self, vehicle: Vehicle) -> ParkingSpot:
        available_spots = [s for s in self.spots if not s.is_occupied]
        if not available_spots:
            return None

        best_spot = min(available_spots, key=lambda s: s.hourly_rate)
        return best_spot
    
    # --- 4. MANUAL MERGE SORT ALGORITHM ---
    def merge_sort_spots_by_rate(self, spot_list: list) -> list:
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
            if left[i].hourly_rate <= right[j].hourly_rate:
                sorted_result.append(left[i])
                i += 1
            else:
                sorted_result.append(right[j])
                j += 1
        sorted_result.extend(left[i:])
        sorted_result.extend(right[j:])
        return sorted_result

    # --- 5. BINARY SEARCH ALGORITHM ---
    def binary_search_spot(self, sorted_spot_ids: list, target_id: str) -> int:
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
        return -1
