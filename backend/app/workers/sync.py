"""Worker de synchronisation des métriques fictives (phase 4c).

`sync_all_organizations` parcourt les organisations existantes et, pour chacune,
synchronise les connecteurs du registre dans sa propre session : tenant posé,
commit, rollback en cas d'erreur. Un échec pour une organisation est journalisé
sans identifiants personnels et n'arrête pas les suivantes.

Depuis la phase 6c-ii, le même passage évalue les objectifs et émet les
notifications correspondantes : la synchro est ce qui fait bouger les métriques,
donc le bon moment pour vérifier les cibles. Depuis la 6c-iii, il évalue aussi
les règles d'alerte configurables (seuils franchis). Depuis la 6c-iii-b, les
notifications émises sont également poussées (Web Push) via l'émetteur injecté.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.tenancy import set_tenant
from app.repositories.organizations import list_organization_ids
from app.services import alert_rules as alert_rules_service
from app.services import demo as demo_service
from app.services import notifications as notifications_service
from app.services.push import PushSender
from app.services.sync import sync_organization

logger = logging.getLogger(__name__)


async def sync_all_organizations(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    push_sender: PushSender | None = None,
) -> None:
    """Synchronise toutes les organisations ; une session isolée par organisation.

    `push_sender` (optionnel) pousse les notifications émises vers les abonnements
    Web Push ; `None` = canal désactivé (l'in-app reste toujours écrit).
    """
    # Remise à zéro du bac à sable (SPEC §9) : les organisations de démonstration
    # échues disparaissent avec leurs données avant la synchro.
    async with session_factory() as session:
        purged = await demo_service.purge_expired_demos(session)
        await session.commit()
    if purged:
        logger.info("Démonstrations expirées purgées : %d", purged)

    async with session_factory() as session:
        organization_ids = await list_organization_ids(session)

    for organization_id in organization_ids:
        try:
            async with session_factory() as session:
                await set_tenant(session, organization_id=organization_id)
                written = await sync_organization(session, organization_id)
                await notifications_service.evaluate_goal_notifications(
                    session, organization_id, push_sender=push_sender
                )
                await alert_rules_service.evaluate_alert_rules(
                    session, organization_id, push_sender=push_sender
                )
                await session.commit()
            logger.info(
                "Synchronisation des métriques : %d point(s) pour %s",
                written,
                organization_id,
            )
        except Exception:
            logger.exception("Synchronisation des métriques en échec pour %s", organization_id)
