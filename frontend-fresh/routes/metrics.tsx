import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchMetrics, checkHealth, fetchDataFetcherStatus } from "../lib/api.ts";
import type { Metrics } from "../lib/types.ts";

interface MetricsPageData {
  metrics: Metrics | null;
  health: {
    status: string;
    database: string;
    time: string;
  } | null;
  dataFetcherStatus: {
    total_games: number;
    total_players: number;
    total_teams: number;
    last_fetch?: string;
  } | null;
}

export const handler: Handlers<MetricsPageData> = {
  async GET(_req, ctx) {
    try {
      const [metrics, health, dataFetcherStatus] = await Promise.all([
        fetchMetrics().catch(() => null),
        checkHealth().catch(() => null),
        fetchDataFetcherStatus().catch(() => null),
      ]);

      return ctx.render({ metrics, health, dataFetcherStatus });
    } catch (error) {
      console.error("Failed to fetch metrics:", error);
      return ctx.render({
        metrics: null,
        health: null,
        dataFetcherStatus: null,
      });
    }
  },
};

export default function MetricsPage({ data }: PageProps<MetricsPageData>) {
  const { metrics, health, dataFetcherStatus } = data;

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-8">
          <a href="/" class="text-blue-600 hover:underline mb-2 inline-block">
            ← Back to Home
          </a>
          <h1 class="text-4xl font-bold text-gray-900 mb-2">System Metrics</h1>
          <p class="text-gray-600">Real-time performance and health monitoring</p>
        </div>

        {/* Health Status */}
        {health && (
          <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-2xl font-semibold text-gray-900">Health Status</h2>
            </div>
            <div class="p-6">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="flex items-center gap-4">
                  <div
                    class={`text-4xl ${
                      health.status === "healthy" ? "text-green-500" : "text-red-500"
                    }`}
                  >
                    {health.status === "healthy" ? "✅" : "❌"}
                  </div>
                  <div>
                    <div class="text-sm text-gray-500">API Status</div>
                    <div class="text-xl font-bold text-gray-900">
                      {health.status}
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-4">
                  <div
                    class={`text-4xl ${
                      health.database === "connected"
                        ? "text-green-500"
                        : "text-red-500"
                    }`}
                  >
                    {health.database === "connected" ? "🗄️" : "⚠️"}
                  </div>
                  <div>
                    <div class="text-sm text-gray-500">Database</div>
                    <div class="text-xl font-bold text-gray-900">
                      {health.database}
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-4">
                  <div class="text-4xl">⏰</div>
                  <div>
                    <div class="text-sm text-gray-500">Server Time</div>
                    <div class="text-xl font-bold text-gray-900">
                      {new Date(health.time).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Data Fetcher Status */}
        {dataFetcherStatus && (
          <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-2xl font-semibold text-gray-900">Data Fetcher Status</h2>
            </div>
            <div class="p-6">
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="bg-blue-50 rounded-lg p-4">
                  <div class="text-sm text-blue-600 mb-1">Total Teams</div>
                  <div class="text-3xl font-bold text-blue-900">
                    {dataFetcherStatus.total_teams}
                  </div>
                </div>
                <div class="bg-green-50 rounded-lg p-4">
                  <div class="text-sm text-green-600 mb-1">Total Players</div>
                  <div class="text-3xl font-bold text-green-900">
                    {dataFetcherStatus.total_players.toLocaleString()}
                  </div>
                </div>
                <div class="bg-purple-50 rounded-lg p-4">
                  <div class="text-sm text-purple-600 mb-1">Total Games</div>
                  <div class="text-3xl font-bold text-purple-900">
                    {dataFetcherStatus.total_games.toLocaleString()}
                  </div>
                </div>
                <div class="bg-orange-50 rounded-lg p-4">
                  <div class="text-sm text-orange-600 mb-1">Last Fetch</div>
                  <div class="text-sm font-bold text-orange-900">
                    {dataFetcherStatus.last_fetch
                      ? new Date(dataFetcherStatus.last_fetch).toLocaleString()
                      : "Never"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* System Metrics */}
        {metrics && (
          <>
            {/* Application Metrics */}
            <div class="bg-white rounded-lg shadow mb-6">
              <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-2xl font-semibold text-gray-900">
                  Application Metrics
                </h2>
              </div>
              <div class="p-6">
                <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <MetricCard
                    label="Total Requests"
                    value={metrics.application.total_requests.toLocaleString()}
                    icon="📊"
                  />
                  <MetricCard
                    label="Total Errors"
                    value={metrics.application.total_errors.toLocaleString()}
                    icon="⚠️"
                    color="red"
                  />
                  <MetricCard
                    label="Error Rate"
                    value={`${metrics.application.error_rate_percent.toFixed(2)}%`}
                    icon="📉"
                    color={
                      metrics.application.error_rate_percent > 5
                        ? "red"
                        : metrics.application.error_rate_percent > 1
                        ? "yellow"
                        : "green"
                    }
                  />
                  <MetricCard
                    label="Avg Response Time"
                    value={`${metrics.application.avg_response_time_ms.toFixed(0)}ms`}
                    icon="⚡"
                  />
                  <MetricCard
                    label="Requests/Second"
                    value={metrics.application.requests_per_second.toFixed(2)}
                    icon="🚀"
                  />
                </div>
              </div>
            </div>

            {/* Cache Metrics */}
            <div class="bg-white rounded-lg shadow mb-6">
              <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-2xl font-semibold text-gray-900">Cache Performance</h2>
              </div>
              <div class="p-6">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricCard
                    label="Cache Hits"
                    value={metrics.cache.hits.toLocaleString()}
                    icon="✅"
                    color="green"
                  />
                  <MetricCard
                    label="Cache Misses"
                    value={metrics.cache.misses.toLocaleString()}
                    icon="❌"
                    color="red"
                  />
                  <MetricCard
                    label="Hit Rate"
                    value={`${metrics.cache.hit_rate_percent.toFixed(1)}%`}
                    icon="🎯"
                    color={
                      metrics.cache.hit_rate_percent > 80
                        ? "green"
                        : metrics.cache.hit_rate_percent > 50
                        ? "yellow"
                        : "red"
                    }
                  />
                  <MetricCard
                    label="Cache Size"
                    value={metrics.cache.cache_size.toLocaleString()}
                    icon="📦"
                  />
                </div>
              </div>
            </div>

            {/* Database Metrics */}
            <div class="bg-white rounded-lg shadow mb-6">
              <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-2xl font-semibold text-gray-900">
                  Database Connections
                </h2>
              </div>
              <div class="p-6">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricCard
                    label="Max Connections"
                    value={metrics.database.max_connections.toString()}
                    icon="📊"
                  />
                  <MetricCard
                    label="Total Connections"
                    value={metrics.database.total_connections.toString()}
                    icon="🔗"
                  />
                  <MetricCard
                    label="Idle Connections"
                    value={metrics.database.idle_connections.toString()}
                    icon="💤"
                  />
                  <MetricCard
                    label="Acquire Count"
                    value={metrics.database.acquire_count.toLocaleString()}
                    icon="📥"
                  />
                </div>
              </div>
            </div>

            {/* System Metrics */}
            <div class="bg-white rounded-lg shadow mb-6">
              <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-2xl font-semibold text-gray-900">System Resources</h2>
              </div>
              <div class="p-6">
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricCard
                    label="Go Version"
                    value={metrics.system.go_version}
                    icon="🔧"
                  />
                  <MetricCard
                    label="Goroutines"
                    value={metrics.system.num_goroutines.toString()}
                    icon="🧵"
                  />
                  <MetricCard
                    label="CPU Cores"
                    value={metrics.system.num_cpu.toString()}
                    icon="💻"
                  />
                  <MetricCard
                    label="GC Runs"
                    value={metrics.system.num_gc.toString()}
                    icon="🗑️"
                  />
                </div>

                <div class="mt-6">
                  <h3 class="text-lg font-semibold text-gray-900 mb-4">
                    Memory Usage
                  </h3>
                  <div class="grid grid-cols-3 gap-4">
                    <MetricCard
                      label="Allocated"
                      value={`${metrics.system.mem_alloc_mb.toFixed(1)} MB`}
                      icon="📈"
                    />
                    <MetricCard
                      label="Total Allocated"
                      value={`${metrics.system.mem_total_mb.toFixed(1)} MB`}
                      icon="📊"
                    />
                    <MetricCard
                      label="System Memory"
                      value={`${metrics.system.mem_sys_mb.toFixed(1)} MB`}
                      icon="💾"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Uptime */}
            <div class="bg-white rounded-lg shadow">
              <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-2xl font-semibold text-gray-900">Uptime</h2>
              </div>
              <div class="p-6">
                <div class="flex items-center gap-4">
                  <div class="text-5xl">⏱️</div>
                  <div>
                    <div class="text-sm text-gray-500">System Uptime</div>
                    <div class="text-3xl font-bold text-gray-900">
                      {metrics.uptime}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* No Metrics Available */}
        {!metrics && !health && !dataFetcherStatus && (
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <div class="text-red-600 text-4xl mb-4">⚠️</div>
            <h3 class="text-xl font-semibold text-gray-900 mb-2">
              Unable to Load Metrics
            </h3>
            <p class="text-gray-600">
              Could not connect to the backend services. Please check if they are
              running.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Metric Card Component
function MetricCard({
  label,
  value,
  icon,
  color = "blue",
}: {
  label: string;
  value: string;
  icon: string;
  color?: "blue" | "green" | "yellow" | "red" | "purple" | "orange";
}) {
  const bgColors = {
    blue: "bg-blue-50",
    green: "bg-green-50",
    yellow: "bg-yellow-50",
    red: "bg-red-50",
    purple: "bg-purple-50",
    orange: "bg-orange-50",
  };

  const textColors = {
    blue: "text-blue-600",
    green: "text-green-600",
    yellow: "text-yellow-600",
    red: "text-red-600",
    purple: "text-purple-600",
    orange: "text-orange-600",
  };

  const valueColors = {
    blue: "text-blue-900",
    green: "text-green-900",
    yellow: "text-yellow-900",
    red: "text-red-900",
    purple: "text-purple-900",
    orange: "text-orange-900",
  };

  return (
    <div class={`${bgColors[color]} rounded-lg p-4`}>
      <div class="flex items-center gap-2 mb-2">
        <span class="text-xl">{icon}</span>
        <div class={`text-sm ${textColors[color]} font-medium`}>{label}</div>
      </div>
      <div class={`text-2xl font-bold ${valueColors[color]}`}>{value}</div>
    </div>
  );
}
