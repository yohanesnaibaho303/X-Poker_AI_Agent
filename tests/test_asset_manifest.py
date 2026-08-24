import pytest
from pydantic import ValidationError

from xpoker_agent.research.assets import AssetManifest, AssetRecord


def test_asset_manifest_is_provenance_linked_and_metadata_first() -> None:
    manifest = AssetManifest.load()

    assert len(manifest.records) == 4
    assert len({record.asset_id for record in manifest.records}) == 4
    assert all(record.local_path is None for record in manifest.records)
    assert len(manifest.pending_review) == 1


def test_local_asset_requires_hash_and_path() -> None:
    with pytest.raises(ValidationError, match="require a path and content hash"):
        AssetRecord(
            asset_id="invalid_local_asset",
            source_id="00000000-0000-0000-0000-000000000101",
            kind="frame",
            locator="test",
            retention="permitted_local",
            license_review="approved",
            classification={"street": "flop"},
            confidence=1,
            notes="test",
        )
