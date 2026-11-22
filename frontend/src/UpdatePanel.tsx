import { useEffect, useRef, useState } from "react"
import axios from "axios"
import type { UpdateStatus, VersionInfo } from "./types/UpdateStatus"
import './UpdatePanel.css'

const BUSY_STATES = ['CHECKING', 'DOWNLOADING', 'INSTALLING', 'RESTARTING']

const formatVersion = (version: VersionInfo | null) => {
    if (!version) return "unknown (development build)"
    const date = version.commit_date ? new Date(version.commit_date).toLocaleString() : null
    return [version.name, date].filter(Boolean).join(" · ")
}

export const UpdatePanel = () => {
    const [ status, setStatus ] = useState<UpdateStatus | null>(null)
    const [ error, setError ] = useState<string | null>(null)
    const [ showLog, setShowLog ] = useState<boolean>(false)
    // Commit we are updating to. Set while waiting for the server to come back after the restart.
    const [ waitingFor, setWaitingFor ] = useState<string | null>(null)
    const pollTimer = useRef<number | null>(null)

    const fetchStatus = () => axios.get<UpdateStatus>('/api/update/status').then(response => {
        setStatus(response.data)
        return response.data
    })

    useEffect(() => {
        fetchStatus().catch(() => setError("Could not load the update status."))
        return () => { if (pollTimer.current) window.clearTimeout(pollTimer.current) }
    }, [])

    // Poll while an update is running and while the server restarts
    useEffect(() => {
        const busy = status !== null && BUSY_STATES.includes(status.state) && status.state !== 'CHECKING'
        if (!busy && !waitingFor) return

        pollTimer.current = window.setTimeout(() => {
            fetchStatus()
            .then(newStatus => {
                if (waitingFor && newStatus.current?.commit === waitingFor) {
                    // New version is up. Reload so the browser gets the new frontend too.
                    window.location.reload()
                }
                if (waitingFor && newStatus.state === 'ERROR') {
                    setWaitingFor(null) // install failed before the restart
                }
                if (waitingFor && newStatus.state === 'IDLE' && newStatus.last_result && !newStatus.last_result.success) {
                    setWaitingFor(null) // new version didn't start and was rolled back
                }
            })
            .catch(() => { /* server is restarting, keep polling */ setStatus(s => s ? { ...s } : s) })
        }, 2000)

        return () => { if (pollTimer.current) window.clearTimeout(pollTimer.current) }
    }, [status, waitingFor])

    const checkForUpdate = () => {
        setError(null)
        setStatus(s => s ? { ...s, state: 'CHECKING' } : s)
        axios.post<UpdateStatus>('/api/update/check')
        .then(response => setStatus(response.data))
        .catch(() => { setError("Update check failed."); fetchStatus() })
    }

    const installUpdate = () => {
        if (!status?.latest) return
        if (!window.confirm(`Install ${status.latest.name}? The server restarts afterwards and playback is interrupted for a moment.`)) return

        setError(null)
        axios.post<UpdateStatus>('/api/update/install')
        .then(response => {
            setStatus(response.data)
            setWaitingFor(response.data.latest?.commit ?? null)
            setShowLog(true)
        })
        .catch(e => setError(e.response?.data?.detail ?? "Could not start the update."))
    }

    if (!status) {
        return <div className="updatePanel"><p className="updateHint">{error ?? "Loading…"}</p></div>
    }

    const busy = BUSY_STATES.includes(status.state) || waitingFor !== null

    return (
        <div className="updatePanel">
            <dl className="updateVersions">
                <dt>Installed</dt>
                <dd>{formatVersion(status.current)}</dd>
                { status.latest && <>
                    <dt>Latest</dt>
                    <dd>
                        {formatVersion(status.latest)}
                        { status.latest.message && <span className="updateCommitMessage">{status.latest.message}</span> }
                    </dd>
                </> }
            </dl>

            { !status.supported
                ? <p className="updateHint">{status.unsupported_reason}</p>
                : <>
                    { status.last_checked && !status.update_available && status.state !== 'ERROR' && !busy &&
                        <p className="updateHint">You're up to date.</p> }

                    { (busy || status.state === 'ERROR') && status.message &&
                        <p className={status.state === 'ERROR' ? "updateError" : "updateProgress"}>{status.message}</p> }

                    { status.last_result && !busy &&
                        <p className={status.last_result.success ? "updateHint" : "updateError"}>
                            Last update ({new Date(status.last_result.at * 1000).toLocaleString()}): {status.last_result.message}
                        </p> }

                    { error && <p className="updateError">{error}</p> }

                    <div className="updateButtons">
                        <button className="btn" onClick={checkForUpdate} disabled={busy}>
                            { status.state === 'CHECKING' ? "Checking…" : "Check for updates" }
                        </button>
                        { status.update_available &&
                            <button className="btn btn-primary" onClick={installUpdate} disabled={busy}>
                                { busy ? "Updating…" : "Install update" }
                            </button> }
                        { status.log.length > 0 &&
                            <button className="btn btn-ghost" onClick={() => setShowLog(!showLog)}>{ showLog ? "Hide details" : "Show details" }</button> }
                    </div>

                    { showLog && status.log.length > 0 && <pre className="updateLog">{status.log.join("\n")}</pre> }
                </>
            }
        </div>
    )
}
