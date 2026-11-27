import json
import hashlib
import sqlite3
from dataclasses import asdict, replace
from datetime import date, datetime
from pathlib import Path
from contextlib import closing

from fastapi.encoders import jsonable_encoder

from core.itinerary_validator import parse_itinerary
from core.trip_models import Itinerary, Place, TripRequest, WeatherSnapshot

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trips.db"
SCHEMA_VERSION = 1


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS saved_plans (
            plan_id TEXT PRIMARY KEY,
            schema_version INTEGER NOT NULL,
            itinerary_json TEXT NOT NULL,
            saved_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS travel_preferences (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            preferences_json TEXT NOT NULL
        )
    """)
    return connection


def save_itinerary(
    plan_id: str,
    itinerary: Itinerary,
    db_path: Path = DB_PATH,
) -> None:
    payload = json.dumps(
        jsonable_encoder(asdict(itinerary)),
        ensure_ascii=False,
    )
    now = datetime.now().astimezone().isoformat()

    with closing(_connect(db_path)) as connection:
        with connection:
            connection.execute("""
                INSERT INTO saved_plans
                    (plan_id, schema_version, itinerary_json, saved_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(plan_id) DO NOTHING
            """, (plan_id, SCHEMA_VERSION, payload, now, now))


def load_itinerary(
    plan_id: str,
    db_path: Path = DB_PATH,
) -> Itinerary | None:
    with closing(_connect(db_path)) as connection:
        with connection:
            row = connection.execute(
                "SELECT schema_version, itinerary_json "
                "FROM saved_plans WHERE plan_id = ?",
                (plan_id,),
            ).fetchone()

    if row is None:
        return None

    version, raw = row
    if version != SCHEMA_VERSION:
        raise ValueError(f"不支持的行程数据版本：{version}")

    data = json.loads(raw)
    request_data = data["request"]
    request = TripRequest(
        destination=request_data["destination"],
        start_date=date.fromisoformat(request_data["start_date"]),
        days=request_data["days"],
        travelers=request_data["travelers"],
        budget_cny=request_data["budget_cny"],
        preferences=request_data["preferences"],
    )
    places = [
        Place(
            place_id=item["place_id"],
            name=item["name"],
            address=item["address"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            source=item["source"],
            queried_at=datetime.fromisoformat(item["queried_at"]),
            citycode=item.get("citycode"),
        )
        for item in data["places"]
    ]
    weather = [
        WeatherSnapshot(
            forecast_date=date.fromisoformat(item["weather"]["forecast_date"]),
            condition=item["weather"]["condition"],
            min_temp_c=item["weather"]["min_temp_c"],
            max_temp_c=item["weather"]["max_temp_c"],
            available=item["weather"]["available"],
            source=item["weather"]["source"],
            queried_at=datetime.fromisoformat(item["weather"]["queried_at"]),
        )
        for item in data["daily_plans"]
    ]
    validated = parse_itinerary(
        json.dumps({
            "daily_plans": data["daily_plans"],
            "estimated_total_cny": data["estimated_total_cny"],
        }, ensure_ascii=False),
        request,
        places,
        weather,
        restore_routes=True,
    )
    return replace(
        validated,
        generated_at=datetime.fromisoformat(data["generated_at"]),
        web_evidence=data.get("web_evidence", ""),
    )

def list_saved_plans(db_path: Path = DB_PATH) -> list[dict]:
    with closing(_connect(db_path)) as connection:
        rows = connection.execute(
            "SELECT plan_id, schema_version, itinerary_json, saved_at "
            "FROM saved_plans ORDER BY saved_at DESC, plan_id DESC"
        ).fetchall()

    plans = []
    for plan_id, version, raw, saved_at in rows:
        if version != SCHEMA_VERSION:
            raise ValueError(f"不支持的行程数据版本：{version}")

        data = json.loads(raw)
        request = data["request"]
        plans.append({
            "plan_id": plan_id,
            "destination": request["destination"],
            "start_date": request["start_date"],
            "days": request["days"],
            "generated_at": data["generated_at"],
            "saved_at": saved_at,
        })
    return plans


def update_itinerary(
    plan_id: str,
    itinerary: Itinerary,
    db_path: Path = DB_PATH,
) -> bool:
    payload = json.dumps(jsonable_encoder(asdict(itinerary)), ensure_ascii=False)
    now = datetime.now().astimezone().isoformat()

    with closing(_connect(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                "UPDATE saved_plans "
                "SET itinerary_json = ?, updated_at = ? "
                "WHERE plan_id = ? AND schema_version = ?",
                (payload, now, plan_id, SCHEMA_VERSION),
            )
            return cursor.rowcount == 1


def itinerary_fingerprint(itinerary: Itinerary) -> str:
    payload = json.dumps(jsonable_encoder(asdict(itinerary)), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def update_itinerary_if_unchanged(
    plan_id: str, itinerary: Itinerary, expected_fingerprint: str, db_path: Path = DB_PATH,
) -> bool:
    """在同一事务内核对旧记录并写入，避免确认期间覆盖其他编辑。"""
    payload = json.dumps(jsonable_encoder(asdict(itinerary)), ensure_ascii=False)
    now = datetime.now().astimezone().isoformat()
    with closing(_connect(db_path)) as connection:
        with connection:
            row = connection.execute(
                "SELECT itinerary_json FROM saved_plans WHERE plan_id = ? AND schema_version = ?",
                (plan_id, SCHEMA_VERSION),
            ).fetchone()
            if row is None:
                return False
            current = json.dumps(json.loads(row[0]), ensure_ascii=False, sort_keys=True)
            if hashlib.sha256(current.encode("utf-8")).hexdigest() != expected_fingerprint:
                return False
            cursor = connection.execute(
                "UPDATE saved_plans SET itinerary_json = ?, updated_at = ? WHERE plan_id = ? AND itinerary_json = ?",
                (payload, now, plan_id, row[0]),
            )
            return cursor.rowcount == 1


def delete_itinerary(plan_id: str, db_path: Path = DB_PATH) -> bool:
    """按 ID 删除一条已保存行程；不存在时返回 False。"""
    with closing(_connect(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                "DELETE FROM saved_plans WHERE plan_id = ?",
                (plan_id,),
            )
            return cursor.rowcount == 1


def load_preferences(db_path: Path = DB_PATH) -> list[str]:
    with closing(_connect(db_path)) as connection:
        row = connection.execute(
            "SELECT preferences_json FROM travel_preferences WHERE id = 1"
        ).fetchone()
    return json.loads(row[0]) if row else []


def save_preferences(
    preferences: list[str],
    db_path: Path = DB_PATH,
) -> list[str]:
    cleaned = [item.strip() for item in preferences]
    if len(cleaned) > 20 or any(not item or len(item) > 100 for item in cleaned):
        raise ValueError("偏好最多 20 项，每项须为 1–100 个字符")

    with closing(_connect(db_path)) as connection:
        with connection:
            connection.execute(
                "INSERT INTO travel_preferences (id, preferences_json) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET preferences_json = excluded.preferences_json",
                (json.dumps(cleaned, ensure_ascii=False),),
            )
    return cleaned
