from collections.abc import Sequence
from random import Random

from moot.core import MODERATOR_ID, Persona


# Each index identifies a cell in the four-by-four original portrait sheet.
PORTRAIT_COUNT = 16


def assign_avatars(participants: Sequence[Persona], discussion_id: str) -> dict[str, int]:
    """Assign distinct portraits and keep the same seating identities on reload."""
    seats = [MODERATOR_ID, *(persona.id for persona in participants)]
    # The meeting ID randomizes a new meeting and allows saved meetings to replay.
    # A later selection policy can use the full native personas passed here.
    portraits = Random(discussion_id).sample(range(PORTRAIT_COUNT), len(seats))
    return dict(zip(seats, portraits, strict=True))
