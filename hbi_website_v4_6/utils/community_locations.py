"""Traceable, offline location resolution used only for the community map."""
from collections import defaultdict
from functools import lru_cache
import gzip
import json
from pathlib import Path
import re
import unicodedata


def location_key(value):
    text = unicodedata.normalize("NFKD", str(value).casefold())
    return " ".join(re.sub(r"[^\w\s]", "", "".join(c for c in text if not unicodedata.combining(c))).split())


COUNTRY_ALIASES = {"usa": "US", "u s a": "US", "uk": "GB", "united kingdom": "GB",
                   "reino unido": "GB", "espana": "ES", "turkiye": "TR", "turkey": "TR"}
CANADIAN_REGIONS = dict(zip(
    "AB BC MB NB NL NS NT NU ON PE QC SK YT".split(),
    ["Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador",
     "Nova Scotia", "Northwest Territories", "Nunavut", "Ontario", "Prince Edward Island",
     "Quebec", "Saskatchewan", "Yukon"]))
NOISE = re.compile(
    r"\b(about\s+[\d,]+\s+results|mutual connections?|reposted|commented|reacted|"
    r"professor|university|institute|college|school|scientist|researcher|fellow|"
    r"director|manager|coordinator|supervisor|skills?|ph\.?d\.?|congratulations|"
    r"therapist|neurologist|consultant|engineer|student|founder|officer|"
    r"company|inc|ceo|cto)\b", re.I)

# English/local spellings of the same first-level administrative area.
REGION_ALIASES = {
    ("NG", "federal capital territory"): "fct",
    ("NZ", "manawatuwhanganui"): "manawatuwanganui",
    ("DK", "capital region of denmark"): "capital region",
    ("IR", "tehran province"): "tehran",
    ("BE", "walloon region"): "wallonia",
    ("DE", "rhinelandpalatinate"): "rheinlandpfalz",
    ("ET", "oromia region"): "oromiya",
    ("LB", "north governorate"): "north lebanon",
    ("GH", "central region"): "central",
}
# These published locations use a city/county instead of a first-level region.
CITY_REGION_ALIASES = {("2655984", "belfast"), ("2964574", "county dublin"),
                       ("2964180", "county galway")}


@lru_cache(maxsize=1)
def reference():
    path = Path(__file__).resolve().parent.parent / "data" / "map_geonames.json.gz"
    data = json.loads(gzip.decompress(path.read_bytes()))
    country_keys = dict(COUNTRY_ALIASES)
    for code, country in data["countries"].items():
        for alias in (code, country["iso3"], country["name"]):
            country_keys[location_key(alias)] = code
    index = defaultdict(set)
    by_id = {}
    for city in data["cities"]:
        by_id[city["id"]] = city
        for alias in (city["name"], city["ascii"], *city["aliases"]):
            key = location_key(alias)
            if key:
                index[key].add(city["id"])
    return data, country_keys, index, by_id


def clean_location(value):
    text = str(value or "").strip()
    if text.casefold() in {"nan", "none", "<na>"}:
        text = ""
    notes = []
    for encoding in ("latin-1", "cp1252"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if sum(repaired.count(c) for c in "ÃÂï�") < sum(text.count(c) for c in "ÃÂï�"):
            text = repaired
            notes.append("encoding repaired")
    cleaned = re.sub(r"\s*(?:[·•]\s*|\()(?:on-site|remote|hybrid)\)?\s*$", "", text, flags=re.I).strip()
    if cleaned != text:
        notes.append("work arrangement removed")
    return cleaned, notes


def resolve_location(value):
    raw = "" if value is None else str(value)
    cleaned, notes = clean_location(value)
    result = {"raw_location": raw, "cleaned_location": cleaned, "status": "unresolved",
              "reason": "No unambiguous reference match", "city": "", "region": "", "country": "",
              "lat": None, "lon": None, "precision": "", "location_id": "", "source": "",
              "cleanup_notes": "; ".join(notes)}
    if not cleaned:
        return {**result, "status": "missing", "reason": "No location supplied"}
    if NOISE.search(cleaned):
        return {**result, "status": "invalid", "reason": "Non-location profile or feed text"}
    data, countries, index, cities = reference()
    # Only a known, intact country followed by replacement-character garbage
    # can be repaired safely. Do not discard arbitrary trailing words.
    parts = [part.strip() for part in cleaned.split(",")]
    country_part = parts[-1]
    clean_country = re.sub(r"\s*(?:ï¿½|�)+(?:ï)?$", "", country_part).strip()
    if clean_country != country_part and location_key(clean_country) in countries:
        parts[-1] = clean_country
        notes.append("corrupt suffix removed after intact country")
    metro = bool(re.search(r"\b(metropolitan area|greater .+ area)\b", ", ".join(parts), re.I))
    parts = [re.sub(r"\s+Metropolitan Area$", "", part, flags=re.I).strip() for part in parts]
    city_name = re.sub(r"^Greater\s+(.+?)\s+Area$", r"\1", parts[0], flags=re.I)
    result.update(cleaned_location=", ".join(parts), cleanup_notes="; ".join(notes))
    country = countries.get(location_key(parts[-1]))
    region = parts[1] if len(parts) == 3 else ""
    # Infer country only from an explicit Canadian province (not a city alone).
    if not country and len(parts) == 2:
        province = CANADIAN_REGIONS.get(parts[1].upper(), parts[1])
        if location_key(province) in {location_key(v) for v in CANADIAN_REGIONS.values()}:
            country, region = "CA", province
    if not country:
        return {**result, "reason": "Country missing or unrecognized; no city-only guess"}
    result["country"] = data["countries"][country]["name"]
    if len(parts) > 3:
        return {**result, "reason": "Location structure requires review"}
    candidates = [cities[id_] for id_ in index.get(location_key(city_name), ()) if cities[id_]["country"] == country]
    if region:
        region_key = location_key(CANADIAN_REGIONS.get(region.upper(), region) if country == "CA" else region)
        region_key = REGION_ALIASES.get((country, region_key), region_key)
        def region_matches(city):
            region_names = data["regions"].get(country + "." + city["admin1"], [])
            keys = {location_key(n) for n in region_names}
            if country == "US":
                keys.add(location_key(city["admin1"]))
            return region_key in keys or (city["id"], region_key) in CITY_REGION_ALIASES
        candidates = [city for city in candidates if region_matches(city)]
    # Prefer an exact primary name over another city's historical alias.
    primary = [city for city in candidates if location_key(city_name) in {location_key(city["name"]), location_key(city["ascii"])}]
    if primary:
        candidates = primary
    if len(candidates) != 1:
        return {**result, "reason": "Ambiguous city" if len(candidates) > 1 else "Place or region requires review"}
    city = candidates[0]
    region_names = data["regions"].get(country + "." + city["admin1"], [""])
    label = city["name"] + (" metropolitan area" if metro else "")
    return {**result, "status": "mapped", "reason": "Country/region matched to geographic reference",
            "city": label, "region": region_names[0], "lat": city["lat"], "lon": city["lon"],
            "precision": "Metropolitan area (approximate)" if metro else "City (approximate)",
            "location_id": ("metro:" if metro else "city:") + city["id"],
            "source": "https://www.geonames.org/" + city["id"] + "/"}


def build_location_audit(profiles):
    """One traceable mapping decision per published profile; never alter input."""
    import pandas as pd
    columns = ["profile_id", "full_name", "raw_location", "cleaned_location", "status", "reason",
               "city", "region", "country", "lat", "lon", "precision", "location_id", "source", "cleanup_notes"]
    return pd.DataFrame([
        {"profile_id": row["profile_id"], "full_name": row.get("full_name", ""),
         **resolve_location(row.get("location", ""))}
        for row in profiles.fillna("").drop_duplicates("profile_id").to_dict("records")
    ], columns=columns)


def aggregate_locations(audit):
    """Canonical IDs prevent spelling variants and country labels inflating counts."""
    return (audit[audit["status"].eq("mapped")]
            .groupby(["location_id", "city", "region", "country", "lat", "lon", "precision"], as_index=False)
            .agg(count=("profile_id", "nunique"))
            .sort_values("count", ascending=False).reset_index(drop=True))
