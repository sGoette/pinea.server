import React, { useCallback, useEffect, useRef, useState } from "react"
import axios from "axios"
import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import type { Movie } from "./types/Movie"
import { formatDuration, formatYear } from "./format"
import './PlayerOverlay.css'

const HIDE_CONTROLS_AFTER_MS = 2500

/** Fullscreen video player shown above the library. Close with the button, Esc or the browser's back button. */
export const PlayerOverlay = (props: { movieId: number, onClose: () => void }) => {
    const [ movie, setMovie ] = useState<Movie | null>(null)
    const [ error, setError ] = useState<string | null>(null)
    const [ chromeVisible, setChromeVisible ] = useState<boolean>(true)
    const videoRef = useRef<HTMLVideoElement>(null)
    const hideTimer = useRef<number | null>(null)

    useEffect(() => {
        setMovie(null)
        setError(null)
        axios.get<Movie>(`/api/movie/${props.movieId}`)
        .then(response => setMovie(response.data))
        .catch(() => setError("This movie doesn't exist anymore."))
    }, [props.movieId])

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            // In native fullscreen the browser uses Esc to leave fullscreen first
            if (event.key === "Escape" && !document.fullscreenElement) props.onClose()
        }
        window.addEventListener("keydown", onKeyDown)
        const previousOverflow = document.body.style.overflow
        document.body.style.overflow = "hidden"
        return () => {
            window.removeEventListener("keydown", onKeyDown)
            document.body.style.overflow = previousOverflow
        }
    }, [props.onClose])

    // Title bar and cursor fade out while the video plays and the mouse doesn't move
    const showChrome = useCallback(() => {
        setChromeVisible(true)
        if (hideTimer.current) window.clearTimeout(hideTimer.current)
        hideTimer.current = window.setTimeout(() => {
            if (videoRef.current && !videoRef.current.paused) setChromeVisible(false)
        }, HIDE_CONTROLS_AFTER_MS)
    }, [])

    useEffect(() => {
        showChrome()
        videoRef.current?.focus()
        return () => { if (hideTimer.current) window.clearTimeout(hideTimer.current) }
    }, [showChrome])

    const onVideoError = () => {
        const format = [movie?.format, movie?.codec].filter(Boolean).join(", ")
        setError(`This file can't be played in the browser${format ? ` (${format})` : ""}. The tvOS app may still be able to play it.`)
    }

    const meta = movie ? [formatYear(movie.release_date), formatDuration(movie.length_in_seconds)].filter(Boolean).join(" · ") : ""

    return (
        <div
            className={`player${chromeVisible ? "" : " idle"}`}
            role="dialog"
            aria-modal="true"
            aria-label={movie?.title ?? "Player"}
            onMouseMove={showChrome}
            onTouchStart={showChrome}
        >
            <video
                ref={videoRef}
                src={`/api/movie/${props.movieId}/stream`}
                controls
                autoPlay
                playsInline
                preload="metadata"
                onPlay={showChrome}
                onPause={() => setChromeVisible(true)}
                onError={onVideoError}
            />
            <div className="playerTopBar">
                <div className="playerTitle">
                    <p>{movie?.title ?? ""}</p>
                    { meta && <span>{meta}</span> }
                </div>
                <button className="playerClose" onClick={props.onClose} aria-label="Close player" title="Close (Esc)">
                    <CloseRoundedIcon />
                </button>
            </div>
            { error && <div className="playerError"><p>{error}</p><button className="btn" onClick={props.onClose}>Back to library</button></div> }
        </div>
    )
}
