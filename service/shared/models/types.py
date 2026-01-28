"""Custom type definitions for homeapp service."""

from typing import Annotated

from pydantic import AfterValidator, Field


def round_to_two_decimals(v: float) -> float:
    """Round float to 2 decimal places."""
    return round(v, 2)


PositiveAmount = Annotated[
    float,
    Field(gt=0, description='Positive amount rounded to 2 decimal places'),
    AfterValidator(round_to_two_decimals),
]
"""A positive float (> 0) that is automatically rounded to 2 decimal places."""
