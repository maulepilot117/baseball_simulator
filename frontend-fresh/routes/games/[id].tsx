import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchGame } from "../../lib/api.ts";
import type { Game, ApiResponse } from "../../lib/types.ts";

interface GameDetailData {
  game: Game | null;
  error?: string;
}

export const handler: Handlers<GameDetailData> = {
  async GET(_req, ctx) {
    const { id } = ctx.params;

    try {
      const game = await fetchGame(id);

      return ctx.render({
        game,
      });
    } catch (error) {
      console.error("Failed to fetch game:", error);
      return ctx.render({
        game: null,
        error: "Failed to load game data",
      });
    }
  },
};

export default function GameDetailPage({ data }: PageProps<GameDetailData>) {
  const { game, error } = data;

  if (error || !game) {
    return (
      <div class="min-h-screen bg-gray-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <a href="/games" class="text-blue-600 hover:underline mb-4 inline-block">
            ← Back to Games
          </a>
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <div class="text-red-600 text-xl mb-4">⚠️</div>
            <h2 class="text-2xl font-bold text-gray-900 mb-2">
              {error || "Game Not Found"}
            </h2>
            <p class="text-gray-600">
              The game you're looking for doesn't exist or could not be loaded.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const gameDate = new Date(game.game_date);
  const hasScore = game.home_score !== undefined && game.away_score !== undefined;

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-6">
          <a href="/games" class="text-blue-600 hover:underline mb-4 inline-block">
            ← Back to Games
          </a>
        </div>

        {/* Game Info Card */}
        <div class="bg-white rounded-lg shadow mb-6">
          <div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <div class="flex justify-between items-center">
              <div>
                <h2 class="text-sm font-medium text-gray-500">
                  {gameDate.toLocaleDateString("en-US", {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </h2>
                <div class="text-xs text-gray-400 mt-1">Season {game.season}</div>
              </div>
              <span
                class={`px-3 py-1 text-sm font-semibold rounded-full ${
                  game.status === "final"
                    ? "bg-green-100 text-green-800"
                    : game.status === "live"
                    ? "bg-red-100 text-red-800"
                    : game.status === "postponed"
                    ? "bg-yellow-100 text-yellow-800"
                    : "bg-blue-100 text-blue-800"
                }`}
              >
                {game.status.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Scoreboard */}
          <div class="p-8">
            <div class="flex items-center justify-between mb-8">
              {/* Away Team */}
              <div class="flex-1 text-center">
                <div class="text-gray-500 text-sm mb-2">AWAY</div>
                <div class="text-2xl font-bold text-gray-900 mb-2">
                  {game.away_team_name || "Away Team"}
                </div>
                {hasScore && (
                  <div class="text-6xl font-bold text-gray-900">
                    {game.away_score}
                  </div>
                )}
              </div>

              {/* VS Divider */}
              <div class="px-8">
                <div class="text-4xl text-gray-400 font-light">@</div>
              </div>

              {/* Home Team */}
              <div class="flex-1 text-center">
                <div class="text-gray-500 text-sm mb-2">HOME</div>
                <div class="text-2xl font-bold text-gray-900 mb-2">
                  {game.home_team_name || "Home Team"}
                </div>
                {hasScore && (
                  <div class="text-6xl font-bold text-gray-900">
                    {game.home_score}
                  </div>
                )}
              </div>
            </div>

            {/* Winner Badge */}
            {hasScore && game.status === "final" && (
              <div class="text-center">
                {game.home_score! > game.away_score! ? (
                  <div class="inline-block px-4 py-2 bg-green-100 text-green-800 rounded-lg font-semibold">
                    🏆 {game.home_team_name} Wins
                  </div>
                ) : game.away_score! > game.home_score! ? (
                  <div class="inline-block px-4 py-2 bg-green-100 text-green-800 rounded-lg font-semibold">
                    🏆 {game.away_team_name} Wins
                  </div>
                ) : (
                  <div class="inline-block px-4 py-2 bg-gray-100 text-gray-800 rounded-lg font-semibold">
                    Tie Game
                  </div>
                )}
              </div>
            )}

            {/* No Score Yet */}
            {!hasScore && (
              <div class="text-center text-gray-500">
                Score not yet available
              </div>
            )}
          </div>
        </div>

        {/* Game Details */}
        <div class="bg-white rounded-lg shadow mb-6">
          <div class="px-6 py-4 border-b border-gray-200">
            <h2 class="text-xl font-semibold text-gray-900">Game Details</h2>
          </div>
          <div class="p-6">
            <div class="grid grid-cols-2 gap-6">
              <div>
                <div class="text-sm text-gray-500 mb-1">Game ID</div>
                <div class="font-mono text-sm text-gray-900">{game.game_id}</div>
              </div>
              <div>
                <div class="text-sm text-gray-500 mb-1">Internal ID</div>
                <div class="font-mono text-sm text-gray-900">{game.id}</div>
              </div>
              <div>
                <div class="text-sm text-gray-500 mb-1">Away Team ID</div>
                <div class="font-mono text-sm text-gray-900">
                  {game.away_team_id}
                </div>
              </div>
              <div>
                <div class="text-sm text-gray-500 mb-1">Home Team ID</div>
                <div class="font-mono text-sm text-gray-900">
                  {game.home_team_id}
                </div>
              </div>
              {game.stadium_id && (
                <div class="col-span-2">
                  <div class="text-sm text-gray-500 mb-1">Stadium ID</div>
                  <div class="font-mono text-sm text-gray-900">
                    {game.stadium_id}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <h2 class="text-xl font-semibold text-gray-900">Actions</h2>
          </div>
          <div class="p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <a
                href={`/teams/${game.away_team_id}`}
                class="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                <span>⚾</span>
                <span>View {game.away_team_name}</span>
              </a>
              <a
                href={`/teams/${game.home_team_id}`}
                class="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                <span>⚾</span>
                <span>View {game.home_team_name}</span>
              </a>
            </div>

            {/* Future: Simulation Button */}
            <div class="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <div class="flex items-center gap-3">
                <div class="text-2xl">🎮</div>
                <div class="flex-1">
                  <div class="font-semibold text-gray-900">
                    Game Simulation
                  </div>
                  <div class="text-sm text-gray-600">
                    Run Monte Carlo simulation for this game (coming soon)
                  </div>
                </div>
                <button
                  disabled
                  class="px-4 py-2 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed"
                >
                  Simulate
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Future Sections */}
        <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Box Score Placeholder */}
          <div class="bg-white rounded-lg shadow p-6 text-center">
            <div class="text-4xl mb-3">📊</div>
            <h3 class="font-semibold text-gray-900 mb-2">Box Score</h3>
            <p class="text-sm text-gray-600">
              Detailed box score coming soon
            </p>
          </div>

          {/* Play-by-Play Placeholder */}
          <div class="bg-white rounded-lg shadow p-6 text-center">
            <div class="text-4xl mb-3">▶️</div>
            <h3 class="font-semibold text-gray-900 mb-2">Play-by-Play</h3>
            <p class="text-sm text-gray-600">
              Play-by-play data coming soon
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
