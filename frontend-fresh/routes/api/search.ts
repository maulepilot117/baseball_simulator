import { Handlers } from "$fresh/server.ts";
import { search } from "../../lib/api.ts";

export const handler: Handlers = {
  async GET(req) {
    const url = new URL(req.url);
    const query = url.searchParams.get("q") || "";

    if (!query || query.length < 2) {
      return new Response(JSON.stringify([]), {
        headers: { "Content-Type": "application/json" },
      });
    }

    try {
      const results = await search(query);
      return new Response(JSON.stringify(results), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      console.error("Search API error:", error);
      return new Response(JSON.stringify({ error: "Search failed" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
