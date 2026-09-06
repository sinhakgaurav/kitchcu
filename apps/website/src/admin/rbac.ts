/** Mirror of `ckac_common.admin_rbac.role_has_permission` — `*` and write-implies-read. */

export function roleHasPermission(grants: string[] | undefined | null, required: string): boolean {
  if (!grants?.length) return false;
  if (grants.includes("*")) return true;
  if (grants.includes(required)) return true;
  if (required.endsWith(":read")) {
    const write = `${required.slice(0, -5)}:write`;
    if (grants.includes(write)) return true;
  }
  return false;
}
