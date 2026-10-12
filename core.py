from datetime import datetime
import re


class Vehicle:
    def __init__(self, plate_number, vehicle_id=None):
        self.vehicle_id = vehicle_id
        self.plate_number = plate_number
        self.slot_id = None
        self.entry_time = None
        self.exit_time = None
        self.status = "waiting"
        self.parking_duration = None

    def record_entry(self, slot_id):
        # TODO: Record entry time and assigned slot
        pass

    def record_exit(self):
        # TODO: Record exit time and calculate duration
        pass

    def to_record(self):
        # TODO: Return a dictionary using the shared data schema
        pass


class ParkingSlot:
    def __init__(self, slot_id):
        self.slot_id = slot_id
        self.is_occupied = False
        self.vehicle = None

    def occupy(self, vehicle):
        # TODO: Reject occupied slots and assign the vehicle
        pass

    def release(self):
        # TODO: Release the slot and return the previous vehicle
        pass


class ParkingSystem:
    def __init__(self, number_of_slots=10):
        self.slots = [
            ParkingSlot(f"P{i:02d}")
            for i in range(1, number_of_slots + 1)
        ]
        self.vehicles = {}
        self.waiting_queue = None
        self.history = None
        self.vehicle_index = None

    def validate_plate_number(self, plate_number):
        # TODO: Validate non-empty plate numbers using agreed rules
        pass

    def park_vehicle(self, plate_number):
        # TODO: Validate, reject duplicates, allocate or enqueue
        pass

    def exit_vehicle(self, plate_number):
        # TODO: Validate, record exit, release slot, serve queue
        pass

    def find_vehicle(self, plate_number):
        # TODO: Search for a vehicle using the shared lookup structure
        pass

    def get_available_slots(self):
        # TODO: Return a list of available ParkingSlot objects
        pass

    def get_occupied_slots(self):
        # TODO: Return a list of occupied ParkingSlot objects
        pass

    def get_waiting_vehicles(self):
        # TODO: Return waiting vehicles in arrival order
        pass

    def allocate_next_waiting_vehicle(self):
        # TODO: Allocate a newly available slot to the next vehicle
        pass

    def get_parking_status(self):
        # TODO: Return total, available, occupied, and waiting counts
        pass

    def get_history(self):
        # TODO: Return operation history, oldest first
        pass
