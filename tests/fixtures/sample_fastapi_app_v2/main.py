"""
Sample FastAPI app — v2 state (intentional documentation gaps).

NEW in v2:
  DELETE /items/{item_id}  — delete an item by id

Intentional gaps for demo / audit:
  * README still describes only v1 endpoints (new endpoint undocumented)
  * CHANGELOG has no v2.0.0 entry
  * __version__ bumped to 2.0.0 but README/CHANGELOG still say v1.0.0
    → triggers version mismatch detection in audit_agent
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

__version__ = "2.0.0"

app = FastAPI(title="Sample API", version=__version__)


class Item(BaseModel):
    id: int
    name: str


_store: list[Item] = []


@app.get("/items", response_model=list[Item])
def list_items():
    """Return all items."""
    return _store


@app.post("/items", response_model=Item, status_code=201)
def create_item(item: Item):
    """Create a new item."""
    _store.append(item)
    return item


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    """Delete an item by id.

    NOTE: This endpoint is intentionally missing from README and CHANGELOG
    to demonstrate the audit agent detecting undocumented API changes.
    """
    for i, item in enumerate(_store):
        if item.id == item_id:
            _store.pop(i)
            return
    raise HTTPException(status_code=404, detail="Item not found")
