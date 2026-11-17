import React, { useEffect, useState } from "react"
import axios from "axios"
import PersonOutlineRoundedIcon from '@mui/icons-material/PersonOutlineRounded'
import type { Movie } from "./types/Movie"
import type { Person } from "./types/Person"
import { MovieCard } from "./MediaCard"
import { DetailHeader, DetailPage } from "./DetailPage"
import { pluralize, posterUrl } from "./format"

/** tvOS PersonMoviesGridView: the person's photo and name, then all their titles. */
export const PersonDetail = (props: {
    personId: number
    landscape: boolean
    onBack: () => void
    onOpenMovie: (movie: Movie) => void
    onPlay: (movie: Movie) => void
}) => {
    const [ person, setPerson ] = useState<Person | null>(null)
    const [ movies, setMovies ] = useState<Movie[]>([])
    const [ error, setError ] = useState<string | null>(null)

    useEffect(() => {
        let current = true
        setPerson(null)
        setError(null)
        Promise.all([
            axios.get<Person>(`/api/person/${props.personId}`),
            axios.get<Movie[]>(`/api/movies/person/${props.personId}`),
        ])
        .then(([ personResponse, moviesResponse ]) => {
            if (!current) return
            setPerson(personResponse.data)
            setMovies(moviesResponse.data)
        })
        .catch(() => { if (current) setError("This person doesn't exist anymore.") })
        return () => { current = false }
    }, [props.personId])

    if (error) return <DetailPage onBack={props.onBack}><p className="contentHint">{error}</p></DetailPage>
    if (!person) return <DetailPage onBack={props.onBack}><p className="contentHint">Loading…</p></DetailPage>

    return (
        <DetailPage onBack={props.onBack} tintImage={posterUrl(person.poster_file_name)}>
            <DetailHeader
                image={posterUrl(person.poster_file_name)}
                placeholderIcon={<PersonOutlineRoundedIcon />}
                eyebrow={person.role === "DIRECTOR" ? "Director" : "Actor"}
                title={person.name}
                meta={[pluralize(movies.length, "title")]}
            />
            <section className="detailSection">
                <div className={`mediaGrid${props.landscape ? " landscape" : ""}`}>
                    { movies.map(movie => <MovieCard key={movie.id} movie={movie} onOpen={props.onOpenMovie} onPlay={props.onPlay} />) }
                </div>
            </section>
        </DetailPage>
    )
}
