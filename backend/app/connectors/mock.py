"""Connecteurs de démonstration : une entreprise fictive cohérente et réaliste
(saisonnalité, tendances, quelques anomalies), déterministe via le seed (SPEC §5.4).

Un même seed produit toujours les mêmes séries : c'est ce qui rend les tests et
la démo reproductibles, et permet de donner des données stables à chaque
organisation de démonstration.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from app.connectors.base import Connector, ConnectorHealth
from app.models.enums import Module
from app.schemas.metrics import PERIOD_DAY, MetricPoint, MetricSeries

# Époque de référence des séries : aucun point avant cette date (Les données
# fictives racontent l'entreprise depuis sa création en 2020).
CREATION_EPOCH = date(2020, 1, 1)
# Un jour : le pas standard des séries de démonstration (P1D).
_DAY = timedelta(days=1)
# Chance quotidienne d'une anomalie (un jour « hors norme » dans la série).
_ANOMALY_RATE = 0.03


@dataclass(frozen=True)
class MockMetricConfig:
    """Paramètres de réalisme d'une métrique de démonstration.

    La valeur d'un jour prend la forme `base × tendance × saison × semaine × bruit`,
    avec parfois une anomalie ; elle dérive uniquement du seed et de la date.
    """

    key: str
    unit: str
    base: float
    # Tendance annuelle relative (ex. 0.12 → +12 %/an depuis l'époque de référence).
    trend: float
    # Amplitude de la saisonnalité annuelle (sinusoïde, en fraction de la valeur).
    seasonality: float
    # Facteur du week-end (ex. 0.6 → 40 % de moins le samedi/dimanche).
    weekend_factor: float
    # Amplitude du bruit quotidien (fraction autour de la valeur de base).
    noise: float
    # True : la valeur est un cumul depuis CREATION_EPOCH (ex. nombre d'abonnés).
    cumulative: bool = False
    # Nombre de décimales de la valeur arrondie (0 → entier).
    decimals: int = 0
    # False : pas d'anomalie quotidienne (ex. une cible de budget doit rester lisse).
    anomalies: bool = True


# Une métrique de démonstration par module « simple » (SPÉC §5.4, §3). Finance,
# web et réseaux sociaux produisent un écosystème plus riche dans `finance.py`,
# `web.py` et `social.py`.
MOCK_METRICS: tuple[MockMetricConfig, ...] = (
    MockMetricConfig(
        key="projects.tasks_done",
        unit="tasks",
        base=18,
        trend=0.08,
        seasonality=0.08,
        weekend_factor=0.20,
        noise=0.25,
    ),
)


def hash01(seed: int, *parts: object) -> float:
    """Valeur pseudo-aléatoire stable dans [0, 1) dérivée du seed et des parts."""
    payload = "|".join(str(part) for part in (seed, *parts))
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def daily_value(seed: int, config: MockMetricConfig, day: date) -> float:
    """Valeur d'un jour : base × tendance × saison × semaine × bruit × (anomalie)."""
    elapsed_years = max(day.toordinal() - CREATION_EPOCH.toordinal(), 0) / 365.25
    trend = 1.0 + config.trend * elapsed_years

    year_day = day.timetuple().tm_yday - 1
    year_length = 366 if (day.year % 4 == 0 and day.year % 100 != 0) or day.year % 400 == 0 else 365
    season = 1.0 + config.seasonality * math.sin(2.0 * math.pi * year_day / year_length)

    weekday_factor = config.weekend_factor if day.weekday() >= 5 else 1.0

    noise = 1.0 + config.noise * (2.0 * hash01(seed, config.key, day) - 1.0)

    value = config.base * trend * season * weekday_factor * noise

    # Une petite probabilité d'anomalie : un jour nettement au-dessus de la norme.
    if config.anomalies and hash01(seed, config.key, day) < _ANOMALY_RATE:
        value *= 1.5 + 2.0 * hash01(seed, config.key, "spike")

    return round(value, config.decimals)


def cumulative_value(seed: int, config: MockMetricConfig, day: date) -> float:
    """Cumul déterministe (ex. abonnés) : croissance hebdomadaire depuis l'époque.

    Le cumul est indépendant du nombre de jours demandés : la valeur d'un jour
    ne dépend que du seed et de la date.
    """
    weeks = max(day.toordinal() - CREATION_EPOCH.toordinal(), 0) // 7
    total = config.base
    for week in range(weeks + 1):
        growth = config.base * (0.003 + 0.005 * hash01(seed, config.key, "week", week))
        total += growth
    return round(total, config.decimals)


def value_on(seed: int, config: MockMetricConfig, day: date) -> float:
    if config.cumulative:
        return cumulative_value(seed, config, day)
    return daily_value(seed, config, day)


def build_series(seed: int, config: MockMetricConfig, since: datetime) -> MetricSeries:
    """Série quotidienne d'une métrique fictive, du jour de `since` (borné par
    l'époque de référence) au jour courant. Vide si `since` est dans le futur."""
    start = since.date()
    if start < CREATION_EPOCH:
        start = CREATION_EPOCH
    today = datetime.now(UTC).date()
    points = [
        MetricPoint(
            at=datetime.combine(day, time.min, tzinfo=UTC),
            value=value_on(seed, config, day),
        )
        for day in _daterange(start, today)
    ]
    return MetricSeries(key=config.key, unit=config.unit, period=PERIOD_DAY, points=points)


class MockConnector(Connector):
    """Connecteur de démonstration déterministe (SPEC §5.4) basé sur un seed."""

    auth_type = "none"

    @classmethod
    def metric_configs(cls) -> tuple[MockMetricConfig, ...]:
        """Les configurations des métriques de démonstration du module."""
        return tuple(
            config for config in MOCK_METRICS if config.key.startswith(f"{cls.category.value}.")
        )

    async def connect(self) -> None:
        """Rien à ouvrir pour une simulation."""

    async def disconnect(self) -> None:
        """Rien à fermer pour une simulation."""

    async def healthcheck(self) -> ConnectorHealth:
        return ConnectorHealth(status="ok", latency_ms=1, message="Simulation prête.")

    async def handle_webhook(self, payload: dict[str, object]) -> list[MetricSeries]:
        """Les mocks ne reçoivent pas de webhooks : ils répondent une série vide."""
        return []

    async def sync(self, since: datetime) -> list[MetricSeries]:
        """Séries quotidiennes du module, du jour de `since` (au plus tôt à l'époque
        de référence) au jour courant. Vides si `since` est dans le futur."""
        seed = self.seed
        if seed is None:
            # Défense : un connecteur de démonstration n'a de sens que seedé.
            raise RuntimeError("Un connecteur de démonstration doit être instancié avec un seed.")
        series = [build_series(seed, config, since) for config in self.metric_configs()]
        return [series for series in series if series.points]


class MockProjectsConnector(MockConnector):
    """Démo projets/tâches : tâches terminées par jour."""

    provider = "mock.projects"
    category = Module.PROJECTS


# Le mock « simple » (une série par module) : la finance, le web et les réseaux
# sociaux ont leur panneau dédié dans `finance.py` / `web.py` / `social.py`
# (enregistrés dans `app/connectors`).
MOCK_CONNECTORS: tuple[type[MockConnector], ...] = (MockProjectsConnector,)


def _daterange(start: date, end: date) -> Iterator[date]:
    """Itère sur les jours inclus entre `start` et `end`."""
    day = start
    while day <= end:
        yield day
        day += _DAY
