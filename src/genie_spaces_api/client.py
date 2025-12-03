"""
Databricks Genie Spaces API Client.

Provides a high-level interface for exporting, importing, and updating Genie Spaces
via the Databricks REST API.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from genie_spaces_api.models import GenieSpaceExport, SpaceResponse


class GenieSpacesError(Exception):
    """Base exception for Genie Spaces API errors."""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AuthenticationError(GenieSpacesError):
    """Raised when authentication fails."""

    pass


class NotFoundError(GenieSpacesError):
    """Raised when a resource is not found."""

    pass


class ValidationError(GenieSpacesError):
    """Raised when request validation fails."""

    pass


class GenieSpacesClient:
    """Client for the Databricks Genie Spaces Import/Export API.

    This client provides methods to:
    - Export existing Genie Spaces as serialized JSON
    - Import new Genie Spaces from serialized configurations
    - Update existing Genie Spaces with new configurations

    Example:
        ```python
        from genie_spaces_api import GenieSpacesClient

        # Initialize client
        client = GenieSpacesClient(
            host="https://your-workspace.cloud.databricks.com",
            token="your-personal-access-token"
        )

        # Export a space
        space = client.export_space("space-id-here")
        print(space.title)

        # Get the parsed configuration
        config = space.get_export()
        print(config.data_sources.tables)
        ```
    """

    API_VERSION = "2.0"
    BASE_PATH = f"/api/{API_VERSION}/genie/spaces"

    def __init__(
        self,
        host: str | None = None,
        token: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the Genie Spaces client.

        Args:
            host: Databricks workspace URL (e.g., "https://your-workspace.cloud.databricks.com").
                  Falls back to DATABRICKS_HOST environment variable.
            token: Personal access token for authentication.
                   Falls back to DATABRICKS_TOKEN environment variable.
            timeout: Request timeout in seconds (default: 30).

        Raises:
            ValueError: If host or token is not provided and not found in environment.
        """
        self.host = (host or os.environ.get("DATABRICKS_HOST", "")).rstrip("/")
        self.token = token or os.environ.get("DATABRICKS_TOKEN", "")

        if not self.host:
            raise ValueError(
                "Databricks host is required. Provide 'host' parameter or set DATABRICKS_HOST."
            )
        if not self.token:
            raise ValueError(
                "Databricks token is required. Provide 'token' parameter or set DATABRICKS_TOKEN."
            )

        self._client = httpx.Client(
            base_url=self.host,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def __enter__(self) -> GenieSpacesClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise appropriate exceptions."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            data = {"raw": response.text}

        if response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed. Check your token and permissions.",
                status_code=response.status_code,
                response=data,
            )
        elif response.status_code == 404:
            raise NotFoundError(
                f"Resource not found: {data.get('message', 'Unknown')}",
                status_code=response.status_code,
                response=data,
            )
        elif response.status_code == 400:
            raise ValidationError(
                f"Validation error: {data.get('message', 'Unknown')}",
                status_code=response.status_code,
                response=data,
            )
        elif response.status_code >= 400:
            raise GenieSpacesError(
                f"API error: {data.get('message', response.text)}",
                status_code=response.status_code,
                response=data,
            )

        return data

    # =========================================================================
    # Export Operations
    # =========================================================================

    def export_space(self, space_id: str) -> SpaceResponse:
        """Export a Genie Space as a serialized configuration.

        Args:
            space_id: The unique identifier of the Genie Space to export.

        Returns:
            SpaceResponse containing the space metadata and serialized configuration.

        Raises:
            NotFoundError: If the space does not exist.
            AuthenticationError: If authentication fails or user lacks permissions.

        Example:
            ```python
            space = client.export_space("01234567-89ab-cdef-0123-456789abcdef")

            # Access the parsed configuration
            export = space.get_export()
            for table in export.data_sources.tables:
                print(f"Table: {table.identifier}")
            ```
        """
        response = self._client.get(
            f"{self.BASE_PATH}/{space_id}",
            params={"include_serialized_space": "true"},
        )
        data = self._handle_response(response)
        return SpaceResponse.model_validate(data)

    def export_space_to_file(self, space_id: str, output_path: str | Path) -> GenieSpaceExport:
        """Export a Genie Space and save to a JSON file.

        Args:
            space_id: The unique identifier of the Genie Space to export.
            output_path: Path where the JSON file will be saved.

        Returns:
            The parsed GenieSpaceExport object.

        Example:
            ```python
            export = client.export_space_to_file(
                space_id="my-space-id",
                output_path="./exports/my-space.json"
            )
            ```
        """
        space = self.export_space(space_id)
        export = space.get_export()

        if export is None:
            raise GenieSpacesError("Space export returned empty serialized_space")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        export.to_file(str(output_path))

        return export

    # =========================================================================
    # Import Operations
    # =========================================================================

    def import_space(
        self,
        warehouse_id: str,
        parent_path: str,
        serialized_space: str | GenieSpaceExport,
        title: str | None = None,
        description: str | None = None,
    ) -> SpaceResponse:
        """Create a new Genie Space from a serialized configuration.

        Args:
            warehouse_id: SQL warehouse ID for the space.
            parent_path: Workspace path where the space will be created
                        (e.g., "/Workspace/Users/user@company.com/Genie Spaces").
            serialized_space: The exported configuration as JSON string or GenieSpaceExport.
            title: Optional display title (overrides title in serialized_space).
            description: Optional description (overrides description in serialized_space).

        Returns:
            SpaceResponse containing the newly created space metadata.

        Raises:
            ValidationError: If the request is invalid.
            AuthenticationError: If authentication fails.

        Example:
            ```python
            # Import from file
            with open("my-space.json") as f:
                config = f.read()

            new_space = client.import_space(
                warehouse_id="abc123def456",
                parent_path="/Workspace/Users/user@company.com/Genie Spaces",
                serialized_space=config,
                title="My New Space"
            )
            print(f"Created space: {new_space.space_id}")
            ```
        """
        if isinstance(serialized_space, GenieSpaceExport):
            serialized_space = serialized_space.to_json()

        payload: dict[str, Any] = {
            "warehouse_id": warehouse_id,
            "parent_path": parent_path,
            "serialized_space": serialized_space,
        }

        if title:
            payload["title"] = title
        if description:
            payload["description"] = description

        response = self._client.post(self.BASE_PATH, json=payload)
        data = self._handle_response(response)
        return SpaceResponse.model_validate(data)

    def import_space_from_file(
        self,
        warehouse_id: str,
        parent_path: str,
        file_path: str | Path,
        title: str | None = None,
        description: str | None = None,
    ) -> SpaceResponse:
        """Create a new Genie Space from a JSON file.

        Args:
            warehouse_id: SQL warehouse ID for the space.
            parent_path: Workspace path where the space will be created.
            file_path: Path to the JSON file containing the GenieSpaceExport.
            title: Optional display title.
            description: Optional description.

        Returns:
            SpaceResponse containing the newly created space metadata.

        Example:
            ```python
            new_space = client.import_space_from_file(
                warehouse_id="abc123def456",
                parent_path="/Workspace/Users/user@company.com/Genie Spaces",
                file_path="./exports/my-space.json",
                title="Production Space"
            )
            ```
        """
        export = GenieSpaceExport.from_file(str(file_path))
        return self.import_space(
            warehouse_id=warehouse_id,
            parent_path=parent_path,
            serialized_space=export,
            title=title,
            description=description,
        )

    # =========================================================================
    # Update Operations
    # =========================================================================

    def update_space(
        self,
        space_id: str,
        serialized_space: str | GenieSpaceExport | None = None,
        warehouse_id: str | None = None,
        parent_path: str | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> SpaceResponse:
        """Update an existing Genie Space configuration.

        Args:
            space_id: The unique identifier of the Genie Space to update.
            serialized_space: New configuration as JSON string or GenieSpaceExport.
            warehouse_id: New SQL warehouse ID (optional).
            parent_path: New workspace path (optional).
            title: New display title (optional).
            description: New description (optional).

        Returns:
            SpaceResponse containing the updated space metadata.

        Raises:
            NotFoundError: If the space does not exist.
            ValidationError: If the request is invalid.

        Example:
            ```python
            # Export, modify, and update
            space = client.export_space("my-space-id")
            export = space.get_export()

            # Modify the configuration
            export.config.sample_questions.append(
                SampleQuestion.from_text("What is the total revenue?")
            )

            # Update the space
            updated = client.update_space(
                space_id="my-space-id",
                serialized_space=export
            )
            ```
        """
        payload: dict[str, Any] = {}

        if serialized_space is not None:
            if isinstance(serialized_space, GenieSpaceExport):
                serialized_space = serialized_space.to_json()
            payload["serialized_space"] = serialized_space

        if warehouse_id:
            payload["warehouse_id"] = warehouse_id
        if parent_path:
            payload["parent_path"] = parent_path
        if title:
            payload["title"] = title
        if description:
            payload["description"] = description

        response = self._client.patch(f"{self.BASE_PATH}/{space_id}", json=payload)
        data = self._handle_response(response)
        return SpaceResponse.model_validate(data)

    def update_space_from_file(
        self,
        space_id: str,
        file_path: str | Path,
        warehouse_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> SpaceResponse:
        """Update a Genie Space from a JSON file.

        Args:
            space_id: The unique identifier of the Genie Space to update.
            file_path: Path to the JSON file containing the GenieSpaceExport.
            warehouse_id: New SQL warehouse ID (optional).
            title: New display title (optional).
            description: New description (optional).

        Returns:
            SpaceResponse containing the updated space metadata.

        Example:
            ```python
            updated = client.update_space_from_file(
                space_id="my-space-id",
                file_path="./exports/updated-config.json"
            )
            ```
        """
        export = GenieSpaceExport.from_file(str(file_path))
        return self.update_space(
            space_id=space_id,
            serialized_space=export,
            warehouse_id=warehouse_id,
            title=title,
            description=description,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def clone_space(
        self,
        source_space_id: str,
        warehouse_id: str,
        parent_path: str,
        title: str | None = None,
        description: str | None = None,
    ) -> SpaceResponse:
        """Clone a Genie Space to a new location.

        This exports the source space and imports it as a new space.

        Args:
            source_space_id: The space to clone.
            warehouse_id: SQL warehouse ID for the new space.
            parent_path: Workspace path for the new space.
            title: Title for the new space (defaults to source title with " (Copy)").
            description: Description for the new space.

        Returns:
            SpaceResponse containing the newly created space metadata.

        Example:
            ```python
            # Clone a space to a different location
            cloned = client.clone_space(
                source_space_id="source-id",
                warehouse_id="new-warehouse-id",
                parent_path="/Workspace/Users/user@company.com/Genie Spaces",
                title="My Cloned Space"
            )
            ```
        """
        source = self.export_space(source_space_id)
        export = source.get_export()

        if export is None:
            raise GenieSpacesError("Source space export returned empty serialized_space")

        return self.import_space(
            warehouse_id=warehouse_id,
            parent_path=parent_path,
            serialized_space=export,
            title=title or f"{source.title} (Copy)",
            description=description or source.description,
        )

    def diff_spaces(
        self,
        space_id_1: str,
        space_id_2: str,
    ) -> dict[str, Any]:
        """Compare two Genie Spaces and return differences.

        Args:
            space_id_1: First space to compare.
            space_id_2: Second space to compare.

        Returns:
            Dictionary containing the differences between the two spaces.

        Example:
            ```python
            diff = client.diff_spaces("space-1", "space-2")
            print(json.dumps(diff, indent=2))
            ```
        """
        export1 = self.export_space(space_id_1).get_export()
        export2 = self.export_space(space_id_2).get_export()

        if export1 is None or export2 is None:
            raise GenieSpacesError("One or both spaces returned empty exports")

        dict1 = export1.to_dict()
        dict2 = export2.to_dict()

        return {
            "space_1": space_id_1,
            "space_2": space_id_2,
            "config_1": dict1,
            "config_2": dict2,
            # A full diff implementation would go here
            # For now, return both for manual comparison
        }
