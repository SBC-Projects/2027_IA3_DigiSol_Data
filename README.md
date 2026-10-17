# Capricorn College Sports Performance Integrity API

Teacher-hosted data and REST API for the 2027 Digital Solutions IA3.

Capricorn College is a fictional rugby squad. GPS measurements come from a published study. Player names, jersey numbers, devices and 2027 dates were added for the school scenario.

**Live API:** [https://2027-ia-3-digi-sol-data.vercel.app](https://2027-ia-3-digi-sol-data.vercel.app)

Use the **untrusted** `/dirty` feed as the exchanged session data. Compare it with the trusted hashes. The clean feed is the original rebuilt dataset.

## Folders

| Folder | What it is |
|---|---|
| `data_original/` | Published PLOS GPS CSV. No player IDs. |
| `data_modified_clean/` | Rebuilt trusted dataset: 26 players, 30 sessions, 780 records. |
| `data_modified_dirty/` | Same data after 24 planted problems: 783 session rows. |
| `planted_problems/` | List of the 24 changes and how they should be detected. |
| `scripts/` | Rebuilds the clean and dirty files from the original CSV. |

Each modified folder has CSV and JSON. Integrity hashes sit in both clean and dirty folders. They were calculated from the **clean** records.

## Counts

- 26 players (15 forwards, 11 backs)
- 30 training sessions across two 5-week models
- 30 records per player in the clean file
- Dirty file: 21 changed records plus 3 duplicate rows

## API

Replace the host with `http://localhost:3000` when running locally.

### Untrusted feed (students)

| Request | Purpose |
|---|---|
| `GET /dirty` | Endpoint list |
| `GET /dirty/api/meta` | Field definitions, units, hash recipe |
| `GET /dirty/api/players` | Roster and registered GPS devices |
| `GET /dirty/api/players/PLAYER_01` | One player |
| `GET /dirty/api/sessions` | Session records (default 50 per page) |
| `GET /dirty/api/sessions/REC_0001` | One record |
| `GET /dirty/api/integrity` | Trusted hashes (large if you omit `limit`) |
| `GET /dirty/api/integrity/REC_0001` | Hashes for one record, including each field |
| `GET /dirty/sessions.csv` | Download untrusted sessions |
| `GET /dirty/integrity.csv` | Download record hashes |
| `GET /dirty/integrity_fields.csv` | Download per-field hashes |

### Trusted feed

Same routes without `/dirty`, for example `GET /api/sessions` and `GET /integrity.csv`. Clean sessions have 780 rows. Dirty sessions have 783.

### Session filters

`player_id`, `session_id`, `position_group`, `playing_position`, `acquisition_day`, `training_model` (1 or 2), `week`, `jersey_number`, `device_id`, `date`, `date_from`, `date_to`

Paging: `page` (from 1) and `limit`. Dirty maximum `limit` is 783.

Examples:

```
https://2027-ia-3-digi-sol-data.vercel.app/dirty/api/sessions?player_id=PLAYER_01&limit=30
https://2027-ia-3-digi-sol-data.vercel.app/dirty/api/sessions?position_group=backs&acquisition_day=strength
https://2027-ia-3-digi-sol-data.vercel.app/dirty/api/integrity/REC_0001
```

## Integrity hashes

Hashes are SHA-256 of UTF-8 text, shown as lowercase hex. They are **not** stored on the session records. Fetch them from `/dirty/api/integrity`.

1. Convert each field to a string. Use the JSON number text from the API.
2. Treat JSON `null` or an empty CSV cell as `""`.
3. Join with `|` (no spaces).
4. Hash the UTF-8 bytes.

### Record hashes

| Hash | Fields |
|---|---|
| `identity_hash` | `record_id`, `player_id`, `session_id`, `session_date`, `device_id` |
| `performance_hash` | duration, PlayerLoad, distances, speeds, accelerations |
| `all_data_hash` | every field in the record, including `source_row` |

Worked identity example for the **original** `REC_0001`:

```
REC_0001|PLAYER_01|SESSION_001|2027-02-01|GPS_01
```

SHA-256: `2f7a7146d47d339edff59cdd5885d232d6d72d075d894a788543a74fda6b84f7`

### Field hashes

To see **which value** changed, hash:

```
record_id|field_name|value
```

Original distance for `REC_0001`:

```
REC_0001|distance_m|3604.04182
```

SHA-256: `596f1cf09e761b0ecb35e3df93201a262c48991cb6023efa79e43b4c09a1aa4a`

The dirty record has `distance_m` of `4604.04182`, so that field hash fails. Other fields on that row still match.

Duplicates still match every hash. Find them by counting `player_id` + `session_id` (or `record_id`).

JavaScript outline:

```js
function canonical(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return JSON.stringify(value);
  return String(value);
}

function payload(record, fields) {
  return fields.map((field) => canonical(record[field])).join("|");
}

async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}
```

## Other checks

These are useful besides hashing:

- `device_id` should match the device on that player in the roster
- `distance_over_25_kmh_m` ≤ `distance_over_21_kmh_m` ≤ `distance_over_15_kmh_m` ≤ `distance_m`
- `player_load_slow` ≤ `player_load`
- `accel_decel_over_2_5` ≤ `accel_decel_over_2`
- `distance_m / duration_min` should match `avg_speed_m_per_min` within **0.5 m/min** (the published averages are slightly rounded)
- each `player_id` and `session_id` pair should appear once

## Planted problems

24 problems in the dirty feed:

| Type | Count |
|---|---|
| Altered measurement | 10 |
| Wrong GPS device | 4 |
| Logical inconsistency | 4 |
| Missing value | 3 |
| Duplicate / replayed record | 3 |

Details are in `planted_problems/planted_problems.csv`.

## Run locally

```bash
npm install
npm start
```

API: [http://localhost:3000](http://localhost:3000)  
Dirty feed: [http://localhost:3000/dirty](http://localhost:3000/dirty)

Rebuild datasets (Python 3):

```bash
npm run build-data
```

## Source

GPS measurements: Hu et al. (2024), *PLOS ONE*, [https://doi.org/10.1371/journal.pone.0288345](https://doi.org/10.1371/journal.pone.0288345), CC BY 4.0.

The published file has no player identifier. Rows are ordered by training model, position group, acquisition day, then five weeks per player. `PLAYER_01` to `PLAYER_26` follow that order. Names, playing positions, jerseys, devices and dates are fictional.
