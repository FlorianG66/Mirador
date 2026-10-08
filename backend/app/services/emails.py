"""Envoi d'e-mails : interface + implémentation de développement (journalisation).

Le MVP n'a pas encore de SMTP (prévu avec les e-mails transactionnels en phase 11) :
en développement, chaque message est journalisé. L'interface rend la bascule
transparente pour les routes et les tests (les tests injectent un faux émetteur).
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    """Envoie un e-mail transactionnel (récupération de compte, bientôt invitations)."""

    async def send(self, *, to: str, subject: str, content: str) -> None: ...


class LogEmailSender:
    """Développement : le message est journalisé, rien n'est expédié."""

    async def send(self, *, to: str, subject: str, content: str) -> None:
        logger.info("e-mail (non expédié) → %s | %s\\n%s", to, subject, content)
