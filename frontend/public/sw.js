// Service worker Web Push (sous-phase 6c-iii-b). Il vit hors du bundle React :
// il ne peut donc pas importer i18next. Le message poussé ne porte jamais de texte
// affichable : il porte un `kind` (clé i18n) et des `params`. Pour respecter la
// règle « aucun texte en dur » (AGENTS.md §7), ce service worker résout le `kind`
// via une table explicite — jamais la clé brute — dans la langue du navigateur.
// La table de `kind` reflète `src/notifications/format.ts` : les deux doivent
// rester alignées (le fichier est public et non importable, donc un test Vitest
// vérifie la correspondance des `kind` en lisant ces deux fichiers source).
//
// Les libellés d'indicateur, eux, restent dans l'application : le corps d'un push
// est donc volontairement générique. Dès que l'utilisateur ouvre l'application, le
// centre de notifications affiche le libellé complet et formaté. Cela évite de
// dupliquer la source de vérité des KPI (`src/pulse/format.ts`).
//
// Aucune dépendance réseau : le contenu du push est chiffré côté serveur et
// déchiffré par le navigateur ; ce fichier ne fait qu'afficher et router le clic.

const MESSAGES = {
  fr: {
    defaultTitle: 'Mirador',
    defaultBody: 'Un événement est survenu dans votre organisation.',
    kinds: {
      'goal.achieved': {
        title: 'Objectif atteint',
        body: 'Un objectif de votre organisation vient d’être atteint.',
      },
      'goal.off_track': {
        title: 'Objectif en dérive',
        body: 'Un objectif de votre organisation s’éloigne de sa cible.',
      },
      'legal.diverged': {
        title: 'Écart sur la fiche légale',
        body: 'Une valeur saisie manuellement diffère du registre officiel.',
      },
      'alert.threshold.above': {
        title: 'Seuil franchi à la hausse',
        body: 'Un indicateur surveillé est passé au-dessus de son seuil.',
      },
      'alert.threshold.below': {
        title: 'Seuil franchi à la baisse',
        body: 'Un indicateur surveillé est passé en dessous de son seuil.',
      },
    },
  },
  en: {
    defaultTitle: 'Mirador',
    defaultBody: 'An event occurred in your organization.',
    kinds: {
      'goal.achieved': {
        title: 'Goal reached',
        body: 'A goal in your organization has just been reached.',
      },
      'goal.off_track': {
        title: 'Goal off track',
        body: 'A goal in your organization is drifting from its target.',
      },
      'legal.diverged': {
        title: 'Legal record discrepancy',
        body: 'A manually entered value differs from the official registry.',
      },
      'alert.threshold.above': {
        title: 'Threshold exceeded',
        body: 'A monitored metric has risen above its threshold.',
      },
      'alert.threshold.below': {
        title: 'Threshold fallen below',
        body: 'A monitored metric has dropped below its threshold.',
      },
    },
  },
}

/** Clé de message d'un événement : `alert.threshold` se scinde selon le sens. */
function kindKey(kind, params) {
  if (kind === 'alert.threshold') {
    const comparison = params && params.comparison === 'below' ? 'below' : 'above'
    return `alert.threshold.${comparison}`
  }
  return kind
}

/** Texte (titre + corps) d'un message poussé, dans la langue du navigateur. */
function describe(payload) {
  const lang = (self.navigator && self.navigator.language) || 'fr'
  const locale = lang.toLowerCase().startsWith('en') ? 'en' : 'fr'
  const table = MESSAGES[locale]
  const params = (payload && payload.params) || {}
  const entry = table.kinds[kindKey(payload && payload.kind, params)]
  if (!entry) {
    return { title: table.defaultTitle, body: table.defaultBody }
  }
  return { title: entry.title, body: entry.body }
}

self.addEventListener('push', (event) => {
  let payload = {}
  try {
    payload = event.data ? event.data.json() : {}
  } catch (error) {
    payload = {}
  }
  const text = describe(payload)
  event.waitUntil(
    self.registration.showNotification(text.title, {
      body: text.body,
      icon: '/icon.svg',
      badge: '/icon.svg',
      // La cible du clic accompagne la notification (jamais devinée).
      data: { link: (payload && payload.link) || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const link = (event.notification.data && event.notification.data.link) || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        // Un onglet déjà ouvert sur l'application : on le ramène au premier plan.
        if ('focus' in client && client.url.startsWith(self.location.origin)) {
          client.navigate(link)
          return client.focus()
        }
      }
      return self.clients.openWindow(link)
    }),
  )
})
