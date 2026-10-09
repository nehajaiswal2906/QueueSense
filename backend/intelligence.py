
def calculate_waiting_time(queue_count, service_rate):
    """Calculate estimated waiting time in minutes."""

    # Reject invalid input types
    if isinstance(queue_count, bool) or isinstance(service_rate, bool):
        return None

    if not isinstance(queue_count, (int, float)):
        return None

    if not isinstance(service_rate, (int, float)):
        return None

    # Reject negative queue counts and invalid service rates
    if queue_count < 0 or service_rate <= 0:
        return None

    # Waiting time = people waiting / people served per minute
    return round(queue_count / service_rate, 2)


def get_queue_status(queue_count):
    """Return a readable queue status."""

    if isinstance(queue_count, bool):
        return "unknown"

    if not isinstance(queue_count, (int, float)):
        return "unknown"

    if queue_count < 0:
        return "unknown"

    if queue_count <= 3:
        return "low"

    if queue_count <= 7:
        return "moderate"

    return "high"


def format_queue_result(queue_count, service_rate):
    """Create a readable result for displaying queue information."""

    status = get_queue_status(queue_count)
    waiting_time = calculate_waiting_time(queue_count, service_rate)

    if waiting_time is None:
        waiting_message = "Waiting time unavailable"
    else:
        waiting_message = f"Estimated waiting time: {waiting_time} minutes"

    if status == "unknown":
        status_message = "Queue status unavailable"
    else:
        status_message = f"Queue status: {status.upper()}"

    return {
        "queue_count": queue_count,
        "service_rate": service_rate,
        "estimated_wait": waiting_time,
        "status": status,
        "message": f"{status_message}. {waiting_message}."
    }