"""Qualitative aggregation and A/B comparison boundary."""

from .models import Comparison, ComparisonView, MetricChange, Pair, Panel, Scores, Variant, Vote
from .simulation import pending_exposures


def comparison_view(comparison: Comparison, panel: Panel) -> ComparisonView:
    total = 2 * len(panel.members)
    pending = pending_exposures(panel, comparison)
    if pending:
        return ComparisonView(**comparison.model_dump(), next_index=pending[0], total_exposures=total)

    by_member = {(result.member_id, result.variant): result.reaction for result in comparison.exposures}
    pairs = [
        Pair(
            member_id=member.member_id,
            member_name=member.name,
            original=by_member[(member.member_id, "A")],
            revised=by_member[(member.member_id, "B")],
        )
        for member in panel.members
    ]
    votes: tuple[Vote, ...] = ("would_consider", "unsure", "would_pass")
    vote_counts: dict[Variant, dict[Vote, int]] = {
        "A": dict.fromkeys(votes, 0),
        "B": dict.fromkeys(votes, 0),
    }
    for exposure in comparison.exposures:
        vote_counts[exposure.variant][exposure.reaction.vote] += 1
    changes = {}
    for metric in Scores.model_fields:
        deltas = [
            getattr(pair.revised.scores, metric) - getattr(pair.original.scores, metric)
            for pair in pairs
        ]
        changes[metric] = MetricChange(
            higher=sum(delta > 0 for delta in deltas),
            same=deltas.count(0),
            lower=sum(delta < 0 for delta in deltas),
        )

    return ComparisonView(
        **comparison.model_dump(),
        next_index=None, total_exposures=total, pairs=pairs,
        vote_counts=vote_counts, metric_changes=changes,
    )
