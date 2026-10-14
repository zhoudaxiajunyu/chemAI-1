# Tasks

## 1. README content

- [x] 1.1 Create `README.md` at repo root with a project intro describing chemAI-1 as a chemistry-AI application, and verify the file exists and the intro section renders as a top-level heading
- [x] 1.2 Add a "Tech Stack & Prerequisites" section listing Node.js 20.19+ (for OpenSpec) and the `@fission-ai/openspec` global package, and verify the list items render as a bullet list
- [x] 1.3 Add a "Quick Start" section with setup steps (clone, `npm install -g @fission-ai/openspec@latest`, `openspec init`, run `/opsx-propose` from the AI chat) and verify each step is a numbered item with a runnable command
- [x] 1.4 Add a "Project Layout" section describing `CLAUDE.md`, `docs/`, and `openspec/` (specs, changes, explorations, initiatives, work) and verify each entry links to the real path

## 2. Cross-references & verification

- [x] 2.1 Add a "Behavioral Guidelines" section linking to [CLAUDE.md](CLAUDE.md) and verify the relative link resolves to an existing file
- [x] 2.2 Run `openspec status --change add-project-readme` and verify `tasks` reads `done` and no missing artifacts remain
