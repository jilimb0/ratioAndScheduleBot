# Ratio & Schedule Bot

Russian-language Telegram bot for maintaining daily routines. Sends scheduled reminders, tracks completion, weekly reports with motivational messages.

## Tech Stack
- **Language:** TypeScript (Node.js, strict mode)
- **Bot:** @tgwrapper/core
- **UI:** React 19 + Vite (Telegram WebApp)
- **Database:** SQLite (via `src/database.ts`)
- **Deploy:** Render (free tier, Docker / Node)

## Commands
- `pnpm install` — install deps
- `pnpm dev` — run WebApp dev server
- `pnpm build` — type-check + build (`tsc && vite build`)
- `pnpm test` — run Vitest suite
- `pnpm type-check` — `tsc --noEmit`
- `pnpm check` / `pnpm check:ci` — Biome lint + format

## Structure
- `src/bot.ts` — bot wiring
- `src/worker.ts` — production entry (`node dist/worker.js`)
- `src/serverless-handler.ts` — webhook / serverless handler
- `src/database.ts` — SQLite access
- `src/engine.ts` — scheduling / ratio engine
- `src/config.ts` — constants, messages, schedule (Russian)
- `src/App.tsx`, `src/main.tsx` — Telegram WebApp
- `tests/` — Vitest specs (`*.spec.ts`)

## Conventions
- All user-facing strings in Russian
- Config-driven schedule in `src/config.ts`
- pnpm over npm/yarn, Biome for lint/format
- `type` over `interface` for unions, no `any`, `const` by default
