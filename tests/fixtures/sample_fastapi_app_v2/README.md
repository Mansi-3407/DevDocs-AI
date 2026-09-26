# Sample FastAPI App

A minimal FastAPI application used as a fixture for DevDocs AI tests and demo.

## Installation

```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

## Usage

Start the server and visit `http://localhost:8000/docs` for the auto-generated
Swagger UI.

### List items

```bash
curl http://localhost:8000/items
```

### Create an item

```bash
curl -X POST http://localhost:8000/items \
     -H "Content-Type: application/json" \
     -d '{"id": 1, "name": "Widget"}'
```

## API Reference

| Method | Path     | Description     |
|--------|----------|-----------------|
| GET    | /items   | List all items  |
| POST   | /items   | Create an item  |

<!-- NOTE: DELETE /items/{id} is intentionally undocumented here to demonstrate
     the audit agent detecting missing documentation for new endpoints. -->
