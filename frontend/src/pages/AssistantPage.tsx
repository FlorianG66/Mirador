// Page Assistant (phase 8) : questions en langage naturel sur les données de
// l'entreprise. Le backend répond en lecture seule, avec les droits du membre ;
// la page n'affiche que l'historique personnel et traduit les refus connus
// (assistant non configuré, quota atteint).
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { ApiError } from '../api/client.ts'
import { useAskAssistant, useChatHistory } from '../assistant/queries.ts'
import { useAuth } from '../auth/context.ts'
import { Button } from '../components/ui/Button.tsx'
import { Card, CardContent } from '../components/ui/Card.tsx'
import { PageHeader } from '../components/ui/PageHeader.tsx'
import { Skeleton } from '../components/ui/Skeleton.tsx'
import { cn } from '../lib/utils.ts'

function errorKey(error: unknown): string {
  if (error instanceof ApiError && error.status === 503) return 'assistant.errorUnavailable'
  if (error instanceof ApiError && error.status === 429) return 'assistant.errorQuota'
  return 'assistant.errorGeneric'
}

export function AssistantPage() {
  const { t } = useTranslation()
  const { activeOrganizationId } = useAuth()
  const organizationId = activeOrganizationId ?? ''
  const history = useChatHistory(activeOrganizationId)
  const ask = useAskAssistant(organizationId)
  const [question, setQuestion] = useState('')

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const content = question.trim()
    if (!content || ask.isPending) return
    ask.mutate(content, { onSuccess: () => setQuestion('') })
  }

  const messages = history.data ?? []

  return (
    <div className="space-y-6 p-6">
      <PageHeader title={t('assistant.title')} subtitle={t('assistant.subtitle')} />
      <Card className="max-w-3xl">
        <CardContent className="space-y-4 pt-6">
          <ol aria-live="polite" aria-label={t('assistant.historyLabel')} className="space-y-3">
            {history.isPending && activeOrganizationId ? (
              <Skeleton className="h-16 w-full" />
            ) : messages.length === 0 ? (
              <li className="text-sm text-muted">{t('assistant.empty')}</li>
            ) : (
              messages.map((message) => (
                <li
                  key={message.id}
                  className={cn(
                    'rounded-lg px-4 py-3 text-sm whitespace-pre-wrap',
                    message.role === 'user' ? 'ml-12 bg-brand/10' : 'mr-12 bg-muted/40',
                  )}
                >
                  <span className="mb-1 block text-xs font-medium text-muted">
                    {message.role === 'user' ? t('assistant.you') : t('assistant.assistant')}
                  </span>
                  {message.content}
                </li>
              ))
            )}
            {ask.isPending ? (
              <li className="mr-12 text-sm text-muted">{t('assistant.thinking')}</li>
            ) : null}
          </ol>
          {ask.isError ? (
            <p role="alert" className="text-sm text-danger">
              {t(errorKey(ask.error))}
            </p>
          ) : null}
          <form onSubmit={handleSubmit} className="flex gap-2">
            <label className="sr-only" htmlFor="assistant-question">
              {t('assistant.inputLabel')}
            </label>
            <input
              id="assistant-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              maxLength={2000}
              placeholder={t('assistant.placeholder')}
              className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
            />
            <Button type="submit" disabled={ask.isPending || !question.trim()}>
              {t('assistant.send')}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
