from xpoker_agent.research.registry import SourceRegistry


def test_initial_source_registry_is_valid_and_unique() -> None:
    registry = SourceRegistry.load()

    assert len(registry.records) == 7
    assert len(registry.content_sha256) == 64
    assert len({record.source_id for record in registry.records}) == 7
    assert len({record.url for record in registry.records}) == 7


def test_required_license_boundaries_are_encoded() -> None:
    registry = SourceRegistry.load()
    by_title = {record.title: record for record in registry.records}

    assert by_title["PokerGPT"].license == "MIT"
    assert by_title["dickreuter/Poker"].license == "GPL-3.0"
    assert "reference-only" in by_title["GTO Wizard"].license
    assert (
        "no assumption of asset reuse rights" in by_title["X-Poker - Holdem,Omaha,OFC"].intended_use
    )


def test_repository_sources_are_queryable() -> None:
    registry = SourceRegistry.load()
    repositories = registry.by_type("source_repository")

    assert {record.title for record in repositories} == {"PokerGPT", "dickreuter/Poker"}
