# Frontend Migration Guide

This folder contains the new Next.js + TypeScript frontend for the project.

It replaces the role of the older browser demo in `static/index.html`, while keeping the same backend websocket pipeline.

## What this frontend does

- connects to the FastAPI websocket backend
- sends natural-language football analysis queries
- receives coordinate and event-context payloads
- renders the match view on a pitch canvas
- shows event details and frame information
- adds playback-oriented controls for stepping through frames

## Main files

- `app/page.tsx`
  - root page entry for the frontend
- `app/layout.tsx`
  - global layout and fonts
- `app/globals.css`
  - global styling tokens and base styles
- `components/analysis-workspace.tsx`
  - the main interactive UI
- `components/pitch-canvas.tsx`
  - the pitch renderer using `<canvas>`
- `lib/analysis-store.ts`
  - Zustand state store for websocket, queries, and playback
- `lib/types.ts`
  - shared TypeScript types for backend payloads

## Requirements

You need:

- Node.js
- the Python backend running on `ws://127.0.0.1:8000/ws/analysis`

## Install

From the `frontend` folder:

```powershell
npm install
```

## Run in development

In one terminal, start the Python backend from the project root:

```powershell
.\.venv\Scripts\python.exe main.py
```

In another terminal, start the Next frontend:

```powershell
cd frontend
npm run dev
```

Open:

- `http://localhost:3000`

## Production build check

To verify the frontend compiles:

```powershell
cd frontend
npm run build
```

## Notes

- The old `static/index.html` is still kept in the repo as a lightweight fallback demo.
- The new frontend is the better long-term path because it gives us:
  - TypeScript safety
  - component structure
  - state management with Zustand
  - easier future animation and tactical overlays
