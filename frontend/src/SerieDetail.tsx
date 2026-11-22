import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
import axios from "axios"
import PlayArrowRoundedIcon from '@mui/icons-material/PlayArrowRounded'
import TvOutlinedIcon from '@mui/icons-material/TvOutlined'
import { WebSocketContext } from "./App"
import { NotificationType } from "./types/NotificationType"
import type { Movie } from "./types/Movie"
import type { Serie } from "./types/Serie"
import { EpisodeCard } from "./MediaCard"
import { DetailHeader, DetailPage } from "./DetailPage"
import { formatDuration, formatYear, pluralize, posterUrl, seasonLabel } from "./format"
import './SerieDetail.css'

const REFRESH_DEBOUNCE_MS = 800

type Season = { key: string, season: string | null, episodes: Movie[], posterFileName: string | null }

/** Specials (season 0) */
const isSpecials = (season: string | null) => season !== null && /^0+$/.test(season)

/**
 * The season poster (same rule as tvOS): scrapers store the season poster on every episode they matched
 * (those also have a still). Otherwise a poster that several episodes share, else the serie's poster
 * (frame grabs are one per episode, they don't stand for the season).
 */
const seasonPoster = (episodes: Movie[], seriePoster: string | null): string | null => {
    const scraped = episodes.find(episode => episode.still_file_name !== null && episode.poster_file_name !== null)
    if (scraped) return scraped.poster_file_name
    const counts = new Map<string, number>()
    for (const episode of episodes) {
        if (episode.poster_file_name) counts.set(episode.poster_file_name, (counts.get(episode.poster_file_name) ?? 0) + 1)
    }
    const [ shared, count ] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0] ?? [ null, 0 ]
    return shared !== null && count > 1 ? shared : seriePoster
}

/** Seasons from the episodes: numeric order, specials (0) last, episodes without a season at the very end. */
const buildSeasons = (episodes: Movie[], seriePoster: string | null): Season[] => {
    const bySeason = new Map<string, Movie[]>()
    for (const episode of episodes) {
        const key = episode.season ?? "none"
        bySeason.set(key, [...(bySeason.get(key) ?? []), episode])
    }
    const rank = (season: string | null) => {
        if (season === null) return Number.MAX_SAFE_INTEGER
        if (isSpecials(season)) return Number.MAX_SAFE_INTEGER - 1
        return /^\d+$/.test(season) ? Number(season) : Number.MAX_SAFE_INTEGER - 2
    }
    return [...bySeason.entries()]
        .map(([ key, seasonEpisodes ]) => ({
            key,
            season: seasonEpisodes[0]!.season,
            episodes: [...seasonEpisodes].sort((a, b) => (a.episode ?? Infinity) - (b.episode ?? Infinity) || a.title.localeCompare(b.title)),
            posterFileName: seasonPoster(seasonEpisodes, seriePoster),
        }))
        .sort((a, b) => rank(a.season) - rank(b.season) || (a.season ?? "").localeCompare(b.season ?? ""))
}

const yearRange = (episodes: Movie[]): string | null => {
    const years = episodes.map(episode => formatYear(episode.release_date)).filter((year): year is string => year !== null).map(Number)
    if (years.length === 0) return null
    const first = Math.min(...years), last = Math.max(...years)
    return first === last ? String(first) : `${first}–${last}`
}

/** "10 episodes · 2019–2020 · 7 h 30 min" */
const seasonStats = (episodes: Movie[]): string => {
    const totalSeconds = episodes.reduce((sum, episode) => sum + (episode.length_in_seconds ?? 0), 0)
    return [pluralize(episodes.length, "episode"), yearRange(episodes), formatDuration(totalSeconds)].filter(Boolean).join(" · ")
}

/**
 * Serie page (like tvOS): poster, title, then all seasons on one page. Each season has a header
 * (season poster, name, stats) and a row of 16:9 episode cards. An episode opens the movie detail page (with cast).
 */
export const SerieDetail = (props: {
    serieId: number
    onBack: () => void
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

    const seasons = useMemo(() => buildSeasons(episodes, serie?.poster_file_name ?? null), [episodes, serie])

    if (error) return <DetailPage onBack={props.onBack}><p className="contentHint">{error}</p></DetailPage>
    if (!serie) return <DetailPage onBack={props.onBack}><p className="contentHint">Loading…</p></DetailPage>

    // Play starts with the first regular season (not the specials)
    const regularSeasons = seasons.filter(s => s.season !== null && !isSpecials(s.season))
    const firstEpisode = (regularSeasons[0] ?? seasons[0])?.episodes[0]
    return (
        <DetailPage onBack={props.onBack}>
            <DetailHeader
                image={posterUrl(serie.poster_file_name)}
                placeholderIcon={<TvOutlinedIcon />}
                title={serie.title}
                meta={[regularSeasons.length > 0 ? pluralize(regularSeasons.length, "season") : null, episodes.length > 0 ? pluralize(episodes.length, "episode") : null, yearRange(episodes)]}
                actions={firstEpisode && <button className="btn btn-primary btnLarge" onClick={() => props.onPlay(firstEpisode)}><PlayArrowRoundedIcon /> Play</button>}
            />
            {
                seasons.length === 0 && <p className="contentHint">No episodes found for this serie.</p>
            }
            {
                seasons.map(season => (
                    <section key={season.key} className="detailSection">
                        <div className="seasonHeader">
                            <div className="seasonPoster">
                                {
                                    season.posterFileName
                                    ? <img src={posterUrl(season.posterFileName, "thumb") ?? undefined} alt="" loading="lazy" decoding="async" />
                                    : <div className="artPlaceholder"><TvOutlinedIcon /></div>
                                }
                            </div>
                            <div className="seasonText">
                                <h2>{seasonLabel(season.season)}</h2>
                                <span className="seasonStats">{seasonStats(season.episodes)}</span>
                            </div>
                        </div>
                        <div className="shelf artShelf episodeShelf">
                            { season.episodes.map(episode => <EpisodeCard key={episode.id} episode={episode} onOpen={props.onOpenEpisode} onPlay={props.onPlay} />) }
                        </div>
                    </section>
                ))
            }
        </DetailPage>
    )
}
