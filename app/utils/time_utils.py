"""Time-related utility functions for the Green Time Schedule API."""

from datetime import datetime, timedelta
from typing import List, Tuple, Dict


def get_settlement_period(dt: datetime) -> int:
    """
    Convert a datetime to a settlement period (1-48).

    Args:
        dt: The datetime to convert

    Returns:
        An integer representing the settlement period (1-48)
    """
    # Calculate minutes since start of day
    minutes_since_midnight = dt.hour * 60 + dt.minute
    # Calculate the settlement period (each period is 30 minutes)
    period = (minutes_since_midnight // 30) + 1
    return period


def datetime_from_period(date_str: str, period: int) -> Tuple[datetime, datetime]:
    """
    Convert a date string and settlement period to start and end datetimes.

    Args:
        date_str: Date in YYYY-MM-DD format
        period: Settlement period (1-48)

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    # Convert period to hours and minutes
    minutes_since_midnight = (period - 1) * 30
    hours = minutes_since_midnight // 60
    minutes = minutes_since_midnight % 60

    # Create start datetime
    start_date = datetime.strptime(date_str, "%Y-%m-%d")
    start_dt = start_date.replace(hour=hours, minute=minutes, second=0, microsecond=0)

    # End datetime is 30 minutes later
    end_dt = start_dt + timedelta(minutes=30)

    return (start_dt, end_dt)


def get_date_periods_between(
    start_dt: datetime, end_dt: datetime
) -> Dict[str, List[int]]:
    """
    Get all date and period combinations between two datetimes.

    Args:
        start_dt: Start datetime
        end_dt: End datetime

    Returns:
        Dictionary mapping date strings to lists of periods
    """
    if start_dt >= end_dt:
        return {}

    result = {}
    current_dt = start_dt

    while current_dt < end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        period = get_settlement_period(current_dt)

        if date_str not in result:
            result[date_str] = []

        if period not in result[date_str]:
            result[date_str].append(period)

        # Move to next period (30 minutes later)
        current_dt += timedelta(minutes=30)

        # Handle case where we cross midnight
        if current_dt.date() != start_dt.date() and len(result[date_str]) < 48:
            # Fill in remaining periods for the day if needed
            missing_periods = [p for p in range(1, 49) if p not in result[date_str]]
            result[date_str].extend(missing_periods)

    return result


def generate_time_windows(
    start_dt: datetime, end_dt: datetime, window_minutes: int
) -> List[Tuple[datetime, datetime]]:
    """
    Generate all possible time windows of specified duration between start and end times.

    Args:
        start_dt: Start datetime
        end_dt: End datetime
        window_minutes: Duration of the window in minutes

    Returns:
        List of (window_start, window_end) tuples
    """
    if window_minutes < 30:
        window_minutes = 30  # Minimum window size is 30 minutes

    # Round window_minutes to nearest multiple of 30
    window_minutes = ((window_minutes + 29) // 30) * 30

    window_delta = timedelta(minutes=window_minutes)
    if start_dt + window_delta > end_dt:
        return []  # Not enough time for even one window

    windows = []
    current_start = start_dt

    # Generate windows with 30-minute steps
    while current_start + window_delta <= end_dt:
        windows.append((current_start, current_start + window_delta))
        current_start += timedelta(minutes=30)

    return windows


def format_datetime_iso(dt: datetime) -> str:
    """Format a datetime in ISO 8601 format with Z timezone designator."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
