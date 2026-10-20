// Test d'alignement entre le service worker et l'application (6c-iii-b). Le
// service worker (`public/sw.js`) vit hors du bundle React : il ne peut pas
// importer la table de `src/notifications/format.ts`. Les deux traduisent
// pourtant les **mêmes** `kind`, et rien ne doit en manquer : un `kind` oublié
// dans le service worker retomberait sur un message générique. Ce test lit les
// deux fichiers source et exige que chaque `kind` connu de l'application soit
// présent dans la table FR et EN du service worker (et réciproquement).
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

// Vitest est lancé depuis `frontend/` (script `npm test`).
const SW_PATH = resolve(process.cwd(), 'public/sw.js')
const FORMAT_PATH = resolve(process.cwd(), 'src/notifications/format.ts')

/** `kind` reconnus par l'application (clés de `TITLE_BODY_KEYS`). */
function applicationKinds(): string[] {
  const source = readFileSync(FORMAT_PATH, 'utf-8')
  const block = source.slice(source.indexOf('TITLE_BODY_KEYS'))
  return [...block.matchAll(/^ {2}'([a-z_.]+)':/gm)].map((match) => match[1])
}

/** `kind` reconnus par le service worker, dans une langue donnée. */
function serviceWorkerKinds(locale: 'fr' | 'en'): string[] {
  const source = readFileSync(SW_PATH, 'utf-8')
  const start = source.indexOf(`${locale}: {`)
  const block = source.slice(start, source.indexOf('},\n  },', start))
  return [...block.matchAll(/^ {6}'([a-z_.]+)':/gm)].map((match) => match[1])
}

describe('service worker — alignement des kind', () => {
  it('l’application déclare au moins les quatre kind attendus', () => {
    expect(applicationKinds().sort()).toEqual(
      ['alert.threshold', 'goal.achieved', 'goal.off_track', 'legal.diverged'].sort(),
    )
  })

  it('le service worker couvre chaque kind de l’application (FR et EN)', () => {
    // `alert.threshold` éclate en deux variantes côté service worker.
    const expected = applicationKinds().flatMap((kind) =>
      kind === 'alert.threshold' ? ['alert.threshold.above', 'alert.threshold.below'] : [kind],
    )
    for (const locale of ['fr', 'en'] as const) {
      const kinds = serviceWorkerKinds(locale)
      for (const kind of expected) {
        expect(kinds, `kind « ${kind} » manquant en ${locale}`).toContain(kind)
      }
      expect(kinds.length).toBe(expected.length)
    }
  })
})
