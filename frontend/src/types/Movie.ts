export type Movie = {
    id: number
    title: string
    file_location: string
    length_in_seconds: number | null
    width: number | null
    height: number | null
    codec: string | null
    format: string | null
    poster_file_name: string | null
    library_id: number
    metadata_last_updated: number | null
    release_date: number | null
    added_date: number
    is_extra_of_movie_id: number | null
    extra_type: string | null
    is_episode_of_serie_id: number | null
    episode: number | null
    season: string | null
    still_file_name: string | null
}
