"""
geo_utils.py
============
Compatibility helpers for community profile locations.

The original coordinate dictionary remains for historical reference. Active
geocoding delegates to community_locations and its offline GeoNames reference,
which checks country/region context and preserves unresolved locations.
"""

from typing import Optional
import re

# ── City → (lat, lon) ─────────────────────────────────────────────────────────
# Keyed on lowercase "<city>, <region/country>" or just "<city>" patterns
# found in LinkedIn profile location strings.
CITY_COORDS: dict[str, tuple[float, float]] = {
    # Alberta
    "calgary, alberta, canada":            (51.0447,  -114.0719),
    "calgary, ab, canada":                 (51.0447,  -114.0719),
    "calgary, alberta":                    (51.0447,  -114.0719),
    "calgary":                             (51.0447,  -114.0719),
    "cochrane, alberta, canada":           (51.1893,  -114.4673),
    "cochrane, alberta":                   (51.1893,  -114.4673),
    "airdrie, alberta, canada":            (51.2917,  -114.0144),
    "okotoks, alberta, canada":            (50.7260,  -113.9752),
    "chestermere, alberta, canada":        (51.0466,  -113.8175),
    "strathmore, alberta, canada":         (51.0322,  -113.4001),
    "edmonton, alberta, canada":           (53.5461,  -113.4938),
    "edmonton, alberta":                   (53.5461,  -113.4938),
    "edmonton":                            (53.5461,  -113.4938),
    "lethbridge, alberta, canada":         (49.6956,  -112.8451),
    "red deer, alberta, canada":           (52.2681,  -113.8113),
    "medicine hat, alberta, canada":       (50.0405,  -110.6764),
    "banff, alberta, canada":              (51.1784,  -115.5708),
    "canmore, alberta, canada":            (51.0892,  -115.3494),
    "grande prairie, alberta, canada":     (55.1708,  -118.7941),
    "fort mcmurray, alberta, canada":      (56.7265,  -111.3790),
    "canada":                              (60.0000,   -95.0000),
    "alberta, canada":                     (53.9333,  -116.5765),
    # British Columbia
    "vancouver, british columbia, canada": (49.2827,  -123.1207),
    "vancouver, bc, canada":               (49.2827,  -123.1207),
    "surrey, british columbia, canada":    (49.1913,  -122.8490),
    "victoria, british columbia, canada":  (48.4284,  -123.3656),
    "kelowna, british columbia, canada":   (49.8880,  -119.4960),
    "burnaby, british columbia, canada":   (49.2488,  -122.9805),
    "richmond, british columbia, canada":  (49.1666,  -123.1336),
    "abbotsford, british columbia, canada":(49.0504,  -122.3045),
    "nanaimo, british columbia, canada":   (49.1659,  -123.9401),
    "prince george, british columbia, canada": (53.9171, -122.7497),
    # Saskatchewan
    "saskatoon, saskatchewan, canada":     (52.1332,  -106.6700),
    "regina, saskatchewan, canada":        (50.4452,  -104.6189),
    "prince albert, saskatchewan, canada": (53.2028,  -105.7531),
    # Manitoba
    "winnipeg, manitoba, canada":          (49.8951,   -97.1384),
    "winnipeg, mb, canada":                (49.8951,   -97.1384),
    # Ontario
    "toronto, ontario, canada":            (43.6532,   -79.3832),
    "toronto, on, canada":                 (43.6532,   -79.3832),
    "toronto":                             (43.6532,   -79.3832),
    "ottawa, ontario, canada":             (45.4215,   -75.6972),
    "kingston, ontario, canada":           (44.2312,   -76.4860),
    "hamilton, ontario, canada":           (43.2557,   -79.8711),
    "london, ontario, canada":             (42.9849,   -81.2453),
    "mississauga, ontario, canada":        (43.5890,   -79.6441),
    "brampton, ontario, canada":           (43.7315,   -79.7624),
    "waterloo, ontario, canada":           (43.4668,   -80.5164),
    "guelph, ontario, canada":             (43.5448,   -80.2482),
    "windsor, ontario, canada":            (42.3149,   -83.0364),
    "thunder bay, ontario, canada":        (48.3809,   -89.2477),
    "sudbury, ontario, canada":            (46.4920,   -80.9930),
    "barrie, ontario, canada":             (44.3894,   -79.6903),
    "markham, ontario, canada":            (43.8561,   -79.3370),
    "richmond hill, ontario, canada":      (43.8828,   -79.4403),
    # Quebec
    "montreal, quebec, canada":            (45.5017,   -73.5673),
    "montreal, qc, canada":                (45.5017,   -73.5673),
    "gatineau, quebec, canada":            (45.4768,   -75.7013),
    "quebec city, quebec, canada":         (46.8139,   -71.2080),
    "laval, quebec, canada":               (45.6066,   -73.7124),
    "sherbrooke, quebec, canada":          (45.4046,   -71.8929),
    # Atlantic
    "halifax, nova scotia, canada":        (44.6488,   -63.5752),
    "fredericton, new brunswick, canada":  (45.9636,   -66.6431),
    "moncton, new brunswick, canada":      (46.0878,   -64.7782),
    "st. john's, newfoundland, canada":    (47.5615,   -52.7126),
    "charlottetown, pei, canada":          (46.2382,   -63.1311),
    # Northwest / Yukon
    "whitehorse, yukon, canada":           (60.7212,  -135.0568),
    "yellowknife, nwt, canada":            (62.4540,  -114.3718),
    # United States
    "liberty lake, washington, united states": (47.6653, -117.1208),
    "liberty lake, wa, united states":     (47.6653,  -117.1208),
    "seattle, washington, united states":  (47.6062,  -122.3321),
    "new york, new york, united states":   (40.7128,   -74.0060),
    "new york, ny, united states":         (40.7128,   -74.0060),
    "boston, massachusetts, united states":(42.3601,   -71.0589),
    "chicago, illinois, united states":    (41.8781,   -87.6298),
    "san francisco, california, united states": (37.7749, -122.4194),
    "los angeles, california, united states":   (34.0522, -118.2437),
    "houston, texas, united states":       (29.7604,   -95.3698),
    "denver, colorado, united states":     (39.7392,  -104.9903),
    "washington, dc, united states":       (38.9072,   -77.0369),
    "united states":                       (37.0902,   -95.7129),
    # Europe
    "london, england, united kingdom":     (51.5074,    -0.1278),
    "london, united kingdom":              (51.5074,    -0.1278),
    "london":                              (51.5074,    -0.1278),
    "edinburgh, scotland, united kingdom": (55.9533,    -3.1883),
    "oxford, england, united kingdom":     (51.7520,    -1.2577),
    "cambridge, england, united kingdom":  (52.2053,     0.1218),
    "amsterdam, netherlands":              (52.3676,     4.9041),
    "paris, ile-de-france, france":        (48.8566,     2.3522),
    "paris, france":                       (48.8566,     2.3522),
    "berlin, germany":                     (52.5200,    13.4050),
    "munich, bavaria, germany":            (48.1351,    11.5820),
    "zurich, switzerland":                 (47.3769,     8.5417),
    "stockholm, sweden":                   (59.3293,    18.0686),
    "oslo, norway":                        (59.9139,    10.7522),
    "copenhagen, denmark":                 (55.6761,    12.5683),
    "helsinki, finland":                   (60.1699,    24.9384),
    "rome, italy":                         (41.9028,    12.4964),
    "milan, italy":                        (45.4654,     9.1859),
    "madrid, spain":                       (40.4168,    -3.7038),
    "barcelona, spain":                    (41.3851,     2.1734),
    # Middle East
    "tehran province, iran":               (35.6892,    51.3890),
    "tehran, iran":                        (35.6892,    51.3890),
    "dubai, united arab emirates":         (25.2048,    55.2708),
    "riyadh, saudi arabia":                (24.7136,    46.6753),
    # Asia-Pacific
    "sydney, new south wales, australia":  (-33.8688,  151.2093),
    "sydney, australia":                   (-33.8688,  151.2093),
    "melbourne, victoria, australia":      (-37.8136,  144.9631),
    "brisbane, queensland, australia":     (-27.4698,  153.0251),
    "auckland, new zealand":               (-36.8509,  174.7645),
    "tokyo, japan":                        (35.6762,   139.6503),
    "beijing, china":                      (39.9042,   116.4074),
    "shanghai, china":                     (31.2304,   121.4737),
    "hong kong":                           (22.3193,   114.1694),
    "singapore":                           (1.3521,    103.8198),
    "mumbai, maharashtra, india":          (19.0760,    72.8777),
    "new delhi, delhi, india":             (28.6139,    77.2090),
    "bangalore, karnataka, india":         (12.9716,    77.5946),
    # South America
    "sao paulo, brazil":                   (-23.5505,  -46.6333),
    "buenos aires, argentina":             (-34.6037,  -58.3816),
    # Africa
    "cape town, western cape, south africa": (-33.9249, 18.4241),
    "johannesburg, south africa":          (-26.2041,   28.0473),
    "nairobi, kenya":                      (-1.2921,    36.8219),
}


def parse_location_string(location: str) -> tuple[str, str, str]:
    """
    Split a LinkedIn location string into (city, region, country).

    Handles formats:
    - "Calgary, Alberta, Canada"          → ("calgary", "alberta", "canada")
    - "Calgary, AB, Canada"               → ("calgary", "ab", "canada")
    - "Calgary, Alberta"                  → ("calgary", "alberta", "")
    - "Canada"                            → ("canada", "", "")
    """
    parts = [p.strip().lower() for p in str(location).split(",")]
    city = parts[0] if len(parts) >= 1 else ""
    region = parts[1] if len(parts) >= 2 else ""
    country = parts[2] if len(parts) >= 3 else ""
    return city, region, country


def geocode_location(location: Optional[str]) -> Optional[tuple[float, float]]:
    """Resolve through the conservative offline reference, without city-only guesses."""
    from utils.community_locations import resolve_location
    resolved = resolve_location(location)
    if resolved["status"] == "mapped":
        return resolved["lat"], resolved["lon"]
    return None
