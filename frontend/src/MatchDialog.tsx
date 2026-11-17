import React, { useCallback, useEffect, useRef, useState } from "react"
import axios from "axios"
import SearchRoundedIcon from '@mui/icons-material/SearchRounded'
import MovieOutlinedIcon from '@mui/icons-material/MovieOutlined'
import { Dialog } from "./Dialog"
import { useToast } from "./Toast"
import { formatDate } from "./format"
import type { Movie } from "./types/Movie"
import type { SearchResult } from "./types/SearchResult"
import './MatchDialog.css'

const errorMessage = (error: unknown, fallback: string) =>
    axios.isAxiosError(error) && typeof error.response?.data?.detail === "string" ? error.response.data.detail : fallback

/** Runs the movie's scraper and lets the user pick the right hit. The choice is applied, not stored. */
export const MatchDialog = (props: { movie: Movie, onClose: () => void, onMatched: () => void }) => {
    const { movie } = props
    const toast = useToast()
    const [ query, setQuery ] = useState<string>("")
    const [ results, setResults ] = useState<SearchResult[] | null>(null)
    const [ searching, setSearching ] = useState<boolean>(false)
    const [ applying, setApplying ] = useState<string | null>(null)
    const [ error, setError ] = useState<string | null>(null)
    const requestCounter = useRef(0)

    const runSearch = useCallback((searchQuery: string) => {
        const requestId = ++requestCounter.current
        setSearching(true)
        setError(null)
        axios.get<SearchResult[]>(`/api/movie/${movie.id}/search`, { params: searchQuery.trim() ? { query: searchQuery.trim() } : {} })
        .then(response => { if (requestId === requestCounter.current) setResults(response.data) })
        .catch(error => { if (requestId === requestCounter.current) { setResults(null); setError(errorMessage(error, "The search failed.")) } })
        .finally(() => { if (requestId === requestCounter.current) setSearching(false) })
    }, [movie.id])

    // First search: what the scanner would search for (title from the file name)
    useEffect(() => { runSearch("") }, [runSearch])

    const apply = (result: SearchResult) => {
        setApplying(result.id)
        axios.post(`/api/movie/${movie.id}/match`, result)
        .then(() => {
            toast(`Applying “${result.name}” to “${movie.title}”…`)
            props.onMatched()
            props.onClose()
        })
        .catch(error => {
            setError(errorMessage(error, "Could not apply the match."))
            setApplying(null)
        })
    }

    const fileName = movie.file_location.split("/").pop() ?? movie.file_location

    return (
        <Dialog title="Find match" onClose={props.onClose} width={720}>
            <p className="matchFile">File: <code>{fileName}</code></p>

            <form className="matchSearch" onSubmit={event => { event.preventDefault(); runSearch(query) }}>
                <input
                    type="search"
                    value={query}
                    onChange={event => setQuery(event.target.value)}
                    placeholder="Title and year, e.g. The Two Towers 2002, or an IMDb / TMDB id"
                    aria-label="Search title"
                    autoFocus
                />
                <button className="btn" type="submit" disabled={searching}><SearchRoundedIcon /> Search</button>
            </form>

            { error && <p className="formError">{error}</p> }

            {
                searching && results === null
                ? <p className="contentHint">Searching…</p>
                : results !== null && results.length === 0
                ? <p className="contentHint">No results. Try another title or add the year.</p>
                : results !== null && (
                    <ul className={`matchResults${searching ? " stale" : ""}`}>
                        {
                            results.map(result => (
                                <li key={result.id}>
                                    <button className={`matchResult${applying === result.id ? " applying" : ""}`} onClick={() => apply(result)} disabled={applying !== null}>
                                        <div className="matchPoster">
                                            { result.poster_url ? <img src={result.poster_url} alt="" loading="lazy" /> : <span className="artPlaceholder"><MovieOutlinedIcon /></span> }
                                        </div>
                                        <div className="matchText">
                                            <p className="matchTitle">{result.name}</p>
                                            <p className="matchMeta">
                                                {[formatDate(result.release_date), result.original_name].filter(Boolean).join(" · ") || "No date"}
                                            </p>
                                            { result.overview && <p className="matchOverview">{result.overview}</p> }
                                        </div>
                                        <span className="matchUse">{applying === result.id ? "Applying…" : "Use"}</span>
                                    </button>
                                </li>
                            ))
                        }
                    </ul>
                )
            }
        </Dialog>
    )
}
