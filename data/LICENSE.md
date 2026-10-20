# OpenStreetMap data license

The OpenStreetMap-derived data in `pois.db`, `snapshots/*.json`, and their metadata
are © OpenStreetMap contributors and distributed under the
[Open Data Commons Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
This notice applies to the data, independently of the application code license.

Source and attribution: [OpenStreetMap copyright and license](https://www.openstreetmap.org/copyright).
The derived database removes contact information and contributor metadata,
selects relevant categories and named records, and calculates approximate points
for complete way/multipolygon geometry. See `docs/DATA_PROVENANCE.md` and the
snapshot metadata for source URLs, retrieval times, scope, and transformations.

Preserve attribution and the ODbL notice when redistributing these data. A public
derived database must comply with the ODbL attribution and share-alike terms.
There are no manually invented POIs or private user locations in this snapshot.

The supplemental `2gis:*` records originate from public 2GIS organization cards
and separately cited official venue pages, not from OpenStreetMap. Their field
sources and access dates are recorded in `curated_places.json`. This OSM notice
does not assign an OSM license to those external sources. See
`docs/DATA_EXPANSION_2026-10-20.md` for the exact references.

Additional hours and closure facts from public venue pages, 2GIS, Yandex Maps,
Visit Astana and directories are attributed individually in `manual_overrides.csv`,
`hours_review.tsv`, `hours_gap_review_2026-10-20.json` and
`hours_followup_2026-10-20.json`. The OSM notice above
does not assign an OSM license to those external source pages.
