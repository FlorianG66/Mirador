// English translations — mirror of the French file.
const en = {
  app: {
    tagline: 'Business dashboard',
  },
  nav: {
    moduleLabel: 'Modules',
    settingsLabel: 'Settings',
    primaryAria: 'Primary navigation',
    dashboard: 'Overview',
    finance: 'Finance',
    web: 'Web analytics',
    social: 'Social media',
    projects: 'Projects & tasks',
    legal: 'Legal identity',
    team: 'Team',
    collapse: 'Collapse menu',
    expand: 'Expand menu',
  },
  common: {
    themeToggleDark: 'Switch to dark mode',
    themeToggleLight: 'Switch to light mode',
    openMenu: 'Open menu',
    closeMenu: 'Close menu',
    language: 'Language',
    languageFr: 'Français',
    languageEn: 'English',
    skipToContent: 'Skip to main content',
    retry: 'Retry',
    loading: 'Loading…',
  },
  topbar: {
    breadcrumbAria: 'Breadcrumb',
    roleAdmin: 'Admin',
    roleMember: 'Member',
  },
  dashboard: {
    title: 'Overview',
    subtitle: 'The pulse of your company, at a glance.',
    welcomeTitle: 'Welcome to your dashboard',
    welcomeText:
      'Find your modules here and, once they are connected to your tools, the pulse of your activity.',
    quickAccess: 'Quick access',
    activityTitle: 'Recent activity',
    activityEmptyTitle: 'No activity yet',
    activityEmptyDescription: 'Events from your modules will show up here.',
  },
  login: {
    title: 'Sign in',
    description: 'Sign in to access your dashboard.',
    email: 'Email address',
    password: 'Password',
    submit: 'Sign in',
    submitting: 'Signing in…',
    error: 'Invalid credentials. Check your email and password.',
    totpUnsupported:
      'Two-factor authentication is not handled in the UI yet (planned for 3d).',
    forgotPassword: 'Forgot password?',
    noAccount: 'No account yet? Sign up',
  },
  forbidden: {
    title: 'Access denied',
    description: "You don't have the required permissions to view this page.",
  },
  placeholder: {
    title: 'Module under construction',
    description:
      'This module is coming in a later phase — the backend is already ready.',
  },
  emptyState: {
    title: 'Nothing to show yet',
    description:
      'Data will appear here once the module is connected to a tool.',
  },
  errorState: {
    title: 'Could not load the data',
    description: 'Something went wrong. Please try again in a moment.',
  },
  notFound: {
    title: 'Page not found',
    description: 'The page you are looking for does not exist or has moved.',
    backHome: 'Back to overview',
  },
  register: {
    title: 'Create an account',
    description: 'Set up your organization in a few seconds.',
    organizationName: 'Organization name',
    siren: 'SIREN (optional)',
    email: 'Email address',
    password: 'Password',
    submit: 'Create my account',
    submitting: 'Creating…',
    error: 'An error occurred during registration.',
    backToLogin: 'Already have an account? Sign in',
  },
  forgotPassword: {
    title: 'Forgot password',
    description: 'Enter your email address to receive a reset link.',
    email: 'Email address',
    submit: 'Send link',
    submitting: 'Sending…',
    error: 'An error occurred. Please try again in a moment.',
    sentTitle: 'Email sent',
    sentDescription: 'If an account exists with this address, you will receive a password reset email.',
    backToLogin: 'Back to sign in',
  },
  resetPassword: {
    title: 'New password',
    description: 'Choose a new password.',
    password: 'New password',
    confirmPassword: 'Confirm password',
    submit: 'Reset',
    submitting: 'Resetting…',
    error: 'An error occurred.',
    mismatch: 'Passwords do not match.',
    invalidTitle: 'Invalid link',
    invalidDescription: 'The reset link is invalid or has expired.',
    requestNew: 'Request a new link',
    backToLogin: 'Back to sign in',
  }
}

export default en
