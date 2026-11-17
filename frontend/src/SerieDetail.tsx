import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
import axios from "axios"
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import TvOutlinedIcon from '@mui/icons-material/TvOutlined'
import { WebSocketContext } from "./App"
import { NotificationType } from "./types/NotificationType"
import type { Movie } from "./types/Movie"
import type { Serie } from "./types/Serie"
import { SeasonCard } from "./MediaCard"
import { DetailHeader, DetailPage } from "./DetailPage"
import { formatDate, formatDuration, formatYear, pluralize, posterUrl, seasonLabel } from "./format"
import './SerieDetail.css'

const REFRESH_DEBOUNCE_MS = 800

/** URL value of a season: its name, or "none" for episodes without a season */
export const seasonKey = (season: string | null) => season ?? "none"

type Season = { key: string, season: string | null, episodes: Movie[], posterFileName: string | null }

/** Seasons from the episodes (like tvOS): numeric order, specials (0) last, episodes without a season at the very end. */
const buildSeasons = (episodes: Movie[], seriePoster: string | null): Season[] => {
    const bySeason = new Map<string, Season>()
    for (const episode of episodes) {
        const key = seasonKey(episode.season)
        let season = bySeason.get(key)
        if (!season) {
            season = { key, season: episode.season, episodes: [], posterFileName: null }
            bySeason.set(key, season)
        }
        season.episodes.push(episode)
    }
    const rank = (season: string | null) => {
        if (season === null) return Number.MAX_SAFE_INTEGER
        if (/^0+$/.test(season)) return Number.MAX_SAFE_INTEGER - 1
        return /^\d+$/.test(season) ? Number(season) : Number.MAX_SAFE_INTEGER - 2
    }
    return [...bySeason.values()]
        .map(season => ({
            ...season,
            episodes: [...season.episodes].sort((a, b) => (a.episode ?? Infinity) - (b.episode ?? Infinity) || a.title.localeCompare(b.title)),
            // The scrapers store the season poster on every episode. Without one: the serie's poster.
            posterFileName: season.episodes.find(episode => episode.poster_file_name)?.poster_file_name ?? seriePoster,
        }))
        .sort((a, b) => rank(a.season) - rank(b.season) || (a.season ?? "").localeCompare(b.season ?? ""))
}

const yearRange = (episodes: Movie[]): string | null => {
    const years = episodes.map(episode => formatYear(episode.release_date)).filter((year): year is string => year !== null).map(Number)
    if (years.length === 0) return null
    const first = Math.min(...years), last = Math.max(...years)
    return first === last ? String(first) : `${first}–${last}`
}

/**
 * Serie page (season = null): poster, title, seasons.
 * Season page: season poster, its episodes as a list. An episode opens the movie detail page (with cast).
 */
export const SerieDetail = (props: {
    serieId: number
    season: string | null
    onBack: () => void
    onOpenSeason: (key: string) => void
    onOpenEpisode: (episode: Movie) => void
    onPlay: (episode: Movie) => void
}) => {
    const [ serie, setSerie ] = useState<Serie | null>(null)
    const [ episodes, setEpisodes ] = useState<Movie[]>([])
    const [ error, setError ] = useState<string | null>(null)
    const websocketMessage = useContext(WebSocketContext)

    const requestCounter = useRef(0)
    const load = useCallback(() => {
        const requestId = ++requestCounter.current
        Promise.all([
            axios.get<Serie>(`/api/serie/${props.serieId}`),
            axios.get<Movie[]>(`/api/serie/${props.serieId}/episodes`),
        ])
        .then(([ serieResponse, episodesResponse ]) => {
            if (requestId !== requestCounter.current) return
            setSerie(serieResponse.data)
            setEpisodes(episodesResponse.data)
            setError(null)
        })
        .catch(() => { if (requestId === requestCounter.current) setError("This serie doesn't exist anymore.") })
    }, [props.serieId])

    useEffect(() => {
        setSerie(null)
        load()
    }, [load])

    const timer = useRef<number | null>(null)
    useEffect(() => {
        if (websocketMessage.message !== NotificationType.MOVIES_UPDATED) return
        if (timer.current) window.clearTimeout(timer.current)
        timer.current = window.setTimeout(load, REFRESH_DEBOUNCE_MS)
        return () => { if (timer.current) window.clearTimeout(timer.current) }
    }, [websocketMessage, load])

    // Serie page <-> season page reuse this component: start each level at the top
    useEffect(() => { window.scrollTo(0, 0) }, [props.season])

    const seasons = useMemo(() => buildSeasons(episodes, serie?.poster_file_name ?? null), [episodes, serie])

    if (error) return <DetailPage onBack={props.onBack}><p className="contentHint">{error}</p></DetailPage>
    if (!serie) return <DetailPage onBack={props.onBack}><p className="contentHint">Loading…</p></DetailPage>

    // --- Season page ---
    if (props.season !== null) {
        const season = seasons.find(s => s.key === props.season)
        if (!season) return <DetailPage onBack={props.onBack}><p className="contentHint">This season has no episodes anymore.</p></DetailPage>
        const first = season.episodes[0]
        return (
            <DetailPage onBack={props.onBack} tintImage={posterUrl(season.posterFileName, "thumb")}>
                <DetailHeader
                    image={posterUrl(season.posterFileName)}
                    placeholderIcon={<TvOutlinedIcon />}
                    eyebrow={serie.title}
                    title={seasonLabel(season.season)}
                    meta={[pluralize(season.episodes.length, "episode"), yearRange(season.episodes)]}
                    actions={first && <button className="btn btn-primary btnLarge" onClick={() => props.onPlay(first)}><PlayArrowRoundedIcon /> Play</button>}
                />
                <section className="detailSection">
                    <h2>Episodes</h2>
                    <ol className="episodeList">
                        { season.episodes.map(episode => <EpisodeRow key={episode.id} episode={episode} onOpen={props.onOpenEpisode} onPlay={props.onPlay} />) }
                    </ol>
                </section>
            </DetailPage>
        )
    }

    // --- Serie page ---
    // Play starts with the first regular season (not the specials)
    const firstSeason = seasons.find(s => s.season !== null && !/^0+$/.test(s.season)) ?? seasons[0]
    const firstEpisode = firstSeason?.episodes[0]
    const regularSeasons = seasons.filter(s => s.season !== null && !/^0+$/.test(s.season)).length
    return (
        <DetailPage onBack={props.onBack} tintImage={posterUrl(serie.poster_file_name, "thumb")}>
            <DetailHeader
                image={posterUrl(serie.poster_file_name)}
                placeholderIcon={<TvOutlinedIcon />}
                title={serie.title}
                meta={[regularSeasons > 0 ? pluralize(regularSeasons, "season") : null, pluralize(episodes.length, "episode"), yearRange(episodes)]}
                actions={firstEpisode && <button className="btn btn-primary btnLarge" onClick={() => props.onPlay(firstEpisode)}><PlayArrowRoundedIcon /> Play</button>}
            />
            {
                seasons.length > 0
                ? <section className="detailSection">
                    <h2>Seasons</h2>
                    <div className="mediaGrid">
                        {
                            seasons.map(season => (
                                <SeasonCard
                                    key={season.key}
                                    title={seasonLabel(season.season)}
                                    episodeCount={season.episodes.length}
                                    posterFileName={season.posterFileName}
                                    onOpen={() => props.onOpenSeason(season.key)}
                                />
                            ))
                        }
                    </div>
                </section>
                : <p className="contentHint">No episodes found for this serie.</p>
            }
        </DetailPage>
    )
}

/** One row of the episode list: number, title, air date · duration. Opens the episode, play button plays it. */
const EpisodeRow = (props: { episode: Movie, onOpen: (episode: Movie) => void, onPlay: (episode: Movie) => void }) => {
    const { episode } = props
    const meta = [formatDate(episode.release_date), formatDuration(episode.length_in_seconds)].filter(Boolean).join(" · ")
    return (
        <li>
            <div
                className="episodeRow"
                role="button"
                tabIndex={0}
                onClick={() => props.onOpen(episode)}
                onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); props.onOpen(episode) } }}
            >
                <span className="episodeNumber">{episode.episode ?? "–"}</span>
                <span className="episodeText">
                    <span className="episodeTitle">{episode.title}</span>
                    { meta && <span className="episodeMeta">{meta}</span> }
                </span>
                <button
                    className="episodePlay"
                    title="Play"
                    aria-label={`Play ${episode.title}`}
                    onClick={event => { event.stopPropagation(); props.onPlay(episode) }}
                    onKeyDown={event => event.stopPropagation()}
                >
                    <PlayArrowRoundedIcon />
                </button>
            </div>
        </li>
    )
}
