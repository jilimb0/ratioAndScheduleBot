# Contributing

## Setup

```bash
git clone <repo>
cd RatioAndScheduleBot
corepack enable
pnpm install
cp .env.example .env  # edit BOT_TOKEN
```

## Commands

- `pnpm check` — Biome lint + format (write)
- `pnpm check:ci` — Biome check (CI)
- `pnpm type-check` — `tsc --noEmit`
- `pnpm test` — Vitest suite
- `pnpm build` — `tsc && vite build`
- `pnpm dev` — WebApp dev server

## Conventions

- TypeScript strict mode, Node 22+
- Biome for linting/formatting
- pnpm over npm/yarn
- All user-facing strings in Russian
- Tests live alongside source (`*.spec.ts`, Vitest)
