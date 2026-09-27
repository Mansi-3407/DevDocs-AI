"""
Sample FastAPI application for testing the API endpoint scanner.

This module provides a minimal but realistic FastAPI app with typed endpoints,
Pydantic request/response models, path parameters, query parameters, and
request bodies — covering all the patterns the scanner must detect.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Sample API",
    description="A sample API used as a test fixture for the DevDocs AI scanner.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Request body schema for creating a new user."""

    name: str
    email: str
    age: int


class UserResponse(BaseModel):
    """Response schema representing a user resource."""

    id: int
    name: str
    email: str
    age: int


class PostSummary(BaseModel):
    """A brief summary of a post belonging to a user."""

    post_id: int
    title: str


class UserDetailResponse(BaseModel):
    """Extended user response that optionally includes post summaries."""

    id: int
    name: str
    email: str
    age: int
    posts: list[PostSummary] | None = None


class HealthResponse(BaseModel):
    """Response schema for the health-check endpoint."""

    status: str
    version: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["system"],
)
def health_check() -> HealthResponse:
    """
    Return the current health status of the API.

    Use this endpoint to verify that the service is running and responsive.
    No authentication is required.
    """
    return HealthResponse(status="ok", version="1.0.0")


@app.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="Get a user by ID",
    tags=["users"],
)
def get_user(user_id: int, include_posts: bool = False) -> UserDetailResponse:
    """
    Retrieve a single user by their numeric ID.

    - **user_id**: The unique integer identifier of the user.
    - **include_posts**: When ``True``, the response includes a list of the
      user's post summaries. Defaults to ``False``.
    """
    posts = None
    if include_posts:
        posts = [
            PostSummary(post_id=1, title="Hello World"),
            PostSummary(post_id=2, title="Getting Started"),
        ]

    return UserDetailResponse(
        id=user_id,
        name="Jane Doe",
        email="jane.doe@example.com",
        age=30,
        posts=posts,
    )


@app.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="Create a new user",
    tags=["users"],
)
def create_user(user: UserCreate) -> UserResponse:
    """
    Create a new user resource.

    Accepts a JSON request body conforming to the ``UserCreate`` schema and
    returns the newly created user with its assigned ID.

    - **name**: Full display name of the user.
    - **email**: Unique email address for the user account.
    - **age**: Age of the user in years (must be a positive integer).
    """
    return UserResponse(
        id=42,
        name=user.name,
        email=user.email,
        age=user.age,
    )
