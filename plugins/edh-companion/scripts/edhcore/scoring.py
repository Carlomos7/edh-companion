"""Ranking numbers from EDHREC counts: Wilson intervals and a cautious lift. Pure functions, no network.

Popularity, never strength: these say how strongly a card is associated with a commander's decks, not how good it is.
"""
import math

N_FLOOR = 100       # fewer decks than this: no lift (a thin sample); matches candidates.py data_strength
LIFT_CAP = 8.0      # lifts above this are noise from tiny baselines
LIFT_MIN_PCT = 10.0  # lift only counts once the card is in at least this share of decks (lower bound)
# shortcut: thresholds are untuned design choices; tune on 3-5 commanders once baseline data is available


def wilson(n, tot, z=1.96):
    """95% Wilson score interval for n of tot, in % points."""
    p, d = n / tot, 1 + z * z / tot
    mid, half = (p + z * z / (2 * tot)) / d, z * math.sqrt(p * (1 - p) / tot + z * z / (4 * tot * tot)) / d
    return 100 * max(0.0, mid - half), 100 * min(1.0, mid + half)


def score(stats):
    """{inclusion_lb, lift_lb} for one card's EDHREC stats, or None without deck counts.
    inclusion_lb: Wilson lower bound of inclusion (%). lift_lb: inclusion_lb / baseline_pct, capped, only with a
    baseline, at least N_FLOOR decks and inclusion_lb >= LIFT_MIN_PCT; else None."""
    n, tot = (stats or {}).get("decks"), (stats or {}).get("total_decks")
    if n is None or not tot or not 0 <= n <= tot:  # decks > total_decks is bad data (validate warns): no score
        return None
    lb = wilson(n, tot)[0]
    base = stats.get("baseline_pct")
    lift = round(min(LIFT_CAP, lb / base), 2) if base and tot >= N_FLOOR and lb >= LIFT_MIN_PCT else None
    return {"inclusion_lb": round(lb, 1), "lift_lb": lift}


def rank_key(s):
    """Sort key (ascending = best first): lift lower bound, then inclusion lower bound. No lift counts as 1 (no
    association, and a lift under 1 counts as 1 so high-baseline staples aren't pushed down); no numbers sorts last."""
    if not s:
        return (1, 0, 0)
    return (0, -max(s["lift_lb"] or 1.0, 1.0), -s["inclusion_lb"])  # lift under 1 ties with none: inclusion decides
