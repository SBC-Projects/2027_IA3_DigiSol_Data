"""Build the untrusted session feed, trusted hashes, and teacher problem list."""

from __future__ import annotations

import csv
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hashing import ALL_DATA_FIELDS, hashes_for, recipe  # noqa: E402

CLEAN_DIR = ROOT / "data"
DIRTY_DIR = ROOT / "dirty_modified"
TEACHER_DIR = ROOT / "teacher"

# 21 changed records plus 3 appended copies. Hashes are always taken from the
# clean record before these edits.
PROBLEMS = [
    {
        "problem_id": "A01",
        "type": "altered_measurement",
        "record_id": "REC_0001",
        "field": "distance_m",
        "new_value": 4604.04182,
        "intended_detection": "performance_hash and all_data_hash mismatch; average-speed inconsistency",
    },
    {
        "problem_id": "A02",
        "type": "altered_measurement",
        "record_id": "REC_0027",
        "field": "player_load",
        "new_value": 605.12,
        "intended_detection": "performance_hash and all_data_hash mismatch",
    },
    {
        "problem_id": "A03",
        "type": "altered_measurement",
        "record_id": "REC_0104",
        "field": "max_speed_kmh",
        "new_value": 42.51,
        "intended_detection": "performance_hash and all_data_hash mismatch",
    },
    {
        "problem_id": "A04",
        "type": "altered_measurement",
        "record_id": "REC_0156",
        "field": "duration_min",
        "new_value": 54.9,
        "intended_detection": "performance_hash and all_data_hash mismatch; average-speed inconsistency",
    },
    {
        "problem_id": "A05",
        "type": "altered_measurement",
        "record_id": "REC_0400",
        "field": "distance_m",
        "new_value": 2042.68,
        "intended_detection": "performance_hash and all_data_hash mismatch; average-speed inconsistency",
    },
    {
        "problem_id": "A06",
        "type": "altered_measurement",
        "record_id": "REC_0450",
        "field": "repeated_high_intensity_efforts",
        "new_value": 35,
        "intended_detection": "performance_hash and all_data_hash mismatch",
    },
    {
        "problem_id": "A07",
        "type": "altered_measurement",
        "record_id": "REC_0500",
        "field": "max_acceleration_ms2",
        "new_value": 9.51,
        "intended_detection": "performance_hash and all_data_hash mismatch",
    },
    {
        "problem_id": "A08",
        "type": "altered_measurement",
        "record_id": "REC_0600",
        "field": "player_load_slow",
        "new_value": 200.25,
        "intended_detection": "performance_hash and all_data_hash mismatch",
    },
    {
        "problem_id": "A09",
        "type": "altered_measurement",
        "record_id": "REC_0700",
        "field": "avg_speed_m_per_min",
        "new_value": 110.25,
        "intended_detection": "performance_hash and all_data_hash mismatch; average-speed inconsistency",
    },
    {
        "problem_id": "A10",
        "type": "altered_measurement",
        "record_id": "REC_0740",
        "field": "accel_decel_over_2",
        "new_value": 180,
        "intended_detection": "performance_hash and all_data_hash mismatch",
    },
    {
        "problem_id": "D01",
        "type": "incorrect_device",
        "record_id": "REC_0002",
        "field": "device_id",
        "new_value": "GPS_17",
        "intended_detection": "identity_hash and all_data_hash mismatch; device does not match players.csv",
    },
    {
        "problem_id": "D02",
        "type": "incorrect_device",
        "record_id": "REC_0130",
        "field": "device_id",
        "new_value": "GPS_01",
        "intended_detection": "identity_hash and all_data_hash mismatch; device does not match players.csv",
    },
    {
        "problem_id": "D03",
        "type": "incorrect_device",
        "record_id": "REC_0550",
        "field": "device_id",
        "new_value": "GPS_22",
        "intended_detection": "identity_hash and all_data_hash mismatch; device does not match players.csv",
    },
    {
        "problem_id": "D04",
        "type": "incorrect_device",
        "record_id": "REC_0650",
        "field": "device_id",
        "new_value": "GPS_09",
        "intended_detection": "identity_hash and all_data_hash mismatch; device does not match players.csv",
    },
    {
        "problem_id": "L01",
        "type": "logical_inconsistency",
        "record_id": "REC_0003",
        "field": "distance_over_21_kmh_m",
        "new_value": 500.5,
        "intended_detection": "performance_hash mismatch; distance over 21 km/h exceeds distance over 15 km/h",
    },
    {
        "problem_id": "L02",
        "type": "logical_inconsistency",
        "record_id": "REC_0182",
        "field": "player_load_slow",
        "new_value": 650.5,
        "intended_detection": "performance_hash mismatch; player_load_slow exceeds player_load",
    },
    {
        "problem_id": "L03",
        "type": "logical_inconsistency",
        "record_id": "REC_0234",
        "field": "accel_decel_over_2_5",
        "new_value": 90,
        "intended_detection": "performance_hash mismatch; accel_decel_over_2_5 exceeds accel_decel_over_2",
    },
    {
        "problem_id": "L04",
        "type": "logical_inconsistency",
        "record_id": "REC_0338",
        "field": "distance_over_25_kmh_m",
        "new_value": 200.5,
        "intended_detection": "performance_hash mismatch; distance over 25 km/h exceeds distance over 21 km/h",
    },
    {
        "problem_id": "M01",
        "type": "missing_measurement",
        "record_id": "REC_0005",
        "field": "player_load_slow",
        "new_value": None,
        "intended_detection": "performance_hash mismatch; missing player_load_slow",
    },
    {
        "problem_id": "M02",
        "type": "missing_measurement",
        "record_id": "REC_0390",
        "field": "distance_m",
        "new_value": None,
        "intended_detection": "performance_hash mismatch; missing distance_m",
    },
    {
        "problem_id": "M03",
        "type": "missing_measurement",
        "record_id": "REC_0572",
        "field": "player_load",
        "new_value": None,
        "intended_detection": "performance_hash mismatch; missing player_load",
    },
    {
        "problem_id": "R01",
        "type": "duplicate_record",
        "record_id": "REC_0004",
        "field": "",
        "new_value": "appended copy",
        "intended_detection": "player_id and session_id appear twice; record_id appears twice",
    },
    {
        "problem_id": "R02",
        "type": "duplicate_record",
        "record_id": "REC_0208",
        "field": "",
        "new_value": "appended copy",
        "intended_detection": "player_id and session_id appear twice; record_id appears twice",
    },
    {
        "problem_id": "R03",
        "type": "duplicate_record",
        "record_id": "REC_0780",
        "field": "",
        "new_value": "appended copy",
        "intended_detection": "player_id and session_id appear twice; record_id appears twice",
    },
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, records: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def display(value) -> str:
    if value is None:
        return ""
    return json.dumps(value) if isinstance(value, float) else str(value)


def main() -> None:
    players = load_json(CLEAN_DIR / "players.json")
    clean_sessions = load_json(CLEAN_DIR / "sessions.json")
    clean_meta = load_json(CLEAN_DIR / "meta.json")
    by_id = {record["record_id"]: record for record in clean_sessions}

    problem_ids = [item["record_id"] for item in PROBLEMS]
    if len(problem_ids) != 24 or len(set(problem_ids)) != 24:
        raise SystemExit("Expected 24 problems on 24 different records")
    missing = [record_id for record_id in problem_ids if record_id not in by_id]
    if missing:
        raise SystemExit(f"Unknown record ids: {missing}")

    trusted = [hashes_for(record) for record in clean_sessions]
    hash_recipe = recipe(by_id["REC_0001"])

    dirty = deepcopy(clean_sessions)
    dirty_by_id = {record["record_id"]: record for record in dirty}
    teacher_rows = []

    for problem in PROBLEMS:
        original = by_id[problem["record_id"]]
        if problem["type"] == "duplicate_record":
            dirty.append(deepcopy(dirty_by_id[problem["record_id"]]))
            teacher_rows.append(
                {
                    "problem_id": problem["problem_id"],
                    "type": problem["type"],
                    "record_id": problem["record_id"],
                    "player_id": original["player_id"],
                    "session_id": original["session_id"],
                    "session_date": original["session_date"],
                    "field": "entire record",
                    "original_value": "unmodified",
                    "new_value": "identical copy appended",
                    "intended_detection": problem["intended_detection"],
                }
            )
            continue

        field = problem["field"]
        dirty_by_id[problem["record_id"]][field] = problem["new_value"]
        teacher_rows.append(
            {
                "problem_id": problem["problem_id"],
                "type": problem["type"],
                "record_id": problem["record_id"],
                "player_id": original["player_id"],
                "session_id": original["session_id"],
                "session_date": original["session_date"],
                "field": field,
                "original_value": display(original[field]),
                "new_value": display(problem["new_value"]),
                "intended_detection": problem["intended_detection"],
            }
        )

    if len(dirty) != 783:
        raise SystemExit(f"Expected 783 dirty rows, found {len(dirty)}")

    dirty_meta = {
        **clean_meta,
        "dataset": "untrusted",
        "title": "School rugby training workload — untrusted exchange",
        "warning": (
            "These session records are the exchanged feed. Some values have been "
            "changed, left empty or repeated. Check them against /dirty/api/integrity "
            "and the player roster. Do not treat a hash stored next to a record as proof."
        ),
        "hash": hash_recipe,
        "validation_hints": [
            "device_id should match the registered device in the player roster",
            "distance_over_25_kmh_m <= distance_over_21_kmh_m <= distance_over_15_kmh_m <= distance_m",
            "player_load_slow <= player_load",
            "accel_decel_over_2_5 <= accel_decel_over_2",
            "distance_m / duration_min should match avg_speed_m_per_min within 0.5 m/min",
            "each player_id and session_id pair should appear once",
        ],
        "counts": {
            **clean_meta["counts"],
            "records": len(dirty),
            "trusted_hashes": len(trusted),
        },
    }

    integrity = {
        **hash_recipe,
        "total": len(trusted),
        "results": trusted,
    }

    DIRTY_DIR.mkdir(exist_ok=True)
    TEACHER_DIR.mkdir(exist_ok=True)

    write_json(DIRTY_DIR / "players.json", players)
    write_json(DIRTY_DIR / "sessions.json", dirty)
    write_json(DIRTY_DIR / "meta.json", dirty_meta)
    write_json(DIRTY_DIR / "integrity.json", integrity)
    write_json(CLEAN_DIR / "integrity.json", integrity)

    write_csv(DIRTY_DIR / "players.csv", players, list(players[0].keys()))
    write_csv(DIRTY_DIR / "sessions.csv", dirty, ALL_DATA_FIELDS)
    write_csv(
        DIRTY_DIR / "integrity.csv",
        trusted,
        ["record_id", "identity_hash", "performance_hash", "all_data_hash"],
    )
    field_rows = [
        {
            "record_id": row["record_id"],
            "field": field,
            "field_hash": digest,
        }
        for row in trusted
        for field, digest in row["field_hashes"].items()
    ]
    write_csv(
        DIRTY_DIR / "integrity_fields.csv",
        field_rows,
        ["record_id", "field", "field_hash"],
    )
    write_csv(
        TEACHER_DIR / "planted_problems.csv",
        teacher_rows,
        [
            "problem_id",
            "type",
            "record_id",
            "player_id",
            "session_id",
            "session_date",
            "field",
            "original_value",
            "new_value",
            "intended_detection",
        ],
    )
    write_json(TEACHER_DIR / "planted_problems.json", teacher_rows)

    print(f"Dirty records: {len(dirty)}")
    print(f"Trusted hashes: {len(trusted)}")
    print(f"Problems: {len(teacher_rows)}")
    print(f"Wrote {DIRTY_DIR}")
    print(f"Teacher key: {TEACHER_DIR / 'planted_problems.csv'}")


if __name__ == "__main__":
    main()
