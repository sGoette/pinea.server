export type Role = "ACTOR" | "DIRECTOR"

export type Person = {
    id: number
    name: string
    poster_file_name: string | null
    role: Role
}

/** A person as part of one movie (GET /api/movie/{id}/people), already sorted by the server. */
export type MoviePerson = Person & {
    character: string | null
    sort_order: number | null
}

/** A person of a library (GET /api/people/{library_id}), sorted by name. */
export type LibraryPerson = Person & {
    movie_count: number
}
