"""Pure derived metric functions; no claim of comprehensive security coverage."""
def detection_rate(detected: int, missed: int):
    total = detected + missed
    return round(100.0 * detected / total, 1) if total else None

def freshness(received_at, now, minutes=10):
    if received_at is None:
        return False
    return 0 <= (now - received_at).total_seconds() <= minutes * 60
