// Traductions françaises — fichier de référence pour l'anglais.
// Aucun texte visible n'est écrit en dur dans les composants (AGENTS.md §7).
const fr = {
  app: {
    tagline: 'Tableau de bord d’entreprise',
  },
  nav: {
    moduleLabel: 'Modules',
    settingsLabel: 'Paramètres',
    primaryAria: 'Navigation principale',
    dashboard: 'Vue d’ensemble',
    finance: 'Finance',
    web: 'Web analytics',
    social: 'Réseaux sociaux',
    projects: 'Projets & tâches',
    legal: 'Identité légale',
    team: 'Équipe',
    collapse: 'Replier le menu',
    expand: 'Déplier le menu',
  },
  common: {
    themeToggleDark: 'Basculer en mode sombre',
    themeToggleLight: 'Basculer en mode clair',
    openMenu: 'Ouvrir le menu',
    closeMenu: 'Fermer le menu',
    language: 'Langue',
    languageFr: 'Français',
    languageEn: 'English',
    skipToContent: 'Aller au contenu principal',
    retry: 'Réessayer',
    loading: 'Chargement…',
  },
  topbar: {
    breadcrumbAria: 'Fil d’ariane',
    roleAdmin: 'Admin',
    roleMember: 'Membre',
  },
  dashboard: {
    title: 'Vue d’ensemble',
    subtitle: 'Le pouls de votre entreprise, en un coup d’œil.',
    welcomeTitle: 'Bienvenue sur votre tableau de bord',
    welcomeText:
      'Retrouvez ici vos modules et, dès qu’ils seront connectés à vos outils, le pouls de votre activité.',
    quickAccess: 'Accès rapide',
    activityTitle: 'Activité récente',
    activityEmptyTitle: 'Aucune activité pour l’instant',
    activityEmptyDescription: 'Les événements de vos modules apparaîtront ici.',
  },
  login: {
    title: 'Connexion',
    description: 'Connectez-vous pour accéder à votre tableau de bord.',
    email: 'Adresse e-mail',
    password: 'Mot de passe',
    submit: 'Se connecter',
    submitting: 'Connexion…',
    error: 'Identifiants incorrects. Vérifie ton e-mail et ton mot de passe.',
    totpUnsupported:
      "La double authentification n'est pas encore gérée côté interface (prévue en 3d).",
    forgotPassword: 'Mot de passe oublié ?',
    noAccount: 'Pas encore de compte ? S\'inscrire',
  },
  forbidden: {
    title: 'Accès refusé',
    description: "Vous n'avez pas les droits nécessaires pour voir cette page.",
  },
  placeholder: {
    title: 'Module en construction',
    description:
      'Ce module arrivera dans une prochaine phase — le backend est déjà prêt.',
  },
  emptyState: {
    title: 'Rien à afficher pour l’instant',
    description:
      'Les données apparaîtront ici une fois le module connecté à un outil.',
  },
  errorState: {
    title: 'Impossible de charger les données',
    description: 'Une erreur est survenue. Réessayez dans un instant.',
  },
  notFound: {
    title: 'Page introuvable',
    description: 'La page que vous cherchez n’existe pas ou a été déplacée.',
    backHome: 'Retour à la vue d’ensemble',
  },
  register: {
    title: 'Créer un compte',
    description: 'Inscrivez votre organisation en quelques secondes.',
    organizationName: 'Nom de l’organisation',
    siren: 'SIREN (optionnel)',
    email: 'Adresse e-mail',
    password: 'Mot de passe',
    submit: 'Créer mon compte',
    submitting: 'Création…',
    error: 'Une erreur est survenue lors de l’inscription.',
    backToLogin: 'Déjà inscrit ? Se connecter',
  },
  forgotPassword: {
    title: 'Mot de passe oublié',
    description: 'Entrez votre adresse e-mail pour recevoir un lien de réinitialisation.',
    email: 'Adresse e-mail',
    submit: 'Envoyer le lien',
    submitting: 'Envoi…',
    error: 'Une erreur est survenue. Réessayez dans un instant.',
    sentTitle: 'E-mail envoyé',
    sentDescription: 'Si un compte existe avec cette adresse, vous recevrez un e-mail de réinitialisation.',
    backToLogin: 'Retour à la connexion',
  },
  resetPassword: {
    title: 'Nouveau mot de passe',
    description: 'Choisissez un nouveau mot de passe.',
    password: 'Nouveau mot de passe',
    confirmPassword: 'Confirmer le mot de passe',
    submit: 'Réinitialiser',
    submitting: 'Réinitialisation…',
    error: 'Une erreur est survenue.',
    mismatch: 'Les mots de passe ne correspondent pas.',
    invalidTitle: 'Lien invalide',
    invalidDescription: 'Le lien de réinitialisation est invalide ou a expiré.',
    requestNew: 'Demander un nouveau lien',
    backToLogin: 'Retour à la connexion',
  }
}

export default fr
