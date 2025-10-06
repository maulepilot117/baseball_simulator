import { Handlers } from "$fresh/server.ts";
import { fetchGamesByDate } from "../../../../lib/api.ts";

export const handler: Handlers = {
  async GET(_req, ctx) {
    const { date } = ctx.params;

    try {
      const gamesResponse = await fetchGamesByDate(date);
      // Return the games array with data field for consistency with island expectations
      return new Response(JSON.stringify({
        data: gamesResponse.games || [],
        count: gamesResponse.count,
        date: gamesResponse.date
      }), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      console.error("API route error:", error);
      return new Response(
        JSON.stringify({ error: "Failed to fetch games", data: [] }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }
      );
    }
  },
};
