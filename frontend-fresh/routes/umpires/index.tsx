import { Handlers, PageProps } from "$fresh/server.ts";
import { fetchUmpires } from "../../lib/api.ts";
import type { Umpire, PaginatedResponse } from "../../lib/types.ts";

interface UmpiresPageData {
  umpires: PaginatedResponse<Umpire>;
  page: number;
}

export const handler: Handlers<UmpiresPageData> = {
  async GET(req, ctx) {
    const url = new URL(req.url);
    const page = parseInt(url.searchParams.get("page") || "1");
    const pageSize = 20;

    try {
      const umpires = await fetchUmpires(page, pageSize);
      return ctx.render({ umpires, page });
    } catch (error) {
      console.error("Failed to fetch umpires:", error);
      return ctx.render({
        umpires: {
          data: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 0,
        },
        page: 1,
      });
    }
  },
};

export default function UmpiresPage({ data }: PageProps<UmpiresPageData>) {
  const { umpires, page } = data;
  const { data: umpireList, total, total_pages } = umpires;

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div class="mb-8">
          <a href="/" class="text-blue-600 hover:underline mb-2 inline-block">
            ← Back to Home
          </a>
          <h1 class="text-4xl font-bold text-gray-900 mb-2">Umpires</h1>
          <p class="text-gray-600">{total} umpires in the database</p>
        </div>

        {/* Umpires List */}
        <div class="bg-white rounded-lg shadow overflow-hidden">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {umpireList.length === 0 ? (
                <tr>
                  <td colspan="2" class="px-6 py-8 text-center text-gray-500">
                    No umpires found
                  </td>
                </tr>
              ) : (
                umpireList.map((umpire) => (
                  <tr key={umpire.id} class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="flex items-center">
                        <div class="text-4xl mr-3">👨‍⚖️</div>
                        <div>
                          <a
                            href={`/umpires/${umpire.id}`}
                            class="text-blue-600 hover:underline font-medium text-lg"
                          >
                            {umpire.name}
                          </a>
                        </div>
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">
                      <a
                        href={`/umpires/${umpire.id}`}
                        class="text-blue-600 hover:underline text-sm"
                      >
                        View Stats →
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {total_pages > 1 && (
          <div class="mt-6 flex justify-center items-center gap-4">
            {page > 1 && (
              <a
                href={`?page=${page - 1}`}
                class="px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                ← Previous
              </a>
            )}
            <span class="text-gray-600">
              Page {page} of {total_pages}
            </span>
            {page < total_pages && (
              <a
                href={`?page=${page + 1}`}
                class="px-4 py-2 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Next →
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
