import pandas as pd
from database import list_tickets


def get_analytics() -> dict:
    """Computes operational KPI metrics and returns the underlying ticket DataFrame."""
    tickets = list_tickets()
    df = pd.DataFrame(tickets)

    if df.empty:
        return {
            "total": 0,
            "open": 0,
            "in_progress": 0,
            "resolved": 0,
            "manual_review": 0,
            "resolution_rate": 0.0,
            "data": df,
        }

    total = len(df)
    resolved = int((df["status"] == "Resolved").sum())

    return {
        "total": total,
        "open": int((df["status"] == "Open").sum()),
        "in_progress": int((df["status"] == "In Progress").sum()),
        "resolved": resolved,
        "manual_review": int((df["requires_review"] == 1).sum()),
        "resolution_rate": round(resolved / total * 100, 1),
        "data": df,
    }