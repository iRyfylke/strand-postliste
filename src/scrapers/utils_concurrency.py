import os


def compute_concurrency(min_workers=2, max_workers=6):
    """
    Beregner anbefalt concurrency basert på CPU-kjerner.
    Holder seg innenfor [min_workers, max_workers].

    Eksempel:
        cpu = 8 → cpu - 1 = 7 → clamp(2, 6) = 6
        cpu = 4 → cpu - 1 = 3 → clamp(2, 6) = 3
    """
    cpu = os.cpu_count() or 2
    recommended = cpu - 1

    return max(min_workers, min(max_workers, recommended))
