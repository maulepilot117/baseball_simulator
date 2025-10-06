import { useEffect, useState } from "preact/hooks";
import type { Game, SimulationRun, SimulationResult } from "../lib/types.ts";

interface Props {
  game: Game;
}

export default function GameSimulation({ game }: Props) {
  const [isSimulating, setIsSimulating] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<SimulationRun | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Start simulation
  const startSimulation = async () => {
    setIsSimulating(true);
    setError(null);
    setResult(null);
    setStatus(null);
    setRunId(null);

    try {
      const response = await fetch("/api/simulations/game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_id: game.game_id }),
      });

      if (!response.ok) {
        throw new Error("Failed to start simulation");
      }

      const data = await response.json();
      console.log("✅ Simulation started! Run ID:", data.run_id);
      setRunId(data.run_id);

      // Start polling for status
      pollStatus(data.run_id);
    } catch (err) {
      console.error("❌ Failed to start simulation:", err);
      setError(err instanceof Error ? err.message : "Failed to start simulation");
      setIsSimulating(false);
    }
  };

  // Poll simulation status
  const pollStatus = async (id: string) => {
    const poll = async () => {
      try {
        console.log("🔄 Polling status for run:", id);
        const statusResponse = await fetch(`/api/simulations/${id}/status`);
        if (!statusResponse.ok) {
          console.warn("⚠️ Status check failed:", statusResponse.status);
          return;
        }

        const statusData: SimulationRun = await statusResponse.json();
        console.log("📊 Status update:", statusData.status, `${statusData.completed_runs}/${statusData.total_runs}`);
        setStatus(statusData);

        if (statusData.status === "completed") {
          // Fetch full results
          const resultResponse = await fetch(`/api/simulations/${id}/result`);
          if (resultResponse.ok) {
            const resultData: SimulationResult = await resultResponse.json();
            console.log("Simulation result received:", resultData);
            console.log("Has player_performance?", !!resultData.player_performance);
            if (resultData.player_performance) {
              console.log("Home batting count:", Object.keys(resultData.player_performance.home_team.batting).length);
              console.log("Away batting count:", Object.keys(resultData.player_performance.away_team.batting).length);
            }
            setResult(resultData);
          }
          setIsSimulating(false);
        } else if (statusData.status === "failed") {
          setError("Simulation failed");
          setIsSimulating(false);
        } else {
          // Continue polling
          setTimeout(poll, 2000);
        }
      } catch (err) {
        console.error("Polling error:", err);
        setTimeout(poll, 5000);
      }
    };

    poll();
  };

  const homeTeam = game.home_team?.name || game.home_team_name || "Home Team";
  const awayTeam = game.away_team?.name || game.away_team_name || "Away Team";

  return (
    <div class="space-y-6">
      {/* Simulation Control */}
      <div class="bg-white rounded-xl shadow-md p-6">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">Monte Carlo Simulation</h2>
            <p class="text-gray-600">
              Run 1000 simulations using real player stats, weather forecasts, park factors, and umpire tendencies
            </p>
          </div>
          <button
            onClick={startSimulation}
            disabled={isSimulating}
            class={`px-6 py-3 rounded-lg font-semibold transition-all transform ${
              isSimulating
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-gradient-to-r from-blue-600 to-green-600 text-white hover:from-blue-700 hover:to-green-700 hover:scale-105 shadow-lg"
            }`}
          >
            {isSimulating ? (
              <span class="flex items-center gap-2">
                <svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Simulating...
              </span>
            ) : (
              "🎲 Run Simulation"
            )}
          </button>
        </div>

        {error && (
          <div class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Simulation Progress */}
      {status && status.status === "running" && (
        <div class="bg-white rounded-xl shadow-md p-6">
          <div class="flex items-center gap-2 text-blue-700 text-sm font-medium mb-3">
            <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Running simulation... {status.completed_runs} / {status.total_runs} completed
          </div>
          <div class="w-full bg-blue-200 rounded-full h-3">
            <div
              class="bg-gradient-to-r from-blue-600 to-green-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${status.progress * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Simulation Results */}
      {result && (
        <div class="space-y-6">
          {/* Win Probabilities */}
          <div class="bg-white rounded-xl shadow-md overflow-hidden">
            <div class="bg-gradient-to-r from-blue-600 to-green-600 p-4 text-white">
              <h3 class="text-xl font-bold">Win Probabilities</h3>
              <p class="text-sm text-blue-100">Based on {result.metadata?.total_simulations || 1000} simulations</p>
            </div>
            <div class="p-6">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {/* Away Team */}
                <div class="text-center">
                  <div class="text-sm text-gray-600 mb-2">{awayTeam}</div>
                  <div class="text-5xl font-bold text-gray-900 mb-2">
                    {(result.away_win_probability * 100).toFixed(1)}%
                  </div>
                  <div class="text-sm text-gray-600">
                    Avg Score: {result.expected_away_score.toFixed(1)} runs
                  </div>
                </div>

                {/* Home Team */}
                <div class="text-center">
                  <div class="text-sm text-gray-600 mb-2">{homeTeam}</div>
                  <div class="text-5xl font-bold text-gray-900 mb-2">
                    {(result.home_win_probability * 100).toFixed(1)}%
                  </div>
                  <div class="text-sm text-gray-600">
                    Avg Score: {result.expected_home_score.toFixed(1)} runs
                  </div>
                </div>
              </div>

              {/* Visual Probability Bar */}
              <div class="relative h-10 bg-gray-100 rounded-lg overflow-hidden">
                <div
                  class="absolute left-0 h-full bg-gradient-to-r from-red-500 to-red-400 flex items-center justify-start px-3"
                  style={{ width: `${result.away_win_probability * 100}%` }}
                >
                  <span class="text-white font-semibold text-sm">{awayTeam}</span>
                </div>
                <div
                  class="absolute right-0 h-full bg-gradient-to-l from-blue-500 to-blue-400 flex items-center justify-end px-3"
                  style={{ width: `${result.home_win_probability * 100}%` }}
                >
                  <span class="text-white font-semibold text-sm">{homeTeam}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Score Distributions */}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Away Score Distribution */}
            <div class="bg-white rounded-xl shadow-md p-6">
              <h3 class="text-lg font-bold text-gray-900 mb-4">{awayTeam} Score Distribution</h3>
              <div class="space-y-2">
                {Object.entries(result.away_score_distribution || {})
                  .sort((a, b) => parseInt(a[0]) - parseInt(b[0]))
                  .slice(0, 10)
                  .map(([score, count]) => {
                    const percentage = (count / (result.metadata?.total_simulations || 1000)) * 100;
                    return (
                      <div key={score} class="flex items-center gap-3">
                        <div class="w-8 text-right font-medium text-gray-700">{score}</div>
                        <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                          <div
                            class="bg-red-500 h-full flex items-center px-2"
                            style={{ width: `${percentage}%` }}
                          >
                            <span class="text-xs text-white font-medium">{percentage.toFixed(1)}%</span>
                          </div>
                        </div>
                        <div class="w-12 text-right text-sm text-gray-600">{count}</div>
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* Home Score Distribution */}
            <div class="bg-white rounded-xl shadow-md p-6">
              <h3 class="text-lg font-bold text-gray-900 mb-4">{homeTeam} Score Distribution</h3>
              <div class="space-y-2">
                {Object.entries(result.home_score_distribution || {})
                  .sort((a, b) => parseInt(a[0]) - parseInt(b[0]))
                  .slice(0, 10)
                  .map(([score, count]) => {
                    const percentage = (count / (result.metadata?.total_simulations || 1000)) * 100;
                    return (
                      <div key={score} class="flex items-center gap-3">
                        <div class="w-8 text-right font-medium text-gray-700">{score}</div>
                        <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                          <div
                            class="bg-blue-500 h-full flex items-center px-2"
                            style={{ width: `${percentage}%` }}
                          >
                            <span class="text-xs text-white font-medium">{percentage.toFixed(1)}%</span>
                          </div>
                        </div>
                        <div class="w-12 text-right text-sm text-gray-600">{count}</div>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>

          {/* Statistics */}
          {result.metadata?.statistics && (
            <div class="bg-white rounded-xl shadow-md p-6">
              <h3 class="text-lg font-bold text-gray-900 mb-4">Game Statistics</h3>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="text-center p-4 bg-gray-50 rounded-lg">
                  <div class="text-2xl font-bold text-gray-900">
                    {result.metadata.statistics.one_run_game_percentage?.toFixed(1)}%
                  </div>
                  <div class="text-sm text-gray-600">One-Run Games</div>
                </div>
                <div class="text-center p-4 bg-gray-50 rounded-lg">
                  <div class="text-2xl font-bold text-gray-900">
                    {result.metadata.statistics.shutout_percentage?.toFixed(1)}%
                  </div>
                  <div class="text-sm text-gray-600">Shutouts</div>
                </div>
                <div class="text-center p-4 bg-gray-50 rounded-lg">
                  <div class="text-2xl font-bold text-gray-900">
                    {result.metadata.average_game_duration?.toFixed(0)}
                  </div>
                  <div class="text-sm text-gray-600">Avg Minutes</div>
                </div>
                <div class="text-center p-4 bg-gray-50 rounded-lg">
                  <div class="text-2xl font-bold text-gray-900">
                    {result.metadata.average_pitches?.toFixed(0)}
                  </div>
                  <div class="text-sm text-gray-600">Avg Pitches</div>
                </div>
              </div>
            </div>
          )}

          {/* Player Performance Predictions */}
          {result.player_performance && (
            <div class="space-y-6">
              <h3 class="text-2xl font-bold text-gray-900">Player Performance Predictions</h3>

              {/* Away Team Batting */}
              <div class="bg-white rounded-xl shadow-md overflow-hidden">
                <div class="bg-red-600 p-4 text-white">
                  <h4 class="text-xl font-bold">{awayTeam} - Batting</h4>
                  <p class="text-sm text-red-100">Expected stats per game</p>
                </div>
                <div class="overflow-x-auto">
                  <table class="w-full text-sm">
                    <thead class="bg-gray-50 text-gray-700">
                      <tr>
                        <th class="px-4 py-3 text-left">Player</th>
                        <th class="px-3 py-3 text-center">PA</th>
                        <th class="px-3 py-3 text-center">AB</th>
                        <th class="px-3 py-3 text-center">H</th>
                        <th class="px-3 py-3 text-center">HR</th>
                        <th class="px-3 py-3 text-center">RBI</th>
                        <th class="px-3 py-3 text-center">AVG</th>
                        <th class="px-3 py-3 text-center">OBP</th>
                        <th class="px-3 py-3 text-center">SLG</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                      {Object.values(result.player_performance.away_team.batting).map((player) => (
                        <tr key={player.player_id} class="hover:bg-gray-50">
                          <td class="px-4 py-3 font-medium text-gray-900">{player.player_name}</td>
                          <td class="px-3 py-3 text-center">{player.pa.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.ab.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.h.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.hr.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.rbi.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.avg.toFixed(3)}</td>
                          <td class="px-3 py-3 text-center">{player.obp.toFixed(3)}</td>
                          <td class="px-3 py-3 text-center">{player.slg.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Home Team Batting */}
              <div class="bg-white rounded-xl shadow-md overflow-hidden">
                <div class="bg-blue-600 p-4 text-white">
                  <h4 class="text-xl font-bold">{homeTeam} - Batting</h4>
                  <p class="text-sm text-blue-100">Expected stats per game</p>
                </div>
                <div class="overflow-x-auto">
                  <table class="w-full text-sm">
                    <thead class="bg-gray-50 text-gray-700">
                      <tr>
                        <th class="px-4 py-3 text-left">Player</th>
                        <th class="px-3 py-3 text-center">PA</th>
                        <th class="px-3 py-3 text-center">AB</th>
                        <th class="px-3 py-3 text-center">H</th>
                        <th class="px-3 py-3 text-center">HR</th>
                        <th class="px-3 py-3 text-center">RBI</th>
                        <th class="px-3 py-3 text-center">AVG</th>
                        <th class="px-3 py-3 text-center">OBP</th>
                        <th class="px-3 py-3 text-center">SLG</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                      {Object.values(result.player_performance.home_team.batting).map((player) => (
                        <tr key={player.player_id} class="hover:bg-gray-50">
                          <td class="px-4 py-3 font-medium text-gray-900">{player.player_name}</td>
                          <td class="px-3 py-3 text-center">{player.pa.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.ab.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.h.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.hr.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.rbi.toFixed(1)}</td>
                          <td class="px-3 py-3 text-center">{player.avg.toFixed(3)}</td>
                          <td class="px-3 py-3 text-center">{player.obp.toFixed(3)}</td>
                          <td class="px-3 py-3 text-center">{player.slg.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Starting Pitchers */}
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Away Pitcher */}
                {Object.values(result.player_performance.away_team.pitching).map((pitcher) => (
                  <div key={pitcher.player_id} class="bg-white rounded-xl shadow-md p-6">
                    <h4 class="text-lg font-bold text-gray-900 mb-4">{awayTeam} Pitcher - {pitcher.player_name}</h4>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.ip.toFixed(1)}</div>
                        <div class="text-xs text-gray-600">Innings Pitched</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.era.toFixed(2)}</div>
                        <div class="text-xs text-gray-600">ERA</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.k.toFixed(1)}</div>
                        <div class="text-xs text-gray-600">Strikeouts</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.whip.toFixed(2)}</div>
                        <div class="text-xs text-gray-600">WHIP</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.h.toFixed(1)}</div>
                        <div class="text-xs text-gray-600">Hits Allowed</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.bb.toFixed(1)}</div>
                        <div class="text-xs text-gray-600">Walks</div>
                      </div>
                    </div>
                  </div>
                ))}

                {/* Home Pitcher */}
                {Object.values(result.player_performance.home_team.pitching).map((pitcher) => (
                  <div key={pitcher.player_id} class="bg-white rounded-xl shadow-md p-6">
                    <h4 class="text-lg font-bold text-gray-900 mb-4">{homeTeam} Pitcher - {pitcher.player_name}</h4>
                    <div class="grid grid-cols-2 gap-4">
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.ip.toFixed(1)}</div>
                        <div class="text-xs text-gray-600">Innings Pitched</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.era.toFixed(2)}</div>
                        <div class="text-xs text-gray-600">ERA</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.k.toFixed(1)}</div>
                        <div class="text-xs text-gray-600">Strikeouts</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.whip.toFixed(2)}</div>
                        <div class="text-xs text-gray-600">WHIP</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.h.toFixed(1)}</div>
                        <div class="text-xs text-gray-600">Hits Allowed</div>
                      </div>
                      <div class="text-center p-3 bg-gray-50 rounded-lg">
                        <div class="text-2xl font-bold text-gray-900">{pitcher.bb.toFixed(1)}</div>
                        <div class="text-xs text-gray-600">Walks</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
