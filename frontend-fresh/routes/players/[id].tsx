import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchPlayer, fetchPlayerStats } from "../../lib/api.ts";
import type { Player, PlayerStats } from "../../lib/types.ts";

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
      <div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <a href="/players" class="text-blue-600 hover:text-blue-700 font-medium mb-4 inline-flex items-center gap-2">
            <span>←</span> Back to Players
          </a>
          <div class="bg-white rounded-2xl shadow-xl p-12 text-center mt-6">
            <div class="text-red-500 text-5xl mb-4">⚠️</div>
            <h2 class="text-3xl font-bold text-gray-900 mb-3">
              {error || "Player Not Found"}
            </h2>
            <p class="text-gray-600 text-lg">
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
  const latestFielding = fieldingStats.sort((a, b) => b.season - a.season)[0];

  return (
    <div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back Button */}
        <a href="/players" class="text-blue-600 hover:text-blue-700 font-medium mb-6 inline-flex items-center gap-2 transition-colors">
          <span>←</span> Back to Players
        </a>

        {/* Player Header Card */}
        <div class="bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl shadow-2xl mb-8 overflow-hidden">
          <div class="px-8 py-10">
            <div class="flex items-center gap-8">
              {/* Player Avatar */}
              <div class="w-24 h-24 bg-white/20 rounded-full flex items-center justify-center text-5xl backdrop-blur-sm">
                ⚾
              </div>

              {/* Player Info */}
              <div class="flex-1">
                <h1 class="text-5xl font-bold text-white mb-3">
                  {player.full_name}
                </h1>
                <div class="flex items-center gap-4 flex-wrap">
                  {player.team_name && (
                    <span class="px-4 py-2 bg-white/20 backdrop-blur-sm rounded-lg text-white font-semibold">
                      {player.team_name}
                    </span>
                  )}
                  {player.jersey_number && (
                    <span class="px-4 py-2 bg-white/20 backdrop-blur-sm rounded-lg text-white font-bold">
                      #{player.jersey_number}
                    </span>
                  )}
                  <span class="px-4 py-2 bg-white text-blue-800 rounded-lg font-bold shadow-md">
                    {player.position}
                  </span>
                  {player.status && (
                    <span
                      class={`px-4 py-2 rounded-lg font-semibold shadow-md ${
                        player.status === "active"
                          ? "bg-green-500 text-white"
                          : "bg-gray-400 text-white"
                      }`}
                    >
                      {player.status.toUpperCase()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Latest Season Stats */}
        {(latestBatting || latestPitching) && (
          <div class="mb-8">
            <div class="bg-white rounded-2xl shadow-xl overflow-hidden">
              <div class="px-8 py-6 bg-gradient-to-r from-slate-800 to-slate-700 border-b border-gray-200">
                <h2 class="text-3xl font-bold text-white">
                  {latestBatting?.season || latestPitching?.season} Season Statistics
                </h2>
              </div>

              {/* Batting Stats */}
              {latestBatting && (
                <div class="p-8">
                  <h3 class="text-2xl font-bold text-gray-900 mb-6 pb-3 border-b-2 border-blue-500 inline-block">
                    ⚾ Batting Performance
                  </h3>

                  {/* Offensive Value */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">💎</span> Offensive Value
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <MetricCard
                        label="wRC+"
                        value={formatStat(latestBatting.aggregated_stats['wRC+'] || latestBatting.aggregated_stats.wRC_plus, 0)}
                        tooltip="Weighted Runs Created Plus (100 = league average)"
                        tier={getWrcPlusTier(latestBatting.aggregated_stats['wRC+'] || latestBatting.aggregated_stats.wRC_plus)}
                      />
                      <MetricCard
                        label="OPS+"
                        value={formatStat(latestBatting.aggregated_stats['OPS+'] || latestBatting.aggregated_stats.OPS_plus, 0)}
                        tooltip="On-Base Plus Slugging Plus (100 = league average)"
                        tier={getWrcPlusTier(latestBatting.aggregated_stats['OPS+'] || latestBatting.aggregated_stats.OPS_plus)}
                      />
                      <MetricCard
                        label="wRAA"
                        value={formatStat(latestBatting.aggregated_stats.wRAA, 1)}
                        tooltip="Weighted Runs Above Average"
                        tier={getTier(latestBatting.aggregated_stats.wRAA, [[-10, 'poor'], [0, 'below'], [10, 'average'], [20, 'good'], [999, 'elite']])}
                      />
                      <MetricCard
                        label="wRC"
                        value={formatStat(latestBatting.aggregated_stats.wRC, 0)}
                        tooltip="Weighted Runs Created"
                        tier="neutral"
                      />
                    </div>
                  </div>

                  {/* Traditional Triple Slash */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">📊</span> Triple Slash Line
                    </h4>
                    <div class="grid grid-cols-3 md:grid-cols-6 gap-4">
                      <MetricCard
                        label="AVG"
                        value={formatStat(latestBatting.aggregated_stats.ba || latestBatting.aggregated_stats.avg, 3)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="OBP"
                        value={formatStat(latestBatting.aggregated_stats.obp, 3)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="SLG"
                        value={formatStat(latestBatting.aggregated_stats.slg, 3)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="OPS"
                        value={formatStat(latestBatting.aggregated_stats.OPS || latestBatting.aggregated_stats.ops, 3)}
                        tier={getOpsTier(latestBatting.aggregated_stats.OPS || latestBatting.aggregated_stats.ops)}
                      />
                      <MetricCard
                        label="wOBA"
                        value={formatStat(latestBatting.aggregated_stats.wOBA, 3)}
                        tooltip="Weighted On-Base Average"
                        tier={getWobaTier(latestBatting.aggregated_stats.wOBA)}
                      />
                      <MetricCard
                        label="BABIP"
                        value={formatStat(latestBatting.aggregated_stats.BABIP || latestBatting.aggregated_stats.babip, 3)}
                        tooltip="Batting Average on Balls In Play"
                        tier="neutral"
                      />
                    </div>
                  </div>

                  {/* Contact & Discipline */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">🎯</span> Contact & Discipline
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <MetricCard
                        label="BB%"
                        value={formatStat(latestBatting.aggregated_stats['BB%'], 1) + "%"}
                        tooltip="Walk Rate"
                        tier={getTier(latestBatting.aggregated_stats['BB%'], [[5, 'poor'], [8, 'below'], [10, 'average'], [13, 'good'], [999, 'elite']])}
                      />
                      <MetricCard
                        label="K%"
                        value={formatStat(latestBatting.aggregated_stats['K%'], 1) + "%"}
                        tooltip="Strikeout Rate (lower is better)"
                        tier={getTier(latestBatting.aggregated_stats['K%'], [[15, 'elite'], [20, 'good'], [25, 'average'], [30, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="BB/K"
                        value={formatStat((latestBatting.aggregated_stats['BB%'] || 0) / (latestBatting.aggregated_stats['K%'] || 1), 2)}
                        tooltip="Walk to Strikeout Ratio"
                        tier="neutral"
                      />
                      <MetricCard
                        label="ISO"
                        value={formatStat(latestBatting.aggregated_stats.ISO, 3)}
                        tooltip="Isolated Power (SLG - AVG)"
                        tier={getTier(latestBatting.aggregated_stats.ISO, [[0.1, 'poor'], [0.14, 'below'], [0.17, 'average'], [0.2, 'good'], [999, 'elite']])}
                      />
                    </div>
                  </div>

                  {/* Power & Counting Stats */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">💪</span> Power & Production
                    </h4>
                    <div class="grid grid-cols-3 md:grid-cols-6 gap-4">
                      <MetricCard
                        label="HR"
                        value={formatIntStat(latestBatting.aggregated_stats.homeRuns || latestBatting.aggregated_stats.hr)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="XBH"
                        value={formatIntStat(latestBatting.aggregated_stats.XBH)}
                        tooltip="Extra Base Hits (2B + 3B + HR)"
                        tier="neutral"
                      />
                      <MetricCard
                        label="RBI"
                        value={formatIntStat(latestBatting.aggregated_stats.rbi)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="Runs"
                        value={formatIntStat(latestBatting.aggregated_stats.runs)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="Hits"
                        value={formatIntStat(latestBatting.aggregated_stats.hits || latestBatting.aggregated_stats.h)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="Games"
                        value={latestBatting.games_played.toString()}
                        tier="neutral"
                      />
                    </div>
                  </div>

                  {/* Speed & Base Running */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">⚡</span> Speed & Base Running
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <MetricCard
                        label="SB"
                        value={formatIntStat(latestBatting.aggregated_stats.stolenBases || latestBatting.aggregated_stats.sb)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="SB%"
                        value={formatStat(latestBatting.aggregated_stats['SB%'], 1) + "%"}
                        tooltip="Stolen Base Success Rate"
                        tier={getTier(latestBatting.aggregated_stats['SB%'], [[65, 'poor'], [70, 'below'], [75, 'average'], [80, 'good'], [999, 'elite']])}
                      />
                      <MetricCard
                        label="BSR"
                        value={formatStat(latestBatting.aggregated_stats.BSR, 1)}
                        tooltip="Base Running Runs"
                        tier={getTier(latestBatting.aggregated_stats.BSR, [[-3, 'poor'], [0, 'below'], [2, 'average'], [4, 'good'], [999, 'elite']])}
                      />
                      <MetricCard
                        label="wSB"
                        value={formatStat(latestBatting.aggregated_stats.wSB, 1)}
                        tooltip="Weighted Stolen Base Runs"
                        tier="neutral"
                      />
                      <MetricCard
                        label="Spd"
                        value={formatStat(latestBatting.aggregated_stats.Spd, 1)}
                        tooltip="Speed Score (0-10 scale)"
                        tier={getTier(latestBatting.aggregated_stats.Spd, [[3, 'poor'], [4.5, 'below'], [5.5, 'average'], [7, 'good'], [999, 'elite']])}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Pitching Stats */}
              {latestPitching && (
                <div class="p-8 border-t-4 border-slate-100">
                  <h3 class="text-2xl font-bold text-gray-900 mb-6 pb-3 border-b-2 border-red-500 inline-block">
                    🔥 Pitching Performance
                  </h3>

                  {/* Pitching Value */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">🎖️</span> Pitching Value & ERA Estimators
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <MetricCard
                        label="ERA"
                        value={formatStat(latestPitching.aggregated_stats.ERA || latestPitching.aggregated_stats.era, 2)}
                        tier={getTier(latestPitching.aggregated_stats.ERA || latestPitching.aggregated_stats.era, [[2.5, 'elite'], [3.5, 'good'], [4.0, 'average'], [4.5, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="FIP"
                        value={formatStat(latestPitching.aggregated_stats.FIP, 2)}
                        tooltip="Fielding Independent Pitching"
                        tier={getTier(latestPitching.aggregated_stats.FIP, [[3.0, 'elite'], [3.75, 'good'], [4.2, 'average'], [4.7, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="xFIP"
                        value={formatStat(latestPitching.aggregated_stats.xFIP, 2)}
                        tooltip="Expected FIP (normalized HR/FB)"
                        tier={getTier(latestPitching.aggregated_stats.xFIP, [[3.2, 'elite'], [3.9, 'good'], [4.3, 'average'], [4.8, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="SIERA"
                        value={formatStat(latestPitching.aggregated_stats.SIERA, 2)}
                        tooltip="Skill-Interactive ERA"
                        tier={getTier(latestPitching.aggregated_stats.SIERA, [[3.3, 'elite'], [3.9, 'good'], [4.2, 'average'], [4.6, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="WHIP"
                        value={formatStat(latestPitching.aggregated_stats.WHIP, 2)}
                        tooltip="Walks + Hits per Inning"
                        tier={getTier(latestPitching.aggregated_stats.WHIP, [[1.0, 'elite'], [1.2, 'good'], [1.3, 'average'], [1.4, 'below'], [999, 'poor']])}
                      />
                    </div>
                  </div>

                  {/* Adjusted Metrics */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">⚖️</span> Park-Adjusted Metrics (100 = Average)
                    </h4>
                    <div class="grid grid-cols-3 gap-4">
                      <MetricCard
                        label="ERA-"
                        value={formatStat(latestPitching.aggregated_stats['ERA-'] || latestPitching.aggregated_stats.ERA_minus, 0)}
                        tooltip="Lower is better"
                        tier={getTier(latestPitching.aggregated_stats['ERA-'] || latestPitching.aggregated_stats.ERA_minus, [[70, 'elite'], [85, 'good'], [100, 'average'], [115, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="FIP-"
                        value={formatStat(latestPitching.aggregated_stats['FIP-'] || latestPitching.aggregated_stats.FIP_minus, 0)}
                        tooltip="Lower is better"
                        tier={getTier(latestPitching.aggregated_stats['FIP-'] || latestPitching.aggregated_stats.FIP_minus, [[75, 'elite'], [90, 'good'], [100, 'average'], [110, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="xFIP-"
                        value={formatStat(latestPitching.aggregated_stats['xFIP-'] || latestPitching.aggregated_stats.xFIP_minus, 0)}
                        tooltip="Lower is better"
                        tier={getTier(latestPitching.aggregated_stats['xFIP-'] || latestPitching.aggregated_stats.xFIP_minus, [[80, 'elite'], [90, 'good'], [100, 'average'], [110, 'below'], [999, 'poor']])}
                      />
                    </div>
                  </div>

                  {/* Strikeout & Control */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">🎯</span> Strikeout & Control
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
                      <MetricCard
                        label="K%"
                        value={formatStat(latestPitching.aggregated_stats['K%'], 1) + "%"}
                        tooltip="Strikeout Rate"
                        tier={getTier(latestPitching.aggregated_stats['K%'], [[15, 'poor'], [19, 'below'], [22, 'average'], [26, 'good'], [999, 'elite']])}
                      />
                      <MetricCard
                        label="BB%"
                        value={formatStat(latestPitching.aggregated_stats['BB%'], 1) + "%"}
                        tooltip="Walk Rate (lower is better)"
                        tier={getTier(latestPitching.aggregated_stats['BB%'], [[5, 'elite'], [7, 'good'], [8.5, 'average'], [10, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="K-BB%"
                        value={formatStat(latestPitching.aggregated_stats['K-BB%'], 1) + "%"}
                        tooltip="K% minus BB%"
                        tier={getTier(latestPitching.aggregated_stats['K-BB%'], [[10, 'poor'], [13, 'below'], [16, 'average'], [20, 'good'], [999, 'elite']])}
                      />
                      <MetricCard
                        label="K/9"
                        value={formatStat(latestPitching.aggregated_stats['K/9'], 1)}
                        tooltip="Strikeouts per 9 innings"
                        tier="neutral"
                      />
                      <MetricCard
                        label="BB/9"
                        value={formatStat(latestPitching.aggregated_stats['BB/9'], 1)}
                        tooltip="Walks per 9 innings"
                        tier="neutral"
                      />
                      <MetricCard
                        label="K/BB"
                        value={formatStat(latestPitching.aggregated_stats['K/BB'], 2)}
                        tooltip="Strikeout to Walk Ratio"
                        tier="neutral"
                      />
                    </div>
                  </div>

                  {/* Rate Stats */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">📈</span> Rate Stats per 9 Innings
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <MetricCard
                        label="HR/9"
                        value={formatStat(latestPitching.aggregated_stats['HR/9'], 2)}
                        tooltip="Home Runs per 9 innings"
                        tier={getTier(latestPitching.aggregated_stats['HR/9'], [[0.6, 'elite'], [0.9, 'good'], [1.1, 'average'], [1.3, 'below'], [999, 'poor']])}
                      />
                      <MetricCard
                        label="H/9"
                        value={formatStat(latestPitching.aggregated_stats['H/9'], 1)}
                        tooltip="Hits per 9 innings"
                        tier="neutral"
                      />
                      <MetricCard
                        label="LOB%"
                        value={formatStat(latestPitching.aggregated_stats['LOB%'], 1) + "%"}
                        tooltip="Left On Base Percentage"
                        tier="neutral"
                      />
                      <MetricCard
                        label="E-F"
                        value={formatStat(latestPitching.aggregated_stats['E-F'], 2)}
                        tooltip="ERA minus FIP (luck indicator)"
                        tier="neutral"
                      />
                    </div>
                  </div>

                  {/* Traditional Stats */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">📊</span> Traditional Stats
                    </h4>
                    <div class="grid grid-cols-3 md:grid-cols-6 gap-4">
                      <MetricCard
                        label="W-L"
                        value={`${formatIntStat(latestPitching.aggregated_stats.wins || latestPitching.aggregated_stats.w) || 0}-${
                          formatIntStat(latestPitching.aggregated_stats.losses || latestPitching.aggregated_stats.l) || 0
                        }`}
                        tier="neutral"
                      />
                      <MetricCard
                        label="SV"
                        value={formatIntStat(latestPitching.aggregated_stats.saves || latestPitching.aggregated_stats.sv)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="IP"
                        value={formatStat(latestPitching.aggregated_stats.inningsPitched || latestPitching.aggregated_stats.ip, 1)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="SO"
                        value={formatIntStat(latestPitching.aggregated_stats.strikeOuts || latestPitching.aggregated_stats.so)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="BB"
                        value={formatIntStat(latestPitching.aggregated_stats.baseOnBalls || latestPitching.aggregated_stats.bb)}
                        tier="neutral"
                      />
                      <MetricCard
                        label="Games"
                        value={latestPitching.games_played.toString()}
                        tier="neutral"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Fielding Stats */}
              {latestFielding && (
                <div class="p-8 border-t-4 border-slate-100">
                  <h3 class="text-2xl font-bold text-gray-900 mb-6 pb-3 border-b-2 border-green-500 inline-block">
                    🧤 Fielding & Defense
                  </h3>

                  {/* Advanced Fielding Metrics */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">🏆</span> Advanced Fielding Metrics
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <MetricCard
                        label="UZR"
                        value={formatStat(latestFielding.aggregated_stats.UZR, 1)}
                        tooltip="Ultimate Zone Rating"
                        tier={getTier(latestFielding.aggregated_stats.UZR, [[-10, 'poor'], [-5, 'below'], [0, 'average'], [5, 'good'], [999, 'elite']])}
                      />
                      <MetricCard
                        label="DRS"
                        value={formatStat(latestFielding.aggregated_stats.DRS, 1)}
                        tooltip="Defensive Runs Saved"
                        tier={getTier(latestFielding.aggregated_stats.DRS, [[-10, 'poor'], [-5, 'below'], [0, 'average'], [5, 'good'], [999, 'elite']])}
                      />
                      <MetricCard
                        label="RngR"
                        value={formatStat(latestFielding.aggregated_stats.RngR, 1)}
                        tooltip="Range Runs"
                        tier="neutral"
                      />
                      <MetricCard
                        label="ErrR"
                        value={formatStat(latestFielding.aggregated_stats.ErrR, 1)}
                        tooltip="Error Runs"
                        tier="neutral"
                      />
                      <MetricCard
                        label="DPR"
                        value={formatStat(latestFielding.aggregated_stats.DPR, 1)}
                        tooltip="Double Play Runs"
                        tier="neutral"
                      />
                    </div>
                  </div>

                  {/* Traditional Fielding */}
                  <div class="mb-8">
                    <h4 class="text-lg font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <span class="text-2xl">📊</span> Traditional Fielding
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                      <MetricCard
                        label="FPCT"
                        value={formatStat(latestFielding.aggregated_stats.FPCT || latestFielding.aggregated_stats.fielding, 3)}
                        tooltip="Fielding Percentage"
                        tier="neutral"
                      />
                      <MetricCard
                        label="RF/G"
                        value={formatStat(latestFielding.aggregated_stats['RF/G'] || latestFielding.aggregated_stats.RF, 2)}
                        tooltip="Range Factor per Game"
                        tier="neutral"
                      />
                      <MetricCard
                        label="RF/9"
                        value={formatStat(latestFielding.aggregated_stats['RF/9'], 2)}
                        tooltip="Range Factor per 9 innings"
                        tier="neutral"
                      />
                      <MetricCard
                        label="ZR"
                        value={formatStat(latestFielding.aggregated_stats.ZR, 3)}
                        tooltip="Zone Rating"
                        tier="neutral"
                      />
                      <MetricCard
                        label="Play%"
                        value={formatStat(latestFielding.aggregated_stats['Play%'], 1) + "%"}
                        tooltip="Plays Made Percentage"
                        tier="neutral"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Career Stats Tables */}
        {battingStats.length > 1 && (
          <CareerTable
            title="Career Batting Statistics"
            icon="⚾"
            stats={battingStats}
            type="batting"
          />
        )}

        {pitchingStats.length > 1 && (
          <CareerTable
            title="Career Pitching Statistics"
            icon="🔥"
            stats={pitchingStats}
            type="pitching"
          />
        )}

        {/* No Stats Available */}
        {stats.length === 0 && (
          <div class="bg-white rounded-2xl shadow-xl p-12 text-center">
            <div class="text-gray-300 text-6xl mb-6">📊</div>
            <h3 class="text-2xl font-bold text-gray-900 mb-3">
              No Statistics Available
            </h3>
            <p class="text-gray-600 text-lg">
              Statistics for this player are not yet available in the database.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Enhanced Metric Card with color coding
function MetricCard({
  label,
  value,
  tooltip,
  tier = "neutral",
}: {
  label: string;
  value: string;
  tooltip?: string;
  tier?: "elite" | "good" | "average" | "below" | "poor" | "neutral";
}) {
  const colors = {
    elite: "bg-gradient-to-br from-purple-50 to-purple-100 border-2 border-purple-400",
    good: "bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-400",
    average: "bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-300",
    below: "bg-gradient-to-br from-yellow-50 to-yellow-100 border-2 border-yellow-400",
    poor: "bg-gradient-to-br from-red-50 to-red-100 border-2 border-red-400",
    neutral: "bg-gradient-to-br from-slate-50 to-slate-100 border-2 border-slate-200",
  };

  return (
    <div
      class={`${colors[tier]} rounded-xl p-4 shadow-md hover:shadow-lg transition-shadow`}
      title={tooltip}
    >
      <div class="text-sm font-medium text-gray-600 mb-1">{label}</div>
      <div class="text-2xl font-bold text-gray-900">{value}</div>
      {tooltip && (
        <div class="text-xs text-gray-500 mt-1 truncate">{tooltip}</div>
      )}
    </div>
  );
}

// Career Stats Table Component
function CareerTable({
  title,
  icon,
  stats,
  type,
}: {
  title: string;
  icon: string;
  stats: PlayerStats[];
  type: "batting" | "pitching";
}) {
  return (
    <div class="bg-white rounded-2xl shadow-xl mb-8 overflow-hidden">
      <div class="px-8 py-6 bg-gradient-to-r from-slate-800 to-slate-700">
        <h2 class="text-3xl font-bold text-white flex items-center gap-3">
          <span>{icon}</span> {title}
        </h2>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-slate-50">
            {type === "batting" ? (
              <tr>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Season
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  G
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  AVG
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  OBP
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  SLG
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  OPS
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  wRC+
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  wOBA
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  HR
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  RBI
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  SB
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  BB%
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  K%
                </th>
              </tr>
            ) : (
              <tr>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Season
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  G
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  ERA
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  FIP
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  xFIP
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  WHIP
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  W-L
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  IP
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  K%
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  BB%
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  K/9
                </th>
                <th class="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                  HR/9
                </th>
              </tr>
            )}
          </thead>
          <tbody class="bg-white divide-y divide-gray-100">
            {stats
              .sort((a, b) => b.season - a.season)
              .map((stat, idx) => (
                <tr key={stat.season} class={idx % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                  <td class="px-6 py-4 whitespace-nowrap font-bold text-gray-900">
                    {stat.season}
                  </td>
                  {type === "batting" ? (
                    <>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {stat.games_played}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.ba || stat.aggregated_stats.avg, 3)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.obp, 3)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.slg, 3)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.OPS || stat.aggregated_stats.ops, 3)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                        {formatStat(stat.aggregated_stats['wRC+'] || stat.aggregated_stats.wRC_plus, 0)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.wOBA, 3)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatIntStat(stat.aggregated_stats.homeRuns || stat.aggregated_stats.hr)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatIntStat(stat.aggregated_stats.rbi)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatIntStat(stat.aggregated_stats.stolenBases || stat.aggregated_stats.sb)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats['BB%'], 1)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats['K%'], 1)}
                      </td>
                    </>
                  ) : (
                    <>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {stat.games_played}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.ERA || stat.aggregated_stats.era, 2)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.FIP, 2)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.xFIP, 2)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.WHIP, 2)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatIntStat(stat.aggregated_stats.wins || stat.aggregated_stats.w) || 0}-
                        {formatIntStat(stat.aggregated_stats.losses || stat.aggregated_stats.l) || 0}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats.inningsPitched || stat.aggregated_stats.ip, 1)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats['K%'], 1)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats['BB%'], 1)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats['K/9'], 1)}
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStat(stat.aggregated_stats['HR/9'], 2)}
                      </td>
                    </>
                  )}
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Helper functions for tier coloring
function getWrcPlusTier(value: number): "elite" | "good" | "average" | "below" | "poor" | "neutral" {
  if (!value) return "neutral";
  if (value >= 140) return "elite";
  if (value >= 115) return "good";
  if (value >= 90) return "average";
  if (value >= 75) return "below";
  return "poor";
}

function getOpsTier(value: number): "elite" | "good" | "average" | "below" | "poor" | "neutral" {
  if (!value) return "neutral";
  if (value >= 0.900) return "elite";
  if (value >= 0.800) return "good";
  if (value >= 0.720) return "average";
  if (value >= 0.650) return "below";
  return "poor";
}

function getWobaTier(value: number): "elite" | "good" | "average" | "below" | "poor" | "neutral" {
  if (!value) return "neutral";
  if (value >= 0.370) return "elite";
  if (value >= 0.340) return "good";
  if (value >= 0.310) return "average";
  if (value >= 0.290) return "below";
  return "poor";
}

function getTier(
  value: number,
  thresholds: [number, "elite" | "good" | "average" | "below" | "poor"][]
): "elite" | "good" | "average" | "below" | "poor" | "neutral" {
  if (value === null || value === undefined) return "neutral";
  for (const [threshold, tier] of thresholds) {
    if (value <= threshold) return tier;
  }
  return "neutral";
}

// Helper to safely format numeric stats
function formatStat(value: any, decimals: number = 3): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  return isNaN(num) ? "—" : num.toFixed(decimals);
}

// Helper to format integer stats
function formatIntStat(value: any): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "string" ? parseInt(value) : value;
  return isNaN(num) ? "—" : num.toString();
}
