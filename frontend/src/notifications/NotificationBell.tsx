// Centre de notifications de la barre supérieure (sous-phase 6c-ii) : cloche avec
// compteur de non-lus, panneau déroulant listant les notifications personnelles,
// marquage lu / tout lu et navigation vers le module concerné. Aucun texte en dur
// (i18n) et aucune donnée locale : tout vient des endpoints dédiés (AGENTS.md §7,
// §8). Le panneau se ferme au clic extérieur, à Échap, et après navigation.
import { useEffect, useId, useRef, useState } from 'react'
import { Bell, CheckCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { useAuth } from '../auth/context.ts'
import { cn } from '../lib/utils.ts'
import { formatRelativeTime } from '../pulse/format.ts'
import { describeNotification } from './format.ts'
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from './queries.ts'

export function NotificationBell() {
  const { t, i18n } = useTranslation()
  const { activeOrganizationId } = useAuth()
  const [open, setOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const panelId = useId()

  const { data, isLoading, isError } = useNotifications(activeOrganizationId)
  const markRead = useMarkNotificationRead(activeOrganizationId ?? '')
  const markAllRead = useMarkAllNotificationsRead(activeOrganizationId ?? '')

  const items = data?.items ?? []
  const unread = data?.unread_count ?? 0

  // Fermeture au clic extérieur et à la touche Échap tant que le panneau est ouvert.
  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: PointerEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const openItem = (notificationId: string) => {
    markRead.mutate(notificationId)
    setOpen(false)
  }

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={
          unread > 0
            ? t('notifications.openUnread', { count: unread })
            : t('notifications.open')
        }
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={open ? panelId : undefined}
        className="relative inline-flex size-9 items-center justify-center rounded-md text-muted transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
      >
        <Bell aria-hidden="true" className="size-5" />
        {unread > 0 ? (
          <span
            aria-hidden="true"
            data-testid="notifications-badge"
            className="absolute -top-0.5 -right-0.5 inline-flex min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-danger-foreground"
          >
            {unread > 99 ? '99+' : unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <div
          id={panelId}
          role="dialog"
          aria-label={t('notifications.title')}
          className="absolute right-0 z-40 mt-2 w-80 overflow-hidden rounded-lg border border-border bg-surface shadow-raised sm:w-96"
        >
          <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
            <p className="text-sm font-semibold text-foreground">{t('notifications.title')}</p>
            <button
              type="button"
              onClick={() => markAllRead.mutate()}
              disabled={unread === 0 || markAllRead.isPending}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted transition-colors hover:bg-surface-hover hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:cursor-not-allowed disabled:opacity-50"
            >
              <CheckCheck aria-hidden="true" className="size-3.5" />
              {t('notifications.markAllRead')}
            </button>
          </div>

          {isLoading ? (
            <p className="px-3 py-6 text-center text-sm text-muted">{t('notifications.loading')}</p>
          ) : isError ? (
            <p className="px-3 py-6 text-center text-sm text-muted">
              {t('notifications.loadError')}
            </p>
          ) : items.length === 0 ? (
            <div className="px-3 py-6 text-center">
              <p className="text-sm font-medium text-foreground">
                {t('notifications.emptyTitle')}
              </p>
              <p className="mt-1 text-xs text-muted">{t('notifications.emptyDescription')}</p>
            </div>
          ) : (
            <ul className="max-h-96 divide-y divide-border overflow-y-auto">
              {items.map((notification) => {
                const text = describeNotification(notification, t, i18n.language)
                const unreadItem = notification.read_at === null
                const content = (
                  <>
                    <span className="flex items-center gap-2">
                      {unreadItem ? (
                        <span
                          aria-hidden="true"
                          className="size-2 shrink-0 rounded-full bg-brand"
                        />
                      ) : null}
                      <span className="text-sm font-medium text-foreground">{text.title}</span>
                    </span>
                    <span className="block text-xs text-muted">{text.body}</span>
                    <span className="block text-[11px] text-muted">
                      {unreadItem ? `${t('notifications.unread')} · ` : ''}
                      {formatRelativeTime(notification.created_at, i18n.language)}
                    </span>
                  </>
                )
                const baseClass = cn(
                  'block space-y-1 px-3 py-2.5 text-left transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand',
                  unreadItem ? 'bg-surface-hover/40' : undefined,
                )
                return (
                  <li key={notification.id}>
                    {notification.link ? (
                      <Link
                        to={notification.link}
                        className={baseClass}
                        onClick={() => openItem(notification.id)}
                      >
                        {content}
                      </Link>
                    ) : (
                      <button
                        type="button"
                        className={cn(baseClass, 'w-full')}
                        onClick={() => openItem(notification.id)}
                      >
                        {content}
                      </button>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
