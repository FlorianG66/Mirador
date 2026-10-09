// Règle d'accès en lecture à un module, partagée par le rail de navigation et
// le tableau de bord (un admin a tous les droits).
import type { ModuleKey, MyPermissionsOut } from '../api/types.ts'

export function canSeeModule(
  moduleKey: ModuleKey,
  permissions: MyPermissionsOut | null,
): boolean {
  if (!permissions) {
    return false
  }
  if (permissions.role === 'admin') {
    return true
  }
  return (permissions.modules[moduleKey] ?? 'none') !== 'none'
}
