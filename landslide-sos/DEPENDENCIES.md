# LandslideSOS - Installed Dependencies

## Project Setup
- **Framework:** React 19 + Vite 8
- **Styling:** Tailwind CSS v4
- **Build Tool:** Vite with `@vitejs/plugin-react`

---

## Production Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^19.2.8 | Core UI framework |
| `react-dom` | ^19.2.8 | React DOM renderer |
| `react-router-dom` | ^7.18.3 | Client-side routing (Landing, Dashboard, Map, SOS, Alerts, Login, Admin) |
| `leaflet` | ^1.9.4 | Interactive map engine (OpenStreetMap tiles, markers, circles) |
| `react-leaflet` | ^5.0.0 | React component bindings for Leaflet |
| `recharts` | ^3.10.1 | Chart library (rainfall trend line chart on Dashboard) |
| `lucide-react` | ^1.44.0 | Icon library (Mountain, AlertTriangle, Bell, Shield, etc.) |

## Dev Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `vite` | ^8.3.0 | Dev server and production bundler |
| `@vitejs/plugin-react` | ^6.1.1 | Vite plugin for React JSX/Fast Refresh |
| `tailwindcss` | ^4.3.3 | Utility-first CSS framework |
| `@tailwindcss/vite` | ^4.3.3 | Tailwind CSS integration for Vite |
| `oxlint` | ^1.81.0 | Fast Rust-based linter |
| `@types/react` | ^19.2.18 | React TypeScript type definitions |
| `@types/react-dom` | ^19.2.7 | React DOM TypeScript type definitions |

## CDN Dependencies (loaded in index.html)

| Resource | Source | Purpose |
|----------|--------|---------|
| Inter Font | Google Fonts | Primary typeface for the UI |
| Leaflet CSS | unpkg.com/leaflet@1.9.4 | Map styling (markers, popups, controls) |

---

## Installation Commands

```bash
# Scaffold project
npm create vite@latest landslide-sos -- --template react

# Install production deps
npm install react-router-dom leaflet react-leaflet recharts lucide-react

# Install dev deps
npm install -D tailwindcss @tailwindcss/vite

# Start dev server
npm run dev
```

## Build & Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server at http://localhost:5173 |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run oxlint |
