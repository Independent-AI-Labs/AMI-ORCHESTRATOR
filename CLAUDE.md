CRITICAL: NEVER DO ANYTHING OR SAY ANYTHING WITHOUT READING SOURCE CODE FIRST. NO INTERACTIONS, NO EDITS, NO ASSUMPTIONS. EVERYTHING IS FORBIDDEN UNTIL YOU READ THE RELEVANT SOURCE CODE. This is ABSOLUTE.

SEE AGENTS.md

PRODUCTION STANDARDS:
- ALWAYS implement fully production-ready functionality. Stubs, shims, and placeholders are STRICTLY FORBIDDEN.

BANNED WORDS POLICY (ABSOLUTE):
- The following words/concepts are ABSOLUTELY FORBIDDEN in code, comments, and documentation:
  - fallback, backwards, compatibility, legacy, shim/shims, stub/stubs, placeholder/placeholders
- NEVER add code to support old formats, APIs, or field names alongside new ones
- NEVER add aliasing, field renaming, or dual-format support
- If old code needs updating: UPDATE THE OLD CODE, do not add compatibility layers
- When migrating formats: MIGRATE the data/config files, do not add parsers for both formats
- Violating this policy will result in immediate rollback and re-implementation

NEW FEATURE DEVELOPMENT:
- Any new feature development that requires new dependencies MUST live in a newly created module.
- ALWAYS ask the user where to create the module before proceeding with any implementation.
- NEVER add dependencies to existing modules for new features.

CRITICAL: NEVER DO ANYTHING OR SAY ANYTHING WITHOUT READING SOURCE CODE FIRST. NO INTERACTIONS, NO EDITS, NO ASSUMPTIONS. EVERYTHING IS FORBIDDEN UNTIL YOU READ THE RELEVANT SOURCE CODE. This is ABSOLUTE.
