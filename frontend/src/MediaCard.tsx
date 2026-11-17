import React, { type ReactNode } from "react"
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import MovieOutlinedIcon from '@mui/icons-material/MovieOutlined'
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined'
import PersonOutlineRoundedIcon from '@mui/icons-material/PersonOutlineRounded'
import type { Movie } from "./types/Movie"
import type { Collection } from "./types/Collection"
import type { MoviePerson } from "./types/Person"
import { formatDuration, formatYear, pluralize, posterUrl } from "./format"
import './MediaCard.css'

/** Artwork first (design/DESIGN.md): only the image is visible, the label appears on hover/focus. */
const Card = (props: {
    title: string
    meta: (string | null)[]
    image: string | null
    placeholderIcon: ReactNode
    onOpen: () => void
    onPlay?: () => void
}) => {
    const meta = props.meta.filter(Boolean).join(" · ")
    return (
        <div
            className="card"
            role="button"
            tabIndex={0}
            aria-label={meta ? `${props.title}, ${meta}` : props.title}
            onClick={props.onOpen}
            onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); props.onOpen() } }}
        >
            <div className="cardMedia">
                {
                    props.image
                    ? <img src={props.image} alt="" loading="lazy" decoding="async" />
                    : <div className="artPlaceholder">{props.placeholderIcon}</div>
                }
                {
                    props.onPlay &&
                    <button
                        className="cardPlay"
                        title="Play"
                        aria-label={`Play ${props.title}`}
                        onClick={event => { event.stopPropagation(); props.onPlay!() }}
                        onKeyDown={event => event.stopPropagation()}
                    >
                        <PlayArrowRoundedIcon />
                    </button>
                }
            </div>
            <div className="cardLabel" aria-hidden="true">
                <span className="cardTitle">{props.title}</span>
                { meta && <span className="cardMeta">{meta}</span> }
            </div>
        </div>
    )
}

export const MovieCard = (props: { movie: Movie, onOpen: (movie: Movie) => void, onPlay: (movie: Movie) => void, meta?: (string | null)[] }) => {
    const { movie } = props
    return (
        <Card
            title={movie.title}
            meta={props.meta ?? [formatYear(movie.release_date), formatDuration(movie.length_in_seconds)]}
            image={posterUrl(movie.poster_file_name)}
            placeholderIcon={<MovieOutlinedIcon />}
            onOpen={() => props.onOpen(movie)}
            onPlay={() => props.onPlay(movie)}
        />
    )
}

export const CollectionCard = (props: { collection: Collection, onOpen: (collection: Collection) => void }) => {
    const { collection } = props
    return (
        <Card
            title={collection.title}
            meta={[collection.movie_count !== undefined ? pluralize(collection.movie_count, "title") : null]}
            image={posterUrl(collection.poster_file_name)}
            placeholderIcon={<FolderOutlinedIcon />}
            onOpen={() => props.onOpen(collection)}
        />
    )
}

/** Cast card: circular photo, name and character are always visible (the role is the information). */
export const PersonCard = (props: { person: MoviePerson, onOpen: (person: MoviePerson) => void }) => {
    const { person } = props
    const image = posterUrl(person.poster_file_name)
    const role = person.character ?? (person.role === "DIRECTOR" ? "Director" : null)
    return (
        <button className="personCard" onClick={() => props.onOpen(person)} title={role ? `${person.name} as ${role}` : person.name}>
            <span className="personPhoto">
                { image ? <img src={image} alt="" loading="lazy" decoding="async" /> : <span className="artPlaceholder"><PersonOutlineRoundedIcon /></span> }
            </span>
            <span className="personName">{person.name}</span>
            { role && <span className="personRole">{role}</span> }
        </button>
    )
}
