import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchPlayer, fetchPlayerStats } from "../../lib/api.ts";
import type { Player, PlayerStats, ApiResponse } from "../../lib/types.ts";

interface PlayerDetailData {
  player: Player | null;
  stats: PlayerStats[];
  error?: string;
}

export const handler: Handlers<PlayerDetailData> = {
  async GET(_req, ctx) {
    const { id } = ctx.params;

    try {
      const [player, stats] = await Promise.all([
        fetchPlayer(id),
        fetchPlayerStats(id).catch(() => []),
      ]);

      return ctx.render({
        player,
        stats: Array.isArray(stats) ? stats : [],
      });
    } catch (error) {
      console.error("Failed to fetch player:", error);
      return ctx.render({
        player: null,
        stats: [],
        error: "Failed to load player data",
      });
    }
  },
};

export default function PlayerDetailPage({ data }: PageProps<PlayerDetailData>) {
  const { player, stats, error } = data;

  if (error || !player) {
    return (
      <div class="min-h-screen bg-gray-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <a href="/players" class="text-blue-600 hover:underline mb-4 inline-block">
            ← Back to Players
          </a>
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <div class="text-red-600 text-xl mb-4">⚠️</div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">
              {error || "Player Not Found"}
            </h2>
            <p class="text-gray-600">
              The player you're looking for doesn't exist or could not be loaded.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Group stats by type
  const battingStats = stats.filter((s) => s.stats_type === "batting");
  const pitchingStats = stats.filter((s) => s.stats_type === "pitching");
  const fieldingStats = stats.filter((s) => s.stats_type === "fielding");

  // Get latest season stats
  const latestBatting = battingStats.sort((a, b) => b.season - a.season)[0];
  const latestPitching = pitchingStats.sort((a, b) => b.season - a.season)[0];

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-6">
          <a href="/players" class="text-blue-600 hover:underline mb-4 inline-block">
            ← Back to Players
          </a>
        </div>

        {/* Player Info Card */}
        <div class="bg-white rounded-lg shadow mb-6">
          <div class="px-6 py-8">
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-6">
                <div class="text-6xl">👤</div>
                <div>
                  <h1 class="text-4xl font-bold text-gray-900 mb-2">
                    {player.full_name}
                  </h1>
                  <div class="flex items-center gap-4 text-gray-600">
                    {player.team_name && (
                      <span class="flex items-center gap-2">
                        <span class="font-medium">{player.team_name}</span>
                      </span>
                    )}
                    {player.jersey_number && (
                      <span class="px-3 py-1 bg-gray-100 rounded-full font-bold">
                        #{player.jersey_number}
                      </span>
                    )}
                    <span class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full font-semibold">
                      {player.position}
                    </span>
                    {player.status && (
                      <span
                        class={`px-3 py-1 rounded-full font-semibold ${
                          player.status === "active"
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {player.status}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Latest Stats Summary */}
        {(latestBatting || latestPitching) && (
          <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-2xl font-semibold text-gray-900">
                Latest Season Stats
                {latestBatting && ` (${latestBatting.season})`}
                {!latestBatting && latestPitching && ` (${latestPitching.season})`}
              </h2>
            </div>
            <div class="p-6">
              {/* Batting Stats */}
              {latestBatting && (
                <div class="mb-6">
                  <h3 class="text-lg font-semibold text-gray-700 mb-4">Batting</h3>
                  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <StatCard
                      label="AVG"
                      value={latestBatting.aggregated_stats.ba?.toFixed(3) || "—"}
                    />
                    <StatCard
                      label="OBP"
                      value={latestBatting.aggregated_stats.obp?.toFixed(3) || "—"}
                    />
                    <StatCard
                      label="SLG"
                      value={latestBatting.aggregated_stats.slg?.toFixed(3) || "—"}
                    />
                    <StatCard
                      label="OPS"
                      value={latestBatting.aggregated_stats.ops?.toFixed(3) || "—"}
                    />
                    <StatCard
                      label="HR"
                      value={latestBatting.aggregated_stats.hr?.toString() || "—"}
                    />
                    <StatCard
                      label="RBI"
                      value={latestBatting.aggregated_stats.rbi?.toString() || "—"}
                    />
                    <StatCard
                      label="Hits"
                      value={latestBatting.aggregated_stats.h?.toString() || "—"}
                    />
                    <StatCard
                      label="Runs"
                      value={latestBatting.aggregated_stats.runs?.toString() || "—"}
                    />
                    <StatCard
                      label="SB"
                      value={latestBatting.aggregated_stats.sb?.toString() || "—"}
                    />
                    <StatCard
                      label="BB"
                      value={latestBatting.aggregated_stats.bb?.toString() || "—"}
                    />
                    <StatCard
                      label="SO"
                      value={latestBatting.aggregated_stats.so?.toString() || "—"}
                    />
                    <StatCard
                      label="Games"
                      value={latestBatting.games_played.toString()}
                    />
                  </div>
                </div>
              )}

              {/* Pitching Stats */}
              {latestPitching && (
                <div>
                  <h3 class="text-lg font-semibold text-gray-700 mb-4">Pitching</h3>
                  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <StatCard
                      label="ERA"
                      value={latestPitching.aggregated_stats.era?.toFixed(2) || "—"}
                    />
                    <StatCard
                      label="WHIP"
                      value={latestPitching.aggregated_stats.whip?.toFixed(2) || "—"}
                    />
                    <StatCard
                      label="W-L"
                      value={`${latestPitching.aggregated_stats.w || 0}-${
                        latestPitching.aggregated_stats.l || 0
                      }`}
                    />
                    <StatCard
                      label="SV"
                      value={latestPitching.aggregated_stats.sv?.toString() || "—"}
                    />
                    <StatCard
                      label="SO"
                      value={latestPitching.aggregated_stats.so?.toString() || "—"}
                    />
                    <StatCard
                      label="BB"
                      value={latestPitching.aggregated_stats.bb?.toString() || "—"}
                    />
                    <StatCard
                      label="IP"
                      value={latestPitching.aggregated_stats.ip?.toFixed(1) || "—"}
                    />
                    <StatCard
                      label="Hits"
                      value={latestPitching.aggregated_stats.h?.toString() || "—"}
                    />
                    <StatCard
                      label="ER"
                      value={latestPitching.aggregated_stats.er?.toString() || "—"}
                    />
                    <StatCard
                      label="HR"
                      value={latestPitching.aggregated_stats.hr?.toString() || "—"}
                    />
                    <StatCard
                      label="FIP"
                      value={latestPitching.aggregated_stats.fip?.toFixed(2) || "—"}
                    />
                    <StatCard
                      label="Games"
                      value={latestPitching.games_played.toString()}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Career Stats by Season */}
        {battingStats.length > 0 && (
          <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-2xl font-semibold text-gray-900">
                Career Batting Statistics
              </h2>
            </div>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Season
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      G
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      AVG
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      OBP
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      SLG
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      OPS
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      HR
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      RBI
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      H
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      R
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      SB
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  {battingStats
                    .sort((a, b) => b.season - a.season)
                    .map((stat) => (
                      <tr key={stat.season}>
                        <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                          {stat.season}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.games_played}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.ba?.toFixed(3) || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.obp?.toFixed(3) || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.slg?.toFixed(3) || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.ops?.toFixed(3) || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.hr || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.rbi || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.h || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.runs || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.sb || "—"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Career Pitching Stats */}
        {pitchingStats.length > 0 && (
          <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-2xl font-semibold text-gray-900">
                Career Pitching Statistics
              </h2>
            </div>
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Season
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      G
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      ERA
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      WHIP
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      W-L
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      SV
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      IP
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      SO
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      BB
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      FIP
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  {pitchingStats
                    .sort((a, b) => b.season - a.season)
                    .map((stat) => (
                      <tr key={stat.season}>
                        <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                          {stat.season}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.games_played}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.era?.toFixed(2) || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.whip?.toFixed(2) || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.w || 0}-{stat.aggregated_stats.l || 0}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.sv || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.ip?.toFixed(1) || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.so || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.bb || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.aggregated_stats.fip?.toFixed(2) || "—"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* No Stats Available */}
        {stats.length === 0 && (
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <div class="text-gray-400 text-4xl mb-4">📊</div>
            <h3 class="text-xl font-semibold text-gray-900 mb-2">
              No Statistics Available
            </h3>
            <p class="text-gray-600">
              Statistics for this player are not yet available in the database.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Stat Card Component
function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div class="bg-gray-50 rounded-lg p-4">
      <div class="text-sm text-gray-500 mb-1">{label}</div>
      <div class="text-2xl font-bold text-gray-900">{value}</div>
    </div>
  );
}
