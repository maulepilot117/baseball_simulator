import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchMetrics, fetchGames, fetchTeams, fetchPlayers } from "../lib/api.ts";
import type { Metrics, Game, Team, Player } from "../lib/types.ts";
import LiveSearch from "../islands/LiveSearch.tsx";

interface HomeData {
  metrics: Metrics;
  recentGames: Game[];
  totalTeams: number;
  totalPlayers: number;
}

export const handler: Handlers<HomeData> = {
  async GET(_req, ctx) {
    try {
      const [metrics, gamesResponse, teamsResponse, playersResponse] = await Promise.all([
        fetchMetrics(),
        fetchGames({ page: 1, page_size: 5 }),
        fetchTeams(),
        fetchPlayers({ page: 1, page_size: 1 }),
      ]);

      return ctx.render({
        metrics,
        recentGames: gamesResponse.data,
        totalTeams: teamsResponse.total,
        totalPlayers: playersResponse.total,
      });
    } catch (error) {
      console.error("Failed to fetch home page data:", error);
      return ctx.render({
        metrics: {} as Metrics,
        recentGames: [],
        totalTeams: 0,
        totalPlayers: 0,
      });
    }
  },
};

export default function Home({ data }: PageProps<HomeData>) {
  const { metrics, recentGames, totalTeams, totalPlayers } = data;

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-8">
          <h1 class="text-4xl font-bold text-gray-900 mb-2">
            Baseball Simulation
          </h1>
          <p class="text-gray-600">
            Browse statistics, search players, and simulate games
          </p>
        </div>

        {/* Search Bar (Live Search Island) */}
        <div class="mb-8">
          <LiveSearch />
        </div>

        {/* Featured: Monte Carlo Simulations */}
        <div class="mb-8">
          <a
            href="/simulations"
            class="block bg-gradient-to-r from-blue-600 to-green-600 rounded-xl shadow-lg hover:shadow-xl transition-all transform hover:scale-[1.02] p-8 text-white"
          >
            <div class="flex items-center justify-between">
              <div class="flex-1">
                <div class="flex items-center gap-3 mb-2">
                  <span class="text-4xl">🎲</span>
                  <h2 class="text-2xl font-bold">Monte Carlo Game Simulations</h2>
                </div>
                <p class="text-blue-100 mb-4">
                  Run advanced simulations using real player stats, weather forecasts, umpire tendencies, and park factors
                </p>
                <div class="flex items-center gap-2 text-sm text-blue-100">
                  <span class="bg-white/20 px-3 py-1 rounded-full">Real-time Weather</span>
                  <span class="bg-white/20 px-3 py-1 rounded-full">Park Factors</span>
                  <span class="bg-white/20 px-3 py-1 rounded-full">Umpire Effects</span>
                  <span class="bg-white/20 px-3 py-1 rounded-full">1000+ Runs</span>
                </div>
              </div>
              <div class="text-white/80 text-4xl">→</div>
            </div>
          </a>
        </div>

        {/* Quick Stats */}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div class="bg-white rounded-lg shadow p-6">
            <div class="text-sm font-medium text-gray-500 mb-1">Teams</div>
            <div class="text-3xl font-bold text-blue-600">{totalTeams}</div>
            <a href="/teams" class="text-sm text-blue-600 hover:underline mt-2 inline-block">
              View all teams →
            </a>
          </div>
          <div class="bg-white rounded-lg shadow p-6">
            <div class="text-sm font-medium text-gray-500 mb-1">Players</div>
            <div class="text-3xl font-bold text-green-600">{totalPlayers}</div>
            <a href="/players" class="text-sm text-green-600 hover:underline mt-2 inline-block">
              View all players →
            </a>
          </div>
          <div class="bg-white rounded-lg shadow p-6">
            <div class="text-sm font-medium text-gray-500 mb-1">Uptime</div>
            <div class="text-3xl font-bold text-purple-600">
              {metrics.uptime || "N/A"}
            </div>
            <a href="/metrics" class="text-sm text-purple-600 hover:underline mt-2 inline-block">
              View metrics →
            </a>
          </div>
        </div>

        {/* Recent Games */}
        <div class="bg-white rounded-lg shadow mb-8">
          <div class="px-6 py-4 border-b border-gray-200">
            <h2 class="text-xl font-semibold text-gray-900">Recent Games</h2>
          </div>
          <div class="divide-y divide-gray-200">
            {recentGames.length === 0 ? (
              <div class="px-6 py-8 text-center text-gray-500">
                No recent games found
              </div>
            ) : (
              recentGames.map((game) => (
                <a
                  key={game.id}
                  href={`/games/${game.id}`}
                  class="block px-6 py-4 hover:bg-gray-50 transition"
                >
                  <div class="flex justify-between items-center">
                    <div class="flex-1">
                      <div class="font-medium text-gray-900">
                        {game.away_team_name || "Away Team"} @ {game.home_team_name || "Home Team"}
                      </div>
                      <div class="text-sm text-gray-500">
                        {new Date(game.game_date).toLocaleDateString()}
                      </div>
                    </div>
                    {game.home_score !== undefined && game.away_score !== undefined ? (
                      <div class="text-right">
                        <div class="text-lg font-semibold">
                          {game.away_score} - {game.home_score}
                        </div>
                        <div class="text-sm text-gray-500">{game.status}</div>
                      </div>
                    ) : (
                      <div class="text-sm text-gray-500">{game.status}</div>
                    )}
                  </div>
                </a>
              ))
            )}
          </div>
          <div class="px-6 py-4 border-t border-gray-200">
            <a href="/games" class="text-blue-600 hover:underline">
              View all games →
            </a>
          </div>
        </div>

        {/* Navigation Links */}
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
          <a
            href="/simulations"
            class="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-lg shadow p-6 text-center hover:shadow-lg transition transform hover:scale-105"
          >
            <div class="text-4xl mb-2">🎲</div>
            <div class="font-semibold">Simulations</div>
          </a>
          <a
            href="/teams"
            class="bg-white rounded-lg shadow p-6 text-center hover:shadow-lg transition"
          >
            <div class="text-4xl mb-2">⚾</div>
            <div class="font-semibold text-gray-900">Teams</div>
          </a>
          <a
            href="/players"
            class="bg-white rounded-lg shadow p-6 text-center hover:shadow-lg transition"
          >
            <div class="text-4xl mb-2">👤</div>
            <div class="font-semibold text-gray-900">Players</div>
          </a>
          <a
            href="/games"
            class="bg-white rounded-lg shadow p-6 text-center hover:shadow-lg transition"
          >
            <div class="text-4xl mb-2">🎮</div>
            <div class="font-semibold text-gray-900">Games</div>
          </a>
          <a
            href="/umpires"
            class="bg-white rounded-lg shadow p-6 text-center hover:shadow-lg transition"
          >
            <div class="text-4xl mb-2">👨‍⚖️</div>
            <div class="font-semibold text-gray-900">Umpires</div>
          </a>
        </div>
      </div>
    </div>
  );
}
