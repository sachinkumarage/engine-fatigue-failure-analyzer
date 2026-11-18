"""Provenance records: data status, sources and result notes."""

from dataclasses import dataclass, field
from enum import StrEnum


class Status(StrEnum):
    """Status of an input value (see docs/data_policy.md)."""

    CITED = "cited"
    MEASURED = "measured"
    ASSUMED = "assumed"


@dataclass(frozen=True)
class Source:
    """A reference that an input value is taken from.

    Attributes:
        id: Short unique identifier used to link data to this source.
        kind: Type of source, e.g. "book", "standard", "paper", "dataset",
            "synthetic".
        title: Title of the work.
        authors_or_org: Authors or issuing organisation.
        edition_or_designation: Edition, or standard designation.
        year: Publication year, if known with certainty.
        location: Chapter, table, page or equation number.
        notes: Free-text remarks.
    """

    id: str
    kind: str
    title: str
    authors_or_org: str
    edition_or_designation: str = ""
    year: int | None = None
    location: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        for name in ("id", "kind", "title", "authors_or_org"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"Source.{name} must not be empty.")


@dataclass(frozen=True)
class ResultNote:
    """Traceability record attached to a calculation result.

    Attributes:
        equation_ids: Equation ids used (see docs/methods).
        validity_notes: Model assumptions and validity limits.
        verify_flags: Conditions the user should check before relying on the
            result.
        input_statuses: Status of each tracked input, keyed by input name.
    """

    equation_ids: tuple[str, ...]
    validity_notes: tuple[str, ...] = ()
    verify_flags: tuple[str, ...] = ()
    input_statuses: dict[str, Status] = field(default_factory=dict)
