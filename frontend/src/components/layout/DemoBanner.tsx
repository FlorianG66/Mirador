// Bandeau « Démo » (phase 7, SPEC §9) : visible dans toute la coquille tant que
// l'organisation active est fictive. Il rappelle que rien n'est conservé et
// propose l'inscription, sans bloquer l'exploration du produit.
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { useAuth } from '../../auth/context.ts'

export function DemoBanner() {
  const { t } = useTranslation()
  const { user, activeOrganizationId } = useAuth()

  const membership = user?.memberships.find(
    (item) => item.organization_id === activeOrganizationId,
  )
  if (membership?.is_demo !== true) {
    return null
  }

  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-warning/40 bg-warning/10 px-4 py-2 text-sm lg:px-6 print:hidden"
    >
      <span className="font-medium text-foreground">{t('demo.bannerTitle')}</span>
      <span className="text-muted">{t('demo.bannerText')}</span>
      <Link to="/register" className="ml-auto font-medium text-brand hover:underline">
        {t('demo.bannerCta')}
      </Link>
    </div>
  )
}
