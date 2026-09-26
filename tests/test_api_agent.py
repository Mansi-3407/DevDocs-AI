"""
Tests for app.agents.api_agent — Person 2 implementation.

Covers:
  - scan_endpoints()   (static AST scanner)
  - generate_openapi() (OpenAPI 3.0.3 document builder)
  - generate_examples()
  - run()              (team-standard result envelope)
"""

import json
from pathlib import Path

import pytest

from app.agents.api_agent import APIAgent

# ---------------------------------------------------------------------------
# Fixture path helper
# ---------------------------------------------------------------------------

FIXTURE = str(
    Path(__file__).parent / "fixtures" / "sample_fastapi_app" / "main.py"
)


# ---------------------------------------------------------------------------
# Shared pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def agent() -> APIAgent:
    return APIAgent()


@pytest.fixture(scope="module")
def endpoints(agent: APIAgent) -> list[dict]:
    return agent.scan_endpoints(FIXTURE)


@pytest.fixture(scope="module")
def endpoints_by_key(endpoints: list[dict]) -> dict:
    return {(e["method"], e["path"]): e for e in endpoints}


@pytest.fixture(scope="module")
def openapi(agent: APIAgent) -> dict:
    return agent.generate_openapi(FIXTURE)


@pytest.fixture(scope="module")
def schemas(openapi: dict) -> dict:
    return openapi.get("components", {}).get("schemas", {})


@pytest.fixture(scope="module")
def paths(openapi: dict) -> dict:
    return openapi.get("paths", {})


# ===========================================================================
# 1.  scan_endpoints — endpoint detection
# ===========================================================================

class TestScanEndpoints:

    def test_exactly_three_endpoints(self, endpoints):
        assert len(endpoints) == 3

    def test_get_health_detected(self, endpoints_by_key):
        assert ("GET", "/health") in endpoints_by_key

    def test_get_users_user_id_detected(self, endpoints_by_key):
        assert ("GET", "/users/{user_id}") in endpoints_by_key

    def test_post_users_detected(self, endpoints_by_key):
        assert ("POST", "/users") in endpoints_by_key

    # --- path parameter ---

    def test_user_id_location_is_path(self, endpoints_by_key):
        params = {
            p["name"]: p
            for p in endpoints_by_key[("GET", "/users/{user_id}")]["parameters"]
        }
        assert params["user_id"]["location"] == "path"

    def test_user_id_type_is_int(self, endpoints_by_key):
        params = {
            p["name"]: p
            for p in endpoints_by_key[("GET", "/users/{user_id}")]["parameters"]
        }
        assert params["user_id"]["type"] == "int"

    def test_user_id_is_required(self, endpoints_by_key):
        params = {
            p["name"]: p
            for p in endpoints_by_key[("GET", "/users/{user_id}")]["parameters"]
        }
        assert params["user_id"]["required"] is True

    # --- query parameter ---

    def test_include_posts_location_is_query(self, endpoints_by_key):
        params = {
            p["name"]: p
            for p in endpoints_by_key[("GET", "/users/{user_id}")]["parameters"]
        }
        assert params["include_posts"]["location"] == "query"

    def test_include_posts_type_is_bool(self, endpoints_by_key):
        params = {
            p["name"]: p
            for p in endpoints_by_key[("GET", "/users/{user_id}")]["parameters"]
        }
        assert params["include_posts"]["type"] == "bool"

    def test_include_posts_not_required(self, endpoints_by_key):
        params = {
            p["name"]: p
            for p in endpoints_by_key[("GET", "/users/{user_id}")]["parameters"]
        }
        assert params["include_posts"]["required"] is False

    def test_include_posts_default_false(self, endpoints_by_key):
        params = {
            p["name"]: p
            for p in endpoints_by_key[("GET", "/users/{user_id}")]["parameters"]
        }
        assert params["include_posts"]["default"] is False

    # --- request body ---

    def test_request_body_type_is_UserCreate(self, endpoints_by_key):
        rb = endpoints_by_key[("POST", "/users")]["request_body"]
        assert rb["type"] == "UserCreate"

    def test_request_body_is_required(self, endpoints_by_key):
        rb = endpoints_by_key[("POST", "/users")]["request_body"]
        assert rb["required"] is True

    # --- response models ---

    def test_health_response_model(self, endpoints_by_key):
        resp = endpoints_by_key[("GET", "/health")]["response"]
        assert resp is not None
        assert resp["type"] == "HealthResponse"

    def test_get_user_response_model(self, endpoints_by_key):
        resp = endpoints_by_key[("GET", "/users/{user_id}")]["response"]
        assert resp is not None
        assert resp["type"] == "UserDetailResponse"

    def test_post_users_response_model(self, endpoints_by_key):
        resp = endpoints_by_key[("POST", "/users")]["response"]
        assert resp is not None
        assert resp["type"] == "UserResponse"

    # --- status code ---

    def test_post_users_status_code_201(self, endpoints_by_key):
        assert endpoints_by_key[("POST", "/users")]["status_code"] == 201

    def test_get_health_status_code_200(self, endpoints_by_key):
        assert endpoints_by_key[("GET", "/health")]["status_code"] == 200

    # --- summaries and tags (bonus coverage) ---

    def test_health_summary(self, endpoints_by_key):
        assert endpoints_by_key[("GET", "/health")]["summary"] == "Health check"

    def test_health_tags(self, endpoints_by_key):
        assert endpoints_by_key[("GET", "/health")]["tags"] == ["system"]

    def test_post_users_tags(self, endpoints_by_key):
        assert endpoints_by_key[("POST", "/users")]["tags"] == ["users"]

    # --- error handling ---

    def test_missing_file_does_not_crash(self, agent):
        with pytest.raises(FileNotFoundError):
            agent.scan_endpoints("nonexistent_file.py")


# ===========================================================================
# 2.  generate_openapi — OpenAPI 3.0.3 document
# ===========================================================================

class TestGenerateOpenAPI:

    # --- top-level structure ---

    def test_openapi_version(self, openapi):
        assert openapi["openapi"] == "3.0.3"

    def test_info_title(self, openapi):
        assert openapi["info"]["title"] == "Sample API"

    def test_info_version(self, openapi):
        assert openapi["info"]["version"] == "1.0.0"

    def test_info_description_present(self, openapi):
        assert openapi["info"].get("description")

    # --- paths ---

    def test_path_health_exists(self, paths):
        assert "/health" in paths

    def test_path_users_user_id_exists(self, paths):
        assert "/users/{user_id}" in paths

    def test_path_users_exists(self, paths):
        assert "/users" in paths

    def test_health_has_get_operation(self, paths):
        assert "get" in paths["/health"]

    def test_users_user_id_has_get_operation(self, paths):
        assert "get" in paths["/users/{user_id}"]

    def test_users_has_post_operation(self, paths):
        assert "post" in paths["/users"]

    # --- operation IDs ---

    def test_health_operation_id(self, paths):
        assert paths["/health"]["get"]["operationId"] == "health_check_get"

    def test_get_user_operation_id(self, paths):
        assert paths["/users/{user_id}"]["get"]["operationId"] == "get_user_get"

    def test_create_user_operation_id(self, paths):
        assert paths["/users"]["post"]["operationId"] == "create_user_post"

    # --- parameter schemas ---

    def _get_user_params(self, paths) -> dict:
        return {
            p["name"]: p
            for p in paths["/users/{user_id}"]["get"].get("parameters", [])
        }

    def test_user_id_in_path(self, paths):
        params = self._get_user_params(paths)
        assert params["user_id"]["in"] == "path"

    def test_user_id_required_true(self, paths):
        params = self._get_user_params(paths)
        assert params["user_id"]["required"] is True

    def test_user_id_schema_type_integer(self, paths):
        params = self._get_user_params(paths)
        assert params["user_id"]["schema"]["type"] == "integer"

    def test_include_posts_in_query(self, paths):
        params = self._get_user_params(paths)
        assert params["include_posts"]["in"] == "query"

    def test_include_posts_required_false(self, paths):
        params = self._get_user_params(paths)
        assert params["include_posts"]["required"] is False

    def test_include_posts_schema_type_boolean(self, paths):
        params = self._get_user_params(paths)
        assert params["include_posts"]["schema"]["type"] == "boolean"

    def test_include_posts_schema_default_false(self, paths):
        params = self._get_user_params(paths)
        assert params["include_posts"]["schema"]["default"] is False

    # --- request body ---

    def test_post_users_request_body_required(self, paths):
        rb = paths["/users"]["post"]["requestBody"]
        assert rb["required"] is True

    def test_post_users_request_body_ref_UserCreate(self, paths):
        ref = (
            paths["/users"]["post"]["requestBody"]
            ["content"]["application/json"]["schema"]["$ref"]
        )
        assert ref == "#/components/schemas/UserCreate"

    # --- responses ---

    def test_post_users_response_key_is_201(self, paths):
        assert "201" in paths["/users"]["post"]["responses"]

    def test_post_users_201_refs_UserResponse(self, paths):
        ref = (
            paths["/users"]["post"]["responses"]
            ["201"]["content"]["application/json"]["schema"]["$ref"]
        )
        assert ref == "#/components/schemas/UserResponse"

    def test_health_response_refs_HealthResponse(self, paths):
        ref = (
            paths["/health"]["get"]["responses"]
            ["200"]["content"]["application/json"]["schema"]["$ref"]
        )
        assert ref == "#/components/schemas/HealthResponse"

    def test_get_user_response_refs_UserDetailResponse(self, paths):
        ref = (
            paths["/users/{user_id}"]["get"]["responses"]
            ["200"]["content"]["application/json"]["schema"]["$ref"]
        )
        assert ref == "#/components/schemas/UserDetailResponse"

    # --- tags ---

    def test_health_tags(self, paths):
        assert paths["/health"]["get"]["tags"] == ["system"]

    def test_post_users_tags(self, paths):
        assert paths["/users"]["post"]["tags"] == ["users"]

    # --- JSON serializability ---

    def test_openapi_doc_is_json_serializable(self, openapi):
        serialized = json.dumps(openapi)
        assert isinstance(serialized, str)
        assert len(serialized) > 0


# ===========================================================================
# 3.  components/schemas
# ===========================================================================

class TestSchemas:

    @pytest.mark.parametrize("model_name", [
        "UserCreate",
        "UserResponse",
        "PostSummary",
        "UserDetailResponse",
        "HealthResponse",
    ])
    def test_schema_exists(self, schemas, model_name):
        assert model_name in schemas

    # --- UserCreate field types ---

    def test_UserCreate_name_is_string(self, schemas):
        assert schemas["UserCreate"]["properties"]["name"]["type"] == "string"

    def test_UserCreate_email_is_string(self, schemas):
        assert schemas["UserCreate"]["properties"]["email"]["type"] == "string"

    def test_UserCreate_age_is_integer(self, schemas):
        assert schemas["UserCreate"]["properties"]["age"]["type"] == "integer"

    # --- UserCreate required fields ---

    def test_UserCreate_required_fields(self, schemas):
        required = sorted(schemas["UserCreate"]["required"])
        assert required == ["age", "email", "name"]

    # --- UserDetailResponse.posts is nullable, array, refs PostSummary ---

    def test_UserDetailResponse_posts_is_nullable(self, schemas):
        posts = schemas["UserDetailResponse"]["properties"]["posts"]
        assert posts.get("nullable") is True

    def test_UserDetailResponse_posts_is_array(self, schemas):
        posts = schemas["UserDetailResponse"]["properties"]["posts"]
        assert posts.get("type") == "array"

    def test_UserDetailResponse_posts_items_ref_PostSummary(self, schemas):
        items = schemas["UserDetailResponse"]["properties"]["posts"]["items"]
        assert "$ref" in items
        assert "PostSummary" in items["$ref"]

    def test_UserDetailResponse_posts_not_required(self, schemas):
        required = schemas["UserDetailResponse"].get("required", [])
        assert "posts" not in required


# ===========================================================================
# 4.  generate_examples
# ===========================================================================

class TestGenerateExamples:

    @pytest.fixture(scope="class")
    def examples(self, agent: APIAgent) -> list[dict]:
        return agent.generate_examples(FIXTURE)

    def test_three_examples_generated(self, examples):
        assert len(examples) == 3

    def test_all_fixture_paths_covered(self, examples):
        example_paths = {e["path"] for e in examples}
        assert "/health" in example_paths
        assert "/users/{user_id}" in example_paths
        assert "/users" in example_paths

    def test_user_id_example_is_integer(self, examples):
        user_ex = next(e for e in examples if e["path"] == "/users/{user_id}")
        assert isinstance(user_ex["parameters"]["user_id"], int)

    def test_include_posts_example_is_bool(self, examples):
        user_ex = next(e for e in examples if e["path"] == "/users/{user_id}")
        assert isinstance(user_ex["parameters"]["include_posts"], bool)

    def test_post_users_has_request_body(self, examples):
        post_ex = next(e for e in examples if e["path"] == "/users")
        assert "request" in post_ex

    def test_health_has_no_parameters(self, examples):
        health_ex = next(e for e in examples if e["path"] == "/health")
        assert "parameters" not in health_ex or not health_ex.get("parameters")


# ===========================================================================
# 5.  run() — team-standard result envelope
# ===========================================================================

class TestRun:

    @pytest.fixture(scope="class")
    def result(self, agent: APIAgent) -> dict:
        return agent.run(FIXTURE)

    def test_agent_name(self, result):
        assert result["agent"] == "api_agent"

    def test_status_success(self, result):
        assert result["status"] == "success"

    def test_output_is_dict(self, result):
        assert isinstance(result["output"], dict)

    def test_output_has_endpoints_key(self, result):
        assert "endpoints" in result["output"]

    def test_output_has_openapi_key(self, result):
        assert "openapi" in result["output"]

    def test_output_has_examples_key(self, result):
        assert "examples" in result["output"]

    def test_output_endpoints_count(self, result):
        assert len(result["output"]["endpoints"]) == 3

    def test_output_examples_count(self, result):
        assert len(result["output"]["examples"]) == 3

    def test_no_errors(self, result):
        assert result["errors"] == []

    def test_no_warnings(self, result):
        assert result["warnings"] == []

    def test_run_missing_file_returns_error(self, agent: APIAgent):
        err = agent.run("nonexistent.py")
        assert err["status"] == "error"
        assert err["errors"]
        assert "nonexistent.py" in err["errors"][0]

    # --- override metadata ---

    def test_generate_openapi_title_override(self, agent: APIAgent):
        spec = agent.generate_openapi(FIXTURE, title="Custom Title")
        assert spec["info"]["title"] == "Custom Title"

    def test_generate_openapi_version_override(self, agent: APIAgent):
        spec = agent.generate_openapi(FIXTURE, version="9.9.9")
        assert spec["info"]["version"] == "9.9.9"
