import { useEffect, useState } from "preact/hooks";
import type { Game, SimulationRun, SimulationResult } from "../lib/types.ts";

interface Props {
  initialDate: string;
  initialGames: Game[];
}

interface SimulationState {
  [runId: string]: {
    run: SimulationRun;
    result?: SimulationResult;
  };
}

export default function SimulationDashboard({ initialDate, initialGames }: Props) {
  const [date, setDate] = useState(initialDate);
  const [games, setGames] = useState<Game[]>(initialGames);
  const [simulations, setSimulations] = useState<SimulationState>({});
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load games for selected date
  const loadGames = async (newDate: string) => {
    try {
      setError(null);
      const response = await fetch(`/api/games/date/${newDate}`);
      if (!response.ok) throw new Error("Failed to load games");
      const data = await response.json();
      setGames(data.data || []);
      setDate(newDate);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load games");
    }
  };

  // Start simulations for all games
  const startSimulations = async () => {
    setIsSimulating(true);
    setError(null);

    try {
      const response = await fetch("/api/simulations/daily", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date }),
      });

      if (!response.ok) {
        throw new Error("Failed to start simulations");
      }

      const result = await response.json();

      // Initialize simulation state
      const newSimulations: SimulationState = {};
      result.simulations.forEach((run: SimulationRun) => {
        newSimulations[run.run_id] = { run };
      });
      setSimulations(newSimulations);

      // Start polling
      result.simulations.forEach((run: SimulationRun) => {
        pollSimulation(run.run_id);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start simulations");
      setIsSimulating(false);
    }
  };

  // Poll individual simulation
  const pollSimulation = async (runId: string) => {
    const poll = async () => {
      try {
        const statusResponse = await fetch(`/api/simulations/${runId}/status`);
        if (!statusResponse.ok) return;

        const status: SimulationRun = await statusResponse.json();

        setSimulations(prev => ({
          ...prev,
          [runId]: { ...prev[runId], run: status },
        }));

        if (status.status === "completed") {
          // Fetch full results
          const resultResponse = await fetch(`/api/simulations/${runId}/result`);
          if (resultResponse.ok) {
            const result: SimulationResult = await resultResponse.json();
            setSimulations(prev => ({
              ...prev,
              [runId]: { ...prev[runId], result },
            }));
          }
          setIsSimulating(false);
        } else if (status.status === "failed") {
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

  return (
    <div class="space-y-6">
      {/* Date Selector */}
      <div class="bg-white rounded-xl shadow-md p-6">
        <div class="flex items-center justify-between gap-4">
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Select Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => loadGames((e.target as HTMLInputElement).value)}
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div class="flex items-end">
            <button
              onClick={startSimulations}
              disabled={isSimulating || games.length === 0}
              class={`px-6 py-3 rounded-lg font-semibold transition-all transform ${
                isSimulating || games.length === 0
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
                `🎲 Simulate ${games.length} Game${games.length !== 1 ? "s" : ""}`
              )}
            </button>
          </div>
        </div>
        {error && (
          <div class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Games List */}
      {games.length === 0 ? (
        <div class="bg-white rounded-xl shadow-md p-12 text-center">
          <div class="text-6xl mb-4">📅</div>
          <h3 class="text-xl font-semibold text-gray-700 mb-2">No Games Scheduled</h3>
          <p class="text-gray-500">Select a different date to view scheduled games</p>
        </div>
      ) : (
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {games.map((game) => {
            const gameSimulation = Object.values(simulations).find(
              (sim) => sim.run.game_id === game.game_id
            );

            return (
              <div key={game.id}>
                <a href={`/games/${game.id}`} class="block hover:scale-[1.02] transition-transform">
                  <GameCard
                    game={game}
                    simulation={gameSimulation}
                  />
                </a>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Game Card Component
function GameCard({ game, simulation }: {
  game: Game;
  simulation?: { run: SimulationRun; result?: SimulationResult }
}) {
  const result = simulation?.result;
  const status = simulation?.run.status;

  return (
    <div class="bg-white rounded-xl shadow-md hover:shadow-xl transition-shadow overflow-hidden">
      {/* Game Header */}
      <div class="bg-gradient-to-r from-blue-600 to-blue-700 p-4 text-white">
        <div class="flex justify-between items-center">
          <div class="text-sm font-medium opacity-90">
            {new Date(game.game_date).toLocaleDateString("en-US", {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </div>
          <div class="text-sm font-medium opacity-90">
            {game.status}
          </div>
        </div>
      </div>

      {/* Teams */}
      <div class="p-6">
        <div class="space-y-3 mb-4">
          <TeamRow
            team={(game.away_team?.name) || game.away_team_name || "Away Team"}
            isAway
            winProb={result?.away_win_probability}
            avgScore={result?.avg_away_score}
          />
          <div class="text-center text-gray-400 text-sm font-medium">@</div>
          <TeamRow
            team={(game.home_team?.name) || game.home_team_name || "Home Team"}
            isAway={false}
            winProb={result?.home_win_probability}
            avgScore={result?.avg_home_score}
          />
        </div>

        {/* Simulation Status */}
        {status === "running" && (
          <div class="mt-4 p-3 bg-blue-50 rounded-lg">
            <div class="flex items-center gap-2 text-blue-700 text-sm font-medium mb-2">
              <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Running simulation...
            </div>
            <div class="w-full bg-blue-200 rounded-full h-2">
              <div
                class="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${simulation.run.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div class="mt-4 space-y-3">
            {/* Win Probability Chart */}
            <div class="relative h-8 bg-gray-100 rounded-lg overflow-hidden">
              <div
                class="absolute left-0 h-full bg-gradient-to-r from-red-500 to-red-400"
                style={{ width: `${result.away_win_probability * 100}%` }}
              />
              <div
                class="absolute right-0 h-full bg-gradient-to-l from-blue-500 to-blue-400"
                style={{ width: `${result.home_win_probability * 100}%` }}
              />
            </div>

            {/* Environmental Factors */}
            <div class="grid grid-cols-2 gap-2 text-xs">
              {result.weather && (
                <div class="bg-blue-50 rounded p-2">
                  <div class="font-medium text-blue-900">Weather</div>
                  <div class="text-blue-700">
                    {result.weather.temperature}°F, {result.weather.wind_speed}mph {result.weather.wind_dir}
                  </div>
                </div>
              )}
              {result.park_factors && (
                <div class="bg-green-50 rounded p-2">
                  <div class="font-medium text-green-900">Park</div>
                  <div class="text-green-700">
                    HR: {result.park_factors.hr_factor}, R: {result.park_factors.runs_factor}
                  </div>
                </div>
              )}
              {result.umpire && (
                <div class="bg-purple-50 rounded p-2 col-span-2">
                  <div class="font-medium text-purple-900">Umpire</div>
                  <div class="text-purple-700">
                    {result.umpire.name} (Zone: {result.umpire.strike_zone_size})
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Team Row Component
function TeamRow({
  team,
  isAway,
  winProb,
  avgScore
}: {
  team: string;
  isAway: boolean;
  winProb?: number;
  avgScore?: number;
}) {
  return (
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class={`w-2 h-2 rounded-full ${isAway ? "bg-red-500" : "bg-blue-500"}`} />
        <span class="font-semibold text-gray-900">{team}</span>
      </div>
      {winProb !== undefined && (
        <div class="text-right">
          <div class="text-2xl font-bold text-gray-900">
            {(winProb * 100).toFixed(1)}%
          </div>
          {avgScore !== undefined && (
            <div class="text-sm text-gray-500">
              Avg: {avgScore.toFixed(1)} runs
            </div>
          )}
        </div>
      )}
    </div>
  );
}
