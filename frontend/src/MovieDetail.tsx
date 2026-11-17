import React, { useCallback, useContext, useEffect, useRef, useState } from "react"
import axios from "axios"
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import ManageSearchRoundedIcon from '@mui/icons-material/ManageSearchRounded'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import MovieOutlinedIcon from '@mui/icons-material/MovieOutlined'
import { WebSocketContext } from "./App"
import { NotificationType } from "./types/NotificationType"
import type { Movie } from "./types/Movie"
import type { Collection } from "./types/Collection"
import type { MoviePerson } from "./types/Person"
import { CollectionCard, MovieCard, PersonCard } from "./MediaCard"
import { DetailHeader, DetailPage } from "./DetailPage"
import { formatDate, formatDuration, formatResolution, formatYear, posterUrl } from "./format"

const EXTRA_LABELS: Record<string, string> = {
    TRAILER: "Trailer",
    BEHIND_THE_SCENES: "Behind the scenes",
    MAKING_OFF: "Making of",
}

const REFRESH_DEBOUNCE_MS = 800

type Details = { movie: Movie, people: MoviePerson[], extras: Movie[], collections: Collection[] }

export const MovieDetail = (props: {
    movieId: number
    landscape: boolean
    onBack: () => void
    onPlay: (movie: Movie) => void
    onOpenPerson: (person: MoviePerson) => void
    onOpenCollection: (collection: Collection) => void
    onFindMatch: (movie: Movie) => void
    onRefresh: (movie: Movie) => void
}) => {
    const [ details, setDetails ] = useState<Details | null>(null)
    const [ error, setError ] = useState<string | null>(null)
    const websocketMessage = useContext(WebSocketContext)

    const requestCounter = useRef(0)
    const load = useCallback(() => {
        const requestId = ++requestCounter.current
        const id = props.movieId
        Promise.all([
            axios.get<Movie>(`/api/movie/${id}`),
            axios.get<MoviePerson[]>(`/api/movie/${id}/people`),
            axios.get<Movie[]>(`/api/movie/${id}/extras`),
            axios.get<Collection[]>(`/api/movie/${id}/collections`),
        ])
        .then(([ movie, people, extras, collections ]) => {
            if (requestId !== requestCounter.current) return
            setDetails({ movie: movie.data, people: people.data, extras: extras.data, collections: collections.data })
            setError(null)
        })
        .catch(() => { if (requestId === requestCounter.current) setError("This title doesn't exist anymore.") })
    }, [props.movieId])

    useEffect(() => {
        setDetails(null)
        load()
    }, [load])

    // Refresh / find match run as scan jobs: reload when they report back
    const timer = useRef<number | null>(null)
    useEffect(() => {
        if (websocketMessage.message !== NotificationType.MOVIES_UPDATED && websocketMessage.message !== NotificationType.COLLECTIONS_UPDATED) return
        if (timer.current) window.clearTimeout(timer.current)
        timer.current = window.setTimeout(load, REFRESH_DEBOUNCE_MS)
        return () => { if (timer.current) window.clearTimeout(timer.current) }
    }, [websocketMessage, load])

    if (error) return <DetailPage onBack={props.onBack}><p className="contentHint">{error}</p></DetailPage>
    if (!details) return <DetailPage onBack={props.onBack}><p className="contentHint">Loading…</p></DetailPage>

    const { movie, people, extras, collections } = details
    const resolution = formatResolution(movie.width, movie.height)
    const episodeLabel = movie.season !== null || movie.episode !== null
        ? [movie.season !== null ? `Season ${movie.season}` : null, movie.episode !== null ? `Episode ${movie.episode}` : null].filter(Boolean).join(" · ")
        : null

    const facts: [string, string | null][] = [
        ["Released", formatDate(movie.release_date)],
        ["Duration", formatDuration(movie.length_in_seconds)],
        ["Resolution", movie.width && movie.height ? `${movie.width} × ${movie.height}${resolution ? ` (${resolution})` : ""}` : null],
        ["Video codec", movie.codec],
        ["Container", movie.format],
        ["Added", formatDate(movie.added_date)],
        ["Metadata updated", movie.metadata_last_updated ? formatDate(movie.metadata_last_updated) : "Never"],
    ]

    return (
        <DetailPage onBack={props.onBack} tintImage={posterUrl(movie.poster_file_name, "thumb")}>
            <DetailHeader
                image={posterUrl(movie.poster_file_name)}
                landscape={props.landscape}
                placeholderIcon={<MovieOutlinedIcon />}
                eyebrow={episodeLabel}
                title={movie.title}
                meta={[formatYear(movie.release_date), formatDuration(movie.length_in_seconds), resolution]}
                actions={<>
                    <button className="btn btn-primary btnLarge" onClick={() => props.onPlay(movie)}><PlayArrowRoundedIcon /> Play</button>
                    <button className="btn btnLarge" onClick={() => props.onFindMatch(movie)} title="Search the scraper and pick the right title"><ManageSearchRoundedIcon /> Find match</button>
                    <button className="iconButton btnLarge" onClick={() => props.onRefresh(movie)} title="Refresh metadata" aria-label="Refresh metadata"><RefreshRoundedIcon /></button>
                </>}
            />

            {
                people.length > 0 &&
                <section className="detailSection">
                    <h2>Cast &amp; crew</h2>
                    <div className="shelf">
                        { people.map(person => <PersonCard key={person.id} person={person} onOpen={props.onOpenPerson} />) }
                    </div>
                </section>
            }

            {
                extras.length > 0 &&
                <section className="detailSection">
                    <h2>Extras</h2>
                    <div className="shelf artShelf landscape">
                        {
                            extras.map(extra => (
                                <MovieCard
                                    key={extra.id}
                                    movie={{ ...extra, title: extra.extra_type ? EXTRA_LABELS[extra.extra_type] ?? extra.title : extra.title }}
                                    meta={[formatDuration(extra.length_in_seconds)]}
                                    onOpen={props.onPlay}
                                    onPlay={props.onPlay}
                                />
                            ))
                        }
                    </div>
                </section>
            }

            {
                collections.length > 0 &&
                <section className="detailSection">
                    <h2>Collections</h2>
                    <div className="shelf artShelf">
                        { collections.map(collection => <CollectionCard key={collection.id} collection={collection} onOpen={props.onOpenCollection} />) }
                    </div>
                </section>
            }

            <section className="detailSection">
                <h2>Details</h2>
                <dl className="facts">
                    {
                        facts.filter(([, value]) => value).map(([label, value]) => (
                            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
                        ))
                    }
                    <div className="factWide"><dt>File</dt><dd><code>{movie.file_location}</code></dd></div>
                </dl>
            </section>
        </DetailPage>
    )
}
