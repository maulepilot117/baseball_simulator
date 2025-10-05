import { Handlers, PageProps } from "$fresh/server.ts";
import { search } from "../lib/api.ts";
import type { SearchResult } from "../lib/types.ts";

interface SearchPageData {
  query: string;
  results: SearchResult[];
}

export const handler: Handlers<SearchPageData> = {
  async GET(req, ctx) {
    const url = new URL(req.url);
    const query = url.searchParams.get("q") || "";

    if (!query) {
      return ctx.render({ query: "", results: [] });
    }

    try {
      const results = await search(query);
      return ctx.render({ query, results });
    } catch (error) {
      console.error("Search failed:", error);
      return ctx.render({ query, results: [] });
    }
  },
};

export default function SearchPage({ data }: PageProps<SearchPageData>) {
  const { query, results } = data;

  const getIcon = (type: string) => {
    switch (type) {
      case "team":
        return "⚾";
      case "player":
        return "👤";
      case "game":
        return "🎮";
      case "umpire":
        return "👨‍⚖️";
      default:
        return "📄";
    }
  };

  const getLink = (result: SearchResult) => {
    switch (result.type) {
      case "team":
        return `/teams/${result.id}`;
      case "player":
        return `/players/${result.id}`;
      case "game":
        return `/games/${result.id}`;
      case "umpire":
        return `/umpires/${result.id}`;
      default:
        return "#";
    }
  };

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-8">
          <a href="/" class="text-blue-600 hover:underline mb-2 inline-block">
            ← Back to Home
          </a>
          <h1 class="text-4xl font-bold text-gray-900 mb-4">Search</h1>

          {/* Search Form */}
          <form method="GET" class="w-full">
            <div class="relative">
              <input
                type="text"
                name="q"
                value={query}
                placeholder="Search teams, players, games, umpires..."
                class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                autofocus
              />
              <button
                type="submit"
                class="absolute right-2 top-2 px-4 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Search
              </button>
            </div>
          </form>
        </div>

        {/* Results */}
        {query && (
          <div class="bg-white rounded-lg shadow">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 class="text-xl font-semibold text-gray-900">
                {results.length === 0
                  ? "No results found"
                  : `${results.length} result${results.length === 1 ? "" : "s"} for "${query}"`}
              </h2>
            </div>

            {results.length === 0 ? (
              <div class="px-6 py-8 text-center text-gray-500">
                <p>Try a different search term or browse by category:</p>
                <div class="mt-6 flex justify-center gap-4">
                  <a
                    href="/teams"
                    class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    Browse Teams
                  </a>
                  <a
                    href="/players"
                    class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                  >
                    Browse Players
                  </a>
                  <a
                    href="/games"
                    class="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700"
                  >
                    Browse Games
                  </a>
                </div>
              </div>
            ) : (
              <div class="divide-y divide-gray-200">
                {results.map((result) => (
                  <a
                    key={`${result.type}-${result.id}`}
                    href={getLink(result)}
                    class="block px-6 py-4 hover:bg-gray-50 transition"
                  >
                    <div class="flex items-center">
                      <div class="text-3xl mr-4">{getIcon(result.type)}</div>
                      <div class="flex-1">
                        <div class="flex items-center gap-2">
                          <h3 class="text-lg font-medium text-gray-900">
                            {result.name}
                          </h3>
                          <span class="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-700 uppercase">
                            {result.type}
                          </span>
                        </div>
                        {result.description && (
                          <p class="text-sm text-gray-500 mt-1">
                            {result.description}
                          </p>
                        )}
                      </div>
                      <div class="text-blue-600">→</div>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        )}

        {!query && (
          <div class="bg-white rounded-lg shadow p-8 text-center">
            <p class="text-gray-500 mb-6">
              Enter a search term to find teams, players, games, or umpires.
            </p>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <a
                href="/teams"
                class="p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition"
              >
                <div class="text-3xl mb-2">⚾</div>
                <div class="text-sm font-medium text-gray-900">Teams</div>
              </a>
              <a
                href="/players"
                class="p-4 border border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition"
              >
                <div class="text-3xl mb-2">👤</div>
                <div class="text-sm font-medium text-gray-900">Players</div>
              </a>
              <a
                href="/games"
                class="p-4 border border-gray-200 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition"
              >
                <div class="text-3xl mb-2">🎮</div>
                <div class="text-sm font-medium text-gray-900">Games</div>
              </a>
              <a
                href="/umpires"
                class="p-4 border border-gray-200 rounded-lg hover:border-yellow-500 hover:bg-yellow-50 transition"
              >
                <div class="text-3xl mb-2">👨‍⚖️</div>
                <div class="text-sm font-medium text-gray-900">Umpires</div>
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
