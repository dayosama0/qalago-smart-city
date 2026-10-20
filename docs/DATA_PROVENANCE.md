# Dataset provenance and reproducibility

## What ships with the app

`data/pois.db` is a genuine, locally validated SQLite snapshot derived from
OpenStreetMap plus manually reviewed public venue pages. It contains **207 named POIs**, **144 listed opening schedules and 5 closure markers**,
**207 editorial descriptions**, and **271 field overrides (199 descriptions and 72 hours/closure values)**. All 207 records have unknown
power-outlet availability. These are measured data completeness counts, not
claims that the places are currently open, have been visited, or have been
independently audited. The app reads this database; app startup does not invoke
Overpass or recreate the database.

The 20 October expansion adds 10 source-identified places from 2GIS and official
pages, with 9 schedules and 5 average checks. Two duplicate source representations
are merged from the 199 OSM records, including MEGA Silk Way. See
[the expansion review](DATA_EXPANSION_2026-10-20.md) for field evidence and limits.
`data/curated_places.json` is validated before any database writes; its hash is
recorded in the manifest. The CLI includes it in both offline and live rebuilds.

The successful source downloads were four small, unauthenticated, read-only
[OSM API 0.6 map requests](https://wiki.openstreetmap.org/wiki/API_v0.6#Retrieving_map_data_by_bounding_box:_GET_/api/0.6/map)
on **19 October 2026, 10:35:52–10:36:02 UTC** (15:35:52–15:36:02 in Astana).
This is a fetch time, not the date of a human inspection or the individual OSM
objects' latest edits. The distributed JSON omits contributor identifiers.

Public Overpass attempts during preparation failed with HTTP 406/500/502/504
across several endpoints. Consequently, **the shipped dataset is the explicitly
documented small-area OSM API fallback, not a successful full Overpass city
download**. The API fallback does not supply complete coverage of Astana. Some
otherwise real places will be absent, and a zero-result recommendation is valid.

## Opening-hours review (20 October 2026)

The first review checked 38 schedules (27 gaps filled and 11 existing values
confirmed or updated). The later expansion added 10 places with 9 schedules.
The follow-up search then covered the 92 remaining gaps: **22 schedules added,
2 permanent closures and 1 temporary closure recorded; 67 remained unknown**.
A further pass added **8 schedules and 1 temporary closure**, leaving **58 gaps**.
The [continuation audit](../data/hours_followup_2026-10-20.json) records those changes
and how source conflicts were resolved. The description of Рыба моей мечты now
includes the reservation requirement from its 2GIS card.
Sources are matched to branch addresses or coordinates and retained per field
with a review date. The shipped 149 nonempty opening-hours values consist of
144 schedules and 5 closure markers (including one original OSM `closed`).
Retrieval excludes all five closed records. Temporary closures of Flowerhub and
Central Pizza & Coffee at Respubliki 5 are explicitly distinguished in the audit
and must be rechecked before restoring those places.
This is not a fresh audit of every existing OSM schedule. See the
[review ledger and remaining gaps](OPENING_HOURS_REVIEW.md) and
[the 92-record follow-up audit](../data/hours_gap_review_2026-10-20.json).

## Geographic coverage

Each successful request URL and original XML SHA-256 appears in
`data/snapshots/astana.metadata.json` or `airport.metadata.json`. Bounding boxes
below use **west, south, east, north**, as required by the OSM map API:

| Public landmark area | Bounding box |
| --- | --- |
| EXPO / MEGA Silk Way | 71.395, 51.081, 71.421, 51.100 |
| Baiterek | 71.419, 51.120, 71.442, 51.138 |
| Park Astana and nearby central area | 71.404, 51.155, 71.430, 51.176 |
| NQZ terminals and nearby area | 71.451, 51.019, 71.484, 51.037 |

The map API can return complete ways extending beyond the requested box. We use
only complete way geometry and complete outer geometry for multipolygon
relations; incomplete relations are omitted. A way or multipolygon's point is
the center of its geometry's bounding box, **not a surveyed entrance or a
guaranteed accessible point**. The airport records do not establish landside,
airside, security, or boarding access.

The normal Overpass ETL remains implemented with two bounded queries, using
south/west/north/east: main Astana `(51.06, 71.31, 51.20, 71.54)` and airport
`(50.99, 71.43, 51.05, 71.52)`. Queries select cafes, restaurants, libraries,
arts centres, museums, attractions, viewpoints, galleries, parks, gardens,
playgrounds, malls, monuments and memorials. The latter two map to `attraction`.
There are at most three attempts per area with finite connection/read timeouts;
the downloader rejects Overpass runtime-error remarks rather than caching a
silently incomplete response. Requests never run as part of recommendations.

## Transformations and validation

The original successful HTTP XML bodies remain in ignored `data/raw/*.osm` on
the preparation machine. They are **not committed**, since they contain public
OSM mapper/contact metadata unnecessary for recommendations. The tracked
`data/snapshots/*.json` files are transparently labeled **sanitized, converted
category subsets**, not untouched original HTTP payloads. They preserve source
OSM type, numeric ID, coordinates or calculated geometry center, names,
category tags and relevant original evidence such as opening schedules.
Telephone/email/contact/social-media tags and mapper `user`/`uid` attributes
are omitted. `tags_json` in SQLite applies the same tag minimization.

The two converted inputs contain 296 selected category elements (293 main,
3 airport). Normalization rejects 97 unnamed/invalid/unusable records and
retains 199 unique stable keys such as `osm:node:123` and `osm:way:123`.
Objects are never merged merely because they are nearby. Validation checks
source object type and positive integer ID, a genuine nonempty source name,
finite coordinates in geographic ranges, selected categories, and SQLite
`PRAGMA integrity_check` (`ok` on the shipped database).

Category-based `likely_indoor` is an inference, not confirmation of heating or
weather protection. Category visit durations are estimates. Source hours are retained unless a documented field override replaces them; original snapshot tags remain available. Hours
are stored without a static `opening_status` column. No outlets have been
invented to satisfy the hackathon scenario. `data/manual_overrides.csv` contains
199 individually written Russian descriptions and 72 sourced hours/closure overrides applied before deduplication. Overrides require a whitelisted field,
appropriate enum/range, public evidence URL and ISO check date/time. An override
whose place ID is missing aborts the build so it cannot silently survive removal.

### Editorial descriptions (20 October 2026)

All 199 descriptions are distinct, short editorial summaries rather than copied
reviews or live LLM output. The canonical texts, evidence URLs and review dates
are stored in `data/manual_overrides.csv` and applied on offline or live rebuilds.
The original OSM snapshots are unchanged. The source for each text is copied to
`description_source`; field-level metadata is retained in `verified_fields_json`.

30 records use additional web references, including the newly matched 2GIS
card for Рыба моей мечты and the previously checked sources: the official sites of the philharmonic,
MEGA, Keruen, Abu Dhabi Plaza, The Ritz-Carlton, Rafe, Lepim i Varim and Flowerhub;
Visit Astana, Kazakhstan Travel and individual destination/dining references.
The other 169 descriptions use the existing OSM categories, tags, addresses and
spatial relationships between records in the shipped snapshot. These are not
169 additional live web verifications. Nearby-place references are geographic
orientation, not assertions of common ownership, shared entrances or walking access.
The `manual_reference` provenance method means an editorial source check, not
an on-site inspection or confirmation that a business is still operating.

Sparse records stay sparse: descriptions do not invent dishes from a business
name, quietness, quality, prices, ratings or access. Potential duplicate OSM
records (MEGA and Coffee Stories) are identified in their descriptions but kept
as separate source records. Museum and airport records retain explicit uncertainty
about current use or terminal access. Website descriptions do not override the
OSM hours, features or category used by the recommendation engine.

Cards show the description immediately beneath the place heading in secondary
text; the reference link is inside the collapsed details. Descriptions pass
unchanged from SQLite through retrieval and recommendations and do not require
an API key or internet at runtime.

Measured category counts: cafe 101; restaurant 57; attraction 13; park 12;
mall 7; arts centre 3; museum 2; gallery 1; garden 1; library 1; playground 1.
Indoors statuses are 172 `likely_indoor`, 14 `outdoor`, and 13 `unknown`.

## Public preset coordinate checks

The downloaded OSM geometry supports these approximate public landmark points:

| Preset | OSM evidence | Approximate geometry center |
| --- | --- | --- |
| MEGA Silk Way | [way 499328514](https://www.openstreetmap.org/way/499328514) | 51.0890897, 71.40733035 |
| Baiterek | [way 230401645](https://www.openstreetmap.org/way/230401645) | 51.12828825, 71.4304546 |
| Park Astana | [relation 15957444](https://www.openstreetmap.org/relation/15957444) | 51.15481525, 71.4195693 |
| NQZ Terminal 1 area | [way 166500591](https://www.openstreetmap.org/way/166500591) | 51.0279734, 71.46347995 |

Park relation 15957444 is named `Астана саябағы` / `Парк Астана`. Its two complete
outer ways are 120264226 and 1180153749; combined bounds are south 51.1497946,
west 71.4120564, north 51.1598359, east 71.4270822. These checks identify public
landmark geometry, not pedestrian entrance/access verification. Nearby
`entrance` nodes found in the source belonged to hotel/building footprints and
were deliberately not labeled as park entrances.

## Rebuild and update

Rebuild the exact shipped source subset without network:

```bash
python -m ingestion.build_database --offline
```

Fetch the full intended two-area Overpass source when service is available:

```bash
python -m ingestion.build_database
```

Successful Overpass responses are cached byte-for-byte in ignored `data/raw/`
with retrieval metadata. To rebuild that local full cache without network:

```bash
python -m ingestion.build_database --offline --raw-dir data/raw
```

The live Overpass command updates the database and manifest; it does not replace
the committed sanitized small-area JSON. A maintainer must review, minimize and
update redistributable source snapshots intentionally before publishing a new
dataset. Do not commit the unredacted local raw directory.

The optional fallback collector uses exactly four small public map requests and
does not retry indefinitely. Use this explicitly only if needed:

```bash
python -m ingestion.fetch_osm_api
python -m ingestion.build_database --offline
```

On the preparation machine, `python -m ingestion.fetch_osm_api --offline`
reconverts the original XML only after matching its recorded hash, preserves the
actual original retrieval times, and makes no network calls. The unredacted
XML is intentionally absent from a clean clone; the shipped sanitized JSON is
enough for ordinary offline database rebuilds.

All rebuilds are keyed by stable OSM IDs, replace source fields from the current
input, remove stale objects missing from that input, and apply overrides only
to surviving source IDs. A failure before a complete valid build preserves the
existing usable database. Empty input never overwrites it.

The authoritative current database SHA-256, source hashes, build timestamp and
counts are in `data/pois.manifest.json`. Its database hash should be recomputed
after every rebuild because SQLite file bytes can change even with unchanged
logical records. The shipped source SHA-256 values are:

- `astana.json`: `fb45c09f37c7d97da322fdd631d873dffaab5be2b73eb1a576c6e43f7de079b4`
- `airport.json`: `dd4fe276faa43c16f094f6ed3d53cfd260c1ec5a5ba8ed050327d501d0fd43bd`

## License and attribution

Data: **© OpenStreetMap contributors (ODbL 1.0)**. Redistribution of this derived
database uses the same [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
terms; preserve attribution and comply with share-alike requirements when
publishing derivatives. See [OpenStreetMap copyright](https://www.openstreetmap.org/copyright)
and `data/LICENSE.md`. Public references for manual hours checks include 2GIS cards considered during research.
The general 2GIS button remains a name-and-city search. See
[opening-hours review](OPENING_HOURS_REVIEW.md) for the evidence ledger and gaps. The dataset contains public POI
locations and fixed landmark request boxes, never private user GPS or queries.
