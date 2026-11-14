import React, { type ReactNode } from "react"
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import MovieOutlinedIcon from '@mui/icons-material/MovieOutlined'
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import type { Movie } from "./types/Movie"
import type { Collection } from "./types/Collection"
import { formatDuration, formatYear, pluralize, posterUrl } from "./format"
import './MediaCard.css'

const Card = (props: {
    title: string
    meta: (string | null)[]
    image: string | null
    placeholderIcon: ReactNode
    hoverIcon?: ReactNode
    action?: ReactNode
    onOpen: () => void
}) => {
    const meta = props.meta.filter(Boolean).join(" · ")
    return (
        <div
            className="card"
            role="button"
            tabIndex={0}
            onClick={props.onOpen}
            onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); props.onOpen() } }}
            title={props.title}
        >
            <div className="cardMedia">
                {
                    props.image
                    ? <img src={props.image} alt="" loading="lazy" decoding="async" />
                    : <div className="cardPlaceholder">{props.placeholderIcon}</div>
                }
                { props.hoverIcon && <div className="cardHover">{props.hoverIcon}</div> }
                { props.action }
            </div>
            <div className="cardText">
                <p className="cardTitle">{props.title}</p>
                { meta && <p className="cardMeta">{meta}</p> }
            </div>
        </div>
    )
}

export const MovieCard = (props: { movie: Movie, onPlay: (movie: Movie) => void, onRefresh: (movie: Movie) => void }) => {
    const { movie } = props
    return (
        <Card
            title={movie.title}
            meta={[formatYear(movie.release_date), formatDuration(movie.length_in_seconds)]}
            image={posterUrl(movie.poster_file_name)}
            placeholderIcon={<MovieOutlinedIcon />}
            hoverIcon={<span className="playBadge"><PlayArrowRoundedIcon /></span>}
            onOpen={() => props.onPlay(movie)}
            action={
                <button
                    className="cardAction"
                    title="Refresh metadata"
                    aria-label={`Refresh metadata of ${movie.title}`}
                    onClick={event => { event.stopPropagation(); props.onRefresh(movie) }}
                    onKeyDown={event => event.stopPropagation()}
                >
                    <RefreshRoundedIcon />
                </button>
            }
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
