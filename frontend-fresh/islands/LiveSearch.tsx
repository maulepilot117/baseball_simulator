import { useState, useEffect } from "preact/hooks";

interface SearchResult {
  type: "team" | "player" | "game" | "umpire";
  id: string;
  name: string;
  description?: string;
}

export default function LiveSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setShowResults(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        if (response.ok) {
          const data = await response.json();
          setResults(data.slice(0, 5)); // Limit to 5 results
          setShowResults(true);
        }
      } catch (error) {
        console.error("Search failed:", error);
      } finally {
        setLoading(false);
      }
    }, 300); // Debounce 300ms

    return () => clearTimeout(timer);
  }, [query]);

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
    <div class="relative">
      <div class="relative">
        <input
          type="text"
          value={query}
          onInput={(e) => setQuery(e.currentTarget.value)}
          onFocus={() => query.length >= 2 && setShowResults(true)}
          onBlur={() => setTimeout(() => setShowResults(false), 200)}
          placeholder="Search teams, players, games, umpires..."
          class="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {loading && (
          <div class="absolute right-3 top-3.5">
            <div class="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
          </div>
        )}
      </div>

      {/* Results Dropdown */}
      {showResults && results.length > 0 && (
        <div class="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg">
          {results.map((result) => (
            <a
              key={`${result.type}-${result.id}`}
              href={getLink(result)}
              class="block px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
            >
              <div class="flex items-center gap-3">
                <span class="text-2xl">{getIcon(result.type)}</span>
                <div class="flex-1 min-w-0">
                  <div class="font-medium text-gray-900 truncate">
                    {result.name}
                  </div>
                  {result.description && (
                    <div class="text-sm text-gray-500 truncate">
                      {result.description}
                    </div>
                  )}
                </div>
                <span class="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-700 uppercase">
                  {result.type}
                </span>
              </div>
            </a>
          ))}
          <a
            href={`/search?q=${encodeURIComponent(query)}`}
            class="block px-4 py-2 text-center text-sm text-blue-600 hover:bg-blue-50 font-medium"
          >
            View all results →
          </a>
        </div>
      )}

      {/* No Results */}
      {showResults && query.length >= 2 && results.length === 0 && !loading && (
        <div class="absolute z-10 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg p-4 text-center text-gray-500">
          No results found for "{query}"
        </div>
      )}
    </div>
  );
}
