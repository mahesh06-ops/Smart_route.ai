"""
Route Search History API endpoints.
"""
from fastapi import APIRouter, HTTPException
from src.database.history_repository import history_repo

router = APIRouter(prefix="/history", tags=["History"])


@router.get("")
async def get_history(limit: int = 50):
    """Fetches past route searches from SQLite."""
    items = history_repo.get_all(limit=limit)
    return {"success": True, "count": len(items), "data": items}


@router.get("/{history_id}")
async def get_history_item(history_id: int):
    """Retrieves full details of a specific historical route search."""
    item = history_repo.get_by_id(history_id)
    if not item:
        raise HTTPException(status_code=404, detail="History entry not found.")
    return {"success": True, "data": item}


@router.delete("/{history_id}")
async def delete_history_item(history_id: int):
    """Deletes a single history record."""
    success = history_repo.delete_by_id(history_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found or already deleted.")
    return {"success": True, "message": f"Deleted history item {history_id}"}


@router.delete("")
async def clear_history():
    """Clears all historical route records."""
    count = history_repo.clear_all()
    return {"success": True, "message": f"Cleared {count} history records.", "deleted_count": count}
