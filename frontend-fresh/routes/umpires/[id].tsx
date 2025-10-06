import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchUmpire, fetchUmpireStats } from "../../lib/api.ts";
import type { Umpire, UmpireSeasonStats, ApiResponse } from "../../lib/types.ts";

interface UmpireDetailData {
  umpire: Umpire | null;
  stats: UmpireSeasonStats[];
  error?: string;
}

export const handler: Handlers<UmpireDetailData> = {
  async GET(_req, ctx) {
    const { id } = ctx.params;

    try {
      const [umpire, stats] = await Promise.all([
        fetchUmpire(id),
        fetchUmpireStats(id).catch(() => []),
      ]);

      return ctx.render({
        umpire,
        stats: Array.isArray(stats) ? stats : [],
      });
    } catch (error) {
      console.error("Failed to fetch umpire:", error);
      return ctx.render({
        umpire: null,
        stats: [],
        error: "Failed to load umpire data",
      });
    }
  },
};

export default function UmpireDetailPage({ data }: PageProps<UmpireDetailData>) {
  const { umpire, stats, error } = data;

  if (error || !umpire) {
    return (
      <div class="min-h-screen bg-gray-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <a href="/umpires" class="text-blue-600 hover:underline mb-4 inline-block">
            ← Back to Umpires
          </a>
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <div class="text-red-600 text-xl mb-4">⚠️</div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">
              {error || "Umpire Not Found"}
            </h2>
            <p class="text-gray-600">
              The umpire you're looking for doesn't exist or could not be loaded.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Calculate career totals
  const careerGames = stats.reduce((sum, s) => sum + s.games_umped, 0);
  const careerPitches = stats.reduce((sum, s) => sum + (s.total_calls || 0), 0);
  const avgAccuracy =
    stats.length > 0
      ? stats.reduce((sum, s) => sum + (s.accuracy_pct || 0), 0) / stats.length
      : 0;

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-6">
          <a href="/umpires" class="text-blue-600 hover:underline mb-4 inline-block">
            ← Back to Umpires
          </a>
        </div>

        {/* Umpire Info Card */}
        <div class="bg-white rounded-lg shadow mb-6">
          <div class="px-6 py-8">
            <div class="flex items-start gap-6">
              <div class="text-6xl">👨‍⚖️</div>
              <div class="flex-1">
                <h1 class="text-4xl font-bold text-gray-900 mb-2">
                  {umpire.name}
                </h1>
                {stats.length > 0 && (
                  <div class="text-gray-600">
                    <span class="text-sm">
                      {stats.length} season{stats.length !== 1 ? "s" : ""} recorded
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Career Stats Summary */}
        {stats.length > 0 && (
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-white rounded-lg shadow p-6">
              <div class="text-sm text-gray-500 mb-1">Career Games</div>
              <div class="text-3xl font-bold text-blue-600">{careerGames}</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
              <div class="text-sm text-gray-500 mb-1">Total Pitches</div>
              <div class="text-3xl font-bold text-green-600">
                {careerPitches.toLocaleString()}
              </div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
              <div class="text-sm text-gray-500 mb-1">Avg Accuracy</div>
              <div class="text-3xl font-bold text-purple-600">
                {avgAccuracy.toFixed(1)}%
              </div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
              <div class="text-sm text-gray-500 mb-1">Seasons</div>
              <div class="text-3xl font-bold text-orange-600">{stats.length}</div>
            </div>
          </div>
        )}

        {/* Tendencies */}
        {umpire.tendencies && (
          <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-2xl font-semibold text-gray-900">
                Umpiring Tendencies
              </h2>
            </div>
            <div class="p-6">
              <div class="grid grid-cols-2 md:grid-cols-3 gap-6">
                {umpire.tendencies.expand_zone !== undefined && (
                  <TendencyCard
                    label="Expand Zone"
                    value={umpire.tendencies.expand_zone}
                    description="Tendency to call strikes outside the zone"
                  />
                )}
                {umpire.tendencies.high_strike !== undefined && (
                  <TendencyCard
                    label="High Strike"
                    value={umpire.tendencies.high_strike}
                    description="Tendency to call high strikes"
                  />
                )}
                {umpire.tendencies.low_strike !== undefined && (
                  <TendencyCard
                    label="Low Strike"
                    value={umpire.tendencies.low_strike}
                    description="Tendency to call low strikes"
                  />
                )}
                {umpire.tendencies.outside_strike !== undefined && (
                  <TendencyCard
                    label="Outside Strike"
                    value={umpire.tendencies.outside_strike}
                    description="Tendency to call outside strikes"
                  />
                )}
                {umpire.tendencies.favor_home !== undefined && (
                  <TendencyCard
                    label="Favor Home"
                    value={umpire.tendencies.favor_home}
                    description="Bias toward home team"
                    signed
                  />
                )}
                {umpire.tendencies.consistency !== undefined && (
                  <TendencyCard
                    label="Consistency"
                    value={umpire.tendencies.consistency}
                    description="Call consistency rating"
                  />
                )}
              </div>
            </div>
          </div>
        )}

        {/* Season-by-Season Stats */}
        {stats.length > 0 ? (
          <div class="bg-white rounded-lg shadow">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-2xl font-semibold text-gray-900">
                Season-by-Season Statistics
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
                      Games
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Total Pitches
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Incorrect Calls
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Accuracy
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Favor Home
                    </th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Consistency
                    </th>
                  </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                  {stats
                    .sort((a, b) => b.season - a.season)
                    .map((stat) => (
                      <tr key={stat.season} class="hover:bg-gray-50">
                        <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">
                          {stat.season}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.games_umped}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.total_calls?.toLocaleString() || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.incorrect_calls?.toLocaleString() || "—"}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          <span
                            class={`text-sm font-semibold ${
                              (stat.accuracy_pct || 0) >= 95
                                ? "text-green-600"
                                : (stat.accuracy_pct || 0) >= 90
                                ? "text-yellow-600"
                                : "text-red-600"
                            }`}
                          >
                            {stat.accuracy_pct?.toFixed(2)}%
                          </span>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.favor_home !== undefined ? (
                            <span
                              class={
                                stat.favor_home > 0
                                  ? "text-green-600"
                                  : stat.favor_home < 0
                                  ? "text-red-600"
                                  : "text-gray-600"
                              }
                            >
                              {stat.favor_home > 0 ? "+" : ""}
                              {stat.favor_home.toFixed(2)}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {stat.consistency_pct !== undefined ? (
                            <span
                              class={
                                (stat.consistency_pct || 0) >= 95
                                  ? "text-green-600"
                                  : (stat.consistency_pct || 0) >= 90
                                  ? "text-yellow-600"
                                  : "text-red-600"
                              }
                            >
                              {stat.consistency_pct.toFixed(2)}%
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <div class="text-gray-400 text-4xl mb-4">📊</div>
            <h3 class="text-xl font-semibold text-gray-900 mb-2">
              No Statistics Available
            </h3>
            <p class="text-gray-600">
              Season statistics for this umpire are not yet available in the database.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Tendency Card Component
function TendencyCard({
  label,
  value,
  description,
  signed = false,
}: {
  label: string;
  value: number;
  description: string;
  signed?: boolean;
}) {
  const percentage = (value * 100).toFixed(1);
  const displayValue = signed
    ? `${value > 0 ? "+" : ""}${percentage}%`
    : `${percentage}%`;

  const getColor = () => {
    if (!signed) {
      if (value >= 0.5) return "text-red-600";
      if (value >= 0.3) return "text-yellow-600";
      return "text-green-600";
    }
    if (Math.abs(value) >= 0.05) return "text-red-600";
    if (Math.abs(value) >= 0.02) return "text-yellow-600";
    return "text-green-600";
  };

  return (
    <div class="bg-gray-50 rounded-lg p-4">
      <div class="text-sm text-gray-500 mb-1">{label}</div>
      <div class={`text-2xl font-bold mb-1 ${getColor()}`}>{displayValue}</div>
      <div class="text-xs text-gray-600">{description}</div>
    </div>
  );
}
