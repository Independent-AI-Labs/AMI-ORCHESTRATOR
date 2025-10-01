# TODO – Auth Persistence Migration

## Objective
Replace the temporary in-memory helpers (`base/backend/opsec/utils/user_utils.py`) with UnifiedCRUD-backed persistence that honours the storage order `[postgres, dgraph, vault]`. Persistence must succeed or fail loudly—there is no bundled disk-based emergency path.

## Research Checklist
- [ ] Inventory every import of `user_utils` (AuthService, tests, CLI adapters) and note required behaviours (ensure user, attach/detach providers, record login).
- [ ] Verify Vault DAO continues to own `SecretStr` fields across CRUD operations (no clear-text secrets on disk).
- [ ] Confirm we do not leave residual references to the deprecated file DAO in auth pathways.

## Implementation Steps
1. **StorageConfig updates** – Set `User.Meta.storage_configs` and `AuthProvider.Meta.storage_configs` to `['postgres', 'dgraph', 'vault']`. Remove leftover references to the deprecated `local_file` profile.
2. **AuthService refactor** – Replace all `user_utils` calls with UnifiedCRUD (`get_crud(User)`, `get_crud(AuthProvider)`). Introduce helper methods inside `AuthService` if needed, but keep persistence centralized.
3. **Remove shim** – Delete `base/backend/opsec/utils/user_utils.py` and any tests targeting it. Update imports accordingly.
4. **Error-path verification** – Write integration tests that simulate Postgres/Dgraph/Vault outages and assert the service surfaces actionable errors instead of silently degrading. Ensure secrets still resolve via Vault when it is online.
5. **Docs & tooling** – Update `SPEC-AUTH.md`, `TODO-AUTH.md`, and `SPEC-STORAGE.md` to reflect the simplified storage order and the removal of the implicit disk persistence note.

## Validation
- [ ] `python3 base/scripts/run_tests.py` with full stack running (Postgres, Dgraph, OpenBao) should pass.
- [ ] Add a targeted suite that validates error messaging when Postgres or Dgraph are unreachable.

## Rollout Notes
- Communicate the storage order change to other modules that rely on user data so they always use UnifiedCRUD (no direct DAO usage).
- Remove any provisioning guidance that assumed `${BASE_VAR_DIR}` needed to store auth data.
