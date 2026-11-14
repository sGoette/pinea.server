import React, { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
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
import { MovieCard, CollectionCard } from "./MediaCard"
import { PlayerOverlay } from "./PlayerOverlay"
import { LibraryDialog } from "./LibraryDialog"
import { SettingsDialog } from "./SettingsDialog"
import { useToast } from "./Toast"
import { useScanStatus } from "./useScanStatus"
import { pluralize } from "./format"
import './LibraryBrowser.css'

type View = "collections" | "all"
type OpenDialog = { type: "settings" } | { type: "library", libraryId: number | null } | null

// During scans the server sends MOVIES_UPDATED for every file. Refetch at most this often.
const REFRESH_DEBOUNCE_MS = 800

export const LibraryBrowser = () => {
    const [ params, setParams ] = useSearchParams()
    const navigate = useNavigate()
    const toast = useToast()
    const websocketMessage = useContext(WebSocketContext)
    const { status: scanStatus, startScan } = useScanStatus()

    const [ libraries, setLibraries ] = useState<Library[] | null>(null)
    const [ collections, setCollections ] = useState<Collection[]>([])
    const [ movies, setMovies ] = useState<Movie[]>([])
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
        if (!libraryId) {
            setMovies([])
            setCollections([])
            return
        }
        try {
            if (view === "collections") {
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
    }, [libraryId, view, collectionId, toast])

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
    const itemCount = showCollections ? collections.length : movies.length
    const visibleCount = showCollections ? visibleCollections.length : visibleMovies.length

    // --- Actions ---
    const selectLibrary = (id: number) => updateParams({ library: id, collection: null })
    const setView = (newView: View) => updateParams({ view: newView === "all" ? "all" : null, collection: null })
    const openCollection = (collection: Collection) => updateParams({ collection: collection.id })
    const closeCollection = () => updateParams({ collection: null })

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

    const refreshMovie = (movie: Movie) => {
        startScan({ movie_id: movie.id })
        .then(() => toast(`Refreshing metadata of “${movie.title}”`))
        .catch(() => toast("Could not start the refresh."))
    }

    const closeDialog = useCallback(() => setDialog(null), [])

    // --- Render ---
    const landscape = library?.type === LibraryType.VIDEOS

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
            if (showCollections) {
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

        return (
            <div className={`mediaGrid${landscape ? " landscape" : ""}`}>
                {
                    showCollections
                    ? visibleCollections.map(collection => <CollectionCard key={collection.id} collection={collection} onOpen={openCollection} />)
                    : visibleMovies.map(movie => <MovieCard key={movie.id} movie={movie} onPlay={playMovie} onRefresh={refreshMovie} />)
                }
            </div>
        )
    }

    const countLabel = query
        ? `${visibleCount.toLocaleString()} of ${pluralize(itemCount, showCollections ? "collection" : "title")}`
        : pluralize(itemCount, showCollections ? "collection" : "title")

    return (
        <div className="appShell">
            <header className="topBar">
                <div className="brand"><span className="brandMark" aria-hidden="true" />pinea</div>

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
                    library && (
                        <div className="viewControls">
                            <div className="segmented" role="tablist" aria-label="View">
                                <button role="tab" aria-selected={view === "collections"} className={view === "collections" ? "active" : ""} onClick={() => setView("collections")}>Collections</button>
                                <button role="tab" aria-selected={view === "all"} className={view === "all" ? "active" : ""} onClick={() => setView("all")}>All</button>
                            </div>
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
                    library && (
                        <div className="contentHeader">
                            {
                                collectionId !== null
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
            </main>

            { playId !== null && <PlayerOverlay movieId={playId} onClose={closePlayer} /> }

            { dialog?.type === "library" && <LibraryDialog libraryId={dialog.libraryId} onClose={closeDialog} onSaved={id => { fetchLibraries(); if (id) selectLibrary(id) }} /> }
            { dialog?.type === "settings" && <SettingsDialog onClose={closeDialog} scanAll={() => startScan({}).then(() => toast("Scanning all libraries…"))} scanRunning={scanStatus.running} /> }
        </div>
    )
}
