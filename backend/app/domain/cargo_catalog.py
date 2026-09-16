"""Stable cargo-name catalog used by weighing task entry clients."""

from typing import Final

from app.domain.enums import CargoType


CARGO_CATALOG: Final[dict[CargoType, tuple[str, ...]]] = {
    CargoType.COAL: (
        "其他烟煤",
        "未制成型炼焦煤",
        "无烟煤",
        "原煤",
        "炼焦煤",
        "其他煤炭",
    ),
    CargoType.ORE: (
        "铁矿石",
        "铁精粉",
        "铜矿粉",
        "萤石",
        "锌精粉",
        "锂矿石",
        "锰矿石",
        "铅矿石",
        "钼矿石",
        "钨矿石",
        "石墨",
        "石棉",
        "磷矿",
        "石膏",
        "其他矿物",
    ),
    CargoType.TIMBER: (
        "红松原木",
        "落叶松原木",
        "樟子松原木",
        "白松原木",
        "云杉原木",
        "冷杉原木",
        "桦木原木",
        "杨木原木",
        "鱼鳞松原木",
        "雪松原木",
        "柏木原木",
        "杉木原木",
        "水曲柳原木",
        "柞木原木",
        "松木板材",
        "杉木板材",
        "木方",
        "方木",
        "枕木",
        "其他木材",
    ),
    CargoType.OTHER: (),
}


def get_cargo_catalog() -> dict[str, list[str]]:
    """Return a JSON-ready copy so callers cannot mutate domain constants."""
    return {
        cargo_type.value: list(names)
        for cargo_type, names in CARGO_CATALOG.items()
    }
