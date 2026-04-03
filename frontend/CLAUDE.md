# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev       # Start dev server with HMR
npm run build     # TypeScript check + Vite production build
npm run preview   # Serve the production build locally
npm run lint      # Run ESLint
```

There is no test framework configured.

## Architecture

This is a React 19 + TypeScript + Vite SPA for a logistics document verification platform (DP World "ClearPath").

**Screen routing** is handled manually in `src/App.tsx` via a `currentScreen` state string — there is no router library. Switching screens means updating this state.

**Two main screens:**
- `src/components/ClearPathScreen.tsx` — Landing page with document upload workflow, animated 3D wireframe cube, parallax hero, and scroll-reveal stats.
- `src/components/VerificationResultsScreen.tsx` — Results page showing verification status, metadata points, hash signatures, and scanning animations.

**All data is static mock data** in `src/data/mockData.ts`. There is no backend API integration. The two data objects are `clearPathData` and `verificationResultsData`.

**Scroll animations** are driven by `src/hooks/useScrollAnimation.ts`, which uses `IntersectionObserver` to add a `visible` class to elements with `.scroll-reveal` or `.reveal` class names.

## Styling

- Tailwind CSS v4 via PostCSS (config in `tailwind.config.js`)
- Custom color palette: primary is black, accent/secondary is `#E90716` (red)
- Border radius defaults to `0px` — the design uses sharp corners
- Custom animations defined in Tailwind config: `fade-up`, `pulse-accent`, `status-ping`, `grid-flow`, `float`
- Global styles and custom utilities in `src/index.css`
