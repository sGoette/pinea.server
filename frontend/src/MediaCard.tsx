import React, { type ReactNode } from "react"
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import MovieOutlinedIcon from '@mui/icons-material/MovieOutlined'
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined'
import PersonOutlineRoundedIcon from '@mui/icons-material/PersonOutlineRounded'
import type { Movie } from "./types/Movie"
import type { Collection } from "./types/Collection"
import type { LibraryPerson, MoviePerson, Person } from "./types/Person"
import type { Serie } from "./types/Serie"
import TvOutlinedIcon from '@mui/icons-material/TvOutlined'
import { formatDate, formatDuration, formatYear, pluralize, posterUrl } from "./format"
import './MediaCard.css'

/** Artwork first (design/DESIGN.md): only the image is visible, the label appears on hover/focus. */
const Card = (props: {
    title: string
    meta: (string | null)[]
    image: string | null
    placeholderIcon: ReactNode
    placeholderTitle?: boolean     // write the title on the placeholder (when there is no image)
    className?: string
    onOpen: () => void
    onPlay?: () => void
    onImageRatio?: ((ratio: number) => void) | undefined   // the image's width / height once loaded (justified grid)
}) => {
    const meta = props.meta.filter(Boolean).join(" · ")
    return (
        <div
            className={props.className ? `card ${props.className}` : "card"}
            role="button"
            tabIndex={0}
            aria-label={meta ? `${props.title}, ${meta}` : props.title}
            onClick={props.onOpen}
            onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); props.onOpen() } }}
        >
            <div className="cardMedia">
                {
                    props.image
                    ? <img
                        src={props.image}
                        alt=""
                        loading="lazy"
                        decoding="async"
                        onLoad={props.onImageRatio && (event => props.onImageRatio!(event.currentTarget.naturalWidth / event.currentTarget.naturalHeight))}
                      />
                    : <div className={props.placeholderTitle ? "artPlaceholder withTitle" : "artPlaceholder"}>
                        {props.placeholderIcon}
                        { props.placeholderTitle && <span className="placeholderTitle">{props.title}</span> }
                      </div>
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

export const MovieCard = (props: { movie: Movie, onOpen: (movie: Movie) => void, onPlay: (movie: Movie) => void, meta?: (string | null)[], onImageRatio?: ((ratio: number) => void) | undefined }) => {
    const { movie } = props
    return (
        <Card
            title={movie.title}
            meta={props.meta ?? [formatYear(movie.release_date), formatDuration(movie.length_in_seconds)]}
            image={posterUrl(movie.poster_file_name, "thumb")}
            placeholderIcon={<MovieOutlinedIcon />}
            onOpen={() => props.onOpen(movie)}
            onPlay={() => props.onPlay(movie)}
            onImageRatio={props.onImageRatio}
        />
    )
}

/** Collections are always portrait (like movie posters), also in VIDEOS libraries and on shelves. */
export const CollectionCard = (props: { collection: Collection, onOpen: (collection: Collection) => void }) => {
    const { collection } = props
    return (
        <Card
            title={collection.title}
            meta={[collection.movie_count !== undefined ? pluralize(collection.movie_count, "title") : null]}
            image={posterUrl(collection.poster_file_name, "thumb")}
            placeholderIcon={<FolderOutlinedIcon />}
            placeholderTitle
            className="collectionCard"
            onOpen={() => props.onOpen(collection)}
        />
    )
}

export const SerieCard = (props: { serie: Serie, onOpen: (serie: Serie) => void }) => {
    const { serie } = props
    return (
        <Card
            title={serie.title}
            meta={[serie.seasons_count > 0 ? pluralize(serie.seasons_count, "season") : null]}
            image={posterUrl(serie.poster_file_name, "thumb")}
            placeholderIcon={<TvOutlinedIcon />}
            onOpen={() => props.onOpen(serie)}
        />
    )
}

/** Episode in a season row: always 16:9 (the still, else the poster cropped), "Episode 3: Title" like tvOS. */
export const EpisodeCard = (props: { episode: Movie, onOpen: (episode: Movie) => void, onPlay: (episode: Movie) => void }) => {
    const { episode } = props
    return (
        <Card
            title={episode.episode !== null ? `Episode ${episode.episode}: ${episode.title}` : episode.title}
            meta={[formatDate(episode.release_date), formatDuration(episode.length_in_seconds)]}
            image={posterUrl(episode.still_file_name ?? episode.poster_file_name, "thumb")}
            placeholderIcon={<MovieOutlinedIcon />}
            onOpen={() => props.onOpen(episode)}
            onPlay={() => props.onPlay(episode)}
        />
    )
}

/** Cast card: circular photo, name and character are always visible (the role is the information). */
/** Cast card: name + character (or "Director"). */
export const PersonCard = (props: { person: MoviePerson, onOpen: (person: MoviePerson) => void }) => {
    const { person } = props
    const role = person.character ?? (person.role === "DIRECTOR" ? "Director" : null)
    return <PersonCardBase person={person} detail={role} title={role ? `${person.name} as ${role}` : person.name} onOpen={() => props.onOpen(person)} />
}

/** People view of a library: name + number of titles. */
export const LibraryPersonCard = (props: { person: LibraryPerson, onOpen: (person: LibraryPerson) => void }) => {
    const { person } = props
    const count = pluralize(person.movie_count, "title", "titles")
    return <PersonCardBase person={person} detail={count} title={`${person.name} · ${count}`} onOpen={() => props.onOpen(person)} />
}

const PersonCardBase = (props: { person: Person, detail: string | null, title: string, onOpen: () => void }) => {
    const { person } = props
    const image = posterUrl(person.poster_file_name, "thumb")
    return (
        <button className="personCard" onClick={props.onOpen} title={props.title}>
            <span className="personPhoto">
                { image ? <img src={image} alt="" loading="lazy" decoding="async" /> : <span className="artPlaceholder"><PersonOutlineRoundedIcon /></span> }
            </span>
            <span className="personName">{person.name}</span>
            { props.detail && <span className="personRole">{props.detail}</span> }
        </button>
    )
}
