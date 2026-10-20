// Tests des utilitaires Web Push (sous-phase 6c-iii-b) : conversion de la clé
// VAPID et détection du support navigateur. Aucun réseau, aucune clé réelle.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { supportsPush, urlBase64ToUint8Array } from './register.ts'

describe('urlBase64ToUint8Array', () => {
  it('décode une clé base64url (sans padding) en octets', () => {
    // « SGVsbG8 » = « Hello » en base64url sans padding.
    const bytes = urlBase64ToUint8Array('SGVsbG8')
    expect(Array.from(bytes)).toEqual([72, 101, 108, 108, 111])
  })

  it('convertit les caractères base64url (- et _) en base64 standard', () => {
    // 0xFB 0xFF se code « +/8 » en base64, donc « -_8 » en base64url.
    const bytes = urlBase64ToUint8Array('-_8')
    expect(Array.from(bytes)).toEqual([251, 255])
  })

  it('renvoie un tableau vide pour une chaîne vide', () => {
    expect(Array.from(urlBase64ToUint8Array(''))).toEqual([])
  })
})

describe('supportsPush', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('est vrai quand le navigateur expose Service Worker, PushManager et Notification', () => {
    vi.stubGlobal('navigator', { serviceWorker: {} })
    vi.stubGlobal('PushManager', class {})
    vi.stubGlobal('Notification', class {})
    expect(supportsPush()).toBe(true)
  })

  it('est faux quand PushManager manque', () => {
    vi.stubGlobal('navigator', { serviceWorker: {} })
    vi.stubGlobal('Notification', class {})
    expect(supportsPush()).toBe(false)
  })
})
