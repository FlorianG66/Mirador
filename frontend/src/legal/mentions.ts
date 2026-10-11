// Fiche légale (sous-phase 5e-c) : métadonnées des champs, formatage des dates et
// assemblage du bloc « mentions légales ». Aucun texte visible en dur : tout passe
// par le traducteur (AGENTS.md §7).
import type { TFunction } from 'i18next'
import type { LegalIdentifier, LegalProfile } from '../api/types'

/**
 * Champs texte de la fiche, dans l'ordre d'affichage. Reprend exactement les
 * champs de `LegalProfileOut` (le backend les expose à plat) ; `date_creation` est
 * le seul rendu comme une date.
 */
export const LEGAL_TEXT_FIELDS = [
  'raison_sociale',
  'nom_commercial',
  'forme_juridique',
  'siren',
  'siret_siege',
  'date_creation',
  'code_naf',
  'libelle_naf',
  'adresse_siege',
  'tranche_effectif',
  'capital_social',
  'rcs_greffe',
] as const

export type LegalTextField = (typeof LEGAL_TEXT_FIELDS)[number]

/** Champs rendus par un `<input type="date">` (les autres en texte libre). */
export const LEGAL_DATE_FIELDS: ReadonlySet<LegalTextField> = new Set(['date_creation'])

/** Date longue localisée (ex. « 31 août 2026 ») pour un champ date. */
export function formatDate(iso: string | null | undefined, language: string): string {
  if (!iso) return ''
  return new Intl.DateTimeFormat(language, { dateStyle: 'long' }).format(new Date(iso))
}

/** Date et heure localisées (provenance d'un champ : « synchronisé le … »). */
export function formatDateTime(iso: string | null | undefined, language: string): string {
  if (!iso) return ''
  return new Intl.DateTimeFormat(language, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso))
}

/** Identifiant TVA de la fiche (`schema === 'vat'`), s'il existe. */
export function vatIdentifier(profile: LegalProfile): LegalIdentifier | undefined {
  return profile.identifiers?.find((identifier) => identifier.schema === 'vat')
}

/** Vrai dès qu'un champ, un identifiant ou un dirigeant porte une donnée. */
export function hasAnyData(profile: LegalProfile): boolean {
  const hasField = LEGAL_TEXT_FIELDS.some((field) => profile[field] !== null)
  const hasIdentifier = (profile.identifiers?.length ?? 0) > 0
  const hasDirector = (profile.dirigeants?.length ?? 0) > 0
  return hasField || hasIdentifier || hasDirector
}

/**
 * Assemble le texte des « mentions légales » à partir de la fiche (copie en un
 * clic). Les lignes vides sont omises ; les libellés viennent de l'i18n.
 */
export function buildMentionsText(profile: LegalProfile, t: TFunction): string {
  const lines: string[] = []

  if (profile.raison_sociale) {
    lines.push(profile.raison_sociale)
  }

  const identity: string[] = []
  if (profile.forme_juridique) {
    identity.push(profile.forme_juridique)
  }
  if (profile.capital_social) {
    identity.push(`${t('legal.capital')} : ${profile.capital_social}`)
  }
  if (identity.length > 0) {
    lines.push(identity.join(' — '))
  }

  if (profile.adresse_siege) {
    lines.push(profile.adresse_siege)
  }

  const registrations: string[] = []
  if (profile.siren) {
    registrations.push(`${t('legal.siren')} : ${profile.siren}`)
  }
  if (profile.siret_siege) {
    registrations.push(`${t('legal.siret')} : ${profile.siret_siege}`)
  }
  if (registrations.length > 0) {
    lines.push(registrations.join(' — '))
  }

  if (profile.rcs_greffe) {
    lines.push(`${t('legal.rcs')} : ${profile.rcs_greffe}`)
  }

  const vat = vatIdentifier(profile)
  if (vat) {
    lines.push(`${t('legal.vat')} : ${vat.valeur}`)
  }

  return lines.join('\n')
}
