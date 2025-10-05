import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchTeams } from "../../lib/api.ts";
import type { Team, PaginatedResponse } from "../../lib/types.ts";

export const handler: Handlers<PaginatedResponse<Team>> = {
  async GET(_req, ctx) {
    try {
      const data = await fetchTeams();
      return ctx.render(data);
    } catch (error) {
      console.error("Failed to fetch teams:", error);
      return ctx.render({
        data: [],
        total: 0,
        page: 1,
        page_size: 50,
        total_pages: 0,
      });
    }
  },
};

export default function TeamsPage({ data }: PageProps<PaginatedResponse<Team>>) {
  const teams = data.data;

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-8">
          <a href="/" class="text-blue-600 hover:underline mb-2 inline-block">
            ← Back to Home
          </a>
          <h1 class="text-4xl font-bold text-gray-900 mb-2">Teams</h1>
          <p class="text-gray-600">
            {data.total} teams in the database
          </p>
        </div>

        {/* Teams Grid */}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {teams.length === 0 ? (
            <div class="col-span-3 text-center py-12 text-gray-500">
              No teams found
            </div>
          ) : (
            teams.map((team) => (
              <a
                key={team.id}
                href={`/teams/${team.id}`}
                class="bg-white rounded-lg shadow hover:shadow-lg transition p-6"
              >
                <div class="flex items-start justify-between mb-4">
                  <div class="flex-1">
                    <h3 class="text-xl font-bold text-gray-900">
                      {team.city} {team.name}
                    </h3>
                    <p class="text-gray-500 text-sm">
                      {team.abbreviation}
                    </p>
                  </div>
                  <div class="text-4xl">⚾</div>
                </div>

                {team.league && (
                  <div class="flex items-center gap-4 text-sm text-gray-600">
                    <span class="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                      {team.league}
                    </span>
                    {team.division && (
                      <span class="px-2 py-1 bg-gray-100 text-gray-800 rounded">
                        {team.division}
                      </span>
                    )}
                  </div>
                )}

                {team.stadium && (
                  <div class="mt-4 text-sm text-gray-500">
                    🏟️ {team.stadium}
                  </div>
                )}
              </a>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
