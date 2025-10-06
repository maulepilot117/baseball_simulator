import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchGame } from "../../lib/api.ts";
import type { Game, ApiResponse } from "../../lib/types.ts";
import GameSimulation from "../../islands/GameSimulation.tsx";

interface BoxScoreBatting {
  player_id: string;
  player_name: string;
  batting_order: number | null;
  position: string;
  at_bats: number;
  runs: number;
  hits: number;
  rbis: number;
  walks: number;
  strikeouts: number;
  doubles: number;
  triples: number;
  home_runs: number;
}

interface BoxScorePitching {
  player_id: string;
  player_name: string;
  innings_pitched: number;
  hits_allowed: number;
  runs_allowed: number;
  earned_runs: number;
  walks_allowed: number;
  strikeouts: number;
  home_runs_allowed: number;
}

interface BoxScore {
  home_team_batting: BoxScoreBatting[];
  away_team_batting: BoxScoreBatting[];
  home_team_pitching: BoxScorePitching[];
  away_team_pitching: BoxScorePitching[];
}

interface GamePlay {
  id: string;
  inning: number;
  inning_half: string;
  outs: number;
  batter_name: string;
  pitcher_name: string;
  event_type: string;
  description: string;
  home_score: number;
  away_score: number;
}

interface Weather {
  temp: string | number;
  condition: string;
  wind: string;
  is_dome: boolean;
  roof_closed: boolean;
}

interface GameDetailData {
  game: Game | null;
  boxScore: BoxScore | null;
  plays: GamePlay[];
  weather: Weather | null;
  error?: string;
}

const API_BASE = Deno.env.get("API_BASE_URL") || "http://api-gateway:8080/api/v1";

export const handler: Handlers<GameDetailData> = {
  async GET(_req, ctx) {
    const { id } = ctx.params;

    try {
      const game = await fetchGame(id);

      // Fetch box score, plays, and weather in parallel
      const [boxScoreRes, playsRes, weatherRes] = await Promise.allSettled([
        fetch(`${API_BASE}/games/${id}/boxscore`),
        fetch(`${API_BASE}/games/${id}/plays`),
        fetch(`${API_BASE}/games/${id}/weather`),
      ]);

      let boxScore = null;
      let plays: GamePlay[] = [];
      let weather = null;

      if (boxScoreRes.status === "fulfilled" && boxScoreRes.value.ok) {
        boxScore = await boxScoreRes.value.json();
      }

      if (playsRes.status === "fulfilled" && playsRes.value.ok) {
        plays = await playsRes.value.json();
      }

      if (weatherRes.status === "fulfilled" && weatherRes.value.ok) {
        weather = await weatherRes.value.json();
      }

      return ctx.render({
        game,
        boxScore,
        plays,
        weather,
      });
    } catch (error) {
      console.error("Failed to fetch game:", error);
      return ctx.render({
        game: null,
        boxScore: null,
        plays: [],
        weather: null,
        error: "Failed to load game data",
      });
    }
  },
};

export default function GameDetailPage({ data }: PageProps<GameDetailData>) {
  const { game, boxScore, plays, weather, error } = data;

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
                  {game.away_team?.name || "Away Team"}
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
                  {game.home_team?.name || "Home Team"}
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
                    🏆 {game.home_team?.name} Wins
                  </div>
                ) : game.away_score! > game.home_score! ? (
                  <div class="inline-block px-4 py-2 bg-green-100 text-green-800 rounded-lg font-semibold">
                    🏆 {game.away_team?.name} Wins
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

        {/* Simulation */}
        <GameSimulation game={game} />

        {/* Actions */}
        <div class="bg-white rounded-lg shadow">
          <div class="px-6 py-4 border-b border-gray-200">
            <h2 class="text-xl font-semibold text-gray-900">Team Rosters</h2>
          </div>
          <div class="p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <a
                href={`/teams/${game.away_team_id}`}
                class="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                <span>👕</span>
                <span>{game.away_team?.name || "Away Team"} Roster</span>
              </a>
              <a
                href={`/teams/${game.home_team_id}`}
                class="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                <span>👕</span>
                <span>{game.home_team?.name || "Home Team"} Roster</span>
              </a>
            </div>
          </div>
        </div>

        {/* Weather */}
        {weather && (
          <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-xl font-semibold text-gray-900">Weather Conditions</h2>
            </div>
            <div class="p-6">
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div class="text-sm text-gray-500 mb-1">Temperature</div>
                  <div class="text-lg font-semibold">{weather.temp}°</div>
                </div>
                <div>
                  <div class="text-sm text-gray-500 mb-1">Conditions</div>
                  <div class="text-lg font-semibold">{weather.condition}</div>
                </div>
                <div>
                  <div class="text-sm text-gray-500 mb-1">Wind</div>
                  <div class="text-lg font-semibold">{weather.wind}</div>
                </div>
                <div>
                  <div class="text-sm text-gray-500 mb-1">Venue</div>
                  <div class="text-lg font-semibold">
                    {weather.is_dome ? "Dome" : weather.roof_closed ? "Roof Closed" : "Open"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Box Score */}
        {boxScore && boxScore.away_team_batting && boxScore.home_team_batting && (
          <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-xl font-semibold text-gray-900">Box Score</h2>
            </div>
            <div class="p-6">
              {/* Away Team Batting */}
              <div class="mb-6">
                <h3 class="font-semibold text-gray-900 mb-3">{game.away_team?.name || "Away Team"} - Batting</h3>
                <div class="overflow-x-auto">
                  <table class="min-w-full text-sm">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-3 py-2 text-left">Player</th>
                        <th class="px-3 py-2 text-center">POS</th>
                        <th class="px-3 py-2 text-center">AB</th>
                        <th class="px-3 py-2 text-center">R</th>
                        <th class="px-3 py-2 text-center">H</th>
                        <th class="px-3 py-2 text-center">RBI</th>
                        <th class="px-3 py-2 text-center">BB</th>
                        <th class="px-3 py-2 text-center">K</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y">
                      {boxScore.away_team_batting?.map((player) => (
                        <tr key={player.player_id}>
                          <td class="px-3 py-2">
                            <a href={`/players/${player.player_id}`} class="text-blue-600 hover:underline">
                              {player.player_name}
                            </a>
                          </td>
                          <td class="px-3 py-2 text-center">{player.position}</td>
                          <td class="px-3 py-2 text-center">{player.at_bats}</td>
                          <td class="px-3 py-2 text-center">{player.runs}</td>
                          <td class="px-3 py-2 text-center">{player.hits}</td>
                          <td class="px-3 py-2 text-center">{player.rbis}</td>
                          <td class="px-3 py-2 text-center">{player.walks}</td>
                          <td class="px-3 py-2 text-center">{player.strikeouts}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Home Team Batting */}
              <div class="mb-6">
                <h3 class="font-semibold text-gray-900 mb-3">{game.home_team?.name || "Home Team"} - Batting</h3>
                <div class="overflow-x-auto">
                  <table class="min-w-full text-sm">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-3 py-2 text-left">Player</th>
                        <th class="px-3 py-2 text-center">POS</th>
                        <th class="px-3 py-2 text-center">AB</th>
                        <th class="px-3 py-2 text-center">R</th>
                        <th class="px-3 py-2 text-center">H</th>
                        <th class="px-3 py-2 text-center">RBI</th>
                        <th class="px-3 py-2 text-center">BB</th>
                        <th class="px-3 py-2 text-center">K</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y">
                      {boxScore.home_team_batting?.map((player) => (
                        <tr key={player.player_id}>
                          <td class="px-3 py-2">
                            <a href={`/players/${player.player_id}`} class="text-blue-600 hover:underline">
                              {player.player_name}
                            </a>
                          </td>
                          <td class="px-3 py-2 text-center">{player.position}</td>
                          <td class="px-3 py-2 text-center">{player.at_bats}</td>
                          <td class="px-3 py-2 text-center">{player.runs}</td>
                          <td class="px-3 py-2 text-center">{player.hits}</td>
                          <td class="px-3 py-2 text-center">{player.rbis}</td>
                          <td class="px-3 py-2 text-center">{player.walks}</td>
                          <td class="px-3 py-2 text-center">{player.strikeouts}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Away Team Pitching */}
              <div class="mb-6">
                <h3 class="font-semibold text-gray-900 mb-3">{game.away_team?.name || "Away Team"} - Pitching</h3>
                <div class="overflow-x-auto">
                  <table class="min-w-full text-sm">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-3 py-2 text-left">Pitcher</th>
                        <th class="px-3 py-2 text-center">IP</th>
                        <th class="px-3 py-2 text-center">H</th>
                        <th class="px-3 py-2 text-center">R</th>
                        <th class="px-3 py-2 text-center">ER</th>
                        <th class="px-3 py-2 text-center">BB</th>
                        <th class="px-3 py-2 text-center">K</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y">
                      {boxScore.away_team_pitching?.map((player) => (
                        <tr key={player.player_id}>
                          <td class="px-3 py-2">
                            <a href={`/players/${player.player_id}`} class="text-blue-600 hover:underline">
                              {player.player_name}
                            </a>
                          </td>
                          <td class="px-3 py-2 text-center">{player.innings_pitched}</td>
                          <td class="px-3 py-2 text-center">{player.hits_allowed}</td>
                          <td class="px-3 py-2 text-center">{player.runs_allowed}</td>
                          <td class="px-3 py-2 text-center">{player.earned_runs}</td>
                          <td class="px-3 py-2 text-center">{player.walks_allowed}</td>
                          <td class="px-3 py-2 text-center">{player.strikeouts}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Home Team Pitching */}
              <div>
                <h3 class="font-semibold text-gray-900 mb-3">{game.home_team?.name || "Home Team"} - Pitching</h3>
                <div class="overflow-x-auto">
                  <table class="min-w-full text-sm">
                    <thead class="bg-gray-50">
                      <tr>
                        <th class="px-3 py-2 text-left">Pitcher</th>
                        <th class="px-3 py-2 text-center">IP</th>
                        <th class="px-3 py-2 text-center">H</th>
                        <th class="px-3 py-2 text-center">R</th>
                        <th class="px-3 py-2 text-center">ER</th>
                        <th class="px-3 py-2 text-center">BB</th>
                        <th class="px-3 py-2 text-center">K</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y">
                      {boxScore.home_team_pitching?.map((player) => (
                        <tr key={player.player_id}>
                          <td class="px-3 py-2">
                            <a href={`/players/${player.player_id}`} class="text-blue-600 hover:underline">
                              {player.player_name}
                            </a>
                          </td>
                          <td class="px-3 py-2 text-center">{player.innings_pitched}</td>
                          <td class="px-3 py-2 text-center">{player.hits_allowed}</td>
                          <td class="px-3 py-2 text-center">{player.runs_allowed}</td>
                          <td class="px-3 py-2 text-center">{player.earned_runs}</td>
                          <td class="px-3 py-2 text-center">{player.walks_allowed}</td>
                          <td class="px-3 py-2 text-center">{player.strikeouts}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Play-by-Play */}
        {plays && plays.length > 0 && (
          <div class="bg-white rounded-lg shadow">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-xl font-semibold text-gray-900">Play-by-Play</h2>
            </div>
            <div class="p-6">
              <div class="space-y-3 max-h-96 overflow-y-auto">
                {plays.map((play) => (
                  <div key={play.id} class="border-l-4 border-blue-500 pl-4 py-2">
                    <div class="flex justify-between items-start mb-1">
                      <div class="font-semibold text-sm text-gray-900">
                        {play.inning_half === "top" ? "▲" : "▼"} Inning {play.inning} - {play.outs} Out{play.outs !== 1 ? "s" : ""}
                      </div>
                      <div class="text-sm font-medium text-gray-600">
                        {play.away_score} - {play.home_score}
                      </div>
                    </div>
                    <div class="text-sm text-gray-700">{play.description}</div>
                    <div class="text-xs text-gray-500 mt-1">{play.event_type}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
