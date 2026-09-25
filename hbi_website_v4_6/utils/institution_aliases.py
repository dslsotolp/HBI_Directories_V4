"""Institution name normalization for HBI Organization Tags.

INSTITUTION_ALIASES maps lowercase raw names (as they appear in CSV data) to
canonical display names.  normalize_institution() uses this dict to produce
consistent tag values from free-text education / experience institution fields.
"""

from __future__ import annotations
import re

INSTITUTION_ALIASES: dict[str, str] = {
    # ── University of Calgary ─────────────────────────────────────────────────
    "university of calgary": "University of Calgary",
    "the university of calgary": "University of Calgary",
    "u of c": "University of Calgary",
    "ucalgary": "University of Calgary",
    "calgary university": "University of Calgary",
    "schulich school of engineering, university of calgary": "University of Calgary",
    "faculty of social work, university of calgary": "University of Calgary",
    "cumming school of medicine, university of calgary": "University of Calgary",
    "faculty of nursing, university of calgary": "University of Calgary",
    "faculty of kinesiology, university of calgary": "University of Calgary",
    "hotchkiss brain institute, university of calgary": "University of Calgary",

    # ── Hotchkiss Brain Institute ─────────────────────────────────────────────
    "hotchkiss brain institute": "Hotchkiss Brain Institute",
    "hotchkiss brain institute trainee organization": "Hotchkiss Brain Institute",

    # ── Alberta Health Services ───────────────────────────────────────────────
    "alberta health services": "Alberta Health Services",
    "ahs": "Alberta Health Services",

    # ── Recovery Alberta ──────────────────────────────────────────────────────
    "recovery alberta": "Recovery Alberta",

    # ── Calgary Hospitals / Health Centres ───────────────────────────────────
    "alberta children's hospital": "Alberta Children's Hospital",
    "alberta children's hospital research institute": "Alberta Children's Hospital",
    "foothills medical centre": "Foothills Medical Centre",
    "foothills medical center": "Foothills Medical Centre",
    "peter lougheed centre": "Peter Lougheed Centre",
    "south health campus": "South Health Campus",
    "rockyview general hospital": "Rockyview General Hospital",
    "the hospital for sick children": "Hospital for Sick Children",
    "hospital for sick children": "Hospital for Sick Children",
    "sickkids": "Hospital for Sick Children",
    "houston methodist": "Houston Methodist",

    # ── Research Institutes ───────────────────────────────────────────────────
    "mathison centre for mental health research & education": "Mathison Centre for Mental Health Research & Education",
    "mccaig institute for bone and joint health": "McCaig Institute for Bone and Joint Health",
    "brain climate equity collaborative (brain-ce collab)": "Brain Climate Equity Collaborative",
    "brain climate equity collaborative": "Brain Climate Equity Collaborative",

    # ── University of Alberta ─────────────────────────────────────────────────
    "university of alberta": "University of Alberta",
    "u of a": "University of Alberta",
    "ualberta": "University of Alberta",

    # ── University of Lethbridge ──────────────────────────────────────────────
    "university of lethbridge": "University of Lethbridge",
    "the university of lethbridge": "University of Lethbridge",

    # ── Mount Royal University ────────────────────────────────────────────────
    "mount royal university": "Mount Royal University",
    "mount royal college": "Mount Royal University",

    # ── SAIT ─────────────────────────────────────────────────────────────────
    "southern alberta institute of technology (sait)": "SAIT Polytechnic",
    "sait polytechnic": "SAIT Polytechnic",
    "sait": "SAIT Polytechnic",
    "alberta university of the arts": "Alberta University of the Arts",

    # ── University of British Columbia ───────────────────────────────────────
    "university of british columbia": "University of British Columbia",
    "the university of british columbia": "University of British Columbia",
    "ubc": "University of British Columbia",

    # ── University of Toronto ─────────────────────────────────────────────────
    "university of toronto": "University of Toronto",
    "u of t": "University of Toronto",

    # ── McGill University ─────────────────────────────────────────────────────
    "mcgill university": "McGill University",

    # ── McMaster University ───────────────────────────────────────────────────
    "mcmaster university": "McMaster University",

    # ── Queen's University ────────────────────────────────────────────────────
    "queen's university": "Queen's University",
    "queens university": "Queen's University",

    # ── University of Western Ontario ────────────────────────────────────────
    "university of western ontario": "University of Western Ontario",
    "western university": "University of Western Ontario",

    # ── Dalhousie University ──────────────────────────────────────────────────
    "dalhousie university": "Dalhousie University",

    # ── University of Ottawa ──────────────────────────────────────────────────
    "university of ottawa": "University of Ottawa",

    # ── University of Saskatchewan ────────────────────────────────────────────
    "university of saskatchewan": "University of Saskatchewan",

    # ── University of Manitoba ────────────────────────────────────────────────
    "university of manitoba": "University of Manitoba",

    # ── University of Waterloo ────────────────────────────────────────────────
    "university of waterloo": "University of Waterloo",

    # ── University of Guelph ─────────────────────────────────────────────────
    "university of guelph": "University of Guelph",

    # ── University of Victoria ────────────────────────────────────────────────
    "university of victoria": "University of Victoria",

    # ── Carleton University ───────────────────────────────────────────────────
    "carleton university": "Carleton University",

    # ── York University ───────────────────────────────────────────────────────
    "york university": "York University",

    # ── Concordia University ──────────────────────────────────────────────────
    "concordia university": "Concordia University",

    # ── Memorial University ───────────────────────────────────────────────────
    "memorial university": "Memorial University of Newfoundland",
    "memorial university of newfoundland": "Memorial University of Newfoundland",
    "memorial university, newfoundland and labrador": "Memorial University of Newfoundland",

    # ── University of Regina ──────────────────────────────────────────────────
    "university of regina": "University of Regina",
    "hill and levene schools of business at university of regina": "University of Regina",

    # ── University of New Brunswick ───────────────────────────────────────────
    "university of new brunswick": "University of New Brunswick",

    # ── University of California ──────────────────────────────────────────────
    "university of california": "University of California",

    # ── Harvard University ────────────────────────────────────────────────────
    "harvard university": "Harvard University",

    # ── Johns Hopkins University ──────────────────────────────────────────────
    "johns hopkins university": "Johns Hopkins University",

    # ── Cornell University ────────────────────────────────────────────────────
    "cornell university": "Cornell University",

    # ── Columbia University ───────────────────────────────────────────────────
    "columbia university": "Columbia University",

    # ── Stanford University ───────────────────────────────────────────────────
    "stanford university": "Stanford University",

    # ── University of Chicago ─────────────────────────────────────────────────
    "university of chicago": "University of Chicago",

    # ── University of Michigan ────────────────────────────────────────────────
    "university of michigan": "University of Michigan",

    # ── University of Florida ─────────────────────────────────────────────────
    "university of florida": "University of Florida",

    # ── Ohio State University ─────────────────────────────────────────────────
    "the ohio state university": "The Ohio State University",
    "ohio state university": "The Ohio State University",

    # ── University of Illinois ────────────────────────────────────────────────
    "university of illinois": "University of Illinois",

    # ── State University of New York ─────────────────────────────────────────
    "state university of new york": "State University of New York",

    # ── Washington State University ───────────────────────────────────────────
    "washington state university": "Washington State University",

    # ── UK Universities ───────────────────────────────────────────────────────
    "university of cambridge": "University of Cambridge",
    "university of oxford": "University of Oxford",
    "imperial college london": "Imperial College London",
    "the university of manchester": "University of Manchester",
    "university of manchester": "University of Manchester",
    "university of edinburgh": "University of Edinburgh",
    "bangor university": "Bangor University",
    "university of wales, bangor": "Bangor University",
    "university of wales": "University of Wales",
    "university of london": "University of London",
    "king's college": "King's College London",
    "king's college london": "King's College London",
    "royal college of surgeons in ireland (rcsi)": "RCSI University of Medicine and Health Sciences",

    # ── European Universities ─────────────────────────────────────────────────
    "leiden university": "Leiden University",
    "university of groningen": "University of Groningen",
    "radboud university nijmegen": "Radboud University",
    "radboud university": "Radboud University",
    "uppsala university": "Uppsala University",
    "uppsala universitet": "Uppsala University",
    "slu - swedish university of agricultural sciences": "Swedish University of Agricultural Sciences",
    "stockholm university": "Stockholm University",
    "university of montpellier": "University of Montpellier",
    "university of barcelona": "University of Barcelona",
    "munich technical university": "Technical University of Munich",

    # ── Australian Universities ───────────────────────────────────────────────
    "unsw": "UNSW Sydney",
    "unsw sydney": "UNSW Sydney",
    "university of new south wales": "UNSW Sydney",
    "university of technology sydney": "University of Technology Sydney",

    # ── Iranian Universities ──────────────────────────────────────────────────
    "amirkabir university of technology - tehran polytechnic": "Amirkabir University of Technology",
    "amirkabir university of technology": "Amirkabir University of Technology",
    "iran university of science and technology": "Iran University of Science and Technology",
    "sharif university of technology": "Sharif University of Technology",
    "university of mazandaran": "University of Mazandaran",
    "university of mazandaran": "University of Mazandaran",
    "bnut - babol noshirvani university of technology": "Babol Noshirvani University of Technology",

    # ── Other Notable Institutions ────────────────────────────────────────────
    "chulalongkorn university": "Chulalongkorn University",
    "haramaya university": "Haramaya University",
    "dharmsinh desai university": "Dharmsinh Desai University",
    "universidad nacional autónoma de méxico": "Universidad Nacional Autónoma de México",
    "universidad autónoma de nuevo león": "Universidad Autónoma de Nuevo León",
    "universidade federal de uberlândia - ufu": "Universidade Federal de Uberlândia",
    "university of campinas (unicamp)": "University of Campinas",
    "fluminense federal university": "Fluminense Federal University",
    "university of havana": "University of Havana",
    "university of dhaka": "University of Dhaka",
    "humber college": "Humber College",

    # ── Calgary / Alberta Organizations ──────────────────────────────────────
    "city of calgary": "City of Calgary",
    "ymca calgary": "YMCA Calgary",
    "innovate calgary": "Innovate Calgary",
    "hull services": "Hull Services",
    "united active living inc.": "United Active Living",
    "united active living": "United Active Living",
    "youreka canada": "Youreka Canada",
    "crowfoot village family practice health home": "Crowfoot Village Family Practice",

    # ── Professional / Scientific Organizations ───────────────────────────────
    "ieee": "IEEE",
    "american academy of neurology": "American Academy of Neurology",
    "special olympics alberta": "Special Olympics Alberta",
    "ja worldwide": "JA Worldwide",

    # ── Schools within UCalgary (kept as their own brand names) ───────────────
    "haskayne school of business": "Haskayne School of Business",
    "schulich school of engineering": "Schulich School of Engineering",
    "werklund school of education": "Werklund School of Education",
    "cumming school of medicine": "Cumming School of Medicine",
}

# Substrings that mark a non-institution entry (case-insensitive).
# Entries whose lowercased name contains any of these substrings are skipped.
_NOISE_SUBSTRINGS = frozenset({
    "high school",
    "secondary school",
    "elementary school",
    "middle school",
    "jr. high",
    "junior high",
    "collegiate institute",
})

# Exact lowercased values that are not real institutions.
_NOISE_EXACT = frozenset({
    "why am i seeing this ad?",
    "international baccalaureate",
    "n/a",
    "na",
    "none",
    "unknown",
    "other",
    "self-employed",
    "self employed",
    "freelance",
})


def normalize_institution(name: str) -> str:
    """Return a canonical display name for an institution string.

    Returns an empty string if the value looks like noise (school names,
    ad artefacts, placeholders).  Otherwise returns the aliased canonical
    name if one exists, or the stripped original if not.
    """
    if not name or not isinstance(name, str):
        return ""
    stripped = name.strip()
    if not stripped or len(stripped) < 3:
        return ""
    lower = stripped.lower()

    # Exact noise entries
    if lower in _NOISE_EXACT:
        return ""

    # Noise by substring
    if any(sub in lower for sub in _NOISE_SUBSTRINGS):
        return ""

    # Alias lookup (case-insensitive exact match)
    canonical = INSTITUTION_ALIASES.get(lower)
    if canonical:
        return canonical

    # Reject strings that are too long to be an institution name
    if len(stripped) > 120:
        return ""

    # Reject strings that start with a year (e.g. "2003-2010 College of Physicians…")
    if re.match(r'^\d{4}', stripped):
        return ""

    # Reject strings that contain a sentence boundary (biographical prose)
    if re.search(r'\.\s+[A-Z]', stripped):
        return ""

    # No alias found — return the original stripped name
    return stripped
