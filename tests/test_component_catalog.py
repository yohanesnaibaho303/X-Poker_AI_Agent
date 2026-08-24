from xpoker_agent.research.catalog import ComponentCatalog
from xpoker_agent.research.registry import SourceRegistry


def test_component_catalog_is_unique_and_provenance_linked() -> None:
    sources = SourceRegistry.load()
    catalog = ComponentCatalog.load(sources=sources)
    known_source_ids = {record.source_id for record in sources.records}

    assert len(catalog.records) == 12
    assert len({record.component_id for record in catalog.records}) == 12
    assert all(set(record.source_ids) <= known_source_ids for record in catalog.records)


def test_unverified_critical_components_remain_explicit() -> None:
    catalog = ComponentCatalog.load()
    unresolved = {record.component_id for record in catalog.unresolved_critical}

    assert unresolved == set()


def test_no_public_description_is_treated_as_control_calibration() -> None:
    catalog = ComponentCatalog.load()

    action_controls = next(
        record for record in catalog.records if record.component_id == "action_buttons"
    )
    assert action_controls.verification == "public_frame_observed"
    assert action_controls.confidence < 0.9
