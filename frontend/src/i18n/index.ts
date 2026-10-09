// Instance i18next partagée (FR par défaut, EN disponible). Les composants
// utilisent useTranslation de react-i18next ; charger ce module dans les tests
// initialise l'instance par défaut avant tout rendu. initAsync=false rend
// l'initialisation synchrone (ressources embarquées) : pas de course au premier
// rendu, ni en test ni en navigateur.
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.ts'
import fr from './locales/fr.ts'

i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr },
    en: { translation: en },
  },
  lng: 'fr',
  fallbackLng: 'fr',
  initAsync: false,
  interpolation: {
    // React échappe déjà les valeurs interpolées.
    escapeValue: false,
  },
})

// L'attribut lang de <html> suit la langue active (accessibilité).
document.documentElement.lang = i18n.language
i18n.on('languageChanged', (language) => {
  document.documentElement.lang = language
})

export default i18n
