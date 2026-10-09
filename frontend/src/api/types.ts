// Alias de types métier dérivés du schéma OpenAPI généré (source unique de
// vérité). Évite d'importer `components['schemas'][...]` partout dans l'app.
import type { components } from './schema'

export type MeResponse = components['schemas']['MeResponse']
export type MembershipOut = components['schemas']['MembershipOut']
export type MyPermissionsOut = components['schemas']['MyPermissionsOut']
export type ModuleKey = components['schemas']['Module']
export type PermissionLevel = components['schemas']['PermissionLevel']
export type Role = components['schemas']['Role']
