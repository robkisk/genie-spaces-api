"""Tests for GenieSpacesClient."""

import json
from unittest.mock import patch

import httpx
import pytest
import respx

from genie_spaces_api.client import (
    AuthenticationError,
    GenieSpacesClient,
    GenieSpacesError,
    NotFoundError,
    ValidationError,
)
from genie_spaces_api.models import GenieSpaceExport


@pytest.fixture
def mock_export_response():
    """Sample export response from API."""
    serialized = json.dumps({
        "version": 1,
        "config": {
            "sample_questions": [
                {"id": "abc123", "question": ["Test question?"]}
            ]
        },
        "data_sources": {
            "tables": [
                {"identifier": "catalog.schema.table"}
            ]
        }
    })
    return {
        "space_id": "test-space-123",
        "title": "Test Space",
        "description": "A test space",
        "warehouse_id": "warehouse-456",
        "serialized_space": serialized
    }


class TestClientInitialization:
    """Tests for client initialization."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        client = GenieSpacesClient(
            host="https://test.cloud.databricks.com",
            token="test-token",
        )
        assert client.host == "https://test.cloud.databricks.com"
        assert client.token == "test-token"
        client.close()

    def test_init_strips_trailing_slash(self):
        """Test that trailing slashes are stripped from host."""
        client = GenieSpacesClient(
            host="https://test.cloud.databricks.com/",
            token="test-token",
        )
        assert client.host == "https://test.cloud.databricks.com"
        client.close()

    def test_init_from_env(self):
        """Test initialization from environment variables."""
        with patch.dict("os.environ", {
            "DATABRICKS_HOST": "https://env.cloud.databricks.com",
            "DATABRICKS_TOKEN": "env-token",
        }):
            client = GenieSpacesClient()
            assert client.host == "https://env.cloud.databricks.com"
            assert client.token == "env-token"
            client.close()

    def test_init_missing_host_raises(self):
        """Test that missing host raises ValueError."""
        with patch.dict("os.environ", clear=True):
            with pytest.raises(ValueError, match="host is required"):
                GenieSpacesClient(token="token")

    def test_init_missing_token_raises(self):
        """Test that missing token raises ValueError."""
        with patch.dict("os.environ", clear=True):
            with pytest.raises(ValueError, match="token is required"):
                GenieSpacesClient(host="https://test.com")

    def test_context_manager(self):
        """Test client as context manager."""
        with GenieSpacesClient(
            host="https://test.com",
            token="token",
        ) as client:
            assert client.host == "https://test.com"


class TestExportSpace:
    """Tests for export_space method."""

    @respx.mock
    def test_export_space_success(self, mock_export_response):
        """Test successful space export."""
        respx.get(
            "https://test.com/api/2.0/genie/spaces/space-123",
            params={"include_serialized_space": "true"},
        ).mock(return_value=httpx.Response(200, json=mock_export_response))

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            result = client.export_space("space-123")

        assert result.space_id == "test-space-123"
        assert result.title == "Test Space"
        assert result.warehouse_id == "warehouse-456"

        # Verify parsed export
        export = result.get_export()
        assert export is not None
        assert export.version == 1
        assert len(export.config.sample_questions) == 1

    @respx.mock
    def test_export_space_not_found(self):
        """Test export with non-existent space."""
        respx.get(
            "https://test.com/api/2.0/genie/spaces/nonexistent",
            params={"include_serialized_space": "true"},
        ).mock(return_value=httpx.Response(404, json={"message": "Space not found"}))

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            with pytest.raises(NotFoundError, match="not found"):
                client.export_space("nonexistent")

    @respx.mock
    def test_export_space_auth_error(self):
        """Test export with authentication failure."""
        respx.get(
            "https://test.com/api/2.0/genie/spaces/space-123",
            params={"include_serialized_space": "true"},
        ).mock(return_value=httpx.Response(401, json={"message": "Unauthorized"}))

        with GenieSpacesClient(host="https://test.com", token="bad-token") as client:
            with pytest.raises(AuthenticationError, match="Authentication failed"):
                client.export_space("space-123")


class TestImportSpace:
    """Tests for import_space method."""

    @respx.mock
    def test_import_space_success(self, mock_export_response):
        """Test successful space import."""
        respx.post("https://test.com/api/2.0/genie/spaces").mock(
            return_value=httpx.Response(200, json=mock_export_response)
        )

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            config = GenieSpaceExport(version=1)
            result = client.import_space(
                warehouse_id="warehouse-456",
                parent_path="/Workspace/Users/test/Spaces",
                serialized_space=config,
                title="New Space",
            )

        assert result.space_id == "test-space-123"
        assert result.title == "Test Space"

    @respx.mock
    def test_import_space_from_json_string(self, mock_export_response):
        """Test import with JSON string."""
        respx.post("https://test.com/api/2.0/genie/spaces").mock(
            return_value=httpx.Response(200, json=mock_export_response)
        )

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            json_config = '{"version": 1}'
            result = client.import_space(
                warehouse_id="warehouse-456",
                parent_path="/Workspace/Users/test/Spaces",
                serialized_space=json_config,
            )

        assert result.space_id == "test-space-123"

    @respx.mock
    def test_import_space_validation_error(self):
        """Test import with validation failure."""
        respx.post("https://test.com/api/2.0/genie/spaces").mock(
            return_value=httpx.Response(400, json={"message": "Invalid configuration"})
        )

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            with pytest.raises(ValidationError, match="Validation error"):
                client.import_space(
                    warehouse_id="bad-warehouse",
                    parent_path="/invalid",
                    serialized_space="{}",
                )


class TestUpdateSpace:
    """Tests for update_space method."""

    @respx.mock
    def test_update_space_success(self, mock_export_response):
        """Test successful space update."""
        respx.patch("https://test.com/api/2.0/genie/spaces/space-123").mock(
            return_value=httpx.Response(200, json=mock_export_response)
        )

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            result = client.update_space(
                space_id="space-123",
                title="Updated Title",
            )

        assert result.space_id == "test-space-123"

    @respx.mock
    def test_update_space_with_config(self, mock_export_response):
        """Test update with new configuration."""
        respx.patch("https://test.com/api/2.0/genie/spaces/space-123").mock(
            return_value=httpx.Response(200, json=mock_export_response)
        )

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            config = GenieSpaceExport(version=1)
            result = client.update_space(
                space_id="space-123",
                serialized_space=config,
            )

        assert result.space_id == "test-space-123"


class TestCloneSpace:
    """Tests for clone_space method."""

    @respx.mock
    def test_clone_space_success(self, mock_export_response):
        """Test successful space cloning."""
        # Mock export
        respx.get(
            "https://test.com/api/2.0/genie/spaces/source-123",
            params={"include_serialized_space": "true"},
        ).mock(return_value=httpx.Response(200, json=mock_export_response))

        # Mock import
        clone_response = mock_export_response.copy()
        clone_response["space_id"] = "cloned-456"
        clone_response["title"] = "Test Space (Copy)"
        respx.post("https://test.com/api/2.0/genie/spaces").mock(
            return_value=httpx.Response(200, json=clone_response)
        )

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            result = client.clone_space(
                source_space_id="source-123",
                warehouse_id="new-warehouse",
                parent_path="/Workspace/Shared/Spaces",
            )

        assert result.space_id == "cloned-456"
        assert "Copy" in result.title


class TestErrorHandling:
    """Tests for error handling."""

    @respx.mock
    def test_server_error(self):
        """Test handling of server errors."""
        respx.get(
            "https://test.com/api/2.0/genie/spaces/space-123",
            params={"include_serialized_space": "true"},
        ).mock(return_value=httpx.Response(500, json={"message": "Internal error"}))

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            with pytest.raises(GenieSpacesError, match="API error"):
                client.export_space("space-123")

    @respx.mock
    def test_non_json_response(self):
        """Test handling of non-JSON response."""
        respx.get(
            "https://test.com/api/2.0/genie/spaces/space-123",
            params={"include_serialized_space": "true"},
        ).mock(return_value=httpx.Response(500, text="Server Error"))

        with GenieSpacesClient(host="https://test.com", token="token") as client:
            with pytest.raises(GenieSpacesError):
                client.export_space("space-123")
