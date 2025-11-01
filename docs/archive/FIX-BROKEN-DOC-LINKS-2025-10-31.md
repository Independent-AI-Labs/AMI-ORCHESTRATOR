# Broken Documentation Links Report

**Generated**: 2025-10-31
**Scope**: All markdown files in `docs/`
**Issue**: Links to Git submodules (compliance, learning, etc.) use relative paths but these are separate repositories requiring GitHub URLs

---

## Summary

- **CRITICAL (Submodule Links)**: 36 violations - relative paths to submodules won't work in GitHub UI or external viewers
- **BROKEN (Renamed Files)**: 6 violations - links to old file names after recent documentation refactoring
- **BROKEN (Non-existent Paths)**: 1 violation - link to directory that doesn't exist

**Total**: 43 broken links requiring fixes

---

## CRITICAL: Submodule Links (36 violations)

These links use relative paths like `../../compliance/` or `../../learning/` but those are Git submodules (separate repos). They need to be GitHub URLs instead.

### Submodule Repository URLs

From `.gitmodules`:
- compliance: `git@github.com:Independent-AI-Labs/AMI-COMPLIANCE.git`
- learning: `git@github.com:Independent-AI-Labs/AMI-LEARNING.git`
- base: `git@github.com:Independent-AI-Labs/AMI-BASE.git`
- browser: `git@github.com:Independent-AI-Labs/AMI-BROWSER.git`
- domains: `git@github.com:Independent-AI-Labs/AMI-DOMAINS.git`
- files: `git@github.com:Independent-AI-Labs/AMI-FILES.git`
- nodes: `git@github.com:Independent-AI-Labs/AMI-NODES.git`
- streams: `git@github.com:Independent-AI-Labs/AMI-STREAMS.git`
- ux: `git@github.com:Independent-AI-Labs/AMI-UX.git`

### docs/openami/README.md

**Line 14:**
```markdown
Current: [specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI)
Correct: [specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/)
```

**Line 15:**
```markdown
Current: [learning/](https://github.com/Independent-AI-Labs/AMI-LEARNING)
Correct: [learning/](https://github.com/Independent-AI-Labs/AMI-LEARNING)
```

**Line 17:**
```markdown
Current: [research docs](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research)
Correct: [research docs](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/)
```

**Line 46:**
```markdown
Current: [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
Correct: [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
```

**Line 47:**
```markdown
Current: [bootstrap.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md)
Correct: [bootstrap.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md)
```

**Line 48:**
```markdown
Current: [incremental.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md)
Correct: [incremental.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md)
```

**Line 49:**
```markdown
Current: [SECURITY-MODEL.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SECURITY-MODEL.md)
Correct: [SECURITY-MODEL.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SECURITY-MODEL.md)
```

**Line 52:**
```markdown
Current: [Architecture pillars](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/pillars.md)
Correct: [Architecture pillars](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/pillars.md)
```

**Line 53:**
```markdown
Current: [Compliance manifest](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/compliance_manifest.md)
Correct: [Compliance manifest](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/compliance_manifest.md)
```

**Line 54:**
```markdown
Current: [OAMI protocol](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/oami_protocol.md)
Correct: [OAMI protocol](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/oami_protocol.md)
```

**Line 55:**
```markdown
Current: [Governance alignment](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/compliance/governance_alignment.md)
Correct: [Governance alignment](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/compliance/governance_alignment.md)
```

**Line 58:**
```markdown
Current: [OPENAMI-COMPLIANCE-MAPPING.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OPENAMI-COMPLIANCE-MAPPING.md)
Correct: [OPENAMI-COMPLIANCE-MAPPING.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OPENAMI-COMPLIANCE-MAPPING.md)
```

**Line 59:**
```markdown
Current: [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md)
Correct: [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md)
```

**Line 74:**
```markdown
Current: [Research specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI)
Correct: [Research specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/)
```

### docs/openami/SPEC-VISION.md

**Line 354:**
```markdown
Current: [Research Specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI)
Correct: [Research Specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/)
```

### docs/openami/GUIDE-FRAMEWORK.md

**Line 175:**
```markdown
Current: [Gemini DSE-AI](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md)
Correct: [Gemini DSE-AI](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md)
```

**Line 176:**
```markdown
Current: [Claude Formal Bootstrap](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md)
Correct: [Claude Formal Bootstrap](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md)
```

**Line 177:**
```markdown
Current: [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
Correct: [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
```

**Line 221:**
```markdown
Current: [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md)
Correct: [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md)
```

**Line 274:**
```markdown
Current: [process_theory.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/process_theory.md)
Correct: [process_theory.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/process_theory.md)
```

**Line 287:**
```markdown
Current: [compliance_manifest.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/compliance_manifest.md)
Correct: [compliance_manifest.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/compliance_manifest.md)
```

**Line 300:**
```markdown
Current: [oami_protocol.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/oami_protocol.md)
Correct: [oami_protocol.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/oami_protocol.md)
```

**Line 403:**
```markdown
Current: [incremental.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md)
Correct: [incremental.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md)
```

**Line 426:**
```markdown
Current: [learning/bootstrap.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md)
Correct: [learning/bootstrap.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md)
```

**Line 446:**
```markdown
Current: [architecture/pillars.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/pillars.md)
Correct: [architecture/pillars.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/pillars.md)
```

**Line 447:**
```markdown
Current: [learning/SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
Correct: [learning/SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
```

**Line 448:**
```markdown
Current: [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md)
Correct: [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md)
```

**Line 461:**
```markdown
Current: [Research Specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI)
Correct: [Research Specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/)
```

**Line 463:**
```markdown
Current: [CURRENT_IMPLEMENTATION_STATUS.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/CURRENT_IMPLEMENTATION_STATUS.md)
Correct: [CURRENT_IMPLEMENTATION_STATUS.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/CURRENT_IMPLEMENTATION_STATUS.md)
```

**Line 469:**
```markdown
Current: [Research Specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI)
Correct: [Research Specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/)
```

**Line 470:**
```markdown
Current: [learning/](https://github.com/Independent-AI-Labs/AMI-LEARNING)
Correct: [learning/](https://github.com/Independent-AI-Labs/AMI-LEARNING)
```

**Line 471:**
```markdown
Current: [OPENAMI-COMPLIANCE-MAPPING.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OPENAMI-COMPLIANCE-MAPPING.md)
Correct: [OPENAMI-COMPLIANCE-MAPPING.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OPENAMI-COMPLIANCE-MAPPING.md)
```

**Line 472:**
```markdown
Current: [Open AMI Chapters I-IV Peer Review Draft 3.tex](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/Open%20AMI%20Chapters%20I-IV%20Peer%20Review%20Draft%203.tex)
Correct: [Open AMI Chapters I-IV Peer Review Draft 3.tex](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/Open%20AMI%20Chapters%20I-IV%20Peer%20Review%20Draft%203.tex)
```

**Line 511:**
```markdown
Current: [Research Specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI)
Correct: [Research Specifications](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/)
```

**Line 542:**
```markdown
Current: [CURRENT_IMPLEMENTATION_STATUS.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/CURRENT_IMPLEMENTATION_STATUS.md)
Correct: [CURRENT_IMPLEMENTATION_STATUS.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/CURRENT_IMPLEMENTATION_STATUS.md)
```

### docs/openami/SPEC-ARCHITECTURE.md

**Line 125:**
```markdown
Current: [compliance/docs/research/OpenAMI/architecture/pillars.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/pillars.md)
Correct: [compliance/docs/research/OpenAMI/architecture/pillars.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/pillars.md)
```

**Line 149:**
```markdown
Current: [compliance/docs/research/OpenAMI/architecture/process_theory.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/process_theory.md)
Correct: [compliance/docs/research/OpenAMI/architecture/process_theory.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/process_theory.md)
```

**Line 197:**
```markdown
Current: [process_theory.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/process_theory.md)
Correct: [process_theory.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/architecture/process_theory.md)
```

**Line 249:**
```markdown
Current: [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
Correct: [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
```

**Line 299:**
```markdown
Current: [compliance_manifest.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/compliance_manifest.md)
Correct: [compliance_manifest.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI/systems/compliance_manifest.md)
```

**Line 404:**
```markdown
Current: [SECURITY-MODEL.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SECURITY-MODEL.md)
Correct: [SECURITY-MODEL.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SECURITY-MODEL.md)
```

**Line 494:**
```markdown
Current: [compliance/docs/research/OpenAMI/](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI)
Correct: [compliance/docs/research/OpenAMI/](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/)
```

**Line 497:**
```markdown
Current: [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
Correct: [SYNTHESIS-OPENAMI-BOOTSTRAP.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SYNTHESIS-OPENAMI-BOOTSTRAP.md)
```

**Line 498:**
```markdown
Current: [bootstrap.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md)
Correct: [bootstrap.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/bootstrap.md)
```

**Line 499:**
```markdown
Current: [incremental.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md)
Correct: [incremental.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/incremental.md)
```

**Line 500:**
```markdown
Current: [SECURITY-MODEL.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SECURITY-MODEL.md)
Correct: [SECURITY-MODEL.md](https://github.com/Independent-AI-Labs/AMI-LEARNING/blob/main/SECURITY-MODEL.md)
```

**Line 504:**
```markdown
Current: [OPENAMI-COMPLIANCE-MAPPING.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OPENAMI-COMPLIANCE-MAPPING.md)
Correct: [OPENAMI-COMPLIANCE-MAPPING.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OPENAMI-COMPLIANCE-MAPPING.md)
```

**Line 505:**
```markdown
Current: [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md)
Correct: [EXECUTIVE_ACTION_PLAN.md](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/EXECUTIVE_ACTION_PLAN.md)
```

**Line 522:**
```markdown
Current: [compliance/docs/research/OpenAMI/](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/blob/main/docs/research/OpenAMI)
Correct: [compliance/docs/research/OpenAMI/](https://github.com/Independent-AI-Labs/AMI-COMPLIANCE/tree/main/docs/research/OpenAMI/)
```

---

## BROKEN: Renamed Files (6 violations)

These links point to files that were renamed during the recent documentation refactoring.

### docs/openami/SPEC-VISION.md

**Line 297:**
```markdown
Current: [What is Open AMI?](./what-is-openami.md#real-world-applications)
Correct: What is Open AMI?
Note: File was renamed from what-is-openami.md to GUIDE-FRAMEWORK.md
```

### docs/openami/GUIDE-FRAMEWORK.md

**Line 227:**
```markdown
Current: [system-architecture.md](../architecture/system-architecture.md)
Correct: [SPEC-ARCHITECTURE.md](./SPEC-ARCHITECTURE.md)
Note: File was renamed to SPEC-ARCHITECTURE.md and is in same directory, not ../architecture/
```

**Line 435:**
```markdown
Current: [Executive Summary](./executive-summary.md)
Correct: [Executive Summary](./SPEC-VISION.md)
Note: File was renamed from executive-summary.md to SPEC-VISION.md
```

**Line 509:**
```markdown
Current: [Executive Summary](./executive-summary.md)
Correct: [Executive Summary](./SPEC-VISION.md)
Note: File was renamed from executive-summary.md to SPEC-VISION.md
```

**Line 510:**
```markdown
Current: [System Architecture](../architecture/system-architecture.md)
Correct: [System Architecture](./SPEC-ARCHITECTURE.md)
Note: File was renamed to SPEC-ARCHITECTURE.md and is in same directory, not ../architecture/
```

---

## BROKEN: Non-existent Paths (1 violation)

These links point to directories or files that don't exist.

### docs/openami/GUIDE-FRAMEWORK.md

**Line 462:**
```markdown
Current: Guides README
Status: BROKEN - docs/openami/guides/ directory does not exist
Action: Either remove this link or create the guides directory with README.md
```

---

## Recommendations

1. **Fix submodule links first (CRITICAL)**: Replace all relative paths to submodules with GitHub URLs
2. **Fix renamed file links (BROKEN)**: Update all references to old file names
3. **Remove or create guides directory (BROKEN)**: Either remove the broken link or create the missing directory
4. **Future-proofing**: Consider adding a link checker to CI/CD to catch broken links automatically

---

## Notes

- All submodule links should use `https://github.com/Independent-AI-Labs/` URLs
- For files within submodules, use `/blob/main/` for files or `/tree/main/` for directories
- Internal links within docs/openami/ should use relative paths (e.g., `./SPEC-VISION.md`)
- The docs/openami/ directory structure is now flat (no subdirectories except what was archived)

---

**End of Report**
