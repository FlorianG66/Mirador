"""Tests des connecteurs de démonstration (SPEC §5.4).

Vérifie : le déterminisme du seed, le réalisme (tendance, saison, week-end,
anomalies), le format canonique pour chaque module, et le cumul stable de
`social.followers`.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.connectors import registry
from app.connectors.mock import CREATION_EPOCH
from app.schemas.metrics import PERIOD_DAY

# Fenêtre de démonstration : 12 semaines pleines, équilibrées en jours ouvrés.
_WINDOW = timedelta(days=84)
_NOW = datetime.now(UTC)


def _sync(provider: str, seed: int, since: datetime | None = None):
    connector = registry.make(provider, seed=seed)
    return connector.sync(since or _NOW - _WINDOW)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["mock.finance", "mock.web", "mock.social", "mock.projects"])
async def test_sync_produit_des_series_canoniques_par_module(provider: str) -> None:
    connector = registry.make(provider, seed=42)
    series = await connector.sync(_NOW - _WINDOW)

    # Depuis 5a, la finance produit un panneau entier ; les autres modules une série.
    assert len(series) >= 1
    for metric in series:
        assert metric.key.startswith(f"{connector.category.value}.")
        assert metric.period == PERIOD_DAY
        assert metric.unit
        assert metric.points  # au moins un point sur la fenêtre
        # La marge est une différence : un sale week-end peut la rendre négative.
        if metric.key != "finance.margin":
            assert all(point.value >= 0 for point in metric.points)


@pytest.mark.asyncio
async def test_seed_deterministe() -> None:
    since = _NOW - _WINDOW
    first = await registry.make("mock.finance", seed=7).sync(since)
    again = await registry.make("mock.finance", seed=7).sync(since)
    assert first == again


@pytest.mark.asyncio
async def test_seed_different_produit_des_valeurs_differentes() -> None:
    since = _NOW - _WINDOW
    seed_a = (await registry.make("mock.web", seed=1).sync(since))[0]
    seed_b = (await registry.make("mock.web", seed=2).sync(since))[0]
    values_a = [point.value for point in seed_a.points]
    values_b = [point.value for point in seed_b.points]
    assert any(a != b for a, b in zip(values_a, values_b, strict=True))


@pytest.mark.asyncio
async def test_revenu_plus_faible_le_week_end() -> None:
    since = _NOW - _WINDOW
    revenue = (await registry.make("mock.finance", seed=42).sync(since))[0]
    weekend = [p.value for p in revenue.points if p.at.weekday() >= 5]
    weekday = [p.value for p in revenue.points if p.at.weekday() < 5]
    assert weekend and weekday
    assert sum(weekend) / len(weekend) < sum(weekday) / len(weekday)


@pytest.mark.asyncio
async def test_series_contient_une_anomalie() -> None:
    since = _NOW - timedelta(days=200)
    revenue = (await registry.make("mock.finance", seed=42).sync(since))[0]
    values = sorted(point.value for point in revenue.points)
    median = values[len(values) // 2]
    # L'anomalie multiplie la valeur par 1,5 → 3,5 : le pic dépasse 1,5 × médiane.
    assert values[-1] > 1.5 * median


@pytest.mark.asyncio
async def test_abonnes_cumul_croissant_et_stable() -> None:
    followers = (await registry.make("mock.social", seed=42).sync(_NOW - _WINDOW))[0]
    values = [point.value for point in followers.points]
    assert values == sorted(values)  # cumul : jamais de baisse
    assert values[0] >= 1500  # assise initiale au 1er janvier 2020

    # La valeur d'un jour ne dépend pas de la fenêtre demandée.
    single = await registry.make("mock.social", seed=42).sync(followers.points[-1].at)
    assert single[0].points[-1].value == values[-1]


@pytest.mark.asyncio
async def test_tendance_positive_sur_la_finance() -> None:
    # Deux années complètes : la saisonnalité (période annuelle) se compense sur
    # chaque année pleine, la tendance linéaire reste le signal dominant.
    revenue = (await registry.make("mock.finance", seed=42).sync(_NOW - timedelta(days=730)))[0]
    half = len(revenue.points) // 2
    avg_first = sum(p.value for p in revenue.points[:half]) / half
    avg_second = sum(p.value for p in revenue.points[half:]) / (len(revenue.points) - half)
    assert avg_second > avg_first


@pytest.mark.asyncio
async def test_plus_ancien_que_epoch_raccourcit_la_serie() -> None:
    before_epoch = datetime(2019, 12, 31, tzinfo=UTC)
    projects = await registry.make("mock.projects", seed=42).sync(before_epoch)
    assert projects[0].points[0].at.date() == CREATION_EPOCH


@pytest.mark.asyncio
async def test_webhook_mock_est_vide() -> None:
    connector = registry.make("mock.social", seed=1)
    assert await connector.handle_webhook({"event": "anything"}) == []


@pytest.mark.asyncio
async def test_sync_future_retourne_serie_vide() -> None:
    tomorrow = _NOW + timedelta(days=1)
    assert await registry.make("mock.finance", seed=1).sync(tomorrow) == []
