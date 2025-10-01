# SPEC – DataOps Data Access Pattern

## Scope
Define how application code interacts with DataOps storage models so we avoid mixing persistence patterns or embedding business logic inside Pydantic models.

This spec applies to every module that touches `base/backend/dataops` models (Python services, FastAPI routers, management scripts, and tests). Where production-grade CRUD wiring is still pending, modules may use temporary in-memory helpers (e.g., `opsec/utils/user_utils.py`) so long as the logic stays outside the models and can be swapped for UnifiedCRUD without touching call sites.

## Core Principles
1. **StorageModel = schema only.** Classes under `base/backend/dataops/models/**` describe fields, validation, and metadata (`Meta.storage_configs`). They must not implement CRUD helpers, caching, or business rules.
2. **UnifiedCRUD handles persistence.** All reads/writes flow through `base/backend/dataops/services/unified_crud.py` (or the lower-level `core/unified_crud.py`). Use `get_crud(ModelClass)` to obtain a CRUD instance wired to every configured storage backend.
3. **Services own business logic.** Orchestrate create/update workflows, permission checks, and cross-model coordination in dedicated helpers (e.g., `auth_service.py`, `utils/user_utils.py`). They call UnifiedCRUD and attach `SecurityContext`; models stay passive.
4. **One pattern per module.** Do not mix ad-hoc DAO calls, model-level helpers, and UnifiedCRUD in the same workflow. Pick UnifiedCRUD + services and remove bespoke utilities (e.g., `User.find_or_create`).
5. **Security goes through context.** Whenever a model inherits `SecuredModelMixin`, pass a `SecurityContext` to CRUD operations so ACL/tenant filters apply automatically.

## Recommended Flow

```python
from base.backend.dataops.models.user import User
from base.backend.dataops.models.security import SecurityContext
from base.backend.dataops.services.unified_crud import get_crud

async def ensure_user(email: str, context: SecurityContext) -> User:
    crud = get_crud(User)
    normalized = email.lower()
    existing = await crud.query({"email": normalized}, limit=1, context=context)
    if existing:
        return existing[0]
    return await crud.create({"email": normalized}, context=context)
```

- Querying: `await crud.query(filter_dict, context=context)`
- Creating secured records: `await crud.create(payload, context=context)`
- Updating: `await crud.update(instance_id, patch_dict, context=context)`
- Removing: `await crud.delete(instance_id, context=context)`

## Migration Checklist
- [x] Remove model-level helpers that touch persistence (`User.find_or_create`, `User.get_auth_providers`, etc.). Re-implement them inside services using UnifiedCRUD.
- [ ] Ensure services inject `SecurityContext` so `SecuredModelMixin` fields (owner, ACL, tenant) are populated consistently.
- [ ] Replace direct DAO usage with `get_crud(ModelClass)` unless you are implementing a new DAO backend.
- [ ] Update tests to seed data through UnifiedCRUD to match production behaviour.

## Anti-Patterns to Avoid
- Adding async methods on models that perform storage reads/writes.
- Constructing models directly and assuming they persist (instantiation is in-memory only).
- Mixing UnifiedCRUD calls with raw DAO operations in the same code path.
- Passing around partially populated models with missing security metadata.

## References
- `base/backend/dataops/services/unified_crud.py` – entry point for multi-storage CRUD.
- `base/backend/dataops/models/base_model.py` – describes `StorageModel` responsibilities and security hooks.
- `base/backend/opsec/auth/auth_service.py` – example service layer that should adopt this spec.
