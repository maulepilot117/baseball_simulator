import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchGames, GameFilters } from "../../lib/api.ts";
import type { Game, PaginatedResponse } from "../../lib/types.ts";

interface GamesPageData {
  games: PaginatedResponse<Game>;
  filters: GameFilters;
}

export const handler: Handlers<GamesPageData> = {
  async GET(req, ctx) {
    const url = new URL(req.url);
    const filters: GameFilters = {
      page: parseInt(url.searchParams.get("page") || "1"),
      page_size: 20,
      season: url.searchParams.get("season") ? parseInt(url.searchParams.get("season")!) : undefined,
      team: url.searchParams.get("team") || undefined,
      status: url.searchParams.get("status") || undefined,
      date: url.searchParams.get("date") || undefined,
    };

    try {
      const games = await fetchGames(filters);
      return ctx.render({ games, filters });
    } catch (error) {
      console.error("Failed to fetch games:", error);
      return ctx.render({
        games: {
          data: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 0,
        },
        filters,
      });
    }
  },
};

export default function GamesPage({ data }: PageProps<GamesPageData>) {
  const { games, filters } = data;
  const { data: gameList, total, page, total_pages } = games;

  // Group games by date
  const gamesByDate: Record<string, Game[]> = {};
  gameList.forEach((game) => {
    const date = game.game_date.split("T")[0];
    if (!gamesByDate[date]) {
      gamesByDate[date] = [];
    }
    gamesByDate[date].push(game);
  });

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-8">
          <a href="/" class="text-blue-600 hover:underline mb-2 inline-block">
            ← Back to Home
          </a>
          <h1 class="text-4xl font-bold text-gray-900 mb-2">Games</h1>
          <p class="text-gray-600">{total} games in the database</p>
        </div>

        {/* Filters */}
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <form method="GET" class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Season
              </label>
              <input
                type="number"
                name="season"
                value={filters.season || ""}
                placeholder="e.g., 2024"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Date
              </label>
              <input
                type="date"
                name="date"
                value={filters.date || ""}
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                name="status"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Status</option>
                <option value="scheduled" selected={filters.status === "scheduled"}>
                  Scheduled
                </option>
                <option value="live" selected={filters.status === "live"}>
                  Live
                </option>
                <option value="final" selected={filters.status === "final"}>
                  Final
                </option>
                <option value="postponed" selected={filters.status === "postponed"}>
                  Postponed
                </option>
              </select>
            </div>

            <div class="flex items-end">
              <button
                type="submit"
                class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Apply Filters
              </button>
            </div>
          </form>
        </div>

        {/* Games List */}
        <div class="space-y-6">
          {Object.keys(gamesByDate).length === 0 ? (
            <div class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
              No games found
            </div>
          ) : (
            Object.entries(gamesByDate).map(([date, gamesForDate]) => (
              <div key={date} class="bg-white rounded-lg shadow overflow-hidden">
                <div class="px-6 py-3 bg-gray-50 border-b border-gray-200">
                  <h3 class="text-lg font-semibold text-gray-900">
                    {new Date(date + "T00:00:00").toLocaleDateString("en-US", {
                      weekday: "long",
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </h3>
                </div>
                <div class="divide-y divide-gray-200">
                  {gamesForDate.map((game) => (
                    <a
                      key={game.id}
                      href={`/games/${game.id}`}
                      class="block px-6 py-4 hover:bg-gray-50 transition"
                    >
                      <div class="flex justify-between items-center">
                        <div class="flex-1">
                          <div class="flex items-center gap-3">
                            <div class="text-base font-medium text-gray-900">
                              {game.away_team_name || "Away Team"}
                            </div>
                            <span class="text-gray-400">@</span>
                            <div class="text-base font-medium text-gray-900">
                              {game.home_team_name || "Home Team"}
                            </div>
                          </div>
                          <div class="text-sm text-gray-500 mt-1">
                            Season {game.season}
                          </div>
                        </div>

                        <div class="text-right ml-4">
                          {game.home_score !== undefined && game.away_score !== undefined ? (
                            <div class="flex items-center gap-3">
                              <div class="text-2xl font-bold text-gray-900">
                                {game.away_score}
                              </div>
                              <div class="text-gray-400">-</div>
                              <div class="text-2xl font-bold text-gray-900">
                                {game.home_score}
                              </div>
                            </div>
                          ) : (
                            <div class="text-sm text-gray-500">No score</div>
                          )}
                          <div class="mt-1">
                            <span
                              class={`px-2 py-1 text-xs font-semibold rounded-full ${
                                game.status === "final"
                                  ? "bg-green-100 text-green-800"
                                  : game.status === "live"
                                  ? "bg-red-100 text-red-800"
                                  : game.status === "postponed"
                                  ? "bg-yellow-100 text-yellow-800"
                                  : "bg-blue-100 text-blue-800"
                              }`}
                            >
                              {game.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        {total_pages > 1 && (
          <div class="mt-6 flex justify-center items-center gap-4">
            {page > 1 && (
              <a
                href={`?page=${page - 1}${filters.season ? `&season=${filters.season}` : ""}${
                  filters.date ? `&date=${filters.date}` : ""
                }${filters.status ? `&status=${filters.status}` : ""}`}
                class="px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                ← Previous
              </a>
            )}
            <span class="text-gray-600">
              Page {page} of {total_pages}
            </span>
            {page < total_pages && (
              <a
                href={`?page=${page + 1}${filters.season ? `&season=${filters.season}` : ""}${
                  filters.date ? `&date=${filters.date}` : ""
                }${filters.status ? `&status=${filters.status}` : ""}`}
                class="px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Next →
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
