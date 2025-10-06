import { Handlers } from "$fresh/server.ts";

const SIM_ENGINE_BASE = Deno.env.get("SIM_ENGINE_URL") || "http://localhost:8081";

export const handler: Handlers = {
  async POST(req) {
    try {
      const body = await req.json();

      const response = await fetch(`${SIM_ENGINE_BASE}/simulate/daily`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      return new Response(JSON.stringify(data), {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      });
    } catch (error) {
      console.error("Daily simulation proxy error:", error);
      return new Response(
        JSON.stringify({
          error: "Failed to start simulations",
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
