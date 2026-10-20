// Page Fiche légale (sous-phase 5e-c, SPEC §3/§6/§7) : la fiche de l'entreprise
// pré-remplie depuis les registres officiels, avec la provenance et la date de
// chaque donnée, le bloc « mentions légales » copiable, l'export PDF (impression
// du navigateur) et la saisie manuelle. Réservée aux administrateurs pour
// l'édition ; les dirigeants restent visibles des seuls administrateurs.
import { useState } from 'react'
import { Building2, Check, Copy, Pencil, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../auth/context.ts'
import type { LegalProfile, LegalProfileUpdate } from '../api/types.ts'
import { Button } from '../components/ui/Button.tsx'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'
import { Skeleton } from '../components/ui/Skeleton.tsx'
import { LegalEditForm } from '../legal/LegalEditForm.tsx'
import { ProvenanceBadge } from '../legal/ProvenanceBadge.tsx'
import {
  buildMentionsText,
  formatDate,
  hasAnyData,
  LEGAL_TEXT_FIELDS,
  vatIdentifier,
} from '../legal/mentions.ts'
import {
  useLegalProfile,
  useRefreshLegalProfile,
  useUpdateLegalProfile,
} from '../legal/queries.ts'

interface Notice {
  kind: 'success' | 'info' | 'error'
  text: string
}

export function LegalPage() {
  const { t, i18n } = useTranslation()
  const { activeOrganizationId, permissions } = useAuth()
  const organizationId = activeOrganizationId ?? ''
  const profileQuery = useLegalProfile(organizationId)
  const updateMutation = useUpdateLegalProfile(organizationId)
  const refreshMutation = useRefreshLegalProfile(organizationId)
  const [editing, setEditing] = useState(false)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [copied, setCopied] = useState(false)

  const canEdit = permissions?.role === 'admin' || permissions?.modules['legal'] === 'edit'
  const isAdmin = permissions?.role === 'admin'

  if (profileQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.legal')} />
        <LegalSkeleton />
      </div>
    )
  }

  if (profileQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('nav.legal')} subtitle={t('legal.subtitle')} />
        <ErrorState
          title={t('errorState.title')}
          description={t('legal.errorDescription')}
          retryLabel={t('common.retry')}
          onRetry={() => void profileQuery.refetch()}
        />
      </div>
    )
  }

  const profile = profileQuery.data
  const language = i18n.language
  const mentions = buildMentionsText(profile, t)
  const vat = vatIdentifier(profile)

  function handleRefresh() {
    const before = profile
    setNotice(null)
    refreshMutation.mutate(undefined, {
      onSuccess: (data) => {
        const changed = countChangedFields(before, data)
        setNotice(
          changed > 0
            ? { kind: 'success', text: t('legal.refreshDone', { count: changed }) }
            : { kind: 'info', text: t('legal.refreshNoChange') },
        )
      },
      onError: () => setNotice({ kind: 'error', text: t('legal.refreshError') }),
    })
  }

  function handleSave(payload: LegalProfileUpdate) {
    setNotice(null)
    updateMutation.mutate(payload, {
      onSuccess: () => {
        setEditing(false)
        setNotice({ kind: 'success', text: t('legal.saved') })
      },
    })
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(mentions)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  if (!hasAnyData(profile)) {
    return (
      <div className="space-y-6">
        <PageHeader
          title={t('nav.legal')}
          subtitle={t('legal.subtitle')}
          actions={
            canEdit ? (
              <Button
                variant="secondary"
                onClick={() => handleRefresh()}
                disabled={refreshMutation.isPending}
              >
                <RefreshCw aria-hidden="true" className="size-4" />
                {refreshMutation.isPending ? t('legal.refreshing') : t('legal.refresh')}
              </Button>
            ) : null
          }
        />
        <EmptyState
          icon={Building2}
          title={t('legal.emptyTitle')}
          description={t('legal.emptyDescription')}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('nav.legal')}
        subtitle={t('legal.subtitle')}
        printable
        actions={
          <>
            {canEdit ? (
              <Button
                variant="secondary"
                onClick={() => handleRefresh()}
                disabled={refreshMutation.isPending}
              >
                <RefreshCw aria-hidden="true" className="size-4" />
                {refreshMutation.isPending ? t('legal.refreshing') : t('legal.refresh')}
              </Button>
            ) : null}
            {canEdit && !editing ? (
              <Button onClick={() => setEditing(true)}>
                <Pencil aria-hidden="true" className="size-4" />
                {t('legal.edit')}
              </Button>
            ) : null}
          </>
        }
      />

      {notice ? <NoticeBanner notice={notice} /> : null}

      {editing ? (
        <Card>
          <CardHeader>
            <CardTitle>{t('legal.fieldsTitle')}</CardTitle>
          </CardHeader>
          <CardContent>
            <LegalEditForm
              profile={profile}
              canEditDirectors={isAdmin}
              isSaving={updateMutation.isPending}
              error={updateMutation.isError ? t('legal.saveError') : null}
              onCancel={() => setEditing(false)}
              onSave={handleSave}
            />
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-12">
            <Card className="xl:col-span-8">
              <CardHeader>
                <CardTitle>{t('legal.fieldsTitle')}</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="grid gap-4 sm:grid-cols-2">
                  {LEGAL_TEXT_FIELDS.map((field) => {
                    const raw = profile[field]
                    const value =
                      field === 'date_creation'
                        ? formatDate(raw, language)
                        : (raw ?? '')
                    const source = profile.sources?.[field]
                    return (
                      <div key={field} className="space-y-1">
                        <dt className="text-xs font-medium uppercase tracking-wide text-muted">
                          {t(`legal.fields.${field}`)}
                        </dt>
                        <dd className="flex flex-wrap items-center gap-2 text-sm text-foreground">
                          <span>{value !== '' ? value : t('legal.notProvided')}</span>
                          <ProvenanceBadge source={source?.source} syncedAt={source?.synced_at} />
                        </dd>
                      </div>
                    )
                  })}
                  {vat ? (
                    <div className="space-y-1">
                      <dt className="text-xs font-medium uppercase tracking-wide text-muted">
                        {t('legal.vat')}
                      </dt>
                      <dd className="text-sm text-foreground">{vat.valeur}</dd>
                    </div>
                  ) : null}
                </dl>
              </CardContent>
            </Card>

            <Card className="xl:col-span-4">
              <CardHeader>
                <CardTitle>{t('legal.directorsTitle')}</CardTitle>
              </CardHeader>
              <CardContent>
                {profile.dirigeants && profile.dirigeants.length > 0 ? (
                  <ul className="space-y-3">
                    {profile.dirigeants.map((director, index) => (
                      <li key={index} className="text-sm">
                        <p className="font-medium text-foreground">{director.nom}</p>
                        {director.qualite ? (
                          <p className="text-muted">{director.qualite}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted">
                    {isAdmin ? t('legal.directorsEmpty') : t('legal.directorsAdminOnly')}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>{t('legal.mentionsTitle')}</CardTitle>
              <Button variant="secondary" size="sm" onClick={() => void handleCopy()}>
                {copied ? (
                  <Check aria-hidden="true" className="size-4" />
                ) : (
                  <Copy aria-hidden="true" className="size-4" />
                )}
                {copied ? t('legal.copied') : t('legal.copy')}
              </Button>
            </CardHeader>
            <CardContent>
              <pre className="whitespace-pre-wrap font-sans text-sm text-foreground">
                {mentions !== '' ? mentions : t('legal.notProvided')}
              </pre>
              <p className="mt-3 text-xs text-muted">{t('legal.sourceNote')}</p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

/** Bandeau d'information (succès, info, erreur) annoncé aux lecteurs d'écran. */
function NoticeBanner({ notice }: { notice: Notice }) {
  const styles =
    notice.kind === 'error'
      ? 'border-danger/30 bg-danger/5 text-danger'
      : 'border-brand/30 bg-brand-muted text-foreground'
  return (
    <p
      role={notice.kind === 'error' ? 'alert' : 'status'}
      className={`rounded-md border px-4 py-2 text-sm ${styles}`}
    >
      {notice.text}
    </p>
  )
}

/** Nombre de champs texte modifiés entre deux versions de la fiche. */
function countChangedFields(before: LegalProfile, after: LegalProfile): number {
  return LEGAL_TEXT_FIELDS.filter((field) => before[field] !== after[field]).length
}

/** Squelette chargé pendant la première requête de la fiche. */
function LegalSkeleton() {
  return (
    <div className="grid gap-4 xl:grid-cols-12">
      <div className="space-y-4 xl:col-span-8">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
      <div className="xl:col-span-4">
        <Skeleton className="h-40 w-full" />
      </div>
    </div>
  )
}
