"""
Core tests (Ali). Run from the project folder:
    python -m unittest discover -s tests -v
"""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import core  # noqa: E402
from core import ParkingSystem, ValidationError, can, create_vehicle, normalize_plate  # noqa: E402

T0 = "2026-10-14 08:00"


class TestValidation(unittest.TestCase):
    def test_plates(self):
        self.assertEqual(normalize_plate("abc-1234"), "ABC 1234")
        self.assertEqual(normalize_plate("1234abc"), "ABC 1234")
        self.assertEqual(normalize_plate("سصع٥٥٢"), "س ص ع 552")
        for bad in ["", None, "   ", "12", "ABCD 1", "AB 12345", "A#B 1"]:
            with self.assertRaises(ValidationError):
                normalize_plate(bad)

    def test_polymorphism(self):
        car, ev = create_vehicle("C 1", "Car"), create_vehicle("E 1", "Electric Vehicle")
        self.assertEqual(car.calculate_fee(10), 0)          # grace period
        self.assertEqual(car.calculate_fee(61), 20)         # 2 started hours
        self.assertEqual(ev.calculate_fee(61), 30)          # + charging
        self.assertEqual(car.calculate_fee(24 * 60), 100)   # daily cap
        with self.assertRaises(ValidationError):
            create_vehicle("A 1", "Plane")

    def test_roles(self):
        self.assertFalse(can("Driver", "park"))
        self.assertTrue(can("Gate Operator", "exit"))
        self.assertTrue(can("Admin", "anything"))


class TestParkingFlow(unittest.TestCase):
    def setUp(self):
        self.ps = ParkingSystem(number_of_slots=5, slots_per_row=5)   # C S S S O

    def test_layout_and_grid(self):
        self.assertEqual([s.size for s in self.ps.slots], ["Compact", "Standard", "Standard", "Standard", "Oversized"])
        self.assertEqual(self.ps.get_occupancy_matrix(), [[0, 0, 0, 0, 0]])
        big = ParkingSystem(12, 5)
        self.assertEqual([len(r) for r in big.grid], [5, 5, 2])
        self.assertEqual(big.get_occupancy_matrix()[2], [0, 0, None, None, None])
        with self.assertRaises(ValidationError):
            ParkingSystem(0)

    def test_park_rules(self):
        self.assertEqual(self.ps.park_vehicle("MOT 1", "Motorcycle", now=T0)["slot_id"], "P01")   # smallest fit
        self.assertEqual(self.ps.park_vehicle("TRK 1", "Truck", now=T0)["slot_id"], "P05")
        self.assertEqual(self.ps.park_vehicle("CAR 1", now=T0)["slot_id"], "P02")
        dup = self.ps.park_vehicle("car-1", now=T0)
        self.assertFalse(dup["success"])
        self.assertFalse(self.ps.park_vehicle("", now=T0)["success"])
        self.assertFalse(self.ps.park_vehicle("OK 1", "Bus", now=T0)["success"])

    def test_queue_and_exit(self):
        self.ps.park_vehicle("TRK 1", "Truck", now=T0)
        res = self.ps.park_vehicle("TRK 2", "Truck", now=T0)
        self.assertEqual((res["status"], res["position"]), ("waiting", 1))
        for i in range(3):
            self.ps.park_vehicle(f"CAR {i}", now=T0)
        self.ps.park_vehicle("MOT 1", "Motorcycle", now=T0)             # takes compact
        self.ps.park_vehicle("MOT 2", "Motorcycle", now=T0)             # waits behind truck
        self.assertEqual([v.plate_number for v in self.ps.get_waiting_vehicles()], ["TRK 2", "MOT 2"])
        out = self.ps.exit_vehicle("MOT 1", now="2026-10-14 09:00")
        self.assertEqual([v["plate_number"] for v in out["served_from_queue"]], ["MOT 2"])  # truck skipped
        out = self.ps.exit_vehicle("TRK 1", now="2026-10-14 10:30")
        self.assertEqual((out["duration_minutes"], out["fee"]), (150, 60.0))
        self.assertEqual(out["served_from_queue"][0]["plate_number"], "TRK 2")
        self.assertFalse(self.ps.exit_vehicle("TRK 1")["success"])
        self.assertFalse(self.ps.exit_vehicle("CAR 0", now="2026-10-14 07:00")["success"])  # before entry

    def test_remove_from_waiting(self):
        self.ps.park_vehicle("TRK 1", "Truck", now=T0)
        self.ps.park_vehicle("TRK 2", "Truck", now=T0)
        self.assertTrue(self.ps.remove_from_waiting("TRK 2")["success"])
        self.assertIsNone(self.ps.find_vehicle("TRK 2"))
        self.assertFalse(self.ps.remove_from_waiting("TRK 2")["success"])

    def test_undo(self):
        self.assertFalse(self.ps.undo_last_operation()["success"])
        self.ps.park_vehicle("TRK 1", "Truck", now=T0)
        self.ps.park_vehicle("TRK 2", "Truck", now=T0)
        self.ps.exit_vehicle("TRK 1", now="2026-10-14 09:00")      # TRK 2 served from queue
        self.ps.undo_last_operation()
        self.assertEqual(self.ps.find_vehicle("TRK 2").status, "waiting")
        self.ps.undo_last_operation()
        self.assertEqual(self.ps.find_vehicle("TRK 1").status, "parked")
        self.ps.undo_last_operation()
        self.assertIsNone(self.ps.find_vehicle("TRK 2"))
        self.ps.undo_last_operation()
        self.assertEqual(self.ps.get_parking_status()["occupied"], 0)
        self.assertEqual(self.ps.get_history(), [])

    def test_search_sort_status(self):
        for p in ["XYZ 3", "ABC 1", "ABD 2"]:
            self.ps.park_vehicle(p, now=T0)
        self.ps.exit_vehicle("XYZ 3", now="2026-10-14 12:00")
        self.assertEqual(len(self.ps.search_vehicles("ab")), 2)
        self.assertEqual(self.ps.find_record_by_id("v0002").plate_number, "ABC 1")
        self.assertIsNone(self.ps.find_record_by_id("V0099"))
        self.assertEqual([r["plate_number"] for r in self.ps.sort_records("plate_number")], ["ABC 1", "ABD 2", "XYZ 3"])
        self.assertEqual(self.ps.sort_records("fee", descending=True)[0]["plate_number"], "XYZ 3")
        status = self.ps.get_parking_status()
        self.assertEqual((status["total"], status["occupied"], status["available"]), (5, 2, 3))
        self.assertEqual(self.ps.get_summary(now="2026-10-14 13:00")["revenue_today"], 40.0)
        self.assertEqual(list(self.ps.get_records()[0])[:7],
                         ["vehicle_id", "plate_number", "slot_id", "entry_time", "exit_time", "status", "parking_duration"])

    def test_export(self):
        self.ps.park_vehicle("ABC 1", now=T0)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.ps.export_records_csv(os.path.join(d, "r.csv")), 1)


class TestIbrahimIntegration(unittest.TestCase):
    """When structures_and_algorithms.py is finished, core uses it automatically."""

    def test_team_module_is_used(self):
        finished = textwrap.dedent('''
            class Stack:
                def __init__(self): self.items = []
                def push(self, x): self.items.append(x)
                def pop(self): return self.items.pop() if self.items else None
                def peek(self): return self.items[-1] if self.items else None
                def is_empty(self): return not self.items
            class Queue:
                def __init__(self): self.items = []
                def enqueue(self, x): self.items.append(x)
                def dequeue(self): return self.items.pop(0) if self.items else None
                def peek(self): return self.items[0] if self.items else None
                def is_empty(self): return not self.items
            class HashTable:
                def __init__(self, capacity=101):
                    self.capacity = capacity; self.table = [[] for _ in range(capacity)]
                def _h(self, k): return sum(ord(c) for c in str(k)) % self.capacity
                def insert(self, k, v):
                    b = self.table[self._h(k)]
                    for p in b:
                        if p[0] == k: p[1] = v; return
                    b.append([k, v])
                def search(self, k):
                    for p in self.table[self._h(k)]:
                        if p[0] == k: return p[1]
                    return None
                def delete(self, k):
                    b = self.table[self._h(k)]
                    for p in b:
                        if p[0] == k: b.remove(p); return
            def linear_search(data, target, key=None):
                for x in data:
                    if (key(x) if key else x) == target: return x
                return None
            def binary_search(sorted_data, target, key=None):
                lo, hi = 0, len(sorted_data) - 1
                while lo <= hi:
                    m = (lo + hi) // 2; v = key(sorted_data[m]) if key else sorted_data[m]
                    if v == target: return m
                    if v < target: lo = m + 1
                    else: hi = m - 1
                return -1
            def merge_sort(data, key=None):
                key = key or (lambda x: x)
                if len(data) <= 1: return list(data)
                m = len(data) // 2; a, b = merge_sort(data[:m], key), merge_sort(data[m:], key)
                out = []
                while a and b: out.append(a.pop(0) if key(a[0]) <= key(b[0]) else b.pop(0))
                return out + a + b
            def greedy_slot_allocation(available_slots, vehicle):
                return min(available_slots, key=lambda s: (s.size_rank, s.index)) if available_slots else None
        ''')
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "structures_and_algorithms.py"), "w") as f:
                f.write(finished)
            with open(os.path.join(ROOT, "core.py"), encoding="utf-8") as src, \
                    open(os.path.join(d, "core.py"), "w", encoding="utf-8") as dst:
                dst.write(src.read())
            code = textwrap.dedent('''
                import core
                assert set(core.get_algorithms_status().values()) == {"team"}, core.get_algorithms_status()
                ps = core.ParkingSystem(5)
                for p in ["CCC 3", "AAA 1", "BBB 2"]:
                    ps.park_vehicle(p, now="2026-10-14 08:00")
                assert ps.find_record_by_id("V0002").plate_number == "AAA 1"
                assert [r["plate_number"] for r in ps.sort_records("plate_number")] == ["AAA 1", "BBB 2", "CCC 3"]
                assert ps.exit_vehicle("AAA 1", now="2026-10-14 09:00")["success"]
                print("ok")
            ''')
            out = subprocess.run([sys.executable, "-c", code], cwd=d, capture_output=True, text=True)
            self.assertEqual(out.stdout.strip(), "ok", out.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
