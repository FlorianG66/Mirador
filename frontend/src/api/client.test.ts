// Tests du client API typé (phase 3c) : en-tête CSRF double-submit, lecture de
// cookie et conversion des erreurs RFC 9457 en ApiError.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, readCookie, unwrap } from './client.ts'
import { json, problem, stubFetch } from '../test/mockFetch.ts'

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = 'mirador_csrf=; Max-Age=0'
})

describe('readCookie', () => {
  it('renvoie la valeur du cookie demandé, sinon null', () => {
    document.cookie = 'mirador_csrf=jeton-visible'
    expect(readCookie('mirador_csrf')).toBe('jeton-visible')
    expect(readCookie('cookie_absent')).toBeNull()
  })
})

describe('en-tête CSRF', () => {
  it('pose x-csrf-token sur une écriture quand le cookie est présent', async () => {
    document.cookie = 'mirador_csrf=jeton-visible'
    const fetchMock = stubFetch([
      { match: /logout$/, respond: () => new Response(null, { status: 204 }) },
    ])

    await api.POST('/api/v1/auth/logout')

    const request = fetchMock.mock.calls[0]?.[0] as Request
    expect(new URL(request.url).pathname).toBe('/api/v1/auth/logout')
    expect(request.method).toBe('POST')
    expect(request.headers.get('x-csrf-token')).toBe('jeton-visible')
  })

  it('omet x-csrf-token quand aucun cookie n’est posé', async () => {
    const fetchMock = stubFetch([
      { match: /logout$/, respond: () => new Response(null, { status: 204 }) },
    ])

    await api.POST('/api/v1/auth/logout')

    const request = fetchMock.mock.calls[0]?.[0] as Request
    expect(request.headers.get('x-csrf-token')).toBeNull()
  })

  it('n’ajoute pas x-csrf-token sur une lecture', async () => {
    document.cookie = 'mirador_csrf=jeton-visible'
    const fetchMock = stubFetch([
      {
        match: /auth\/me$/,
        respond: () => json({ id: 'u1', email: 'a@exemple.fr', memberships: [] }),
      },
    ])

    await api.GET('/api/v1/auth/me')

    const request = fetchMock.mock.calls[0]?.[0] as Request
    expect(request.method).toBe('GET')
    expect(request.headers.get('x-csrf-token')).toBeNull()
  })
})

describe('unwrap', () => {
  it('renvoie les données en cas de succès', async () => {
    const response = json({ ok: true })
    const data = { ok: true }
    await expect(unwrap(Promise.resolve({ data, response }))).resolves.toEqual(data)
  })

  it('transforme une erreur RFC 9457 en ApiError exploitable', async () => {
    const response = problem(401, 'Identifiants incorrects.')
    const error = await response.json()

    const raised = await unwrap(Promise.resolve({ error, response })).catch(
      (reason: unknown) => reason,
    )

    expect(raised).toBeInstanceOf(ApiError)
    expect(raised).toMatchObject({
      status: 401,
      title: 'Unauthorized',
      detail: 'Identifiants incorrects.',
    })
  })
})
