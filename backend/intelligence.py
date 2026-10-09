def calculate_waiting_time(queue_count, service_rate):
    if service_rate <= 0:
        return None
    return round(queue_count / service_rate, 2)


def get_queue_status(queue_count):
    if queue_count <= 3:
        return "low"
    if queue_count <= 7:
        return "moderate"
    return "high"
