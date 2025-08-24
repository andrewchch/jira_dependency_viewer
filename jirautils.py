from collections import defaultdict
from datetime import datetime, timezone

SECS_PER_DAY = 3600 * 24


def get_sprint_changes(issue):
    """
    Return a list of sprint changes for a Jira issue.

    Each change is a dict:
    {
        "changed_at": datetime,
        "from": <old_sprint_value>,
        "to": <new_sprint_value>
    }
    """
    sprint_changes = []

    for history in issue.changelog.histories:
        for item in history.items:
            if item.field.lower() == 'sprint':
                changed_at = datetime.strptime(history.created, "%Y-%m-%dT%H:%M:%S.%f%z")
                sprint_changes.append({
                    "key": issue.key,
                    "changed_at": changed_at,
                    "from": item.fromString,
                    "to": item.toString
                })

    # Sort changes in chronological order
    sprint_changes.sort(key=lambda x: x["changed_at"])
    return sprint_changes


def calculate_time_in_status(issue, start_time=None, end_time=None):
    """
    Calculate time spent in each status for a Jira issue.

    Args:
        issue: Jira issue object with changelog expanded.
        start_time (datetime, optional): Only count time after this datetime.
        end_time (datetime, optional): Only count time before this datetime.

    Returns:
        dict: {status_name: hours_spent_in_range}
    """
    # Extract status change history
    status_changes = []
    for history in issue.changelog.histories:
        for item in history.items:
            if item.field.lower() == 'status':
                from_status = item.fromString
                to_status = item.toString
                changed_at = datetime.strptime(history.created, "%Y-%m-%dT%H:%M:%S.%f%z")
                status_changes.append((changed_at, from_status, to_status))

    status_changes.sort(key=lambda x: x[0])

    time_in_status = defaultdict(float)  # hours

    # Determine starting point
    current_status = status_changes[0][1] if status_changes else issue.fields.status.name
    last_change_time = datetime.strptime(issue.fields.created, "%Y-%m-%dT%H:%M:%S.%f%z")

    # Apply filtering to the *start* of the calculation
    if start_time and last_change_time < start_time:
        last_change_time = start_time

    for changed_at, from_status, to_status in status_changes:
        # Determine period start/end clipped to optional time window
        period_start = last_change_time
        period_end = changed_at
        if start_time:
            period_start = max(period_start, start_time)
        if end_time:
            period_end = min(period_end, end_time)

        # Only count positive-duration overlaps
        if period_end > period_start:
            time_in_status[current_status] += (period_end - period_start).total_seconds() / SECS_PER_DAY

        # Move to next status
        current_status = to_status
        last_change_time = changed_at

    # Handle time from last change to now (or end_time)
    period_start = last_change_time
    period_end = datetime.now(timezone.utc)
    if start_time:
        period_start = max(period_start, start_time)
    if end_time:
        period_end = min(period_end, end_time)

    if period_end > period_start:
        time_in_status[current_status] += (period_end - period_start).total_seconds() / SECS_PER_DAY

    return dict(time_in_status)
