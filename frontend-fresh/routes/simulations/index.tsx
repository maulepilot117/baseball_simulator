import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchGamesByDate } from "../../lib/api.ts";
import type { Game } from "../../lib/types.ts";
import SimulationDashboard from "../../islands/SimulationDashboard.tsx";

interface SimulationsData {
  date: string;
  games: Game[];
}

export const handler: Handlers<SimulationsData> = {
  async GET(_req, ctx) {
    // Get today's date or date from query param
    const url = new URL(_req.url);
    const dateParam = url.searchParams.get("date");
    let date = dateParam || new Date().toISOString().split("T")[0];

    try {
      let gamesResponse = await fetchGamesByDate(date);

      // If no games for the requested date and no explicit date param was provided,
      // try to find the most recent date with games (up to 30 days back)
      if ((!gamesResponse.games || gamesResponse.games.length === 0) && !dateParam) {
        for (let daysBack = 1; daysBack <= 30; daysBack++) {
          const testDate = new Date();
          testDate.setDate(testDate.getDate() - daysBack);
          const testDateStr = testDate.toISOString().split("T")[0];

          const testResponse = await fetchGamesByDate(testDateStr);
          if (testResponse.games && testResponse.games.length > 0) {
            date = testDateStr;
            gamesResponse = testResponse;
            break;
          }
        }
      }

      return ctx.render({
        date,
        games: gamesResponse.games || [],
      });
    } catch (error) {
      console.error("Failed to fetch games:", error);
      return ctx.render({
        date,
        games: [],
      });
    }
  },
};

export default function Simulations({ data }: PageProps<SimulationsData>) {
  const { date, games } = data;

  return (
    <div class="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-8">
          <div class="flex items-center justify-between">
            <div>
              <h1 class="text-4xl font-bold text-gray-900 mb-2">
                Game Simulations
              </h1>
              <p class="text-gray-600">
                Monte Carlo simulations using real stats, weather, umpires, and park factors
              </p>
            </div>
            <a
              href="/"
              class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
            >
              ← Back to Home
            </a>
          </div>
        </div>

        {/* Simulation Dashboard Island */}
        <SimulationDashboard initialDate={date} initialGames={games} />
      </div>
    </div>
  );
}
