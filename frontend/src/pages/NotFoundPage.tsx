// Page 404 : état vide + lien de retour vers la vue d'ensemble.
import { SearchX } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { buttonVariants } from '../components/ui/button-variants.ts'

export function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <EmptyState
      icon={SearchX}
      title={t('notFound.title')}
      description={t('notFound.description')}
      action={
        <Link to="/" className={buttonVariants({ size: 'sm' })}>
          {t('notFound.backHome')}
        </Link>
      }
    />
  )
}
