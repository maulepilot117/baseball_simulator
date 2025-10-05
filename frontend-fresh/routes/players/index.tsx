import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchPlayers, PlayerFilters } from "../../lib/api.ts";
import type { Player, PaginatedResponse } from "../../lib/types.ts";

interface PlayersPageData {
  players: PaginatedResponse<Player>;
  filters: PlayerFilters;
}

export const handler: Handlers<PlayersPageData> = {
  async GET(req, ctx) {
    const url = new URL(req.url);
    const filters: PlayerFilters = {
      page: parseInt(url.searchParams.get("page") || "1"),
      page_size: 20,
      team: url.searchParams.get("team") || undefined,
      position: url.searchParams.get("position") || undefined,
      status: url.searchParams.get("status") || undefined,
      sort: url.searchParams.get("sort") || undefined,
      order: (url.searchParams.get("order") as "asc" | "desc") || undefined,
    };

    try {
      const players = await fetchPlayers(filters);
      return ctx.render({ players, filters });
    } catch (error) {
      console.error("Failed to fetch players:", error);
      return ctx.render({
        players: {
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

export default function PlayersPage({ data }: PageProps<PlayersPageData>) {
  const { players, filters } = data;
  const { data: playerList, total, page, total_pages } = players;

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-8">
          <a href="/" class="text-blue-600 hover:underline mb-2 inline-block">
            ← Back to Home
          </a>
          <h1 class="text-4xl font-bold text-gray-900 mb-2">Players</h1>
          <p class="text-gray-600">{total} players in the database</p>
        </div>

        {/* Filters */}
        <div class="bg-white rounded-lg shadow p-6 mb-6">
          <form method="GET" class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Position
              </label>
              <select
                name="position"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Positions</option>
                <option value="P" selected={filters.position === "P"}>
                  Pitcher
                </option>
                <option value="C" selected={filters.position === "C"}>
                  Catcher
                </option>
                <option value="1B" selected={filters.position === "1B"}>
                  First Base
                </option>
                <option value="2B" selected={filters.position === "2B"}>
                  Second Base
                </option>
                <option value="3B" selected={filters.position === "3B"}>
                  Third Base
                </option>
                <option value="SS" selected={filters.position === "SS"}>
                  Shortstop
                </option>
                <option value="LF" selected={filters.position === "LF"}>
                  Left Field
                </option>
                <option value="CF" selected={filters.position === "CF"}>
                  Center Field
                </option>
                <option value="RF" selected={filters.position === "RF"}>
                  Right Field
                </option>
                <option value="DH" selected={filters.position === "DH"}>
                  Designated Hitter
                </option>
              </select>
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
                <option value="active" selected={filters.status === "active"}>
                  Active
                </option>
                <option value="inactive" selected={filters.status === "inactive"}>
                  Inactive
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Sort By
              </label>
              <select
                name="sort"
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Default</option>
                <option value="name" selected={filters.sort === "name"}>
                  Name
                </option>
                <option value="position" selected={filters.sort === "position"}>
                  Position
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

        {/* Players Table */}
        <div class="bg-white rounded-lg shadow overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Team
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Position
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Number
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {playerList.length === 0 ? (
                <tr>
                  <td colspan="5" class="px-6 py-8 text-center text-gray-500">
                    No players found
                  </td>
                </tr>
              ) : (
                playerList.map((player) => (
                  <tr key={player.id} class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                      <a
                        href={`/players/${player.id}`}
                        class="text-blue-600 hover:underline font-medium"
                      >
                        {player.full_name}
                      </a>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {player.team_name || "-"}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span class="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                        {player.position}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {player.jersey_number || "-"}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span
                        class={`px-2 py-1 text-xs font-semibold rounded-full ${
                          player.status === "active"
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {player.status || "Unknown"}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total_pages > 1 && (
          <div class="mt-6 flex justify-center items-center gap-4">
            {page > 1 && (
              <a
                href={`?page=${page - 1}${filters.position ? `&position=${filters.position}` : ""}${
                  filters.status ? `&status=${filters.status}` : ""
                }${filters.sort ? `&sort=${filters.sort}` : ""}`}
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
                href={`?page=${page + 1}${filters.position ? `&position=${filters.position}` : ""}${
                  filters.status ? `&status=${filters.status}` : ""
                }${filters.sort ? `&sort=${filters.sort}` : ""}`}
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
