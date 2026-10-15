"""
Analytics tests. Run from the project folder:
    python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import analytics  # noqa: E402

DATA_PATH = os.path.join(ROOT, "data", "IIoT_Smart_Parking_Management.csv")

SAMPLE = pd.DataFrame({
    "Timestamp": ["2021-01-01 08:00:00", "2021-01-02 09:00:00", "2021-02-03 10:00:00", "2021-02-04 11:00:00"],
    "Entry_Time": [8, 8, 14, 22],
    "Exit_Time": [10, 7, 15, 23],
    "Parking_Lot_Section": ["Zone A", "Zone A", "Zone B", "Zone B"],
    "Occupancy_Status": ["Occupied", "Vacant", "Occupied", "Occupied"],
    "Payment_Status": ["Paid", "Unpaid", "Paid", "Overdue"],
    "Vehicle_Type": ["Car", "Car", "Motorcycle", "Car"],
    "Parking_Duration": [2, 3, 1, 3],
    "Payment_Amount": [10.0, 12.0, 5.0, 11.0],
    "Occupancy_Rate": [0.5, 0.2, 0.4, 0.6],
    "Parking_Violation": [0, 1, 0, 0],
    "Parking_Spot_ID": [1, 2, 3, 4],
})


class TestLoadAndClean(unittest.TestCase):
    def test_header_typo_fixed_and_file_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.csv")
            with open(path, "w", encoding="utf-8") as f:
                f.write("imestamp,Entry_Time\n2021-01-01 00:00:00,5\n")
            with open(path, "rb") as f:
                before = f.read()
            df = analytics.load_parking_data(path)
            self.assertEqual(list(df.columns), ["Timestamp", "Entry_Time"])
            with open(path, "rb") as f:
                self.assertEqual(f.read(), before)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            analytics.load_parking_data("does_not_exist.csv")

    def test_clean_keeps_every_row_and_reports_problems(self):
        messy = SAMPLE.copy().astype({"Timestamp": "object", "Payment_Amount": "object"})
        messy.loc[0, "Timestamp"] = "not a date"
        messy.loc[1, "Payment_Amount"] = "abc"
        messy.loc[2, "Entry_Time"] = 27
        messy.loc[3, "Parking_Lot_Section"] = "   "
        clean = analytics.clean_parking_data(messy)
        self.assertEqual(len(clean), len(messy))
        self.assertTrue(pd.isna(clean.loc[0, "Timestamp"]))
        self.assertTrue(pd.isna(clean.loc[1, "Payment_Amount"]))
        self.assertTrue(pd.isna(clean.loc[2, "Entry_Time"]))
        self.assertTrue(pd.isna(clean.loc[3, "Parking_Lot_Section"]))
        text = " ".join(analytics.get_validation_issues(clean))
        for word in ("Timestamp", "Payment_Amount", "Entry_Time"):
            self.assertIn(word, text)

    def test_valid_integer_columns_stay_integer(self):
        clean = analytics.clean_parking_data(SAMPLE)
        self.assertTrue(pd.api.types.is_integer_dtype(clean["Entry_Time"]))

    def test_missing_columns_do_not_crash(self):
        tiny = analytics.clean_parking_data(pd.DataFrame({"Vehicle_Type": ["Car"]}))
        self.assertEqual(analytics.summary_metrics(tiny)["total_records"], 1)
        self.assertTrue(analytics.section_occupancy(tiny).empty)


class TestAnalyses(unittest.TestCase):
    def setUp(self):
        self.df = analytics.clean_parking_data(SAMPLE)

    def test_summary(self):
        m = analytics.summary_metrics(self.df)
        self.assertEqual((m["total_records"], m["occupied_records"], m["vacant_records"]), (4, 3, 1))
        self.assertEqual(m["unpaid_or_overdue_percent"], 50.0)
        self.assertEqual(m["violation_rate_percent"], 25.0)

    def test_entry_hours(self):
        hours = analytics.entry_hour_counts(self.df)
        self.assertEqual(len(hours), 24)
        self.assertEqual(int(hours.loc[hours["Entry_Time"] == 8, "records"].iloc[0]), 2)
        self.assertEqual(int(analytics.peak_entry_hours(self.df, 1).iloc[0]["Entry_Time"]), 8)

    def test_sections_payments_vehicles(self):
        sections = analytics.section_occupancy(self.df)
        self.assertEqual(sections.iloc[0]["Parking_Lot_Section"], "Zone B")      # 100% occupied
        self.assertEqual(float(sections.iloc[0]["occupied_share_percent"]), 100.0)
        payments = analytics.payment_summary(self.df).set_index("Payment_Status")
        self.assertEqual(int(payments.loc["Paid", "records"]), 2)
        vehicles = analytics.vehicle_type_summary(self.df).set_index("Vehicle_Type")
        self.assertEqual(float(vehicles.loc["Car", "average_duration"]), 2.67)

    def test_duration_and_monthly(self):
        self.assertEqual(int(analytics.duration_distribution(self.df).set_index("Parking_Duration").loc[3, "records"]), 2)
        monthly = analytics.monthly_records(self.df)
        self.assertEqual(monthly["records"].tolist(), [2, 2])

    def test_quality_summary(self):
        q = analytics.data_quality_summary(self.df)
        self.assertEqual(q["possible_overnight_records"], 1)       # exit 7 < entry 8
        self.assertEqual(q["complete_records_percent"], 100.0)
        self.assertEqual(q["issues"], [])

    def test_insights(self):
        self.assertEqual(analytics.generate_insights(self.df)[0], "The dataset contains 4 records.")
        self.assertEqual(analytics.generate_insights(self.df.head(0)), ["The dataset contains 0 records."])


class TestFilters(unittest.TestCase):
    def setUp(self):
        self.df = analytics.clean_parking_data(SAMPLE)

    def test_options(self):
        o = analytics.filter_options(self.df)
        self.assertEqual(o["sections"], ["Zone A", "Zone B"])
        self.assertEqual(o["hours"], (8, 22))
        self.assertEqual(str(o["dates"][0]), "2021-01-01")

    def test_apply(self):
        f = analytics.apply_filters
        self.assertEqual(len(f(self.df)), 4)                                         # no filters
        self.assertEqual(len(f(self.df, sections=["Zone A"])), 2)
        self.assertEqual(len(f(self.df, sections=[])), 0)                            # nothing selected
        self.assertEqual(len(f(self.df, vehicle_types=["Car"], payment_statuses=["Paid"])), 1)
        self.assertEqual(len(f(self.df, hour_range=(8, 14))), 3)
        self.assertEqual(len(f(self.df, date_range=("2021-02-01", "2021-02-28"))), 2)


@unittest.skipUnless(os.path.exists(DATA_PATH), "data/IIoT_Smart_Parking_Management.csv not found")
class TestRealDataset(unittest.TestCase):
    def test_real_csv(self):
        df = analytics.clean_parking_data(analytics.load_parking_data(DATA_PATH))
        self.assertEqual(df.shape, (1000, 28))
        self.assertEqual(df.columns[0], "Timestamp")
        self.assertEqual(int(df["Timestamp"].isna().sum()), 0)
        self.assertEqual(analytics.summary_metrics(df)["occupied_records"], 550)


if __name__ == "__main__":
    unittest.main(verbosity=2)
