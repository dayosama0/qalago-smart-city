# POI enrichment: public-source desk review

Six existing OSM records received short, original Russian descriptions following
a desk review on **19 October 2026**. Two published schedules also received
field-level references. This is **not a site visit, a telephone confirmation,
or verification that a place is open now**. `checked_at` records the day of
research; it is not the page publication date or an on-site inspection date.

No records, names, coordinates, categories or original OSM tags were added or
replaced. The source snapshots and their metadata remain byte-for-byte
unchanged. `description_source` identifies the relevant public page, while
`verified_fields_json` stores that field's `evidence_url`, `checked_at`, and
`method=manual_reference`. Here this method means review of published evidence,
not confirmation by a QalaGo field team.

## Accepted evidence

| Existing OSM key | Place | Fields | Primary source and narrow factual support |
| --- | --- | --- | --- |
| `osm:way:499328514` | MEGA Silk Way | Description; listed hours `Mo-Su 10:00-22:00` | [MEGA operator page](https://mega.kz/Tenant/MEGA-Silk-Way) identifies the Astana mall at Kabanbay Batyr 62, names its cinema and ice-rink facilities, and publishes 10:00–22:00 hours. The hours match the original OSM value. |
| `osm:way:230401645` | Baiterek | Description | [Astana Venue Management's monument page](https://a-vm.kz/en/objects/bayterek/) supports the Tree of Life architectural theme, Nurjol address, and named Ayaly Alaqan/Bata compositions. |
| `osm:way:108096984` | Keruen | Description; listed hours `Mo-Su 10:00-24:00` | [Keruen operator's About page](https://www.keruen.kz/o_kompanii?language=ru) identifies its location near Baiterek on Nurjol, its Silk Road design concept, and daily 10:00–24:00 mall schedule. Individual tenants may differ. |
| `osm:way:240376692` | Saken Seifullin Museum | Description | [City museum directorate's media archive](https://astanamuseums.kz/media) contains institutional accounts of learning about the poet's life and work and the museum's cultural and educational activities. The existing name identifies the same museum. |
| `osm:node:4916363251` | E. Rakhmadiev State Academic Philharmonic | Description | [Institution's archived season announcement](https://astana-filarmonia.kz/afyshalar/417-zha-a-xxvii-kontserttik-mausymyny-ashyluy) names the philharmonic, classical repertoire and its concert hall at Kenesary 32. The historical announcement establishes the institution/venue; it is not presented as an upcoming concert. |
| `osm:way:1239177393` | Atyrau pedestrian bridge in Astana | Description | [Astana city government's infrastructure inventory](https://www.gov.kz/org/astana/press/article/details/17863) lists the pedestrian Atyrau bridge to the amphitheatre. The page was last updated in 2020, so it supports identity/type, not current access or operating conditions. |

Descriptions paraphrase only a few basic facts. No operator marketing claims,
ranking claims, prices, visitor totals, commercial directory text, or 2GIS
records were copied. The OSM object remains the source for the map location.

The review used primary web pages and indexed primary-source content. Some
operator pages, notably the museum website, intermittently timed out or returned
502 when fetched directly; indexed institution material was readable. This is
documented as desk evidence rather than a successful live connection to every
operator. Public pages may change; recheck the linked source before treating
these attributes as current operational information.

## Deliberately unconfirmed fields and rejected sources

- **Power outlets:** all 199 records remain `unknown`; no public evidence in
  this review established visitor power-outlet access.
- **Wi-Fi:** no override. Keruen's operator mentions Wi-Fi specifically on its
  third-floor food court. The current schema cannot express that limited
  coverage, so this was not promoted to a venue-wide confirmed feature.
- **Indoor status, heating, accessibility and safe routes:** unchanged. A
  cultural or commercial category does not prove protected access or heating.
- **Baiterek hours:** the operator publishes summer and winter periods. These
  seasonal expressions were not flattened into an all-year schedule. The
  original unknown hours remain unknown in this dataset.
- **Museum hours:** the directorate distinguishes exhibition hours from the
  earlier cash-desk closing time. No simplified hours override was introduced;
  ticket entry and current opening remain unconfirmed.
- **Atyrau bridge:** [Visit Astana's similarly named page](https://visitastana.kz/ru/about-city/what-to-see/atyrauskiy-most/)
  describes the Ural river and the city of Atyrau. Its geography does not match
  this Astana OSM record. It was rejected, including its advertised 24/7 hours.
- **Museum of the First President:** the source snapshot's institution naming
  and building may be stale. No unsupported operational description or hours
  were added for that record in this review.
- **Airport POIs:** no claims about landside/airside access or boarding
  suitability were added.

## Rebuild and measured result

```bash
python -m ingestion.build_database --offline
python -m pytest tests/test_ingestion.py tests/test_enrichment.py tests/test_cloud.py -q
```

The rebuild applies **8 overrides to 6 existing POIs**, retains **199 records**,
and produces **6 descriptions** and **81 listed schedules** (one new schedule
for Keruen and one referenced, unchanged OSM schedule for MEGA). There remain
**0 confirmed outlet overrides** and **0 confirmed indoor overrides**. Current
database/source hashes and actual build time are in `data/pois.manifest.json`.

The original source hashes stay unchanged:

- `astana.json`: `fb45c09f37c7d97da322fdd631d873dffaab5be2b73eb1a576c6e43f7de079b4`
- `airport.json`: `dd4fe276faa43c16f094f6ed3d53cfd260c1ec5a5ba8ed050327d501d0fd43bd`

Data attribution and [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
remain applicable as described in `data/LICENSE.md` and
`docs/DATA_PROVENANCE.md`.
