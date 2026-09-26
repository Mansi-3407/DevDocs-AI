"""
Sample FastAPI app — v1 state (well-documented baseline).

Endpoints:
  GET  /items        — list all items
  POST /items        — create a new item

This is the "before" state in the demo scenario.
"""
from fastapi import FastAPI
from pydantic import BaseModel

__version__ = "1.0.0"

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
