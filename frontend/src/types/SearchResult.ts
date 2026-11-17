/** A hit of a scraper's search (GET /api/movie/{id}/search). `id` is only meaningful to the scraper. */
export type SearchResult = {
    id: string
    name: string
    original_name: string | null
    release_date: number | null
    poster_url: string | null
    overview: string | null
}
