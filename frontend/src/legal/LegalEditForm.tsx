// Formulaire de saisie manuelle de la fiche légale (sous-phase 5e-c). N'envoie
// que les champs réellement modifiés : un champ inchangé garde sa provenance
// (registre). Les dirigeants ne sont éditables que par un administrateur.
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { LegalProfile, LegalProfileUpdate } from '../api/types'
import { Button } from '../components/ui/Button.tsx'
import {
  LEGAL_DATE_FIELDS,
  LEGAL_TEXT_FIELDS,
  type LegalTextField,
} from './mentions.ts'

interface DirectorDraft {
  nom: string
  qualite: string
}

export interface LegalEditFormProps {
  profile: LegalProfile
  canEditDirectors: boolean
  isSaving: boolean
  error: string | null
  onCancel: () => void
  onSave: (payload: LegalProfileUpdate) => void
}

function fieldValue(profile: LegalProfile, field: LegalTextField): string {
  const value = profile[field]
  return value === null || value === undefined ? '' : String(value)
}

function initialValues(profile: LegalProfile): Record<LegalTextField, string> {
  return Object.fromEntries(
    LEGAL_TEXT_FIELDS.map((field) => [field, fieldValue(profile, field)]),
  ) as Record<LegalTextField, string>
}

function normalizedDirectors(directors: DirectorDraft[]) {
  return directors
    .filter((director) => director.nom.trim() !== '')
    .map((director) => ({ nom: director.nom.trim(), qualite: director.qualite.trim() || null }))
}

export function LegalEditForm({
  profile,
  canEditDirectors,
  isSaving,
  error,
  onCancel,
  onSave,
}: LegalEditFormProps) {
  const { t } = useTranslation()
  const initial = initialValues(profile)
  const [values, setValues] = useState<Record<LegalTextField, string>>(() => initialValues(profile))
  const [directors, setDirectors] = useState<DirectorDraft[]>(() =>
    (profile.dirigeants ?? []).map((director) => ({
      nom: director.nom,
      qualite: director.qualite ?? '',
    })),
  )

  function buildPayload(): LegalProfileUpdate {
    const updates: Partial<Record<LegalTextField, string>> = {}
    for (const field of LEGAL_TEXT_FIELDS) {
      const current = values[field].trim()
      if (current !== '' && current !== initial[field].trim()) {
        updates[field] = current
      }
    }
    const payload: LegalProfileUpdate = { ...updates }
    if (canEditDirectors) {
      const next = normalizedDirectors(directors)
      const before = normalizedDirectors(
        (profile.dirigeants ?? []).map((director) => ({
          nom: director.nom,
          qualite: director.qualite ?? '',
        })),
      )
      if (JSON.stringify(next) !== JSON.stringify(before)) {
        payload.dirigeants = next
      }
    }
    return payload
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildPayload()
    if (Object.keys(payload).length === 0) {
      onCancel()
      return
    }
    onSave(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {LEGAL_TEXT_FIELDS.map((field) => (
          <label key={field} htmlFor={`legal-${field}`} className="block space-y-1 text-sm">
            <span className="font-medium">{t(`legal.fields.${field}`)}</span>
            <input
              id={`legal-${field}`}
              type={LEGAL_DATE_FIELDS.has(field) ? 'date' : 'text'}
              value={values[field]}
              onChange={(event) =>
                setValues((previous) => ({ ...previous, [field]: event.target.value }))
              }
              className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
            />
          </label>
        ))}
      </div>

      {canEditDirectors ? (
        <div className="space-y-2">
          <p className="text-sm font-medium">{t('legal.directorsTitle')}</p>
          {directors.map((director, index) => (
            <div key={index} className="flex flex-wrap items-end gap-2">
              <label className="block flex-1 space-y-1 text-sm">
                <span className="text-muted">{t('legal.directorName')}</span>
                <input
                  value={director.nom}
                  onChange={(event) =>
                    setDirectors((previous) =>
                      previous.map((item, position) =>
                        position === index ? { ...item, nom: event.target.value } : item,
                      ),
                    )
                  }
                  className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
                />
              </label>
              <label className="block flex-1 space-y-1 text-sm">
                <span className="text-muted">{t('legal.directorRole')}</span>
                <input
                  value={director.qualite}
                  onChange={(event) =>
                    setDirectors((previous) =>
                      previous.map((item, position) =>
                        position === index ? { ...item, qualite: event.target.value } : item,
                      ),
                    )
                  }
                  className="h-10 w-full rounded-md border border-border bg-background px-3 text-foreground outline-none focus-visible:ring-2 focus-visible:ring-brand"
                />
              </label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() =>
                  setDirectors((previous) => previous.filter((_, position) => position !== index))
                }
              >
                {t('legal.removeDirector')}
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setDirectors((previous) => [...previous, { nom: '', qualite: '' }])}
          >
            {t('legal.addDirector')}
          </Button>
        </div>
      ) : null}

      {error !== null ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      <div className="flex items-center gap-2">
        <Button type="submit" disabled={isSaving}>
          {isSaving ? t('legal.editing') : t('legal.save')}
        </Button>
        <Button type="button" variant="secondary" onClick={onCancel} disabled={isSaving}>
          {t('legal.cancel')}
        </Button>
      </div>
    </form>
  )
}
