// Client API typé (phase 3c) : instance openapi-fetch adossée aux types générés
// depuis OpenAPI, en-tête CSRF double-submit sur les écritures et conversion des
// erreurs RFC 9457 (application/problem+json) en ApiError.
import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'

export const CSRF_COOKIE = 'mirador_csrf'
export const CSRF_HEADER = 'x-csrf-token'

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

/** Lit un cookie lisible par le JS (ici le jeton CSRF double-submit). */
export function readCookie(name: string): string | null {
  const prefix = `${name}=`
  for (const entry of document.cookie.split('; ')) {
    if (entry.startsWith(prefix)) {
      try {
        return decodeURIComponent(entry.slice(prefix.length))
      } catch {
        return entry.slice(prefix.length)
      }
    }
  }
  return null
}

interface ProblemBody {
  type?: unknown
  title?: unknown
  status?: unknown
  detail?: unknown
  instance?: unknown
  errors?: unknown
}

/** Erreur API normalisée à partir d'un corps problem+json (RFC 9457). */
export class ApiError extends Error {
  status: number
  title: string
  detail: string
  type: string
  instance: string
  errors: unknown

  constructor(status: number, problem: ProblemBody = {}) {
    const detail = typeof problem.detail === 'string' ? problem.detail : ''
    super(detail || `Erreur HTTP ${status}`)
    this.name = 'ApiError'
    this.status = typeof problem.status === 'number' ? problem.status : status
    this.title = typeof problem.title === 'string' ? problem.title : ''
    this.detail = detail
    this.type = typeof problem.type === 'string' ? problem.type : ''
    this.instance = typeof problem.instance === 'string' ? problem.instance : ''
    this.errors = problem.errors
  }

  static from(status: number, body: unknown): ApiError {
    if (body && typeof body === 'object') {
      return new ApiError(status, body as ProblemBody)
    }
    return new ApiError(status)
  }
}

/** Résultat possible renvoyé par openapi-fetch (succès ou erreur). */
export interface ApiResult<T> {
  data?: T
  error?: unknown
  response: Response
}

/** Renvoie les données d'un appel réussi, sinon lève une ApiError. */
export async function unwrap<T>(result: Promise<ApiResult<T>>): Promise<T> {
  const resolved = await result
  if (resolved.response.ok) {
    return resolved.data as T
  }
  throw ApiError.from(resolved.response.status, resolved.error)
}

// Ajoute l'en-tête CSRF uniquement sur les méthodes qui modifient l'état et
// seulement si le cookie est présent (double-submit côté client).
const csrfMiddleware: Middleware = {
  onRequest({ request }) {
    if (SAFE_METHODS.has(request.method)) {
      return
    }
    const token = readCookie(CSRF_COOKIE)
    if (token !== null) {
      request.headers.set(CSRF_HEADER, token)
    }
  },
}

// origine courante : l'API est servie sous le même domaine (proxy en dev, reverse
// proxy en prod). `window.location.origin` fournit une URL absolue, nécessaire
// côté client HTTP (y compris en environnement de test).
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  credentials: 'include',
  // indirection : résout `fetch` au moment de l'appel (et non à l'import), ce qui
  // permet aux tests de le remplacer via vi.stubGlobal. openapi-fetch fournit un
  // `Request` déjà complet (méthode, corps, en-têtes).
  fetch: (input) => globalThis.fetch(input),
})
api.use(csrfMiddleware)
