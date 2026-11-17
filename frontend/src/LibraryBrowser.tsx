import React, { useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import axios from "axios"
import AddRoundedIcon from '@mui/icons-material/AddRounded'
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import SearchRoundedIcon from '@mui/icons-material/SearchRounded'
import ChevronLeftRoundedIcon from '@mui/icons-material/ChevronLeftRounded'
import VideoLibraryOutlinedIcon from '@mui/icons-material/VideoLibraryOutlined'

import { WebSocketContext } from "./App"
import { NotificationType } from "./types/NotificationType"
import { LibraryType, type Library } from "./types/Library"
import type { Movie } from "./types/Movie"
import type { Collection } from "./types/Collection"
import { MovieCard, CollectionCard, SerieCard } from "./MediaCard"
import type { Serie } from "./types/Serie"
import { PlayerOverlay } from "./PlayerOverlay"
import { LibraryDialog } from "./LibraryDialog"
import { SettingsDialog } from "./SettingsDialog"
import { MatchDialog } from "./MatchDialog"
import { MovieDetail } from "./MovieDetail"
import { PersonDetail } from "./PersonDetail"
import { SerieDetail } from "./SerieDetail"
import { useToast } from "./Toast"
import { useScanStatus } from "./useScanStatus"
import { pluralize, posterUrl } from "./format"
import { JustifiedGrid } from "./JustifiedGrid"
import { gridLayoutFor } from "./gridLayout"
import './LibraryBrowser.css'
import logoUrl from '../../design/logo.svg'

type View = "collections" | "all"

// Stable helpers for JustifiedGrid (no new functions on every render)
const movieKey = (movie: Movie) => movie.id
const movieImage = (movie: Movie) => posterUrl(movie.poster_file_name, "thumb")    // same URL as MovieCard
const collectionKey = (collection: Collection) => collection.id
const collectionImage = (collection: Collection) => posterUrl(collection.poster_file_name, "thumb")
type OpenDialog = { type: "settings" } | { type: "library", libraryId: number | null } | { type: "match", movie: Movie } | null

// During scans the server sends MOVIES_UPDATED for every file. Refetch at most this often.
const REFRESH_DEBOUNCE_MS = 800

export const LibraryBrowser = () => {
    const [ params, setParams ] = useSearchParams()
    const navigate = useNavigate()
    const toast = useToast()
    const websocketMessage = useContext(WebSocketContext)
    const { status: scanStatus, startScan, refresh: refreshScanStatus } = useScanStatus()

    const [ libraries, setLibraries ] = useState<Library[] | null>(null)
    const [ collections, setCollections ] = useState<Collection[]>([])
    const [ movies, setMovies ] = useState<Movie[]>([])
    const [ series, setSeries ] = useState<Serie[]>([])
    const [ loading, setLoading ] = useState<boolean>(false)
    const [ search, setSearch ] = useState<string>("")
    const [ dialog, setDialog ] = useState<OpenDialog>(null)

    const searchInput = useRef<HTMLInputElement>(null)
    const playerOpenedInApp = useRef<boolean>(false)

    // --- State in the URL: reload keeps the place, back button works ---
    const libraryId = Number(params.get("library")) || null
    const view: View = params.get("view") === "all" ? "all" : "collections"
    const collectionId = Number(params.get("collection")) || null
    const playId = Number(params.get("play")) || null
    const movieId = Number(params.get("movie")) || null      // detail page
    const personId = Number(params.get("person")) || null    // person page
    const serieId = Number(params.get("serie")) || null      // serie page (SERIES libraries)
    const seasonParam = serieId !== null ? params.get("season") : null   // season page inside a serie
    const detailOpen = movieId !== null || personId !== null || serieId !== null

    const updateParams = useCallback((changes: Record<string, string | number | null>, replace = false) => {
        setParams(previous => {
            const next = new URLSearchParams(previous)
            for (const [key, value] of Object.entries(changes)) {
                if (value === null) next.delete(key)
                else next.set(key, String(value))
            }
            return next
        }, { replace })
    }, [setParams])

    const library = libraries?.find(l => l.id === libraryId) ?? null
    const libraryType = library?.type ?? null
    const isSeriesLibrary = libraryType === LibraryType.SERIES

    // --- Data ---
    const fetchLibraries = useCallback(() => {
        axios.get<Library[]>('/api/libraries')
        .then(response => setLibraries(response.data))
        .catch(() => setLibraries([]))
    }, [])

    const requestCounter = useRef(0)
    const fetchContent = useCallback(async () => {
        const requestId = ++requestCounter.current
        const isCurrent = () => requestId === requestCounter.current
        if (!libraryId || !libraryType) {
            setMovies([])
            setCollections([])
            setSeries([])
            return
        }
        try {
            if (libraryType === LibraryType.SERIES) {
                // Series libraries show only the series (+ files that aren't assigned to one)
                const [ seriesResponse, moviesResponse ] = await Promise.all([
                    axios.get<Serie[]>(`/api/series/${libraryId}`),
                    axios.get<Movie[]>(`/api/movies/${libraryId}`),
                ])
                if (isCurrent()) {
                    setSeries(seriesResponse.data)
                    setMovies(moviesResponse.data.filter(movie => movie.is_episode_of_serie_id === null))
                }
            } else if (view === "collections") {
                const collectionsResponse = await axios.get<Collection[]>(`/api/collections/${libraryId}`)
                if (isCurrent()) setCollections(collectionsResponse.data)
                if (collectionId) {
                    const moviesResponse = await axios.get<Movie[]>(`/api/movies/collection/${collectionId}`)
                    if (isCurrent()) setMovies(moviesResponse.data)
                }
            } else {
                const moviesResponse = await axios.get<Movie[]>(`/api/movies/${libraryId}`)
                if (isCurrent()) setMovies(moviesResponse.data)
            }
        } catch {
            if (isCurrent()) toast("Could not load the library.")
        }
    }, [libraryId, libraryType, view, collectionId, toast])

    const latestFetchContent = useRef(fetchContent)
    latestFetchContent.current = fetchContent

    useEffect(() => { fetchLibraries() }, [fetchLibraries])

    // Select the first library if none (or a deleted one) is selected
    useEffect(() => {
        if (libraries && libraries.length > 0 && !library) {
            updateParams({ library: libraries[0]!.id, collection: null }, true)
        }
    }, [libraries, library, updateParams])

    useEffect(() => {
        setMovies([])
        setCollections([])
        setSeries([])
        setSearch("")
        setLoading(true)
        fetchContent().finally(() => setLoading(false))
    }, [fetchContent])

    const refreshTimer = useRef<number | null>(null)
    useEffect(() => {
        switch (websocketMessage.message) {
            case NotificationType.LIBRARIES_UPDATED:
                fetchLibraries()
                break
            case NotificationType.MOVIES_UPDATED:
            case NotificationType.COLLECTIONS_UPDATED:
                if (refreshTimer.current) window.clearTimeout(refreshTimer.current)
                refreshTimer.current = window.setTimeout(() => latestFetchContent.current(), REFRESH_DEBOUNCE_MS)
                break
        }
    }, [websocketMessage, fetchLibraries])

    // Tell the user when a scan has finished
    const wasScanning = useRef(false)
    useEffect(() => {
        if (wasScanning.current && !scanStatus.running) toast("Scan finished")
        wasScanning.current = scanStatus.running
    }, [scanStatus.running, toast])

    // "/" focuses the search field
    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            const target = event.target as HTMLElement
            if (event.key === "/" && !dialog && !playId && !["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) {
                event.preventDefault()
                searchInput.current?.focus()
            }
        }
        window.addEventListener("keydown", onKeyDown)
        return () => window.removeEventListener("keydown", onKeyDown)
    }, [dialog, playId])

    // --- Derived ---
    const showCollections = view === "collections" && collectionId === null
    const currentCollection = collections.find(c => c.id === collectionId) ?? null
    const query = search.trim().toLocaleLowerCase()
    const visibleCollections = useMemo(
        () => query ? collections.filter(c => c.title.toLocaleLowerCase().includes(query)) : collections,
        [collections, query])
    const visibleMovies = useMemo(
        () => query ? movies.filter(m => m.title.toLocaleLowerCase().includes(query)) : movies,
        [movies, query])
    const visibleSeries = useMemo(
        () => query ? series.filter(s => s.title.toLocaleLowerCase().includes(query)) : series,
        [series, query])
    const itemCount = isSeriesLibrary ? series.length + movies.length : showCollections ? collections.length : movies.length
    const visibleCount = isSeriesLibrary ? visibleSeries.length + visibleMovies.length : showCollections ? visibleCollections.length : visibleMovies.length

    // --- Actions ---
    const selectLibrary = (id: number) => updateParams({ library: id, collection: null, movie: null, person: null, serie: null, season: null })
    const setView = (newView: View) => updateParams({ view: newView === "all" ? "all" : null, collection: null })
    const openCollection = (collection: Collection) => updateParams({ view: null, collection: collection.id, movie: null, person: null, serie: null, season: null })
    const closeCollection = () => updateParams({ collection: null })

    // Detail pages. Remember the grid's scroll position and restore it when coming back.
    const gridScroll = useRef(0)
    const openMovie = (movie: Movie) => {
        if (!detailOpen) gridScroll.current = window.scrollY
        updateParams({ movie: movie.id, person: null })
    }
    const openPerson = (person: { id: number }) => {
        if (!detailOpen) gridScroll.current = window.scrollY
        updateParams({ person: person.id, movie: null })
    }
    // Series: serie -> season -> episode (movie detail). Each level is one history entry.
    const openSerie = (serie: Serie) => {
        if (!detailOpen) gridScroll.current = window.scrollY
        updateParams({ serie: serie.id, season: null, movie: null, person: null })
    }
    const openSeason = (key: string) => updateParams({ season: key, movie: null, person: null })
    const closeDetail = useCallback(() => {
        // Opened inside the app -> browser back (keeps history clean). Opened from a link -> one level up.
        if ((window.history.state?.idx ?? 0) > 0) navigate(-1)
        else if (movieId !== null || personId !== null) updateParams({ movie: null, person: null }, true)
        else if (seasonParam !== null) updateParams({ season: null }, true)
        else updateParams({ serie: null }, true)
    }, [navigate, updateParams, movieId, personId, seasonParam])
    useLayoutEffect(() => {
        if (!detailOpen) window.scrollTo(0, gridScroll.current)
    }, [detailOpen])

    const playMovie = (movie: Movie) => {
        playerOpenedInApp.current = true
        updateParams({ play: movie.id })
    }

    const closePlayer = useCallback(() => {
        if (playerOpenedInApp.current) {
            playerOpenedInApp.current = false
            navigate(-1) // remove the player entry, so "back" doesn't reopen it
        } else {
            updateParams({ play: null }, true)
        }
    }, [navigate, updateParams])

    const scanLibrary = () => {
        if (!library) return
        startScan({ library_id: library.id })
        .then(() => toast(`Scanning ${library.name}…`))
        .catch(() => toast("Could not start the scan."))
    }

    const findMatch = (movie: Movie) => setDialog({ type: "match", movie })

    const refreshMovie = (movie: Movie) => {
        startScan({ movie_id: movie.id })
        .then(() => toast(`Refreshing metadata of “${movie.title}”`))
        .catch(() => toast("Could not start the refresh."))
    }

    const closeDialog = useCallback(() => setDialog(null), [])

    // --- Render ---
    const landscape = library?.type === LibraryType.VIDEOS
    // Grid or justified rows, per library type (gridLayout.ts). ?layout=grid|justified overrides it.
    const layout = gridLayoutFor(library?.type, params.get("layout"))

    const renderContent = () => {
        if (libraries === null) return null

        if (libraries.length === 0) {
            return (
                <div className="emptyState">
                    <VideoLibraryOutlinedIcon className="emptyIcon" />
                    <h2>No libraries yet</h2>
                    <p>Add a library to start scanning your media.</p>
                    <button className="btn btn-primary" onClick={() => setDialog({ type: "library", libraryId: null })}><AddRoundedIcon /> Add library</button>
                </div>
            )
        }

        if (loading && itemCount === 0) return <p className="contentHint">Loading…</p>

        if (visibleCount === 0) {
            if (query) return <p className="contentHint">Nothing matches “{search.trim()}”.</p>
            if (isSeriesLibrary && itemCount === 0) {
                return (
                    <div className="emptyState">
                        <h2>No series yet</h2>
                        <p>Scan the library to find new media. Series and seasons come from the scraper.</p>
                        <button className="btn btn-primary" onClick={scanLibrary} disabled={scanStatus.running}><RefreshRoundedIcon /> Scan library</button>
                    </div>
                )
            }
            if (showCollections && !isSeriesLibrary) {
                return (
                    <div className="emptyState">
                        <h2>No collections</h2>
                        <p>Collections come from folder configs or the scraper. All titles of this library are under “All”.</p>
                        <button className="btn" onClick={() => setView("all")}>Show all titles</button>
                    </div>
                )
            }
            return (
                <div className="emptyState">
                    <h2>No titles yet</h2>
                    <p>Scan the library to find new media.</p>
                    <button className="btn btn-primary" onClick={scanLibrary} disabled={scanStatus.running}><RefreshRoundedIcon /> Scan library</button>
                </div>
            )
        }

        if (isSeriesLibrary) {
            return <>
                {
                    visibleSeries.length > 0 &&
                    <div className="mediaGrid">
                        { visibleSeries.map(serie => <SerieCard key={serie.id} serie={serie} onOpen={openSerie} />) }
                    </div>
                }
                {
                    // Files the scraper couldn't assign to a serie: still reachable
                    visibleMovies.length > 0 &&
                    <section className="unassignedSection">
                        <h2>Not assigned to a series</h2>
                        <div className="mediaGrid">
                            { visibleMovies.map(movie => <MovieCard key={movie.id} movie={movie} onOpen={openMovie} onPlay={playMovie} />) }
                        </div>
                    </section>
                }
            </>
        }

        if (layout === "justified") {
            const defaultRatio = landscape ? 16 / 9 : 0.6748
            return showCollections
                ? <JustifiedGrid
                    items={visibleCollections}
                    getKey={collectionKey}
                    getImage={collectionImage}
                    defaultRatio={defaultRatio}
                    renderItem={(collection, onImageRatio) => <CollectionCard collection={collection} onOpen={openCollection} onImageRatio={onImageRatio} />}
                  />
                : <JustifiedGrid
                    items={visibleMovies}
                    getKey={movieKey}
                    getImage={movieImage}
                    defaultRatio={defaultRatio}
                    renderItem={(movie, onImageRatio) => <MovieCard movie={movie} onOpen={openMovie} onPlay={playMovie} onImageRatio={onImageRatio} />}
                  />
        }

        return (
            <div className={`mediaGrid${landscape ? " landscape" : ""}`}>
                {
                    showCollections
                    ? visibleCollections.map(collection => <CollectionCard key={collection.id} collection={collection} onOpen={openCollection} />)
                    : visibleMovies.map(movie => <MovieCard key={movie.id} movie={movie} onOpen={openMovie} onPlay={playMovie} />)
                }
            </div>
        )
    }

    const countNoun: [string, string] = isSeriesLibrary ? ["series", "series"] : showCollections ? ["collection", "collections"] : ["title", "titles"]
    const countValue = isSeriesLibrary ? series.length : itemCount
    const visibleCountValue = isSeriesLibrary ? visibleSeries.length : visibleCount
    const countLabel = query
        ? `${visibleCountValue.toLocaleString()} of ${pluralize(countValue, ...countNoun)}`
        : pluralize(countValue, ...countNoun)

    return (
        <div className="appShell">
            <header className="topBar">
                <div className="brand"><img src={logoUrl} alt="pinea" /></div>

                <nav className="libraryTabs" aria-label="Libraries">
                    {
                        (libraries ?? []).map(l => (
                            <button key={l.id} className={`libraryTab${l.id === libraryId ? " active" : ""}`} onClick={() => selectLibrary(l.id)} aria-current={l.id === libraryId ? "page" : undefined}>
                                {l.name}
                            </button>
                        ))
                    }
                </nav>

                {
                    library && !detailOpen && (
                        <div className="viewControls">
                            {
                            !isSeriesLibrary &&
                            <div className="segmented" role="tablist" aria-label="View">
                                <button role="tab" aria-selected={view === "collections"} className={view === "collections" ? "active" : ""} onClick={() => setView("collections")}>Collections</button>
                                <button role="tab" aria-selected={view === "all"} className={view === "all" ? "active" : ""} onClick={() => setView("all")}>All</button>
                            </div>
                            }
                            <label className="searchBox">
                                <SearchRoundedIcon />
                                <input ref={searchInput} type="search" placeholder="Search" value={search} onChange={event => setSearch(event.target.value)} aria-label="Search titles" />
                            </label>
                        </div>
                    )
                }

                <div className="topBarActions">
                    {
                        library && <>
                            <button className="btn btn-ghost scanButton" onClick={scanLibrary} disabled={scanStatus.running} title={`Scan ${library.name} for new and removed media`}>
                                <RefreshRoundedIcon className={scanStatus.running ? "spinning" : ""} />
                                <span className="hideNarrow">{scanStatus.running ? "Scanning…" : "Scan"}</span>
                            </button>
                            <button className="iconButton" onClick={() => setDialog({ type: "library", libraryId: library.id })} title="Edit library" aria-label="Edit library">
                                <EditOutlinedIcon />
                            </button>
                            <span className="topBarDivider" />
                        </>
                    }
                    <button className="iconButton" onClick={() => setDialog({ type: "library", libraryId: null })} title="Add library" aria-label="Add library">
                        <AddRoundedIcon />
                    </button>
                    <button className="iconButton" onClick={() => setDialog({ type: "settings" })} title="Settings" aria-label="Settings">
                        <SettingsOutlinedIcon />
                    </button>
                </div>
            </header>

            <main className="content">
                {
                    movieId !== null &&
                    <MovieDetail
                        movieId={movieId}
                        landscape={landscape}
                        onBack={closeDetail}
                        onPlay={playMovie}
                        onOpenPerson={openPerson}
                        onOpenCollection={openCollection}
                        onFindMatch={findMatch}
                        onRefresh={refreshMovie}
                    />
                }
                {
                    movieId === null && personId !== null &&
                    <PersonDetail personId={personId} landscape={landscape} onBack={closeDetail} onOpenMovie={openMovie} onPlay={playMovie} />
                }
                {
                    movieId === null && personId === null && serieId !== null &&
                    <SerieDetail
                        serieId={serieId}
                        season={seasonParam}
                        onBack={closeDetail}
                        onOpenSeason={openSeason}
                        onOpenEpisode={openMovie}
                        onPlay={playMovie}
                    />
                }
                {/* The grid stays mounted behind detail pages: no reload and no flicker when going back */}
                <div hidden={detailOpen}>
                {
                    library && (
                        <div className="contentHeader">
                            {
                                collectionId !== null && !isSeriesLibrary
                                ? <nav className="breadcrumb" aria-label="Breadcrumb">
                                    <button className="btn btn-ghost breadcrumbBack" onClick={closeCollection}><ChevronLeftRoundedIcon /> Collections</button>
                                    <span className="breadcrumbSeparator">/</span>
                                    <h1>{currentCollection?.title ?? "…"}</h1>
                                    <span className="contentCount">{countLabel}</span>
                                </nav>
                                : <span className="contentCount">{loading && itemCount === 0 ? "" : countLabel}</span>
                            }
                        </div>
                    )
                }
                {renderContent()}
                </div>
            </main>

            { playId !== null && <PlayerOverlay movieId={playId} onClose={closePlayer} /> }

            { dialog?.type === "library" && <LibraryDialog libraryId={dialog.libraryId} onClose={closeDialog} onSaved={id => { fetchLibraries(); if (id) selectLibrary(id) }}
                onRebuild={id => startScan({ library_id: id, reset_metadata: true }).then(() => toast("Rebuilding metadata…"))}
                scanRunning={scanStatus.running} /> }
            { dialog?.type === "match" && <MatchDialog movie={dialog.movie} onClose={closeDialog} onMatched={refreshScanStatus} /> }
            { dialog?.type === "settings" && <SettingsDialog onClose={closeDialog} scanAll={() => startScan({}).then(() => toast("Scanning all libraries…"))} scanRunning={scanStatus.running} /> }
        </div>
    )
}
