import { Handlers } from "$fresh/server.ts";

const SIM_ENGINE_BASE = Deno.env.get("SIM_ENGINE_URL") || "http://localhost:8081";

export const handler: Handlers = {
  async GET(_req, ctx) {
    const { runId } = ctx.params;

    try {
      const response = await fetch(`${SIM_ENGINE_BASE}/simulation/${runId}/status`);
      const data = await response.json();

      return new Response(JSON.stringify(data), {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      });
    } catch (error) {
      console.error("Simulation status proxy error:", error);
      return new Response(
        JSON.stringify({
          error: "Failed to fetch simulation status",
          message: error instanceof Error ? error.message : "Unknown error"
        }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }
      );
    }
  },
};
