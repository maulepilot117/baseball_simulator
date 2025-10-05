import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchTeam, fetchPlayers } from "../../lib/api.ts";
import type { Team, Player, ApiResponse, PaginatedResponse } from "../../lib/types.ts";

interface TeamDetailData {
  team: Team | null;
  roster: Player[];
  error?: string;
}

export const handler: Handlers<TeamDetailData> = {
  async GET(_req, ctx) {
    const { id } = ctx.params;

    try {
      const team = await fetchTeam(id);

      // Fetch roster by team ID
      const rosterResponse = await fetchPlayers({
        team: team.team_id,
        page_size: 100,
      }).catch(() => ({ data: [], total: 0, page: 1, page_size: 100, total_pages: 0 }));

      return ctx.render({
        team,
        roster: rosterResponse.data,
      });
    } catch (error) {
      console.error("Failed to fetch team:", error);
      return ctx.render({
        team: null,
        roster: [],
        error: "Failed to load team data",
      });
    }
  },
};

export default function TeamDetailPage({ data }: PageProps<TeamDetailData>) {
  const { team, roster, error } = data;

  if (error || !team) {
    return (
      <div class="min-h-screen bg-gray-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <a href="/teams" class="text-blue-600 hover:underline mb-4 inline-block">
            ← Back to Teams
          </a>
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <div class="text-red-600 text-xl mb-4">⚠️</div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">
              {error || "Team Not Found"}
            </h2>
            <p class="text-gray-600">
              The team you're looking for doesn't exist or could not be loaded.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Group roster by position
  const pitchers = roster.filter((p) => p.position === "P");
  const catchers = roster.filter((p) => p.position === "C");
  const infielders = roster.filter((p) => ["1B", "2B", "3B", "SS"].includes(p.position));
  const outfielders = roster.filter((p) => ["LF", "CF", "RF", "OF"].includes(p.position));
  const designated = roster.filter((p) => p.position === "DH");

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-6">
          <a href="/teams" class="text-blue-600 hover:underline mb-4 inline-block">
            ← Back to Teams
          </a>
        </div>

        {/* Team Info Card */}
        <div class="bg-white rounded-lg shadow mb-6">
          <div class="px-6 py-8">
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-6">
                <div class="text-6xl">⚾</div>
                <div>
                  <h1 class="text-4xl font-bold text-gray-900 mb-2">
                    {team.city} {team.name}
                  </h1>
                  <div class="flex items-center gap-4 text-gray-600 mb-4">
                    <span class="text-2xl font-bold text-blue-600">
                      {team.abbreviation}
                    </span>
                    {team.league && (
                      <span class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full font-semibold">
                        {team.league}
                      </span>
                    )}
                    {team.division && (
                      <span class="px-3 py-1 bg-gray-100 text-gray-800 rounded-full font-semibold">
                        {team.division}
                      </span>
                    )}
                  </div>
                  {team.stadium && (
                    <div class="text-gray-600 flex items-center gap-2">
                      <span class="text-xl">🏟️</span>
                      <span class="font-medium">{team.stadium}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Roster Summary */}
        <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div class="bg-white rounded-lg shadow p-4">
            <div class="text-sm text-gray-500 mb-1">Total Roster</div>
            <div class="text-3xl font-bold text-gray-900">{roster.length}</div>
          </div>
          <div class="bg-white rounded-lg shadow p-4">
            <div class="text-sm text-gray-500 mb-1">Pitchers</div>
            <div class="text-3xl font-bold text-blue-600">{pitchers.length}</div>
          </div>
          <div class="bg-white rounded-lg shadow p-4">
            <div class="text-sm text-gray-500 mb-1">Catchers</div>
            <div class="text-3xl font-bold text-green-600">{catchers.length}</div>
          </div>
          <div class="bg-white rounded-lg shadow p-4">
            <div class="text-sm text-gray-500 mb-1">Infielders</div>
            <div class="text-3xl font-bold text-purple-600">{infielders.length}</div>
          </div>
          <div class="bg-white rounded-lg shadow p-4">
            <div class="text-sm text-gray-500 mb-1">Outfielders</div>
            <div class="text-3xl font-bold text-orange-600">{outfielders.length}</div>
          </div>
        </div>

        {/* Roster Sections */}
        {roster.length === 0 ? (
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <div class="text-gray-400 text-4xl mb-4">👥</div>
            <h3 class="text-xl font-semibold text-gray-900 mb-2">
              No Roster Available
            </h3>
            <p class="text-gray-600">
              Roster information for this team is not yet available in the database.
            </p>
          </div>
        ) : (
          <>
            {/* Pitchers */}
            {pitchers.length > 0 && (
              <RosterSection title="Pitchers" players={pitchers} color="blue" />
            )}

            {/* Catchers */}
            {catchers.length > 0 && (
              <RosterSection title="Catchers" players={catchers} color="green" />
            )}

            {/* Infielders */}
            {infielders.length > 0 && (
              <RosterSection title="Infielders" players={infielders} color="purple" />
            )}

            {/* Outfielders */}
            {outfielders.length > 0 && (
              <RosterSection title="Outfielders" players={outfielders} color="orange" />
            )}

            {/* Designated Hitters */}
            {designated.length > 0 && (
              <RosterSection title="Designated Hitters" players={designated} color="red" />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Roster Section Component
function RosterSection({
  title,
  players,
  color,
}: {
  title: string;
  players: Player[];
  color: string;
}) {
  const colorClasses = {
    blue: "border-blue-200 bg-blue-50",
    green: "border-green-200 bg-green-50",
    purple: "border-purple-200 bg-purple-50",
    orange: "border-orange-200 bg-orange-50",
    red: "border-red-200 bg-red-50",
  };

  const headerColorClasses = {
    blue: "bg-blue-100 text-blue-900",
    green: "bg-green-100 text-green-900",
    purple: "bg-purple-100 text-purple-900",
    orange: "bg-orange-100 text-orange-900",
    red: "bg-red-100 text-red-900",
  };

  return (
    <div class={`bg-white rounded-lg shadow mb-6 border-2 ${colorClasses[color]}`}>
      <div class={`px-6 py-4 ${headerColorClasses[color]} font-semibold text-lg`}>
        {title} ({players.length})
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Number
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Name
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Position
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Status
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {players
              .sort((a, b) => (a.jersey_number || 99) - (b.jersey_number || 99))
              .map((player) => (
                <tr key={player.id} class="hover:bg-gray-50">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class="font-bold text-gray-900">
                      #{player.jersey_number || "—"}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <a
                      href={`/players/${player.id}`}
                      class="text-blue-600 hover:underline font-medium"
                    >
                      {player.full_name}
                    </a>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                      {player.position}
                    </span>
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
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
