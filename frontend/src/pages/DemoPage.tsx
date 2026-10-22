// Page publique de démonstration (phase 7, SPEC §9) : le visiteur choisit un
// secteur, une organisation fictive est provisionnée côté API et sa session est
// posée en cookie. `/demo/<token>` fait la même chose à partir d'un lien à durée
// limitée généré pour un prospect. Aucune donnée réelle n'est exposée.
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ApiError, api, unwrap } from '../api/client'
import type { components } from '../api/schema'
import { useAuth } from '../auth/context'
import { Button } from '../components/ui/Button'
import { PROJECT_NAME } from '../constants'

type DemoSector = components['schemas']['DemoSector']

const SECTORS: DemoSector[] = ['restaurant', 'agency', 'ecommerce']

/** Message traduit d'une ouverture de démo refusée (lien échu, quota, panne). */
function problemMessage(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiError) {
    if (error.status === 410) return t('demo.expired')
    if (error.status === 429) return t('demo.rateLimited')
  }
  return t('demo.error')
}

export function DemoPage() {
  const { t } = useTranslation()
  const { token } = useParams()
  const navigate = useNavigate()
  const { reload } = useAuth()
  const [selected, setSelected] = useState<DemoSector>('restaurant')
  const [problem, setProblem] = useState<string | null>(null)
  // Évite de rejouer l'échange du lien au second rendu (StrictMode).
  const redeemed = useRef(false)

  const scenarios = useQuery({
    queryKey: ['demo', 'scenarios'],
    queryFn: () => unwrap(api.GET('/api/v1/demo/scenarios')),
    enabled: token === undefined,
  })

  const openDemo = useMutation({
    mutationFn: async () => {
      if (token !== undefined) {
        return unwrap(
          api.POST('/api/v1/demo/links/{token}', {
            params: { path: { token } },
          }),
        )
      }
      return unwrap(api.POST('/api/v1/demo/sessions', { body: { sector: selected } }))
    },
    onSuccess: async () => {
      // Le cookie de session vient d'être posé : recharger `/auth/me` avant de
      // naviguer évite un aller-retour par la page de connexion.
      await reload()
      navigate('/', { replace: true })
    },
    onError: (error) => setProblem(problemMessage(error, t)),
  })

  useEffect(() => {
    if (token === undefined || redeemed.current) return
    redeemed.current = true
    openDemo.mutate()
  }, [token, openDemo])

  const pending = openDemo.isPending

  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-6">
      <section className="w-full max-w-2xl space-y-6 rounded-lg border border-border bg-surface p-6 shadow-card">
        <header className="space-y-2">
          <p className="text-sm font-medium text-brand">{PROJECT_NAME}</p>
          <h1 className="text-2xl font-semibold">{t('demo.title')}</h1>
          <p className="text-sm text-muted">{t('demo.description')}</p>
        </header>

        {token === undefined ? (
          <fieldset className="space-y-3">
            <legend className="text-sm font-medium">{t('demo.sectorLegend')}</legend>
            {scenarios.isPending ? (
              <p className="text-sm text-muted">{t('demo.loading')}</p>
            ) : null}
            {scenarios.isError ? (
              <p role="alert" className="text-sm text-danger">
                {t('demo.error')}
              </p>
            ) : null}
            <div className="grid gap-3 sm:grid-cols-3">
              {SECTORS.map((sector) => {
                const company = scenarios.data?.find((item) => item.key === sector)
                return (
                  <button
                    key={sector}
                    type="button"
                    aria-pressed={selected === sector}
                    onClick={() => setSelected(sector)}
                    className={`rounded-lg border p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand ${
                      selected === sector
                        ? 'border-brand bg-brand/10'
                        : 'border-border bg-background hover:bg-surface-hover'
                    }`}
                  >
                    <span className="block font-medium">{t(`demo.${sector}`)}</span>
                    {company !== undefined ? (
                      <span className="mt-1 block text-xs text-muted">
                        {company.organization_name}
                      </span>
                    ) : null}
                  </button>
                )
              })}
            </div>
          </fieldset>
        ) : (
          <p className="text-sm text-muted">{t('demo.starting')}</p>
        )}

        {problem !== null && (
          <p role="alert" className="text-sm text-danger">
            {problem}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          {token === undefined ? (
            <Button
              type="button"
              onClick={() => openDemo.mutate()}
              disabled={pending || scenarios.isPending}
            >
              {pending ? t('demo.starting') : t('demo.start')}
            </Button>
          ) : null}
          <Link to="/login" className="text-sm text-brand hover:underline">
            {t('demo.backToLogin')}
          </Link>
        </div>
      </section>
    </main>
  )
}
