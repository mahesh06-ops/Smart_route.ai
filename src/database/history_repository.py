"""
Repository for saving, querying, and deleting route search history in SQLite.
"""
import json
from typing import List, Optional, Dict, Any
from src.database.database import get_db_connection
from src.database.models import HistoryEntry
from src.utils.logging_config import logger


class HistoryRepository:
    @staticmethod
    def save_history(entry: Dict[str, Any]) -> int:
        """Inserts a new route search history record."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO route_history (
                    source, destination, source_coords, destination_coords,
                    vehicle_type, preference, emergency_mode, recommended_route_id,
                    distance_km, duration_minutes, smart_score, fuel_liters,
                    fuel_cost, summary, full_result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.get("source"),
                entry.get("destination"),
                entry.get("source_coords", ""),
                entry.get("destination_coords", ""),
                entry.get("vehicle_type", "car"),
                entry.get("preference", "balanced"),
                1 if entry.get("emergency_mode") else 0,
                entry.get("recommended_route_id", "Route 1"),
                round(float(entry.get("distance_km", 0.0)), 2),
                round(float(entry.get("duration_minutes", 0.0)), 1),
                round(float(entry.get("smart_score", 0.0)), 1),
                round(float(entry.get("fuel_liters", 0.0)), 2),
                round(float(entry.get("fuel_cost", 0.0)), 2),
                entry.get("summary", ""),
                json.dumps(entry.get("full_result", {}))
            ))
            row_id = cursor.lastrowid
            logger.info(f"Saved route history ID: {row_id} ({entry.get('source')} -> {entry.get('destination')})")
            return row_id

    @staticmethod
    def get_all(limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves history entries ordered by newest first."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, source, destination, source_coords, destination_coords,
                       vehicle_type, preference, emergency_mode, recommended_route_id,
                       distance_km, duration_minutes, smart_score, fuel_liters,
                       fuel_cost, summary
                FROM route_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def get_by_id(history_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a specific history record including full payload."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM route_history WHERE id = ?", (history_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("full_result_json"):
                try:
                    res["full_result"] = json.loads(res["full_result_json"])
                except Exception:
                    res["full_result"] = None
            return res

    @staticmethod
    def delete_by_id(history_id: int) -> bool:
        """Deletes a single history record."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM route_history WHERE id = ?", (history_id,))
            deleted = cursor.rowcount > 0
            logger.info(f"History entry {history_id} deletion result: {deleted}")
            return deleted

    @staticmethod
    def clear_all() -> int:
        """Clears all history records."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM route_history")
            count = cursor.rowcount
            logger.info(f"Cleared {count} history records.")
            return count


history_repo = HistoryRepository()
