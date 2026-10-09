// Page 403 (phase 3c) : affichée quand l'utilisateur est connecté mais n'a pas
// les droits requis (module non autorisé ou page réservée aux admins).
import { ShieldX } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { buttonVariants } from '../components/ui/button-variants.ts'

export function ForbiddenPage() {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">{t('forbidden.title')}</h1>
      </header>
      <EmptyState
        icon={ShieldX}
        title={t('forbidden.title')}
        description={t('forbidden.description')}
        action={
          <Link to="/" className={buttonVariants({ variant: 'secondary', size: 'sm' })}>
            {t('notFound.backHome')}
          </Link>
        }
      />
    </div>
  )
}
