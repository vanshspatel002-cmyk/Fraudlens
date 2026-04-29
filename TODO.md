# Fix Plan for FraudLens Website

## Errors Identified
1. **Dev Server Crash** — `vite.config.ts` references non-existent `/mocha/emails-service/wrangler.json`
2. **Missing Dependencies** — `framer-motion` and `react-circular-progressbar` not installed in `code/`
3. **Lint/TS Errors** — Unused imports in `types.ts`, `any` type in `vite.config.ts`, fast-refresh warnings in UI components

## Steps
- [ ] 1. Fix `vite.config.ts` — remove invalid auxiliaryWorkers, fix `any` type
- [ ] 2. Install missing dependencies (`framer-motion`, `react-circular-progressbar`)
- [ ] 3. Fix `src/shared/types.ts` — remove unused `z` import
- [ ] 4. Fix fast-refresh warnings in `badge.tsx`, `button.tsx`, `tabs.tsx`
- [ ] 5. Run `npm run build` to verify
- [ ] 6. Run `npm run dev` to start the website

