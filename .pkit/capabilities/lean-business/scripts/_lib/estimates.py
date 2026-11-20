"""The viability estimate: what the idea's goal asks of a variant, worked out through the
customer factory from the canvas's inputs (lean-business DEC-002 point 4; DEC-001 point 7).

The numbers are worked out each time they are shown and never stored. The capability's
README gives the formulas; in short, for each side that pays:

- **a year's revenue from one customer** is the price, times twelve where it is counted by
  the month;
- **the active customers needed** are the goal's yearly revenue divided by that, rounded
  up;
- **the customers lost each year** are the active customers divided by a customer's
  lifetime in years, so as many new customers are needed each year to hold the number;
- **the new customers won by referral** are the referral share of those, and the rest are
  won through the channels;
- **the leads needed each year** are the customers won through the channels divided by the
  conversion;
- **the traction roadmap** gives the active customers each year of the goal's span, the
  last year's the number needed and each year before it the multiplier fewer, so the
  traction grows by the multiplier each year.

A side that pays nothing counts at nothing, and the estimate counts only the sides that
pay. A model with several paying sides is worked out for each as though it alone carried
the goal, since the inputs say nothing of how the goal divides among them.

Where inputs are missing, the estimate names each of them, and works out each number that
rests on none of them. A side that pays nothing needs no input but its price.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from _lib import fingerprint

#: The months in a year, by which an amount or a length counted by the month is a year's.
MONTHS = 12

#: A side's inputs, in the order the estimate names those missing.
INPUTS = ("price", "lifetime", "conversion", "referral-share")


@dataclass(frozen=True)
class Side:
    """The estimate for one set of inputs: its side, or None in a direct model; the numbers
    the inputs let it work out; and what is missing for the rest."""

    side: str | None
    yearly_price: float | None = None
    active: int | None = None
    lost_each_year: float | None = None
    by_referral: float | None = None
    by_channels: float | None = None
    leads_each_year: float | None = None
    roadmap: tuple[tuple[int, int], ...] = ()
    pays_nothing: bool = False
    missing: tuple[str, ...] = ()


@dataclass(frozen=True)
class Estimate:
    """The estimate for a variant: the goal's yearly revenue and span, the multiplier, and
    each side's numbers."""

    yearly_revenue: float
    currency: str
    years: float
    multiplier: float
    sides: tuple[Side, ...] = field(default_factory=tuple)
    several_paying: bool = False


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _yearly(amount: object, per: object) -> float | None:
    found = _number(amount)
    if found is None or per not in ("month", "year"):
        return None
    return found * MONTHS if per == "month" else found


def goal_yearly(goal: Mapping[str, Any]) -> float | None:
    """The goal's revenue in a year."""
    revenue = goal.get("revenue")
    if not isinstance(revenue, Mapping):
        return None
    return _yearly(revenue.get("amount"), revenue.get("per"))


def estimate(canvas: Mapping[str, Any], goal: Mapping[str, Any]) -> Estimate | None:
    """The estimate for `canvas` against `goal`, or None where the goal gives no yearly
    revenue or no span."""
    yearly = goal_yearly(goal)
    years = _number(goal.get("years"))
    if yearly is None or years is None or years <= 0:
        return None
    multiplier = _number(fingerprint.traction(canvas).get("multiplier")) or float(
        fingerprint.MULTIPLIER
    )
    sets = canvas.get("viability")
    inputs = [s for s in sets if isinstance(s, Mapping)] if isinstance(sets, list) else []
    sides = tuple(_side(s, yearly, years, multiplier) for s in inputs)
    paying = [s for s in sides if not s.pays_nothing and s.yearly_price is not None]
    return Estimate(
        yearly_revenue=yearly,
        currency=str(goal.get("currency", "")),
        years=years,
        multiplier=multiplier,
        sides=sides,
        several_paying=len(paying) > 1,
    )


def _yearly_price(price: object) -> float | None:
    if not isinstance(price, Mapping):
        return None
    return _yearly(price.get("amount"), price.get("per"))


def _years_kept(lifetime: object) -> float | None:
    if not isinstance(lifetime, Mapping):
        return None
    length = _number(lifetime.get("length"))
    unit = lifetime.get("unit")
    if length is None or length <= 0 or unit not in ("month", "year"):
        return None
    return length / MONTHS if unit == "month" else length


def _conversion(value: object) -> float | None:
    found = _number(value)
    return found if found is not None and found > 0 else None


def _referral_share(value: object) -> float | None:
    found = _number(value)
    return found if found is not None and 0 <= found < 1 else None


def _side(inputs: Mapping[str, Any], yearly: float, years: float, multiplier: float) -> Side:
    side = inputs.get("side") if isinstance(inputs.get("side"), str) else None
    yearly_price = _yearly_price(inputs.get("price"))
    if yearly_price == 0:
        return Side(side, yearly_price=0.0, pays_nothing=True)
    years_kept = _years_kept(inputs.get("lifetime"))
    conversion = _conversion(inputs.get("conversion"))
    share = _referral_share(inputs.get("referral-share"))
    given = (yearly_price, years_kept, conversion, share)
    missing = tuple(name for name, value in zip(INPUTS, given, strict=True) if value is None)
    if yearly_price is None:
        return Side(side, missing=missing)
    active = math.ceil(yearly / yearly_price)
    lost = active / years_kept if years_kept is not None else None
    by_referral = by_channels = leads = None
    if lost is not None and share is not None:
        by_referral = lost * share
        by_channels = lost - by_referral
        if conversion is not None:
            leads = by_channels / conversion
    return Side(
        side,
        yearly_price=yearly_price,
        active=active,
        lost_each_year=lost,
        by_referral=by_referral,
        by_channels=by_channels,
        leads_each_year=leads,
        roadmap=roadmap(active, years, multiplier),
        missing=missing,
    )


def roadmap(active: int, years: float, multiplier: float) -> tuple[tuple[int, int], ...]:
    """The active customers each year of the goal's span: the last year's `active`, and each
    year before it `multiplier` fewer, rounded up."""
    span = max(1, math.ceil(years))
    return tuple(
        (year, math.ceil(active / multiplier ** (span - year))) for year in range(1, span + 1)
    )


def lines(found: Estimate) -> list[str]:
    """The estimate in words, one line each, in the idea's currency."""
    out = [
        f"The goal: {_amount(found.yearly_revenue)} {found.currency} a year, within "
        f"{_plain(found.years)} years; traction grows {_plain(found.multiplier)} times a year.",
    ]
    if not found.sides:
        out.append("The canvas gives no inputs yet: `pkit lean set-inputs` gives them.")
        return out
    if found.several_paying:
        out.append(
            "Several sides pay: each is worked out as though it alone carried the goal, since "
            "the inputs say nothing of how the goal divides among them."
        )
    for side in found.sides:
        out.append("")
        out.append(f"The side `{side.side}`:" if side.side is not None else "The model:")
        if side.pays_nothing:
            out.append("  pays nothing, so it counts at nothing toward the goal")
            continue
        if side.yearly_price is None or side.active is None:
            out.append(f"  nothing is worked out, for want of: {', '.join(side.missing)}")
            continue
        out.append(
            f"  a year's revenue from one customer: {_amount(side.yearly_price)} {found.currency}"
        )
        out.append(f"  active customers needed: {_count(side.active)}")
        if side.lost_each_year is not None:
            lost = _count(side.lost_each_year)
            out.append(f"  customers lost each year, and as many won to replace them: {lost}")
        if side.by_referral is not None and side.by_channels is not None:
            out.append(
                f"  of those, won by referral: {_count(side.by_referral)}; through the "
                f"channels: {_count(side.by_channels)}"
            )
        if side.leads_each_year is not None:
            out.append(f"  leads needed each year: {_count(side.leads_each_year)}")
        if side.roadmap:
            steps = ", ".join(f"year {year}: {_count(count)}" for year, count in side.roadmap)
            out.append(f"  active customers on the way: {steps}")
        if side.missing:
            out.append(f"  not worked out, for want of: {', '.join(side.missing)}")
    return out


def _plain(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:g}"


def _amount(value: float) -> str:
    return f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"


def _count(value: float) -> str:
    return f"{math.ceil(value):,}"
