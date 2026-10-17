"""Shared SHA-256 recipe for the IA3 integrity hashes."""

from __future__ import annotations

import hashlib
import json

SEPARATOR = "|"

IDENTITY_FIELDS = [
    "record_id",
    "player_id",
    "session_id",
    "session_date",
    "device_id",
]

PERFORMANCE_FIELDS = [
    "duration_min",
    "player_load",
    "player_load_slow",
    "distance_m",
    "avg_speed_m_per_min",
    "max_speed_kmh",
    "repeated_high_intensity_efforts",
    "max_acceleration_ms2",
    "max_deceleration_ms2",
    "accel_decel_over_2",
    "accel_decel_over_2_5",
    "distance_over_15_kmh_m",
    "distance_over_21_kmh_m",
    "distance_over_25_kmh_m",
]

ALL_DATA_FIELDS = [
    "record_id",
    "session_id",
    "session_date",
    "player_id",
    "given_name",
    "family_name",
    "position_group",
    "playing_position",
    "jersey_number",
    "device_id",
    "training_model",
    "training_model_name",
    "acquisition_day",
    "week",
    "duration_min",
    "player_load",
    "player_load_slow",
    "distance_m",
    "avg_speed_m_per_min",
    "max_speed_kmh",
    "repeated_high_intensity_efforts",
    "max_acceleration_ms2",
    "max_deceleration_ms2",
    "accel_decel_over_2",
    "accel_decel_over_2_5",
    "distance_over_15_kmh_m",
    "distance_over_21_kmh_m",
    "distance_over_25_kmh_m",
    "source_row",
]


def canonical(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return json.dumps(value)
    return str(value)


def payload(record: dict, fields: list[str]) -> str:
    return SEPARATOR.join(canonical(record[field]) for field in fields)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def field_payload(record: dict, field: str) -> str:
    return SEPARATOR.join(
        [
            canonical(record["record_id"]),
            field,
            canonical(record[field]),
        ]
    )


def field_hashes_for(record: dict) -> dict[str, str]:
    return {field: sha256_hex(field_payload(record, field)) for field in ALL_DATA_FIELDS}


def hashes_for(record: dict) -> dict:
    identity = payload(record, IDENTITY_FIELDS)
    performance = payload(record, PERFORMANCE_FIELDS)
    all_data = payload(record, ALL_DATA_FIELDS)
    return {
        "record_id": record["record_id"],
        "identity_hash": sha256_hex(identity),
        "performance_hash": sha256_hex(performance),
        "all_data_hash": sha256_hex(all_data),
        "field_hashes": field_hashes_for(record),
    }


def recipe(example_record: dict) -> dict:
    identity = payload(example_record, IDENTITY_FIELDS)
    distance = field_payload(example_record, "distance_m")
    return {
        "algorithm": "SHA-256",
        "encoding": "utf-8",
        "digest": "lowercase hex",
        "separator": SEPARATOR,
        "missing_value": "",
        "identity_fields": IDENTITY_FIELDS,
        "performance_fields": PERFORMANCE_FIELDS,
        "all_data_fields": ALL_DATA_FIELDS,
        "field_hash_fields": ALL_DATA_FIELDS,
        "how_to_hash": (
            "Record hashes: convert each listed field to a string, in that order. "
            "Use the JSON number text returned by the API. Treat JSON null or an empty "
            "CSV cell as an empty string. Join the strings with | and hash the UTF-8 "
            "bytes with SHA-256."
        ),
        "how_to_hash_field": (
            "Field hashes: SHA-256 of record_id|field_name|value, using the same string "
            "rules. Compare each field with field_hashes in /api/integrity. A mismatch "
            "names the value that changed. Duplicates still match every hash; find those "
            "by counting player_id and session_id pairs."
        ),
        "example": {
            "record_id": example_record["record_id"],
            "identity_payload": identity,
            "identity_hash": sha256_hex(identity),
            "field": "distance_m",
            "field_payload": distance,
            "field_hash": sha256_hex(distance),
        },
    }
