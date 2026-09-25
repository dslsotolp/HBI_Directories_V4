# Community map location reference

Snapshot: 2026-09-21. `map_geonames.json.gz` contains an offline geographic
reference derived from [GeoNames downloads](https://download.geonames.org/export/dump/),
licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The map includes visible attribution. The compressed payload records source-file
SHA-256 hashes, source URL, license, and snapshot date.

The reference contains 34,146 cities from `cities15000.zip` and 15 supplementary
smaller-city candidates from `cities1000.zip`, with country and first-level
administrative names from `countryInfo.txt` and `admin1CodesASCII.txt`. Small-city
names selected for this snapshot are listed in `scripts/build_map_gazetteer.py`.
GeoNames IDs provide per-location evidence URLs in the downloadable review.

To rebuild from downloaded files in the workspace root:

```powershell
.venv\Scripts\python.exe scripts\build_map_gazetteer.py --source .tmp\map_geonames --output hbi_website_v4_6\data\map_geonames.json.gz
```

The website makes no geocoding API requests and does not send profile data to
GeoNames. Standard basemap tiles still load from the existing public tile service.

`utils/community_locations.py` preserves raw location text and derives separate
cleaned text, status, reason, canonical city/region/country, coordinates, precision,
stable location ID, cleanup notes, and source URL. It removes work-arrangement
suffixes, handles accents and known encoding problems, excludes explicit
non-location text, and uses country/region constraints. An unmatched supplied
region is not ignored. Ambiguous cities remain unresolved. Province/country-only
locations are retained for review rather than plotted at a city coordinate.

Metropolitan areas use the representative city's coordinate and are labeled
approximate. City-only markers are also approximate. Region aliases in the
resolver reconcile known naming variants; county labels for Belfast, Dublin,
and Galway are tied to their specific GeoNames IDs. Unknown text remains visible
in the audit rather than being assigned a guessed location.

Production source CSVs are unchanged. Mapping decisions rebuild from published
profiles when the Streamlit cache expires or is cleared; clear caches after a
publication or reference update. Unpublished batches are not included.
