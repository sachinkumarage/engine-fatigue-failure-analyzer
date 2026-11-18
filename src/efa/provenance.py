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
        warnings: Conditions found in this result that limit its use.
    """

    equation_ids: tuple[str, ...]
    validity_notes: tuple[str, ...] = ()
    verify_flags: tuple[str, ...] = ()
    input_statuses: dict[str, Status] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def verify(self) -> bool:
        """True while any relation or input used still needs owner checking."""
        return bool(self.verify_flags)

    def as_markdown(self) -> str:
        """Plain Markdown summary of the note, for reports and the app."""
        parts = ["**Equations used:** " + ", ".join(self.equation_ids)]
        sections = (
            ("Warnings", self.warnings),
            ("Validity", self.validity_notes),
            ("Verify", self.verify_flags),
        )
        for title, items in sections:
            if items:
                parts.append(f"**{title}:**\n" + "\n".join(f"- {i}" for i in items))
        if self.input_statuses:
            lines = (
                f"- {k}: `{Status(v).value}`" for k, v in self.input_statuses.items()
            )
            parts.append("**Input status:**\n" + "\n".join(lines))
        return "\n\n".join(parts)


@dataclass(frozen=True)
class TracedValue:
    """A numeric input together with its basis and provenance.

    Attributes:
        value: The value in SI units (or dimensionless).
        basis: How the value was obtained (equation, table, measurement).
        status: Data status: cited, measured or assumed.
        source_id: Identifier of the source (docs/sources.md), or "" if none.
        verify: True while the value or relation awaits owner checking.
    """

    value: float
    basis: str
    status: Status
    source_id: str = ""
    verify: bool = False

    def __post_init__(self) -> None:
        try:
            v = float(self.value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"value must be a number, got {self.value!r}.") from exc
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("value must be finite.")
        object.__setattr__(self, "value", v)
        object.__setattr__(self, "status", Status(self.status))
