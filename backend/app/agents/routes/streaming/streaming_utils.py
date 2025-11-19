"""Common utilities for streaming workflow status updates."""


def is_forward_progress(current_status: str, new_status: str) -> bool:
    """Check if new_status represents forward progress from current_status."""
    if not current_status:
        return True  # No previous status, allow any

    # Define status progression order
    status_order = {
        "pending": 0,
        "analyzing_mood": 1,
        "gathering_seeds": 2,
        "generating_recommendations": 3,
        "evaluating_quality": 4,
        "optimizing_recommendations": 5,
        "ordering_playlist": 5,
        "completed": 6,
        "failed": 6,
        "cancelled": 6,
    }

    current_order = status_order.get(current_status, -1)
    new_order = status_order.get(new_status, -1)

    # Allow same order (sub-steps) or forward progress
    return new_order >= current_order
