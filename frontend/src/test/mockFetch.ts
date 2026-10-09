// Stub de fetch global pour les tests : associe des gabarits (méthode + chemin)
// à des réponses simulées, sans réseau. Chaque test déclare ses routes ; le
// setup global rétablit fetch après chaque test (vi.unstubAllGlobals).
import { vi } from 'vitest'

export interface FetchRoute {
  /** Chemin de l'URL (pathname) à faire correspondre. */
  match: RegExp
  /** Réponse simulée ; peut lever pour simuler une panne réseau. */
  respond: (request: Request) => Response
}

/** Remplace fetch global par un faux qui suit `routes` (jeton d'accès non simulé). */
export function stubFetch(routes: FetchRoute[]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const request = input instanceof Request ? input : new Request(input)
    const { pathname } = new URL(request.url)
    const route = routes.find((candidate) => candidate.match.test(pathname))
    if (!route) {
      throw new Error(`Aucune route simulée pour ${request.method} ${pathname}`)
    }
    return route.respond(request)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** Réponse JSON (succès ou échec hors format problème). */
export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

/** Réponse d'erreur RFC 9457 (application/problem+json), comme le backend. */
export function problem(status: number, detail: string): Response {
  return new Response(
    JSON.stringify({
      type: 'about:blank',
      title: status === 401 ? 'Unauthorized' : 'Error',
      status,
      detail,
      instance: '/api/v1',
    }),
    { status, headers: { 'content-type': 'application/problem+json' } },
  )
}
