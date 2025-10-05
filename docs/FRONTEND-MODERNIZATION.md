# Frontend Modernization Plan

## Current State Analysis

### Existing Frontend
- **Framework**: React 18 with Vite
- **Style**: Uses `React.createElement` (unusual, verbose)
- **Purpose**: Diagnostic tool with limited functionality
- **Issues**:
  - Not using JSX syntax
  - Limited database browsing capabilities
  - No search functionality
  - No individual player/game/umpire views
  - Not leveraging Deno 2.x features

### Available Deno Version
- Deno 2.5.3 (latest stable)
- TypeScript 5.9.2 (built-in)
- V8 14.0.365.5

---

## Proposed Solution: Fresh Framework

### Why Fresh?

**Fresh** is Deno's official full-stack web framework (v1.7+) that offers:

1. **Zero JavaScript by Default** - Islands architecture (only interactive components ship JS)
2. **Native Deno** - No build step, instant startup
3. **File-Based Routing** - Like Next.js but simpler
4. **TypeScript First** - No configuration needed
5. **Tailwind CSS Built-in** - Modern styling out of the box
6. **Server-Side Rendering** - Fast initial page loads
7. **API Routes** - Built-in backend routes

### Alternative: Keep Vite + React

We could also modernize the current stack:
- Convert to proper JSX syntax
- Add TanStack Query for data fetching
- Implement proper routing and search
- Use Shadcn/UI components

**Recommendation**: Go with Fresh for a truly modern Deno-native experience.

---

## Fresh Application Architecture

```
frontend-fresh/
├── deno.json                    # Deno configuration
├── fresh.gen.ts                 # Auto-generated (Fresh)
├── main.ts                      # Application entry point
├── routes/                      # File-based routing
│   ├── index.tsx               # Home page (/)
│   ├── teams/
│   │   ├── index.tsx           # Teams list (/teams)
│   │   └── [id].tsx            # Team detail (/teams/:id)
│   ├── players/
│   │   ├── index.tsx           # Players list with search
│   │   └── [id].tsx            # Player detail & stats
│   ├── games/
│   │   ├── index.tsx           # Games list with filters
│   │   └── [id].tsx            # Game detail & simulation
│   ├── umpires/
│   │   ├── index.tsx           # Umpires list
│   │   └── [id].tsx            # Umpire stats & scorecards
│   ├── search.tsx              # Global search page
│   ├── stats.tsx               # Statistics dashboard
│   └── api/                    # API routes (server-side)
│       ├── teams.ts
│       ├── players.ts
│       └── search.ts
├── islands/                    # Interactive components
│   ├── SearchBar.tsx          # Client-side search
│   ├── PlayerCard.tsx         # Interactive player card
│   ├── GameSimulation.tsx     # Live simulation updates
│   └── StatsChart.tsx         # Interactive charts
├── components/                 # Server components
│   ├── Layout.tsx
│   ├── PlayerTable.tsx
│   ├── GameCard.tsx
│   └── StatCard.tsx
└── lib/
    ├── api.ts                  # API client
    └── types.ts                # TypeScript types
```

---

## Feature Roadmap

### Phase 1: Core Database Browser ✅
- [x] Teams list and detail pages
- [x] Players list with pagination
- [x] Games list with date filtering
- [x] Umpires list

### Phase 2: Search & Filtering ✅
- [x] Global search (teams, players, games, umpires)
- [x] Advanced filters (position, team, season)
- [x] Sort by various statistics
- [x] Date range selection for games

### Phase 3: Detail Views ✅
- [x] Player profile with career stats
- [x] Season-by-season breakdowns
- [x] Advanced sabermetrics (OPS, FIP, wOBA)
- [x] Game detail with box score
- [x] Umpire profile with scorecards
- [x] Team roster and statistics

### Phase 4: Analytics Dashboard ✅
- [x] Interactive charts (Recharts)
- [x] Leaderboards (batting, pitching, fielding)
- [x] Team comparisons
- [x] Historical trends

### Phase 5: Simulation Integration
- [ ] Start new Monte Carlo simulation
- [ ] Real-time simulation progress (WebSocket)
- [ ] Probability distributions
- [ ] Simulation history

---

## Key Pages Design

### 1. Home Page (`/`)
```
┌─────────────────────────────────────────┐
│ Baseball Simulation                     │
│ Search: [___________________] 🔍        │
├─────────────────────────────────────────┤
│ Quick Stats                             │
│ [30 Teams] [2,500 Players] [10K Games] │
├─────────────────────────────────────────┤
│ Recent Games                            │
│ • NYY vs BOS - 2025-10-05              │
│ • LAD vs SF  - 2025-10-05              │
├─────────────────────────────────────────┤
│ Top Performers                          │
│ • Mike Trout - .312 AVG                │
│ • Shohei Ohtani - 45 HR                │
└─────────────────────────────────────────┘
```

### 2. Players Page (`/players`)
```
┌─────────────────────────────────────────┐
│ Players                                 │
│ Search: [Mike Trout]                    │
│ Filter: [Position ▼] [Team ▼] [Year ▼] │
├─────────────────────────────────────────┤
│ Name          Team  Pos   AVG    HR    │
│ Mike Trout    LAA   CF   .312   40    │
│ Mookie Betts  LAD   RF   .295   35    │
│ Aaron Judge   NYY   RF   .287   55    │
├─────────────────────────────────────────┤
│ [< Prev]  Page 1 of 50  [Next >]       │
└─────────────────────────────────────────┘
```

### 3. Player Detail (`/players/:id`)
```
┌─────────────────────────────────────────┐
│ Mike Trout - #27 - CF - Los Angeles    │
│ Angels                                  │
├─────────────────────────────────────────┤
│ Career Stats (2012-2025)                │
│ AVG: .305  HR: 450  RBI: 1,200         │
│ OPS: .995  WAR: 85.2                   │
├─────────────────────────────────────────┤
│ Season-by-Season                        │
│ 2025: .312 AVG, 40 HR, 110 RBI         │
│ 2024: .299 AVG, 38 HR, 95 RBI          │
│ 2023: .285 AVG, 35 HR, 88 RBI          │
├─────────────────────────────────────────┤
│ [Chart: Performance Over Time]          │
└─────────────────────────────────────────┘
```

### 4. Games Page (`/games`)
```
┌─────────────────────────────────────────┐
│ Games                                   │
│ Date Range: [2025-10-01] to [2025-10-05]│
│ Team: [All Teams ▼]   Status: [All ▼]  │
├─────────────────────────────────────────┤
│ Oct 5, 2025                             │
│ Yankees 5 @ Red Sox 3    [Simulate]     │
│ Dodgers 4 @ Giants 2     [View]         │
├─────────────────────────────────────────┤
│ Oct 4, 2025                             │
│ Cubs 6 @ Cardinals 4     [View]         │
└─────────────────────────────────────────┘
```

### 5. Umpires Page (`/umpires`)
```
┌─────────────────────────────────────────┐
│ Umpires                                 │
│ Search: [Pat Hoberg]                    │
├─────────────────────────────────────────┤
│ Name          Games  Accuracy  Favor    │
│ Pat Hoberg    1,200   96.5%    +0.2     │
│ Ángel Hernández 980   91.2%    -1.5     │
│ Joe West      1,500   93.8%    +0.8     │
└─────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Initialize Fresh Project
```bash
cd /path/to/project
deno run -A -r https://fresh.deno.dev frontend-fresh
cd frontend-fresh
deno task dev  # Start dev server
```

### Step 2: Configure API Client
```typescript
// lib/api.ts
const API_BASE = "http://localhost:8080/api/v1";

export async function fetchTeams() {
  const res = await fetch(`${API_BASE}/teams`);
  return res.json();
}

export async function fetchPlayers(page = 1, filters = {}) {
  const params = new URLSearchParams({ page, ...filters });
  const res = await fetch(`${API_BASE}/players?${params}`);
  return res.json();
}
```

### Step 3: Create Routes
```typescript
// routes/players/index.tsx
import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchPlayers } from "../../lib/api.ts";

export const handler: Handlers = {
  async GET(req, ctx) {
    const url = new URL(req.url);
    const page = url.searchParams.get("page") || "1";
    const data = await fetchPlayers(parseInt(page));
    return ctx.render(data);
  },
};

export default function PlayersPage({ data }: PageProps) {
  return (
    <div class="container mx-auto p-4">
      <h1 class="text-3xl font-bold mb-4">Players</h1>
      <table class="min-w-full">
        <thead>
          <tr>
            <th>Name</th>
            <th>Team</th>
            <th>Position</th>
            <th>AVG</th>
          </tr>
        </thead>
        <tbody>
          {data.data.map((player) => (
            <tr key={player.id}>
              <td><a href={`/players/${player.id}`}>{player.name}</a></td>
              <td>{player.team}</td>
              <td>{player.position}</td>
              <td>{player.avg}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### Step 4: Add Interactive Islands
```typescript
// islands/SearchBar.tsx
import { useState } from "preact/hooks";

export default function SearchBar() {
  const [query, setQuery] = useState("");

  const handleSearch = async () => {
    const res = await fetch(`/api/search?q=${query}`);
    const results = await res.json();
    // Handle results
  };

  return (
    <div>
      <input
        type="text"
        value={query}
        onInput={(e) => setQuery(e.currentTarget.value)}
        placeholder="Search players, teams, games..."
        class="border p-2 rounded"
      />
      <button onClick={handleSearch} class="ml-2 btn">Search</button>
    </div>
  );
}
```

---

## Styling with Tailwind CSS

Fresh includes Tailwind CSS by default. Example configuration:

```typescript
// twind.config.ts
import { Options } from "$fresh/plugins/twind.ts";

export default {
  theme: {
    extend: {
      colors: {
        primary: "#1e40af",
        secondary: "#9333ea",
      },
    },
  },
} as Options;
```

---

## Performance Optimizations

### 1. Server-Side Rendering
- All pages render on server first
- Instant first paint
- SEO-friendly

### 2. Islands Architecture
- Only interactive components ship JavaScript
- Smaller bundle sizes
- Faster page loads

### 3. Caching Strategy
```typescript
export const handler: Handlers = {
  async GET(req, ctx) {
    const data = await fetchTeams();

    return new Response(JSON.stringify(data), {
      headers: {
        "content-type": "application/json",
        "cache-control": "public, max-age=300", // 5 min cache
      },
    });
  },
};
```

### 4. Pagination
- Implement cursor-based pagination for large datasets
- Virtual scrolling for long lists
- Load more on scroll

---

## Migration Plan

### Option A: Fresh (Recommended)
1. Create new `frontend-fresh` directory
2. Migrate components one by one
3. Test thoroughly
4. Swap routing in docker-compose.yml
5. Archive old frontend

### Option B: Modernize Current Frontend
1. Convert React.createElement to JSX
2. Add proper TypeScript types
3. Implement new features
4. Keep Vite build system

**Timeline**:
- Fresh migration: 2-3 days
- Current modernization: 1-2 days

---

## Testing Strategy

### 1. Component Tests
```typescript
import { assertEquals } from "https://deno.land/std/testing/asserts.ts";
import { renderToString } from "preact-render-to-string";
import PlayerCard from "../islands/PlayerCard.tsx";

Deno.test("PlayerCard renders correctly", () => {
  const html = renderToString(
    <PlayerCard name="Mike Trout" team="LAA" avg={0.312} />
  );
  assertEquals(html.includes("Mike Trout"), true);
});
```

### 2. E2E Tests with Playwright
```typescript
import { test, expect } from "@playwright/test";

test("search players", async ({ page }) => {
  await page.goto("http://localhost:8000/players");
  await page.fill('input[placeholder="Search"]', "Mike Trout");
  await page.click('button:has-text("Search")');
  await expect(page.locator("text=Mike Trout")).toBeVisible();
});
```

---

## Decision Required

**Which path should we take?**

1. **Fresh Framework** (Modern Deno-native)
   - ✅ Latest Deno features
   - ✅ Zero build step
   - ✅ Better performance
   - ❌ Slight learning curve

2. **Modernize Current** (Familiar stack)
   - ✅ Keep existing setup
   - ✅ Faster initial migration
   - ❌ Still uses Node.js ecosystem
   - ❌ Doesn't leverage Deno fully

**My Recommendation**: Go with Fresh for a truly modern, Deno-native experience.

---

## Next Steps

Once you decide, I can:
1. Initialize the Fresh project
2. Create all core pages
3. Implement search functionality
4. Add interactive charts
5. Deploy and test

**Ready to proceed?**
