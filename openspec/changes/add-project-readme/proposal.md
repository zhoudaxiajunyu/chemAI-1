# Proposal

## Why

The chemAI-1 repository currently has no `README.md`. A visitor opening the project sees only `CLAUDE.md` (LLM behavioral guidelines) and an empty `docs/` tree, so the project's purpose, tech stack, and setup steps are undocumented. A README is the canonical entry point for any repo; without it, onboarding for contributors, AI assistants, and future-you is guesswork.

## What Changes

- Add a top-level `README.md` introducing chemAI-1 as a chemistry-AI application.
- Document the project's purpose and intended scope at a glance.
- List the tech stack and prerequisites (Node.js 20.19+ for OpenSpec; Python pending once the chemistry stack is chosen).
- Provide setup steps: clone, install OpenSpec globally, `openspec init` (already done), and how to invoke the `/opsx-*` slash commands from the AI chat.
- Link to [CLAUDE.md](../../../CLAUDE.md) for the behavioral guidelines that govern AI-assisted work in this repo.
- Link to the [docs/](../../../docs) folder and the [openspec/](../../../openspec) spec tree.

## Capabilities

This change is documentation-only. No system behavior changes, so no spec-level requirements are introduced or modified. Specs are explicitly opted out via `skip_specs: true` in [.openspec.yaml](.openspec.yaml).

### New Capabilities

- _(none)_ README creation is not a runtime capability.

### Modified Capabilities

- _(none)_ No existing capabilities exist to modify.

## Impact

- **Files added**: `README.md` at the repository root.
- **Code/APIs**: No source code or API changes.
- **Dependencies**: No new dependencies; the README references the already-installed OpenSpec CLI and the existing `CLAUDE.md`.
- **Systems**: None beyond the documentation surface.
