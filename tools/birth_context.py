"""Birth-time normalization and audit metadata for MingLi charts.

The calendar engine works with a naive local datetime.  This module is the
only place where a caller's civil time is converted into the effective time
used for chart construction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


TIME_NORMALIZATION_VERSION = "true-solar-v3"
GEONAMES_SOURCE = "geonamescache-2.0.0"
ZI_HOUR_CONVENTIONS = ("benchmark", "early", "late")
CALENDAR_BACKEND_TIMEZONE = "Asia/Shanghai"


class BirthContextError(ValueError):
    """A caller-correctable birth-context error."""

    def __init__(self, code: str, message: str, candidates: Optional[List[Dict]] = None):
        super().__init__(message)
        self.code = code
        self.candidates = candidates or []

    def as_dict(self) -> Dict[str, Any]:
        value = {"code": self.code, "message": str(self)}
        if self.candidates:
            value["candidates"] = self.candidates
        return value


@dataclass(frozen=True)
class ResolvedPlace:
    name: str
    latitude: float
    longitude: float
    timezone: str
    country_code: Optional[str]
    source: str
    geoname_id: Optional[int] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "country_code": self.country_code,
            "source": self.source,
            "geoname_id": self.geoname_id,
        }


@dataclass(frozen=True)
class NormalizedBirthContext:
    civil_time: datetime
    effective_time: datetime
    calendar_time: datetime
    timezone: str
    calendar_timezone: str
    time_basis: str
    correction_minutes: float
    equation_of_time_minutes: float
    standard_meridian: float
    place: Optional[ResolvedPlace]
    uncertainty_minutes: int
    zi_hour_convention: str
    warnings: tuple[Dict[str, Any], ...]

    def as_dict(self) -> Dict[str, Any]:
        value: Dict[str, Any] = {
            "version": TIME_NORMALIZATION_VERSION,
            "time_basis": self.time_basis,
            "civil_time": self.civil_time.isoformat(timespec="seconds"),
            "effective_time": self.effective_time.isoformat(timespec="seconds"),
            "calendar_time": self.calendar_time.isoformat(timespec="seconds"),
            "timezone": self.timezone,
            "calendar_timezone": self.calendar_timezone,
            "correction_minutes": round(self.correction_minutes, 3),
            "equation_of_time_minutes": round(self.equation_of_time_minutes, 3),
            "standard_meridian": self.standard_meridian,
            "uncertainty_minutes": self.uncertainty_minutes,
            "zi_hour_convention": self.zi_hour_convention,
            "place": self.place.as_dict() if self.place else None,
            "warnings": list(self.warnings),
        }
        if self.uncertainty_minutes:
            earliest = self.effective_time - timedelta(minutes=self.uncertainty_minutes)
            latest = self.effective_time + timedelta(minutes=self.uncertainty_minutes)
            value["effective_time_range"] = {
                "start": earliest.isoformat(timespec="seconds"),
                "end": latest.isoformat(timespec="seconds"),
            }
        return value


def _normalise_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return "".join(char for char in normalized if char.isalnum())


def _pinyin_terms(value: str) -> Iterable[str]:
    """Return compact pinyin fallbacks for Chinese place names when available."""
    if not any("\u4e00" <= char <= "\u9fff" for char in value):
        return ()
    try:
        from pypinyin import Style, lazy_pinyin
    except ImportError:
        return ()

    candidates = [value]
    stripped = re.sub(r"^.*?[省市自治区特别行政区]", "", value)
    stripped = re.sub(r"(自治州|地区|盟|市|县|区|旗)$", "", stripped)
    if stripped and stripped != value:
        candidates.append(stripped)

    return tuple(
        _normalise_name("".join(lazy_pinyin(candidate, style=Style.NORMAL)))
        for candidate in candidates
    )


def _place_terms(name: str) -> set[str]:
    terms = {_normalise_name(name)}
    terms.update(term for term in _pinyin_terms(name) if term)
    return {term for term in terms if term}


def _city_candidates(
    name: str,
    country_code: Optional[str] = None,
) -> List[ResolvedPlace]:
    try:
        import geonamescache
    except ImportError as exc:
        raise BirthContextError(
            "location_resolver_unavailable",
            "城市名解析需要 geonamescache 依赖。",
        ) from exc

    terms = _place_terms(name)
    cities = geonamescache.GeonamesCache().get_cities().values()
    matches: List[ResolvedPlace] = []
    for city in cities:
        if country_code and city.get("countrycode") != country_code.upper():
            continue
        names = [city.get("name", "")] + list(city.get("alternatenames") or [])
        city_terms = {_normalise_name(candidate) for candidate in names if candidate}
        if not terms.intersection(city_terms):
            continue
        timezone = city.get("timezone")
        if not timezone:
            continue
        matches.append(
            ResolvedPlace(
                name=city["name"],
                latitude=float(city["latitude"]),
                longitude=float(city["longitude"]),
                timezone=timezone,
                country_code=city.get("countrycode"),
                source=GEONAMES_SOURCE,
                geoname_id=int(city["geonameid"]) if city.get("geonameid") else None,
            )
        )
    return matches


def _candidate_payload(candidates: Iterable[ResolvedPlace]) -> List[Dict[str, Any]]:
    return [
        {
            "name": candidate.name,
            "country_code": candidate.country_code,
            "latitude": candidate.latitude,
            "longitude": candidate.longitude,
            "timezone": candidate.timezone,
            "geoname_id": candidate.geoname_id,
        }
        for candidate in candidates
    ]


def resolve_place(place: Dict[str, Any]) -> ResolvedPlace:
    """Resolve direct coordinates or a city name without network access."""
    if not isinstance(place, dict):
        raise BirthContextError("invalid_place", "place 必须是对象。")

    longitude = place.get("longitude")
    latitude = place.get("latitude")
    timezone = place.get("timezone")
    if longitude is not None or latitude is not None:
        if longitude is None or latitude is None or not timezone:
            raise BirthContextError(
                "incomplete_coordinates",
                "经纬度地点必须同时提供 longitude、latitude 和 timezone。",
            )
        try:
            numeric_longitude = float(longitude)
            numeric_latitude = float(latitude)
            if not -180 <= numeric_longitude <= 180:
                raise BirthContextError(
                    "invalid_coordinates", "longitude 必须在 -180 至 180 之间。"
                )
            if not -90 <= numeric_latitude <= 90:
                raise BirthContextError(
                    "invalid_coordinates", "latitude 必须在 -90 至 90 之间。"
                )
            return ResolvedPlace(
                name=str(place.get("name") or "provided-coordinates"),
                latitude=numeric_latitude,
                longitude=numeric_longitude,
                timezone=str(timezone),
                country_code=place.get("country_code"),
                source="caller-provided",
                geoname_id=None,
            )
        except (TypeError, ValueError) as exc:
            raise BirthContextError("invalid_coordinates", "经纬度必须是数字。") from exc

    name = place.get("name")
    if not isinstance(name, str) or not name.strip():
        raise BirthContextError(
            "missing_place",
            "真太阳时需要地点。请提供 city name 或 longitude/latitude/timezone。",
        )
    candidates = _city_candidates(name.strip(), place.get("country_code"))
    if not candidates:
        raise BirthContextError(
            "location_not_found",
            f"未找到城市“{name}”。请补充国家/省份或直接提供经纬度。",
        )
    if len(candidates) > 1:
        raise BirthContextError(
            "ambiguous_location",
            f"城市“{name}”存在多个匹配项，请补充 country_code 或直接提供经纬度。",
            _candidate_payload(candidates[:10]),
        )
    return candidates[0]


def _parse_civil_time(birth_info: Dict[str, Any], birth_context: Dict[str, Any]) -> datetime:
    date_value = birth_context.get("date")
    time_value = birth_context.get("time")
    if date_value:
        try:
            parsed_date = datetime.fromisoformat(str(date_value)).date()
        except ValueError as exc:
            raise BirthContextError("invalid_date", "birth_context.date 必须是 ISO 日期。") from exc
        year, month, day = parsed_date.year, parsed_date.month, parsed_date.day
    else:
        year, month, day = birth_info["year"], birth_info["month"], birth_info["day"]

    if time_value:
        try:
            parsed_time = datetime.fromisoformat(f"2000-01-01T{time_value}").time()
        except ValueError as exc:
            raise BirthContextError("invalid_time", "birth_context.time 必须是 HH:MM[:SS]。") from exc
        hour, minute, second = parsed_time.hour, parsed_time.minute, parsed_time.second
    else:
        hour = birth_info.get("hour", 12)
        minute = birth_info.get("minute", 0)
        second = birth_info.get("second", 0)
    try:
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    except (TypeError, ValueError) as exc:
        raise BirthContextError("invalid_birth_time", "出生日期时间无效。") from exc


def _equation_of_time_minutes(value: datetime) -> float:
    """NOAA approximation of the equation of time, in minutes."""
    day_of_year = value.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (
        day_of_year - 1 + (value.hour - 12 + value.minute / 60) / 24
    )
    return 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )


def _attach_validated_timezone(civil_time: datetime, zone: ZoneInfo) -> datetime:
    """Attach a zone while rejecting impossible or ambiguous wall-clock times."""
    primary = civil_time.replace(tzinfo=zone, fold=0)
    round_tripped = primary.astimezone(timezone.utc).astimezone(zone)
    if round_tripped.replace(tzinfo=None) != civil_time:
        raise BirthContextError(
            "nonexistent_local_time",
            "出生当地时间落在夏令时跳转的不存在区间，请确认原始记录。",
        )
    alternate = civil_time.replace(tzinfo=zone, fold=1)
    if alternate.utcoffset() != primary.utcoffset():
        raise BirthContextError(
            "ambiguous_local_time",
            "出生当地时间在夏令时回拨时段内存在两个可能时刻，请补充偏移量或确认记录。",
        )
    return primary


def _calendar_backend_time(civil_time: datetime, zone: ZoneInfo) -> datetime:
    """Convert a local civil instant to lunar-python's calendar timescale."""
    backend_zone = ZoneInfo(CALENDAR_BACKEND_TIMEZONE)
    return _attach_validated_timezone(civil_time, zone).astimezone(
        backend_zone
    ).replace(tzinfo=None)


def normalize_birth_context(
    birth_info: Dict[str, Any],
    birth_context: Optional[Dict[str, Any]] = None,
) -> NormalizedBirthContext:
    """Return the effective local birth time and enough metadata to audit it.

    A legacy request without ``birth_context`` intentionally stays on standard
    time.  A structured request defaults to true solar time and must resolve a
    location before it can be calculated.
    """
    context = dict(birth_context or {})
    civil_time = _parse_civil_time(birth_info, context)
    uncertainty = context.get("uncertainty_minutes", 0)
    try:
        uncertainty = int(uncertainty)
    except (TypeError, ValueError) as exc:
        raise BirthContextError(
            "invalid_uncertainty", "uncertainty_minutes 必须是非负整数。"
        ) from exc
    if uncertainty < 0:
        raise BirthContextError(
            "invalid_uncertainty", "uncertainty_minutes 必须是非负整数。"
        )
    zi_hour_convention = context.get(
        "zi_hour_convention",
        birth_info.get("zi_hour_convention", "benchmark"),
    )
    if zi_hour_convention not in ZI_HOUR_CONVENTIONS:
        raise BirthContextError(
            "invalid_zi_hour_convention",
            "zi_hour_convention 必须是 benchmark、early 或 late。",
        )

    if not birth_context:
        return NormalizedBirthContext(
            civil_time=civil_time,
            effective_time=civil_time,
            calendar_time=civil_time,
            timezone="Asia/Shanghai",
            calendar_timezone=CALENDAR_BACKEND_TIMEZONE,
            time_basis="standard",
            correction_minutes=0.0,
            equation_of_time_minutes=0.0,
            standard_meridian=120.0,
            place=None,
            uncertainty_minutes=uncertainty,
            zi_hour_convention=zi_hour_convention,
            warnings=(
                {
                    "code": "time_correction_unavailable",
                    "message": "旧接口未提供出生地，按标准时间排盘，未应用真太阳时校正。",
                },
            ),
        )

    time_basis = context.get("time_basis", "true_solar")
    if time_basis not in ("true_solar", "standard"):
        raise BirthContextError(
            "invalid_time_basis", "time_basis 必须是 true_solar 或 standard。"
        )

    place_data = context.get("place") or {
        key: context[key]
        for key in ("name", "latitude", "longitude", "timezone", "country_code")
        if key in context
    }
    place = resolve_place(place_data) if place_data else None
    if time_basis == "true_solar" and place is None:
        raise BirthContextError(
            "missing_place",
            "默认真太阳时需要出生地。请提供 birth_context.place。",
        )

    timezone_name = context.get("timezone") or (place.timezone if place else None)
    if not timezone_name:
        raise BirthContextError("missing_timezone", "出生地点必须包含 timezone。")
    try:
        zone = ZoneInfo(str(timezone_name))
    except ZoneInfoNotFoundError as exc:
        raise BirthContextError("invalid_timezone", f"未知时区：{timezone_name}") from exc
    calendar_time = _calendar_backend_time(civil_time, zone)

    if time_basis == "standard":
        return NormalizedBirthContext(
            civil_time=civil_time,
            effective_time=civil_time,
            calendar_time=calendar_time,
            timezone=str(timezone_name),
            calendar_timezone=CALENDAR_BACKEND_TIMEZONE,
            time_basis=time_basis,
            correction_minutes=0.0,
            equation_of_time_minutes=0.0,
            standard_meridian=0.0,
            place=place,
            uncertainty_minutes=uncertainty,
            zi_hour_convention=zi_hour_convention,
            warnings=(),
        )

    offset = _attach_validated_timezone(civil_time, zone).utcoffset()
    if offset is None:
        raise BirthContextError("timezone_offset_unavailable", "无法计算出生时刻的时区偏移。")
    standard_meridian = offset.total_seconds() / 3600 * 15
    equation = _equation_of_time_minutes(civil_time)
    correction = 4 * (place.longitude - standard_meridian) + equation
    effective = civil_time + timedelta(minutes=correction)
    return NormalizedBirthContext(
        civil_time=civil_time,
        effective_time=effective,
        calendar_time=calendar_time,
        timezone=str(timezone_name),
        calendar_timezone=CALENDAR_BACKEND_TIMEZONE,
        time_basis=time_basis,
        correction_minutes=correction,
        equation_of_time_minutes=equation,
        standard_meridian=standard_meridian,
        place=place,
        uncertainty_minutes=uncertainty,
        zi_hour_convention=zi_hour_convention,
        warnings=(),
    )
