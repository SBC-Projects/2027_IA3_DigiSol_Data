"""Turn the PLOS GPS file into a player-and-session dataset.

The published file has 780 rows and no player identifier. It is ordered as:

    training model -> position group -> acquisition day -> player -> week

Each player is five consecutive rows (weeks 1 to 5). There are 15 forwards
and 11 backs, and that same player order is repeated for every model and
acquisition day. This script keeps that order and assigns PLAYER_01 to
PLAYER_26.

Measurements are copied from the published file. Names, jersey numbers,
playing positions, device ids and session dates are fictional, for a
school-team scenario. They are not in the research data.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pone.0288345.s001 copy.csv"
DATA_DIR = ROOT / "data"
CSV_DIR = ROOT / "clean_modified"

TEAM_NAME = "Capricorn College"

# Model 1 is the paper's "specific endurance" morphocycle:
# strength Monday, endurance Wednesday, speed Thursday.
# Model 2 is "specific speed": strength Monday, endurance Tuesday, speed Thursday.
MODEL_START = {
    "1": date(2027, 2, 1),
    "2": date(2027, 4, 12),
}
DAY_OFFSET = {
    "1": {"Strength": 0, "Endurance": 2, "Speed": 3},
    "2": {"Strength": 0, "Endurance": 1, "Speed": 3},
}
MODEL_NAME = {"1": "Specific endurance", "2": "Specific speed"}
DAY_NAME = {"1": "Strength", "2": "Endurance", "3": "Speed"}
POSITION_GROUP = {"1": "Forward", "2": "Back"}

# Fictional school roster. The first 15 follow the file's forward order.
# The last 11 follow the file's back order. Playing position is not in the
# source file; only the forward/back group is.
ROSTER = [
    ("Jack", "Brennan", "Prop", 8),
    ("Tom", "Walsh", "Hooker", 9),
    ("Liam", "Harris", "Prop", 10),
    ("Noah", "Campbell", "Second-row", 11),
    ("Cooper", "Blake", "Second-row", 12),
    ("Mason", "Reid", "Lock", 13),
    ("Ethan", "Brooks", "Prop", 14),
    ("Harry", "Nguyen", "Hooker", 15),
    ("Joshua", "Kelly", "Prop", 16),
    ("Patrick", "Murray", "Second-row", 17),
    ("Sam", "Taylor", "Second-row", 18),
    ("Daniel", "Fraser", "Lock", 19),
    ("Ryan", "Mitchell", "Prop", 21),
    ("Caleb", "White", "Second-row", 22),
    ("Luke", "Edwards", "Lock", 24),
    ("Oliver", "Grant", "Fullback", 1),
    ("Finn", "Doyle", "Wing", 2),
    ("Archie", "Bennett", "Centre", 3),
    ("Charlie", "Hughes", "Centre", 4),
    ("Max", "Sullivan", "Wing", 5),
    ("Jake", "Robinson", "Five-eighth", 6),
    ("Henry", "Clarke", "Halfback", 7),
    ("Oscar", "Patel", "Wing", 20),
    ("William", "Foster", "Centre", 23),
    ("Thomas", "Riley", "Fullback", 25),
    ("George", "Palmer", "Five-eighth", 26),
]

MEASURES = [
    ("duration_min", "Duration", "min", "Session duration, from warm-up to the last drill."),
    ("player_load", "PlayerLoad", "AU", "Total accelerometer workload (PlayerLoad)."),
    ("player_load_slow", "PLSlow", "AU", "PlayerLoad accumulated below 2 m/s (7.2 km/h)."),
    ("distance_m", "Distance", "m", "Total distance."),
    ("avg_speed_m_per_min", "avg_vlo", "m/min", "Average speed. Multiplied by duration_min, this is within a few metres of total distance."),
    ("max_speed_kmh", "max_vlo", "km/h", "Maximum speed."),
    ("repeated_high_intensity_efforts", "RHIE", "count", "Repeated high-intensity efforts."),
    ("max_acceleration_ms2", "Max_Acc", "m/s^2", "Maximum acceleration."),
    ("max_deceleration_ms2", "Max_Dec", "m/s^2", "Maximum deceleration. Negative means slowing down."),
    ("accel_decel_over_2", "Tot_Acc_Dec2", "count", "Accelerations and decelerations above 2 m/s^2."),
    ("accel_decel_over_2_5", "Tot_Acc_Dec2.5", "count", "Accelerations and decelerations above 2.5 m/s^2."),
    ("distance_over_15_kmh_m", "Dis_15", "m", "Distance covered above 15 km/h (high-speed running)."),
    ("distance_over_21_kmh_m", "Dis_21", "m", "Distance covered above 21 km/h (very high-speed running)."),
    ("distance_over_25_kmh_m", "Dis_25", "m", "Distance covered above 25 km/h (sprint running)."),
]


def parse_number(raw: str):
    if "." not in raw:
        return int(raw)
    places = len(raw.split(".", 1)[1])
    return round(float(raw), places)


def load_source() -> list[dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 780:
        raise SystemExit(f"Expected 780 data rows, found {len(rows)}")
    return rows


def player_key(position_code: str, slot: int) -> str:
    number = slot + 1 if position_code == "1" else 15 + slot + 1
    return f"PLAYER_{number:02d}"


def assign_players(rows: list[dict[str, str]]) -> list[str]:
    """Return a player id for every source row."""
    next_slot: dict[tuple[str, str, str], int] = defaultdict(int)
    player_ids: list[str] = []

    if len(rows) % 5 != 0:
        raise SystemExit("Row count is not divisible by 5 weeks")

    for block_start in range(0, len(rows), 5):
        block = rows[block_start : block_start + 5]
        weeks = [row["Week"] for row in block]
        keys = {(row["Model"], row["Position"], row["Day"]) for row in block}
        if weeks != ["1", "2", "3", "4", "5"] or len(keys) != 1:
            raise SystemExit(f"Unexpected block at source row {block_start + 1}")

        model, position, day = block[0]["Model"], block[0]["Position"], block[0]["Day"]
        slot = next_slot[(model, position, day)]
        next_slot[(model, position, day)] += 1
        player_id = player_key(position, slot)
        player_ids.extend([player_id] * 5)

    expected_blocks = {
        ("1", "1", "1"): 15,
        ("1", "1", "2"): 15,
        ("1", "1", "3"): 15,
        ("1", "2", "1"): 11,
        ("1", "2", "2"): 11,
        ("1", "2", "3"): 11,
        ("2", "1", "1"): 15,
        ("2", "1", "2"): 15,
        ("2", "1", "3"): 15,
        ("2", "2", "1"): 11,
        ("2", "2", "2"): 11,
        ("2", "2", "3"): 11,
    }
    if dict(next_slot) != expected_blocks:
        raise SystemExit(f"Player blocks did not match 15 forwards and 11 backs: {dict(next_slot)}")

    return player_ids


def session_date(model: str, week: int, acquisition_day: str) -> date:
    start = MODEL_START[model]
    if start.weekday() != 0:
        raise SystemExit(f"Model {model} start {start} is not a Monday")
    week_start = start + timedelta(days=(week - 1) * 7)
    return week_start + timedelta(days=DAY_OFFSET[model][acquisition_day])


def build_players() -> list[dict]:
    players = []
    for index, (given, family, playing_position, jersey) in enumerate(ROSTER, start=1):
        group = "Forward" if index <= 15 else "Back"
        players.append(
            {
                "player_id": f"PLAYER_{index:02d}",
                "given_name": given,
                "family_name": family,
                "position_group": group,
                "playing_position": playing_position,
                "jersey_number": jersey,
                "device_id": f"GPS_{index:02d}",
            }
        )
    return players


def build_sessions(rows: list[dict[str, str]], player_ids: list[str], players: list[dict]) -> list[dict]:
    by_id = {player["player_id"]: player for player in players}
    drafted = []

    for index, (row, player_id) in enumerate(zip(rows, player_ids), start=1):
        player = by_id[player_id]
        if player["position_group"] != POSITION_GROUP[row["Position"]]:
            raise SystemExit(f"{player_id} position does not match source row {index}")

        acquisition_day = DAY_NAME[row["Day"]]
        model = row["Model"]
        week = int(row["Week"])
        played_on = session_date(model, week, acquisition_day)

        record = {
            "player_id": player_id,
            "given_name": player["given_name"],
            "family_name": player["family_name"],
            "position_group": player["position_group"],
            "playing_position": player["playing_position"],
            "jersey_number": player["jersey_number"],
            "device_id": player["device_id"],
            "training_model": int(model),
            "training_model_name": MODEL_NAME[model],
            "acquisition_day": acquisition_day,
            "week": week,
            "session_date": played_on.isoformat(),
            "source_row": index,
        }
        for field, source_column, _unit, _description in MEASURES:
            record[field] = parse_number(row[source_column])

        # Average speed times duration matches total distance within a few metres.
        # The published values are rounded, so the match is not exact.
        predicted_distance = record["duration_min"] * record["avg_speed_m_per_min"]
        if abs(predicted_distance - record["distance_m"]) > 20:
            raise SystemExit(
                f"Distance check failed at source row {index}: "
                f"{record['duration_min']} * {record['avg_speed_m_per_min']} != {record['distance_m']}"
            )
        drafted.append(record)

    session_keys = sorted({(row["session_date"], row["acquisition_day"], row["training_model"]) for row in drafted})
    session_ids = {key: f"SESSION_{number:03d}" for number, key in enumerate(session_keys, start=1)}

    for record in drafted:
        key = (record["session_date"], record["acquisition_day"], record["training_model"])
        record["session_id"] = session_ids[key]

    drafted.sort(key=lambda record: (record["session_date"], record["player_id"], record["source_row"]))
    for number, record in enumerate(drafted, start=1):
        record["record_id"] = f"REC_{number:04d}"

    return drafted


def ordered_session(record: dict) -> dict:
    preferred = [
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
    return {key: record[key] for key in preferred}


def write_csv(path: Path, records: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_meta(players: list[dict], sessions: list[dict]) -> dict:
    per_player = defaultdict(int)
    per_session = defaultdict(int)
    for record in sessions:
        per_player[record["player_id"]] += 1
        per_session[record["session_id"]] += 1
    if set(per_player.values()) != {30}:
        raise SystemExit("Every player should have 30 session records")
    if set(per_session.values()) != {26}:
        raise SystemExit("Every session should have 26 player records")

    return {
        "team": TEAM_NAME,
        "title": "School rugby training workload",
        "source": {
            "citation": "Hu X, Boisbluche S, Philippe K, Maurelli O, Ren X, Li S, et al. (2024) Position-specific workload of professional rugby union players during tactical periodization training. PLoS ONE 19(3): e0288345.",
            "url": "https://doi.org/10.1371/journal.pone.0288345",
            "licence": "CC BY 4.0",
            "file": SOURCE.name,
        },
        "what_is_measured": [
            {
                "field": field,
                "source_column": source_column,
                "unit": unit,
                "description": description,
            }
            for field, source_column, unit, description in MEASURES
        ],
        "what_is_fictional": [
            "player names",
            "player_id values",
            "playing_position and jersey_number",
            "device_id",
            "session_date, session_id and record_id",
            "the Capricorn College team name",
        ],
        "reconstruction": (
            "The published CSV has no player id. Rows are grouped by training model, "
            "position (1 = forward, 2 = back), acquisition day (1 = strength, 2 = endurance, "
            "3 = speed), then player, then week 1 to 5. The same 15 forwards and 11 backs "
            "appear in the same order in every block, so PLAYER_01 to PLAYER_26 stay stable. "
            "That player identity is reconstructed from the file order. It was not published "
            "by the researchers."
        ),
        "calendar": {
            "training_model_1": "Specific endurance. Five weeks from Monday 1 February 2027. Strength Monday, endurance Wednesday, speed Thursday.",
            "training_model_2": "Specific speed. Five weeks from Monday 12 April 2027. Strength Monday, endurance Tuesday, speed Thursday.",
        },
        "counts": {
            "players": len(players),
            "forwards": sum(1 for player in players if player["position_group"] == "Forward"),
            "backs": sum(1 for player in players if player["position_group"] == "Back"),
            "sessions": len(per_session),
            "records": len(sessions),
            "records_per_player": 30,
        },
    }


def main() -> None:
    rows = load_source()
    player_ids = assign_players(rows)
    players = build_players()
    sessions = [ordered_session(record) for record in build_sessions(rows, player_ids, players)]
    meta = build_meta(players, sessions)

    DATA_DIR.mkdir(exist_ok=True)
    CSV_DIR.mkdir(exist_ok=True)
    write_csv(CSV_DIR / "players.csv", players)
    write_csv(CSV_DIR / "sessions.csv", sessions)
    write_json(DATA_DIR / "players.json", players)
    write_json(DATA_DIR / "sessions.json", sessions)
    write_json(DATA_DIR / "meta.json", meta)

    print(f"Players:  {meta['counts']['players']} ({meta['counts']['forwards']} forwards, {meta['counts']['backs']} backs)")
    print(f"Sessions: {meta['counts']['sessions']}")
    print(f"Records:  {meta['counts']['records']}")
    print(f"CSV:      {CSV_DIR}")
    print(f"API JSON: {DATA_DIR}")


if __name__ == "__main__":
    main()
