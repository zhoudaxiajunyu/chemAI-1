# chemAI-1

chemAI-1 is a chemistry-AI application — a workspace for building and experimenting with AI-assisted chemistry tooling. The project is in its bootstrap phase: spec-driven development is set up via [OpenSpec](https://github.com/Fission-AI/OpenSpec), and the chemistry stack is being defined alongside the first features.

## Tech Stack & Prerequisites

- **Node.js 20.19+** — required by the OpenSpec CLI.
- **`@fission-ai/openspec`** — spec-driven development CLI, installed globally.
- **Trae** — the AI assistant integration targeted by this repo's slash commands (`.trae/`).
- Chemistry runtime stack — to be declared as features land.

## Quick Start

1. Clone the repository and enter it:
   ```bash
   git clone <repo-url> chemAI-1
   cd chemAI-1
   ```
2. Install the OpenSpec CLI globally:
   ```bash
   npm install -g @fission-ai/openspec@latest
   ```
3. Initialize OpenSpec in the project (creates `openspec/` and `.trae/`):
   ```bash
   openspec init --tools trae
   ```
4. From your AI chat, start a change:
   ```
   /opsx-propose "your idea"
   ```

## Project Layout

- [CLAUDE.md](CLAUDE.md) — behavioral guidelines that govern AI-assisted work in this repo.
- [docs/](docs) — project documentation (design files live here).
- [openspec/](openspec) — the OpenSpec spec tree:
  - `specs/` — the system's durable, agreed-upon requirements.
  - `changes/` — in-flight and archived changes (proposal + specs + design + tasks).
  - `explorations/` — no-stakes thinking notes from `/opsx-explore`.
  - `initiatives/` and `work/` — planning containers for larger efforts.
  - `config.yaml` — project-level OpenSpec config (schema, context, rules).

## Behavioral Guidelines

All AI-assisted work in this repo follows [CLAUDE.md](CLAUDE.md): think before coding, simplicity first, surgical changes, and goal-driven execution. Read it before proposing or implementing a change.
