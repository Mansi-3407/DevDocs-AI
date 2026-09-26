"""
API Documentation Agent — static AST-based endpoint scanner and OpenAPI generator.

Scans a Python source file for FastAPI and Flask route decorators without
importing or executing the target application.  All analysis is performed
purely on the Abstract Syntax Tree produced by the standard-library ``ast``
module, so the target's dependencies do not need to be installed.

Public interface
----------------
::

    agent = APIAgent()

    # Returns list[dict] — one dict per detected endpoint.
    endpoints = agent.scan_endpoints("path/to/app.py")

    # Returns an OpenAPI 3.0.3 specification as a Python dict.
    spec = agent.generate_openapi("path/to/app.py")

    # Returns lightweight request/response examples for each endpoint.
    examples = agent.generate_examples("path/to/app.py")

    # Returns the team-standard result envelope.
    result = agent.run("path/to/app.py")

Result envelope shape
---------------------
::

    {
        "agent":    "api_agent",
        "status":   "success" | "error",
        "output":   {
            "endpoints": [...],
            "openapi":   {...},
            "examples":  [...]
        },
        "warnings": [<str>, ...],
        "errors":   [<str>, ...]
    }
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# HTTP method constants
# ---------------------------------------------------------------------------

# FastAPI single-method decorator names  →  HTTP method
_FASTAPI_METHOD_DECORATORS: dict[str, str] = {
    "get":     "GET",
    "post":    "POST",
    "put":     "PUT",
    "patch":   "PATCH",
    "delete":  "DELETE",
    "options": "OPTIONS",
    "head":    "HEAD",
}

# Flask converter names  →  canonical type string
_FLASK_CONVERTERS: dict[str, str] = {
    "int":    "int",
    "float":  "float",
    "string": "str",
    "str":    "str",
    "path":   "str",
    "uuid":   "str",
}

# Regex to detect Flask path parameters:  <converter:name>  or  <name>
_FLASK_PARAM_RE = re.compile(r"<(?:([a-z]+):)?([a-zA-Z_][a-zA-Z0-9_]*)>")

# Python type → OpenAPI type mapping
_PYTHON_TO_OPENAPI_TYPE: dict[str, str] = {
    "str":   "string",
    "int":   "integer",
    "float": "number",
    "bool":  "boolean",
    "bytes": "string",
}


# ---------------------------------------------------------------------------
# Safe static value extractor (no eval)
# ---------------------------------------------------------------------------

def _extract_value(node: ast.expr | None) -> Any:
    """
    Safely extract a static Python value from an AST expression node.

    Handles: str, int, float, bool, None, list of those, tuple of those.
    Returns ``None`` for any expression that cannot be safely resolved.
    """
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        items = [_extract_value(elt) for elt in node.elts]
        # Return None if any element is un-extractable (contains complex expr)
        return None if any(v is None and not isinstance(elt, ast.Constant)
                           for v, elt in zip(items, node.elts)) else items
    # ast.NameConstant / ast.Num / ast.Str are subsumed by ast.Constant in
    # Python 3.8+, but guard against older parse trees just in case.
    return None


# ---------------------------------------------------------------------------
# Type annotation → string representation
# ---------------------------------------------------------------------------

def _annotation_to_str(node: ast.expr | None) -> str | None:
    """
    Convert an AST annotation node to a human-readable type string.

    Examples:
        ``int``             → ``"int"``
        ``bool``            → ``"bool"``
        ``UserCreate``      → ``"UserCreate"``
        ``list[PostSummary]``          → ``"list[PostSummary]"``
        ``list[PostSummary] | None``   → ``"list[PostSummary] | None"``
    """
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and node.value is None:
        return "None"
    if isinstance(node, ast.Attribute):
        return f"{_annotation_to_str(node.value)}.{node.attr}"
    # Python 3.9+ generic alias:  list[X]
    if isinstance(node, ast.Subscript):
        origin = _annotation_to_str(node.value)
        slice_str = _annotation_to_str(node.slice)
        return f"{origin}[{slice_str}]" if origin and slice_str else None
    # Python 3.10+ union:  X | Y
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left  = _annotation_to_str(node.left)
        right = _annotation_to_str(node.right)
        return f"{left} | {right}" if left and right else None
    # Python 3.8 typing.Union / Optional expressed as ast.Index (3.8 only)
    if isinstance(node, ast.Index):          # type: ignore[attr-defined]
        return _annotation_to_str(node.value)  # type: ignore[attr-defined]
    return None


# ---------------------------------------------------------------------------
# Pydantic model collector (names only — used by scanner)
# ---------------------------------------------------------------------------

def _collect_pydantic_models(tree: ast.Module) -> set[str]:
    """
    Walk the module AST and return the names of all classes that directly
    inherit from ``BaseModel`` (bare name only — no import resolution needed
    for the fixture use-case).
    """
    models: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_name = _annotation_to_str(base)
            if base_name in ("BaseModel", "pydantic.BaseModel"):
                models.add(node.name)
                break
    return models


# ---------------------------------------------------------------------------
# Decorator keyword argument extraction
# ---------------------------------------------------------------------------

def _decorator_kwargs(call: ast.Call) -> dict[str, Any]:
    """
    Extract keyword arguments from a decorator Call node into a plain dict.

    Values are resolved with ``_extract_value``; unresolvable values are
    stored as ``None``.
    """
    kwargs: dict[str, Any] = {}
    for kw in call.keywords:
        if kw.arg is not None:
            kwargs[kw.arg] = _extract_value(kw.value)
    return kwargs


def _decorator_response_model(call: ast.Call) -> str | None:
    """
    Extract the *string name* of the ``response_model`` keyword argument from
    a decorator Call node, without evaluating it.
    """
    for kw in call.keywords:
        if kw.arg == "response_model":
            return _annotation_to_str(kw.value)
    return None


# ---------------------------------------------------------------------------
# Path parameter extraction helpers
# ---------------------------------------------------------------------------

def _fastapi_path_params(path: str) -> set[str]:
    """Return the set of parameter names embedded in a FastAPI path string."""
    return set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", path))


def _flask_path_params(path: str) -> list[dict[str, Any]]:
    """
    Parse Flask-style path parameters from a route string.

    Returns a list of partial parameter dicts (name, type).
    """
    params = []
    for converter, name in _FLASK_PARAM_RE.findall(path):
        type_str = _FLASK_CONVERTERS.get(converter, "str") if converter else "str"
        params.append({"name": name, "type": type_str})
    return params


def _normalise_flask_path(path: str) -> str:
    """Convert a Flask path such as ``/users/<int:user_id>`` to ``/users/{user_id}``."""
    return _FLASK_PARAM_RE.sub(lambda m: "{" + m.group(2) + "}", path)


# ---------------------------------------------------------------------------
# Function parameter analysis
# ---------------------------------------------------------------------------

def _analyse_function_params(
    func: ast.FunctionDef,
    path_param_names: set[str],
    pydantic_models: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """
    Inspect the function's argument list and classify each parameter.

    Returns ``(parameters, request_body)`` where:

    * ``parameters`` is a list of query/path parameter dicts.
    * ``request_body`` is a single dict if a Pydantic-model parameter is found,
      otherwise ``None``.
    """
    args       = func.args
    parameters: list[dict[str, Any]] = []
    request_body: dict[str, Any] | None = None

    # Build default-value map.  Positional defaults are right-aligned against
    # the argument list:  last N args correspond to the N defaults.
    all_args    = args.args  # excludes *args / **kwargs
    n_defaults  = len(args.defaults)
    n_args      = len(all_args)
    # Index of the first arg that has a default
    default_offset = n_args - n_defaults

    for idx, arg in enumerate(all_args):
        name = arg.arg
        if name == "self":
            continue

        annotation_str = _annotation_to_str(arg.annotation)

        # Determine whether this arg has a default
        has_default = idx >= default_offset
        default_val: Any = None
        if has_default:
            default_node = args.defaults[idx - default_offset]
            default_val  = _extract_value(default_node)

        # --- Pydantic request body? ---
        if annotation_str and annotation_str in pydantic_models:
            request_body = {
                "name":     name,
                "type":     annotation_str,
                "required": not has_default,
            }
            continue  # do not also add as a query param

        # --- Path parameter? ---
        if name in path_param_names:
            parameters.append({
                "name":     name,
                "location": "path",
                "type":     annotation_str or "str",
                "required": True,
                "default":  None,
            })
            continue

        # --- Query / other parameter ---
        parameters.append({
            "name":     name,
            "location": "query",
            "type":     annotation_str or "str",
            "required": not has_default,
            "default":  default_val,
        })

    return parameters, request_body


# ---------------------------------------------------------------------------
# Decorator identification helpers
# ---------------------------------------------------------------------------

def _is_attr_call(node: ast.expr) -> bool:
    """Return True if the node is an attribute call:  ``obj.method(...)``."""
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)


def _fastapi_method_from_decorator(
    dec: ast.expr,
) -> tuple[str | None, str | None, dict[str, Any]]:
    """
    Try to interpret a single decorator as a FastAPI route decorator.

    Returns ``(http_method, path, kwargs)`` or ``(None, None, {})``.

    Matches patterns:
    * ``@app.get("/path", ...)``
    * ``@router.post("/path", ...)``
    * ``@app.api_route("/path", methods=[...])``
    """
    if not _is_attr_call(dec):
        return None, None, {}

    call: ast.Call           = dec  # type: ignore[assignment]
    attr: ast.Attribute      = call.func  # type: ignore[assignment]
    method_name: str         = attr.attr

    # Positional first argument must be the path string
    if not call.args:
        return None, None, {}
    path = _extract_value(call.args[0])
    if not isinstance(path, str):
        return None, None, {}

    kwargs = _decorator_kwargs(call)

    # Single-method decorator
    http_method = _FASTAPI_METHOD_DECORATORS.get(method_name)
    if http_method:
        return http_method, path, kwargs

    # api_route decorator with explicit methods list
    if method_name == "api_route":
        methods = kwargs.get("methods")
        if isinstance(methods, list) and methods:
            # Return first method; caller can expand if needed
            return str(methods[0]).upper(), path, kwargs
        return "GET", path, kwargs  # default assumption

    return None, None, {}


def _flask_method_from_decorator(
    dec: ast.expr,
) -> tuple[list[str], str | None]:
    """
    Try to interpret a single decorator as a Flask ``route`` decorator.

    Returns ``(http_methods, path)`` or ``([], None)``.

    Matches:
    * ``@app.route("/path", methods=["GET", "POST"])``
    * ``@bp.route("/path")``   → defaults to ["GET"]
    """
    if not _is_attr_call(dec):
        return [], None

    call: ast.Call      = dec  # type: ignore[assignment]
    attr: ast.Attribute = call.func  # type: ignore[assignment]

    if attr.attr != "route":
        return [], None

    if not call.args:
        return [], None
    path = _extract_value(call.args[0])
    if not isinstance(path, str):
        return [], None

    kwargs  = _decorator_kwargs(call)
    methods = kwargs.get("methods")
    if isinstance(methods, list) and methods:
        return [str(m).upper() for m in methods], path
    return ["GET"], path


# ---------------------------------------------------------------------------
# App metadata extraction (FastAPI / Flask)
# ---------------------------------------------------------------------------

def _extract_app_metadata(tree: ast.Module) -> dict[str, str]:
    """
    Scan the module AST for a ``FastAPI(...)`` or ``Flask(...)`` constructor
    call and extract ``title``, ``description``, and ``version`` keyword args.

    Returns a dict with whatever keys are found; callers supply fallbacks for
    missing keys.  No import or execution of the target app is performed.

    Handles both assignment forms::

        app = FastAPI(title="...", ...)
        app = Flask(__name__)
    """
    metadata: dict[str, str] = {}

    for node in ast.walk(tree):
        # We want:  <name> = <constructor_call>(...)
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue

        # Resolve the callable name — may be a bare Name or an Attribute
        func_node = value.func
        if isinstance(func_node, ast.Name):
            ctor_name = func_node.id
        elif isinstance(func_node, ast.Attribute):
            ctor_name = func_node.attr
        else:
            continue

        if ctor_name not in ("FastAPI", "Flask"):
            continue

        # Extract string keyword arguments
        for kw in value.keywords:
            if kw.arg in ("title", "description", "version"):
                val = _extract_value(kw.value)
                if isinstance(val, str):
                    metadata[kw.arg] = val

        # Stop at the first recognised app constructor
        if metadata:
            break

    return metadata


# ---------------------------------------------------------------------------
# OpenAPI type-schema builder
# ---------------------------------------------------------------------------

def _annotation_to_openapi_schema(
    annotation_str: str | None,
    known_models: set[str],
) -> dict[str, Any]:
    """
    Convert a Python type annotation string to an OpenAPI-compatible JSON
    Schema fragment.

    Rules:
    * Primitive types are mapped via ``_PYTHON_TO_OPENAPI_TYPE``.
    * Known Pydantic model names become ``{"$ref": "#/components/schemas/<Name>"}``.
    * ``list[X]`` becomes ``{"type": "array", "items": <schema of X>}``.
    * ``X | None`` or ``Optional[X]`` becomes the schema of ``X`` with
      ``"nullable": true`` added (OpenAPI 3.0.x style).
    * Anything unrecognised falls back to ``{"type": "string"}``.
    """
    if not annotation_str:
        return {"type": "string"}

    ann = annotation_str.strip()

    # ---- Nullable / Optional: X | None  or  None | X ----
    if " | " in ann:
        parts = [p.strip() for p in ann.split(" | ")]
        non_none = [p for p in parts if p != "None"]
        if len(non_none) == 1:
            inner = _annotation_to_openapi_schema(non_none[0], known_models)
            inner["nullable"] = True
            return inner
        # Multi-union — return anyOf
        return {"anyOf": [_annotation_to_openapi_schema(p, known_models) for p in parts if p != "None"]}

    # ---- list[X] ----
    list_match = re.fullmatch(r"list\[(.+)\]", ann)
    if list_match:
        inner_ann = list_match.group(1).strip()
        return {
            "type":  "array",
            "items": _annotation_to_openapi_schema(inner_ann, known_models),
        }

    # ---- Optional[X]  (typing.Optional style — appears as a raw string) ----
    optional_match = re.fullmatch(r"Optional\[(.+)\]", ann)
    if optional_match:
        inner_ann = optional_match.group(1).strip()
        inner = _annotation_to_openapi_schema(inner_ann, known_models)
        inner["nullable"] = True
        return inner

    # ---- Known Pydantic model → $ref ----
    if ann in known_models:
        return {"$ref": f"#/components/schemas/{ann}"}

    # ---- Primitive Python type ----
    openapi_type = _PYTHON_TO_OPENAPI_TYPE.get(ann)
    if openapi_type:
        return {"type": openapi_type}

    # ---- Fallback ----
    return {"type": "string"}


# ---------------------------------------------------------------------------
# Pydantic model schema builder (for components/schemas)
# ---------------------------------------------------------------------------

def _build_model_schemas(
    tree: ast.Module,
    known_models: set[str],
) -> dict[str, Any]:
    """
    Walk the module AST and generate OpenAPI-compatible JSON Schema objects
    for every class that inherits from ``BaseModel``.

    Returns a dict keyed by class name, suitable for ``components.schemas``.
    """
    schemas: dict[str, Any] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        # Only process Pydantic models
        if node.name not in known_models:
            continue

        properties: dict[str, Any] = {}
        required_fields: list[str] = []

        for item in node.body:
            # We only care about annotated class-body assignments:
            #   field_name: Type
            #   field_name: Type = default
            if not isinstance(item, ast.AnnAssign):
                continue

            # Target must be a simple name (not a complex subscript etc.)
            if not isinstance(item.target, ast.Name):
                continue

            field_name = item.target.id
            ann_str    = _annotation_to_str(item.annotation)
            schema     = _annotation_to_openapi_schema(ann_str, known_models)

            # Detect default: item.value is present if there is `= <default>`
            has_default = item.value is not None

            # If the default is the literal None we still consider it optional
            if not has_default:
                required_fields.append(field_name)

            properties[field_name] = schema

        model_schema: dict[str, Any] = {
            "type":       "object",
            "properties": properties,
        }
        if required_fields:
            model_schema["required"] = required_fields

        schemas[node.name] = model_schema

    return schemas


# ---------------------------------------------------------------------------
# OpenAPI parameter / requestBody / response builders
# ---------------------------------------------------------------------------

def _build_openapi_parameter(param: dict[str, Any], known_models: set[str]) -> dict[str, Any]:
    """Convert a scanner parameter dict to an OpenAPI Parameter Object."""
    location = param.get("location", "query")
    # Path parameters MUST be required regardless of scanner metadata
    is_required = True if location == "path" else bool(param.get("required", False))

    schema = _annotation_to_openapi_schema(param.get("type"), known_models)

    # Attach default value to schema when present and parameter is optional
    default_val = param.get("default")
    if default_val is not None and not is_required:
        schema = dict(schema)  # shallow copy so we don't mutate the original
        schema["default"] = default_val

    oa_param: dict[str, Any] = {
        "name":     param["name"],
        "in":       location,
        "required": is_required,
        "schema":   schema,
    }
    return oa_param


def _build_request_body(request_body: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert a scanner request_body dict to an OpenAPI Request Body Object."""
    if not request_body:
        return None
    model_name = request_body.get("type", "")
    return {
        "required": bool(request_body.get("required", True)),
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{model_name}"}
            }
        },
    }


def _build_responses(endpoint: dict[str, Any]) -> dict[str, Any]:
    """
    Build the OpenAPI Responses Object for a single endpoint.

    Uses the endpoint's status_code and response type.
    """
    status_code = str(endpoint.get("status_code") or 200)
    response    = endpoint.get("response") or {}
    model_name  = response.get("type") if response else None

    success_response: dict[str, Any] = {"description": "Successful Response"}
    if model_name:
        success_response["content"] = {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{model_name}"}
            }
        }

    return {status_code: success_response}


# ---------------------------------------------------------------------------
# Example value generator
# ---------------------------------------------------------------------------

_EXAMPLE_VALUES: dict[str, Any] = {
    "string":  "example",
    "integer": 1,
    "number":  1.0,
    "boolean": False,
}


def _example_value_for_schema(schema: dict[str, Any]) -> Any:
    """Return a simple placeholder example value for a JSON Schema fragment."""
    if "$ref" in schema:
        # Model reference — return a generic object placeholder
        return {}
    schema_type = schema.get("type", "string")
    if schema_type == "array":
        inner = schema.get("items", {})
        return [_example_value_for_schema(inner)]
    return _EXAMPLE_VALUES.get(schema_type, "example")


def _example_value_for_type(type_str: str | None, known_models: set[str]) -> Any:
    """Convenience wrapper: type annotation string → example value."""
    schema = _annotation_to_openapi_schema(type_str, known_models)
    return _example_value_for_schema(schema)


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

class APIAgent:
    """
    Static AST-based API endpoint scanner and OpenAPI 3.0 document generator.

    All public methods operate purely on Python source text; the target
    application is never imported or executed.
    """

    # ======================================================================
    # Existing public scanner interface (unchanged)
    # ======================================================================

    def scan_endpoints(self, target_path: str) -> list[dict[str, Any]]:
        """
        Parse *target_path* and return a list of detected endpoint dicts.

        Each dict contains: path, method, function, parameters, request_body,
        response, status_code, summary, tags, docstring.

        Raises ``FileNotFoundError`` or ``SyntaxError`` — callers (``run``)
        handle these; do not swallow them here.
        """
        source = Path(target_path).read_text(encoding="utf-8")
        tree   = ast.parse(source, filename=target_path)

        pydantic_models = _collect_pydantic_models(tree)
        endpoints: list[dict[str, Any]] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            for dec in node.decorator_list:
                endpoint = self._try_fastapi(node, dec, pydantic_models)
                if endpoint:
                    endpoints.append(endpoint)
                    break  # one route decorator per function is the norm

                flask_endpoints = self._try_flask(node, dec, pydantic_models)
                if flask_endpoints:
                    endpoints.extend(flask_endpoints)
                    break

        # Restore declaration order (ast.walk does not guarantee it)
        endpoints.sort(key=lambda e: e.get("_lineno", 0))
        for ep in endpoints:
            ep.pop("_lineno", None)

        return endpoints

    # ======================================================================
    # New public methods
    # ======================================================================

    def generate_openapi(
        self,
        target_path: str,
        title: str | None = None,
        version: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate an OpenAPI 3.0.3 specification from *target_path*.

        Scans endpoints statically, extracts Pydantic model schemas, and
        assembles a complete OpenAPI document dict.  The document is never
        written to disk here; callers may serialise it as needed.

        Parameters
        ----------
        target_path:
            Path to the Python source file containing the API.
        title, version, description:
            Override the values extracted from the source.  When ``None``,
            values are read from the ``FastAPI(...)`` constructor in the
            source; sensible fallbacks are used when not found.
        """
        source = Path(target_path).read_text(encoding="utf-8")
        tree   = ast.parse(source, filename=target_path)

        # Collect Pydantic models (names)
        known_models   = _collect_pydantic_models(tree)

        # Scan endpoints (reuse existing scanner, parse once)
        pydantic_models = known_models
        endpoints_raw: list[dict[str, Any]] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                ep = self._try_fastapi(node, dec, pydantic_models)
                if ep:
                    endpoints_raw.append(ep)
                    break
                flask_eps = self._try_flask(node, dec, pydantic_models)
                if flask_eps:
                    endpoints_raw.extend(flask_eps)
                    break
        endpoints_raw.sort(key=lambda e: e.get("_lineno", 0))
        for ep in endpoints_raw:
            ep.pop("_lineno", None)

        # Extract app metadata from source
        app_meta = _extract_app_metadata(tree)

        resolved_title       = title       or app_meta.get("title",       "API Documentation")
        resolved_version     = version     or app_meta.get("version",     "0.1.0")
        resolved_description = description or app_meta.get("description", "")

        # Build paths
        paths = self._build_paths(endpoints_raw, known_models)

        # Build component schemas
        schemas = _build_model_schemas(tree, known_models)

        # Assemble document
        openapi_doc: dict[str, Any] = {
            "openapi": "3.0.3",
            "info": {
                "title":   resolved_title,
                "version": resolved_version,
            },
            "paths": paths,
        }
        if resolved_description:
            openapi_doc["info"]["description"] = resolved_description
        if schemas:
            openapi_doc["components"] = {"schemas": schemas}

        return openapi_doc

    def generate_examples(self, target_path: str) -> list[dict[str, Any]]:
        """
        Generate lightweight, deterministic request/response examples for
        every endpoint detected in *target_path*.

        These are documentation placeholders only — no real API is called.
        """
        source = Path(target_path).read_text(encoding="utf-8")
        tree   = ast.parse(source, filename=target_path)
        known_models = _collect_pydantic_models(tree)
        endpoints    = self.scan_endpoints(target_path)

        examples = []
        for ep in endpoints:
            examples.append(self._build_example(ep, known_models))
        return examples

    # ======================================================================
    # Public run() — team-standard result envelope (updated)
    # ======================================================================

    def run(self, target_path: str) -> dict[str, Any]:
        """
        Scan *target_path* and return the team-standard result envelope.

        The ``output`` field now contains a structured dict with three keys:

        * ``endpoints`` — raw scanner output (same as before)
        * ``openapi``   — OpenAPI 3.0.3 specification dict
        * ``examples``  — lightweight documentation examples

        On error the envelope degrades gracefully::

            {
                "agent":  "api_agent",
                "status": "error",
                "output": [],
                "warnings": [],
                "errors": ["<message>"]
            }
        """
        try:
            # Parse once; reuse tree for all three operations
            source = Path(target_path).read_text(encoding="utf-8")
            tree   = ast.parse(source, filename=target_path)
            known_models = _collect_pydantic_models(tree)

            # Scan endpoints (honours existing scanner contract)
            endpoints = self.scan_endpoints(target_path)

            # Generate OpenAPI spec
            openapi = self.generate_openapi(target_path)

            # Generate examples
            examples = self.generate_examples(target_path)

            return {
                "agent":  "api_agent",
                "status": "success",
                "output": {
                    "endpoints": endpoints,
                    "openapi":   openapi,
                    "examples":  examples,
                },
                "warnings": [],
                "errors":   [],
            }

        except FileNotFoundError:
            return {
                "agent":    "api_agent",
                "status":   "error",
                "output":   [],
                "warnings": [],
                "errors":   [f"File not found: {target_path}"],
            }
        except SyntaxError as exc:
            return {
                "agent":    "api_agent",
                "status":   "error",
                "output":   [],
                "warnings": [],
                "errors":   [f"Syntax error in {target_path}: {exc}"],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "agent":    "api_agent",
                "status":   "error",
                "output":   [],
                "warnings": [],
                "errors":   [f"Unexpected error scanning {target_path}: {exc}"],
            }

    # ======================================================================
    # FastAPI handler (unchanged from original)
    # ======================================================================

    def _try_fastapi(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        dec: ast.expr,
        pydantic_models: set[str],
    ) -> dict[str, Any] | None:
        """Return an endpoint dict if *dec* is a FastAPI route decorator."""
        http_method, path, kwargs = _fastapi_method_from_decorator(dec)
        if http_method is None or path is None:
            return None

        path_param_names = _fastapi_path_params(path)
        parameters, request_body = _analyse_function_params(
            func, path_param_names, pydantic_models
        )

        # Response type — prefer decorator keyword, fall back to return ann.
        response_model  = _decorator_response_model(dec)  # type: ignore[arg-type]
        return_ann      = _annotation_to_str(func.returns)
        response_type   = response_model or return_ann

        status_code: int = kwargs.get("status_code") or 200
        if not isinstance(status_code, int):
            status_code = 200

        summary   = kwargs.get("summary")
        tags      = kwargs.get("tags")
        docstring = ast.get_docstring(func)

        endpoint: dict[str, Any] = {
            "_lineno":      func.lineno,
            "path":         path,
            "method":       http_method,
            "function":     func.name,
            "parameters":   parameters,
            "request_body": request_body,
            "response":     {"type": response_type} if response_type else None,
            "status_code":  status_code,
            "summary":      summary,
            "tags":         tags if isinstance(tags, list) else None,
            "docstring":    docstring,
        }
        return endpoint

    # ======================================================================
    # Flask handler (unchanged from original)
    # ======================================================================

    def _try_flask(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        dec: ast.expr,
        pydantic_models: set[str],
    ) -> list[dict[str, Any]]:
        """
        Return a list of endpoint dicts if *dec* is a Flask route decorator.

        Flask's ``methods`` list can contain multiple HTTP verbs, so one
        decorator may produce multiple endpoint entries.
        """
        http_methods, raw_path = _flask_method_from_decorator(dec)
        if not http_methods or raw_path is None:
            return []

        flask_params     = _flask_path_params(raw_path)
        path_param_names = {p["name"] for p in flask_params}
        normalised_path  = _normalise_flask_path(raw_path)

        parameters, request_body = _analyse_function_params(
            func, path_param_names, pydantic_models
        )

        # Merge Flask converter types into the detected parameters
        flask_type_map = {p["name"]: p["type"] for p in flask_params}
        for param in parameters:
            if param["location"] == "path":
                param["type"] = flask_type_map.get(param["name"], param["type"])

        docstring = ast.get_docstring(func)
        endpoints = []
        for method in http_methods:
            endpoints.append({
                "_lineno":      func.lineno,
                "path":         normalised_path,
                "method":       method,
                "function":     func.name,
                "parameters":   parameters,
                "request_body": request_body,
                "response":     None,
                "status_code":  200,
                "summary":      None,
                "tags":         None,
                "docstring":    docstring,
            })
        return endpoints

    # ======================================================================
    # OpenAPI assembly helpers (private)
    # ======================================================================

    def _build_paths(
        self,
        endpoints: list[dict[str, Any]],
        known_models: set[str],
    ) -> dict[str, Any]:
        """
        Convert a list of scanner endpoint dicts into an OpenAPI Paths Object.

        Multiple endpoints sharing the same path (e.g. GET and POST /users)
        are merged under the same path key.
        """
        paths: dict[str, Any] = {}

        for ep in endpoints:
            path   = ep["path"]
            method = ep["method"].lower()

            if path not in paths:
                paths[path] = {}

            operation = self._build_operation(ep, known_models)
            paths[path][method] = operation

        return paths

    def _build_operation(
        self,
        ep: dict[str, Any],
        known_models: set[str],
    ) -> dict[str, Any]:
        """Build an OpenAPI Operation Object from a scanner endpoint dict."""
        operation: dict[str, Any] = {}

        # operationId — deterministic: function_name + "_" + lowercase_method
        func_name = ep.get("function", "unknown")
        method    = ep.get("method", "get").lower()
        operation["operationId"] = f"{func_name}_{method}"

        if ep.get("tags"):
            operation["tags"] = ep["tags"]

        if ep.get("summary"):
            operation["summary"] = ep["summary"]

        if ep.get("docstring"):
            operation["description"] = ep["docstring"]

        # Parameters
        oa_params = [
            _build_openapi_parameter(p, known_models)
            for p in (ep.get("parameters") or [])
        ]
        if oa_params:
            operation["parameters"] = oa_params

        # Request body
        rb = _build_request_body(ep.get("request_body"))
        if rb:
            operation["requestBody"] = rb

        # Responses
        operation["responses"] = _build_responses(ep)

        return operation

    # ======================================================================
    # Example builder (private)
    # ======================================================================

    def _build_example(
        self,
        ep: dict[str, Any],
        known_models: set[str],
    ) -> dict[str, Any]:
        """
        Build a deterministic documentation example for a single endpoint.

        The example values are static placeholders suitable for documentation;
        they do not represent real API responses.
        """
        # Parameter examples
        param_examples: dict[str, Any] = {}
        for param in ep.get("parameters") or []:
            param_examples[param["name"]] = _example_value_for_type(
                param.get("type"), known_models
            )

        # Request body example
        request_example: dict[str, Any] | None = None
        rb = ep.get("request_body")
        if rb:
            model_name = rb.get("type", "")
            if model_name in known_models:
                request_example = {"$schema": f"#/components/schemas/{model_name}"}
            else:
                request_example = {}

        # Response example
        response_example: dict[str, Any] | None = None
        resp = ep.get("response") or {}
        resp_type = resp.get("type") if resp else None
        if resp_type and resp_type in known_models:
            response_example = {"$schema": f"#/components/schemas/{resp_type}"}
        elif resp_type:
            response_example = _example_value_for_type(resp_type, known_models)  # type: ignore[assignment]

        example: dict[str, Any] = {
            "method": ep.get("method", "GET"),
            "path":   ep.get("path", "/"),
        }
        if param_examples:
            example["parameters"] = param_examples
        if request_example is not None:
            example["request"] = request_example
        if response_example is not None:
            example["response"] = response_example

        return example
