"""Cargo catalog coverage and immutable-copy behavior."""

from fastapi.testclient import TestClient

from app.domain.cargo_catalog import CARGO_CATALOG, get_cargo_catalog
from app.domain.enums import CargoType


def test_every_cargo_type_has_a_catalog() -> None:
    assert set(CARGO_CATALOG) == set(CargoType)
    assert "铁矿石" in CARGO_CATALOG[CargoType.ORE]
    assert "原煤" in CARGO_CATALOG[CargoType.COAL]
    assert "落叶松原木" in CARGO_CATALOG[CargoType.TIMBER]
    assert CARGO_CATALOG[CargoType.OTHER] == ()


def test_switching_cargo_type_returns_the_matching_choices() -> None:
    catalog = get_cargo_catalog()

    assert "铁精粉" in catalog["ORE"]
    assert "铁精粉" not in catalog["TIMBER"]
    assert "樟子松原木" in catalog["TIMBER"]
    assert catalog["OTHER"] == []


def test_catalog_api_returns_all_categories(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/weighing/cargo-catalog")

    assert response.status_code == 200
    assert set(response.json()) == {item.value for item in CargoType}
