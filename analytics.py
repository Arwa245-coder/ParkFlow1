"""
ParkFlow - Analytics (Owner: Arwa)

Data loading, cleaning, validation and analysis for the IIoT Smart Parking
dataset. Built from analytics.ipynb. No Streamlit code lives here: dashboard.py
shows the results, this module only prepares and summarizes the data.

Required by main.py:
    load_parking_data(path)  -> pd.DataFrame   raw data, column names normalized
    clean_parking_data(df)   -> pd.DataFrame   typed copy, no rows deleted

Analysis helpers (each returns a DataFrame / dict / list, never draws anything):
    summary_metrics, entry_hour_counts, peak_entry_hours, section_occupancy,
    payment_summary, vehicle_type_summary, generate_insights
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

TIMESTAMP_COLUMN = "Timestamp"
_TIMESTAMP_TYPO = "imestamp"  # the external CSV lost the leading "T"

NUMERIC_COLUMNS = [
    "Parking_Spot_ID", "Sensor_Reading_Proximity", "Sensor_Reading_Pressure",
    "Vehicle_Type_Weight", "Vehicle_Type_Height", "Weather_Temperature",
    "Weather_Precipitation", "Entry_Time", "Exit_Time", "Electric_Vehicle",
    "Reserved_Status", "Occupancy_Rate", "Payment_Amount", "Parking_Violation",
    "Sensor_Reading_Ultrasonic", "Parking_Duration", "Environmental_Noise_Level",
    "Dynamic_Pricing_Factor", "Proximity_To_Exit", "User_Parking_History",
]

REQUIRED_COLUMNS = [
    "Timestamp", "Parking_Spot_ID", "Entry_Time", "Exit_Time", "Occupancy_Rate",
    "Payment_Amount", "Parking_Lot_Section", "Payment_Status", "Occupancy_Status",
    "Vehicle_Type", "Parking_Duration", "Parking_Violation",
]

# Values outside these ranges are impossible, so they become missing (NaN).
# The row itself is always kept. (min, max); None = no limit on that side.
VALID_RANGES = {
    "Entry_Time": (0, 23),
    "Exit_Time": (0, 23),
    "Occupancy_Rate": (0, 1),
    "Parking_Duration": (0, None),
    "Payment_Amount": (0, None),
    "Parking_Spot_ID": (0, None),
}

DATA_LIMITATIONS = (
    "Entry_Time and Exit_Time are hours of day (0-23), not full timestamps.",
    "Exit_Time earlier than Entry_Time may mean overnight parking; it is not treated as an error.",
    "The unit of Parking_Duration is not confirmed by the dataset metadata.",
    "Occupancy_Status is a row-level label, not the real-time occupancy of physical spots.",
    "Payment_Amount is not confirmed to be revenue (currency and units unknown).",
    "This is a historical Kaggle dataset, not a live connection to ParkFlow.",
)


# ===================================================================== loading
def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip spaces/BOM from column names and fix 'imestamp' -> 'Timestamp'.

    Works on a copy; the original DataFrame and the CSV file are not modified.
    """
    df = df.rename(columns=lambda c: str(c).strip().lstrip("\ufeff"))
    if len(df.columns) and TIMESTAMP_COLUMN not in df.columns:
        if str(df.columns[0]).casefold() == _TIMESTAMP_TYPO:
            df = df.rename(columns={df.columns[0]: TIMESTAMP_COLUMN})
    return df


def load_parking_data(path) -> pd.DataFrame:
    """Read the external CSV and normalize the column names (file stays untouched)."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Parking dataset not found: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig")
    if df.empty:
        raise ValueError(f"The parking dataset is empty: {path.name}")
    return normalize_column_names(df)


# ================================================================== validation
def validate_parking_data(df: pd.DataFrame) -> list[str]:
    """Report data-quality problems as readable messages. Never changes the data."""
    issues = []
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_columns:
        issues.append(f"Missing required columns: {missing_columns}")

    for column in (c for c in REQUIRED_COLUMNS if c in df.columns):
        count = int(df[column].isna().sum())
        if count:
            issues.append(f"{column}: {count} missing/invalid values")

    for column, (low, high) in VALID_RANGES.items():
        if column in df.columns:
            count = int(_out_of_range(df[column], low, high).sum())
            if count:
                issues.append(f"{column}: {count} values outside the valid range {low}..{high}")

    if "Parking_Violation" in df.columns:
        values = df["Parking_Violation"]
        count = int((values.notna() & ~values.isin([0, 1])).sum())
        if count:
            issues.append(f"Parking_Violation: {count} values are not 0 or 1")

    duplicates = int(df.duplicated().sum())
    if duplicates:
        issues.append(f"{duplicates} exact duplicate rows (kept, not removed)")
    return issues


def get_validation_issues(df: pd.DataFrame) -> list[str]:
    """Issues found by clean_parking_data (stored on the cleaned DataFrame)."""
    return list(df.attrs.get("validation_issues", []))


def _out_of_range(series: pd.Series, low, high) -> pd.Series:
    bad = pd.Series(False, index=series.index)
    if low is not None:
        bad |= series < low
    if high is not None:
        bad |= series > high
    return bad.fillna(False)


# =================================================================== cleaning
def clean_parking_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy. No row is ever deleted.

    1. normalize column names
    2. strip text; blank text -> missing
    3. Timestamp -> datetime (invalid -> NaT)
    4. numeric columns -> numbers (invalid -> NaN)
    5. impossible values (hour 25, negative amount, ...) -> NaN
    Every problem found is stored in df.attrs["validation_issues"].
    """
    clean = normalize_column_names(df).copy()
    notes = []

    for column in clean.columns:  # 2. text
        series = clean[column]
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            text = series.astype("string").str.strip()
            clean[column] = text.mask(text.eq("").fillna(False), pd.NA)

    if TIMESTAMP_COLUMN in clean.columns:  # 3. timestamp
        before = int(clean[TIMESTAMP_COLUMN].isna().sum())
        clean[TIMESTAMP_COLUMN] = pd.to_datetime(clean[TIMESTAMP_COLUMN], errors="coerce")
        bad = int(clean[TIMESTAMP_COLUMN].isna().sum()) - before
        if bad:
            notes.append(f"{TIMESTAMP_COLUMN}: {bad} values could not be read as dates (kept as missing)")

    for column in NUMERIC_COLUMNS:  # 4. numbers
        if column in clean.columns:
            before = int(clean[column].isna().sum())
            clean[column] = pd.to_numeric(clean[column], errors="coerce")
            bad = int(clean[column].isna().sum()) - before
            if bad:
                notes.append(f"{column}: {bad} values could not be converted to numbers (kept as missing)")

    issues = notes + validate_parking_data(clean)  # report first, then fix

    for column, (low, high) in VALID_RANGES.items():  # 5. impossible values
        if column in clean.columns:
            bad = _out_of_range(clean[column], low, high)
            if bad.any():  # only touch the column when needed, so valid integer columns stay integer
                clean.loc[bad, column] = pd.NA
    if "Parking_Violation" in clean.columns:
        values = clean["Parking_Violation"]
        bad = values.notna() & ~values.isin([0, 1])
        if bad.any():
            clean.loc[bad, "Parking_Violation"] = pd.NA

    clean.attrs["validation_issues"] = issues
    return clean


# =================================================================== analysis
def _has(df: pd.DataFrame, *columns: str) -> bool:
    return all(column in df.columns for column in columns)


def _is_occupied(df: pd.DataFrame) -> pd.Series:
    status = df["Occupancy_Status"].astype("string").str.casefold()
    return status.eq("occupied").fillna(False).astype(bool)


def summary_metrics(df: pd.DataFrame) -> dict:
    """Headline numbers (notebook section 6). Missing columns give None."""
    metrics = {"total_records": len(df)}
    if _has(df, "Occupancy_Status"):
        occupied = _is_occupied(df)
        vacant = df["Occupancy_Status"].astype("string").str.casefold().eq("vacant").fillna(False)
        metrics["occupied_records"] = int(occupied.sum())
        metrics["vacant_records"] = int(vacant.sum())
    if _has(df, "Parking_Duration"):
        metrics["average_parking_duration"] = round(float(df["Parking_Duration"].mean()), 2)
    if _has(df, "Occupancy_Rate"):
        metrics["average_occupancy_rate_percent"] = round(float(df["Occupancy_Rate"].mean()) * 100, 2)
    if _has(df, "Payment_Amount"):
        metrics["total_payment_amount"] = round(float(df["Payment_Amount"].sum()), 2)
        metrics["average_payment_amount"] = round(float(df["Payment_Amount"].mean()), 2)
    if _has(df, "Parking_Violation"):
        metrics["violation_rate_percent"] = round(float(df["Parking_Violation"].mean()) * 100, 2)
    if _has(df, "Payment_Status") and len(df):
        status = df["Payment_Status"].astype("string").str.casefold()
        not_paid = (status.notna() & status.ne("paid")).fillna(False)
        metrics["unpaid_or_overdue_percent"] = round(float(not_paid.mean()) * 100, 2)
    return metrics


def entry_hour_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Records per entry hour for all 24 hours (empty hours = 0). Columns: Entry_Time, records."""
    if not _has(df, "Entry_Time"):
        return pd.DataFrame({"Entry_Time": range(24), "records": 0})
    counts = df["Entry_Time"].dropna().astype(int).value_counts().reindex(range(24), fill_value=0).sort_index()
    return counts.rename_axis("Entry_Time").reset_index(name="records")


def peak_entry_hours(df: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """Busiest entry hours first (notebook section 7)."""
    hours = entry_hour_counts(df)
    return hours[hours["records"] > 0].sort_values("records", ascending=False).head(top).reset_index(drop=True)


def section_occupancy(df: pd.DataFrame) -> pd.DataFrame:
    """Share of rows labelled Occupied per parking section (notebook section 8)."""
    columns = ["Parking_Lot_Section", "records", "occupied_records", "occupied_share", "occupied_share_percent"]
    if not _has(df, "Parking_Lot_Section", "Occupancy_Status"):
        return pd.DataFrame(columns=columns)
    result = (
        df.assign(_occupied=_is_occupied(df))
        .groupby("Parking_Lot_Section", dropna=False)
        .agg(records=("_occupied", "size"), occupied_records=("_occupied", "sum"),
             occupied_share=("_occupied", "mean"))
        .reset_index()
    )
    result["occupied_share_percent"] = (result["occupied_share"] * 100).round(2)
    return result.sort_values("occupied_share_percent", ascending=False).reset_index(drop=True)


def payment_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Records and amounts per payment status (notebook section 9)."""
    columns = ["Payment_Status", "records", "total_amount", "average_amount"]
    if not _has(df, "Payment_Status", "Payment_Amount"):
        return pd.DataFrame(columns=columns)
    return (
        df.groupby("Payment_Status", dropna=False)
        .agg(records=("Payment_Status", "size"), total_amount=("Payment_Amount", "sum"),
             average_amount=("Payment_Amount", "mean"))
        .reset_index().round(2)
    )


def vehicle_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Records, average duration and average payment per vehicle type (notebook section 10)."""
    columns = ["Vehicle_Type", "records", "average_duration", "average_payment"]
    if not _has(df, "Vehicle_Type", "Parking_Duration", "Payment_Amount"):
        return pd.DataFrame(columns=columns)
    return (
        df.groupby("Vehicle_Type", dropna=False)
        .agg(records=("Vehicle_Type", "size"), average_duration=("Parking_Duration", "mean"),
             average_payment=("Payment_Amount", "mean"))
        .reset_index().round(2)
    )


def generate_insights(df: pd.DataFrame) -> list[str]:
    """Plain-language findings (notebook section 11)."""
    if df.empty:
        return ["The dataset contains 0 records."]
    insights = [f"The dataset contains {len(df)} records."]
    if _has(df, "Occupancy_Status"):
        insights.append(f"{_is_occupied(df).mean() * 100:.1f}% of records are labelled Occupied.")

    peaks = peak_entry_hours(df, top=1)
    if not peaks.empty:
        insights.append(f"The most frequent entry hour is {int(peaks.iloc[0]['Entry_Time']):02d}:00, "
                        f"with {int(peaks.iloc[0]['records'])} records.")
    sections = section_occupancy(df)
    if not sections.empty:
        top = sections.iloc[0]
        insights.append(f"{top['Parking_Lot_Section']} has the highest occupied share "
                        f"({top['occupied_share_percent']:.1f}%) in this dataset.")
    payments = payment_summary(df)
    if not payments.empty:
        top = payments.sort_values("records", ascending=False).iloc[0]
        insights.append(f"The most common payment status is {top['Payment_Status']} "
                        f"({int(top['records'])} records).")
    return insights


# ============================================================ filters & extras
FILTER_COLUMNS = {
    "sections": "Parking_Lot_Section",
    "vehicle_types": "Vehicle_Type",
    "payment_statuses": "Payment_Status",
}


def filter_options(df: pd.DataFrame) -> dict:
    """Values the dashboard filters can offer: lists, an hour range and a date range."""
    options = {key: [] for key in FILTER_COLUMNS}
    for key, column in FILTER_COLUMNS.items():
        if column in df.columns:
            options[key] = sorted(df[column].dropna().astype(str).unique())
    options["hours"] = (0, 23)
    if _has(df, "Entry_Time") and df["Entry_Time"].notna().any():
        options["hours"] = (int(df["Entry_Time"].min()), int(df["Entry_Time"].max()))
    options["dates"] = None
    if _has(df, TIMESTAMP_COLUMN) and pd.api.types.is_datetime64_any_dtype(df[TIMESTAMP_COLUMN]):
        valid = df[TIMESTAMP_COLUMN].dropna()
        if not valid.empty:
            options["dates"] = (valid.min().date(), valid.max().date())
    return options


def apply_filters(df, sections=None, vehicle_types=None, payment_statuses=None,
                  hour_range=None, date_range=None) -> pd.DataFrame:
    """Return the rows matching the filters. None = that filter is off.

    An empty list means "nothing selected" and gives an empty result.
    hour_range = (first, last) entry hour, inclusive. date_range = (start, end) dates, inclusive.
    """
    mask = pd.Series(True, index=df.index)
    selections = {"sections": sections, "vehicle_types": vehicle_types, "payment_statuses": payment_statuses}
    for key, selected in selections.items():
        column = FILTER_COLUMNS[key]
        if selected is not None and column in df.columns:
            mask &= df[column].astype("string").isin(list(selected)).fillna(False).astype(bool)
    if hour_range is not None and _has(df, "Entry_Time"):
        mask &= df["Entry_Time"].between(hour_range[0], hour_range[1]).fillna(False).astype(bool)
    if date_range is not None and _has(df, TIMESTAMP_COLUMN):
        start = pd.Timestamp(date_range[0])
        end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
        stamps = df[TIMESTAMP_COLUMN]
        mask &= ((stamps >= start) & (stamps < end)).fillna(False).astype(bool)
    return df.loc[mask]


def duration_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Records per Parking_Duration value (dataset units). Columns: Parking_Duration, records."""
    if not _has(df, "Parking_Duration"):
        return pd.DataFrame(columns=["Parking_Duration", "records"])
    counts = df["Parking_Duration"].dropna().astype(int).value_counts().sort_index()
    return counts.rename_axis("Parking_Duration").reset_index(name="records")


def monthly_records(df: pd.DataFrame) -> pd.DataFrame:
    """Records per calendar month from Timestamp. Columns: Month, records."""
    empty = pd.DataFrame(columns=["Month", "records"])
    if not _has(df, TIMESTAMP_COLUMN) or not pd.api.types.is_datetime64_any_dtype(df[TIMESTAMP_COLUMN]):
        return empty
    stamps = df[TIMESTAMP_COLUMN].dropna()
    if stamps.empty:
        return empty
    months = stamps.dt.to_period("M").dt.to_timestamp()
    return months.value_counts().sort_index().rename_axis("Month").reset_index(name="records")


def data_quality_summary(df: pd.DataFrame) -> dict:
    """Numbers and messages for a data-quality panel (use the unfiltered, cleaned data)."""
    present = [c for c in REQUIRED_COLUMNS if c in df.columns]
    complete = float(df[present].notna().all(axis=1).mean() * 100) if present and len(df) else 0.0
    overnight = 0
    if _has(df, "Entry_Time", "Exit_Time"):
        overnight = int((df["Exit_Time"] < df["Entry_Time"]).fillna(False).sum())
    date_range = None
    if _has(df, TIMESTAMP_COLUMN) and pd.api.types.is_datetime64_any_dtype(df[TIMESTAMP_COLUMN]):
        valid = df[TIMESTAMP_COLUMN].dropna()
        if not valid.empty:
            date_range = (valid.min().date(), valid.max().date())
    issues = get_validation_issues(df) if "validation_issues" in df.attrs else validate_parking_data(df)
    return {
        "total_records": len(df),
        "complete_records_percent": round(complete, 1),
        "possible_overnight_records": overnight,
        "date_range": date_range,
        "issues": issues,
    }


__all__ = [
    "load_parking_data", "clean_parking_data", "normalize_column_names",
    "validate_parking_data", "get_validation_issues", "summary_metrics",
    "entry_hour_counts", "peak_entry_hours", "section_occupancy",
    "payment_summary", "vehicle_type_summary", "generate_insights",
    "filter_options", "apply_filters", "duration_distribution", "monthly_records",
    "data_quality_summary", "DATA_LIMITATIONS",
]