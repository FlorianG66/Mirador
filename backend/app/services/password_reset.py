"""Service de récupération de mot de passe : jeton à usage unique (phase 2c).

Le jeton est remis par l'e-mail (interface `EmailSender`, SMTP en phase 11) et
stocké haché. Sa consommation change le mot de passe et révoque toutes les
sessions du compte : un mot de passe volé, puis réinitialisé, ne vaut plus rien.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PASSWORD_RESET_TOKEN_TTL_SECONDS, PROJECT_NAME
from app.core.security import generate_token, hash_password, hash_token
from app.models.user import User
from app.repositories import password_reset as password_reset_repository
from app.repositories import sessions as sessions_repository
from app.repositories import users as users_repository
from app.services.emails import EmailSender


def _reset_link(base_url: str, token: str) -> str:
    return f"{base_url}/reset-password?token={token}"


async def request_reset(
    session: AsyncSession,
    *,
    email: str,
    base_url: str,
    sender: EmailSender,
) -> bool:
    """Émet le jeton et demande son envoi ; False si l'e-mail est inconnu.

    L'appelant répond ensuite toujours pareil, qu'il y ait envoi ou non
    (anti-énumération : la réponse ne dépend pas de l'existence du compte).
    """
    user = await users_repository.get_user_by_email(session, email)
    if user is None:
        return False
    token = generate_token()
    await password_reset_repository.create_token(
        session,
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(seconds=PASSWORD_RESET_TOKEN_TTL_SECONDS),
    )
    await sender.send(
        to=user.email,
        subject=f"Réinitialisation de votre mot de passe {PROJECT_NAME}",
        content=(
            "Bonjour,\n\n"
            f"Une réinitialisation du mot de passe {PROJECT_NAME} a été demandée "
            f"pour {user.email}.\n"
            f"Ce lien est valable {PASSWORD_RESET_TOKEN_TTL_SECONDS // 60} minutes :\n\n"
            f"{_reset_link(base_url, token)}\n\n"
            "Si vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail.\n"
        ),
    )
    return True


async def reset_password(session: AsyncSession, *, token: str, new_password: str) -> bool:
    """Change le mot de passe si le jeton est présent, inutilisé et non expiré."""
    row = await password_reset_repository.get_by_token_hash(session, hash_token(token))
    now = datetime.now(UTC)
    if row is None or row.used_at is not None or row.expires_at <= now:
        return False
    user = await session.get(User, row.user_id)
    if user is None:
        return False
    user.password_hash = hash_password(new_password)
    await password_reset_repository.mark_used(session, row)
    await sessions_repository.revoke_all_for_user(session, user_id=user.id)
    await session.flush()
    return True
