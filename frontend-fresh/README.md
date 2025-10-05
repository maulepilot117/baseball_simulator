# Baseball Simulation Frontend (Fresh)

Modern, Deno-native frontend for the Baseball Simulation system built with [Fresh](https://fresh.deno.dev/).

## Features

- **Zero Build Step** - Instant startup with Deno
- **Server-Side Rendering** - Fast initial page loads
- **Islands Architecture** - Only ship JavaScript for interactive components
- **TypeScript First** - Full type safety with no configuration
- **Tailwind CSS** - Modern, responsive styling
- **File-Based Routing** - Intuitive page organization

## Pages

- `/` - Home page with quick stats and recent games
- `/teams` - Browse all MLB teams
- `/players` - Search and filter players by position, team, status
- `/games` - Browse games with date and season filters
- `/umpires` - View umpire statistics and tendencies
- `/search` - Global search across all entities

## Development

### Prerequisites

- Deno 2.1+ installed
- Backend services running (API Gateway, Data Fetcher)

### Local Development

```bash
# Start dev server
deno task start

# Run type checking
deno task check

# Build for production
deno task build

# Run production build
deno task preview
```

The dev server will start on http://localhost:8000

### Environment Variables

- `API_BASE_URL` - API Gateway URL (default: http://localhost:8080/api/v1)
- `DATA_FETCHER_URL` - Data Fetcher URL (default: http://localhost:8082)

## Docker

### Build

```bash
docker build -t baseball-frontend-fresh .
```

### Run

```bash
docker run -p 8000:8000 \
  -e API_BASE_URL=http://api-gateway:8080/api/v1 \
  -e DATA_FETCHER_URL=http://data-fetcher:8082 \
  baseball-frontend-fresh
```

### Docker Compose

The frontend is integrated into the main `docker-compose.yml`:

```bash
# Start all services including Fresh frontend
docker-compose up -d

# View logs
docker-compose logs -f frontend

# Rebuild after changes
docker-compose up -d --build frontend
```

## Project Structure

```
frontend-fresh/
├── routes/              # File-based routes (pages)
│   ├── index.tsx       # Home page
│   ├── search.tsx      # Search page
│   ├── teams/
│   │   └── index.tsx   # Teams list
│   ├── players/
│   │   └── index.tsx   # Players list
│   ├── games/
│   │   └── index.tsx   # Games list
│   └── umpires/
│       └── index.tsx   # Umpires list
├── islands/            # Interactive client components
├── components/         # Server-rendered components
├── lib/
│   ├── api.ts         # API client functions
│   └── types.ts       # TypeScript type definitions
├── static/            # Static assets
├── deno.json          # Deno configuration
├── fresh.config.ts    # Fresh configuration
└── Dockerfile         # Docker build
```

## API Integration

The frontend communicates with:

1. **API Gateway** (port 8080) - Main REST API for teams, players, games
2. **Data Fetcher** (port 8082) - Status and metrics

All API calls are type-safe using TypeScript interfaces defined in `lib/types.ts`.

## Performance

- **First Load**: <100ms (server-rendered)
- **Page Navigation**: <50ms (client-side routing)
- **Bundle Size**: Minimal (only interactive islands ship JS)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)
