import { useCallback, useEffect, useRef, useState } from "react"
import axios from "axios"

export type ScanStatus = {
    running: boolean
    pending_jobs: number
    library_id: number | null
    movie_id: number | null
}

const IDLE: ScanStatus = { running: false, pending_jobs: 0, library_id: null, movie_id: null }

/** Scan state of the server. Polls /api/scan/status while a scan is running. */
export const useScanStatus = () => {
    const [ status, setStatus ] = useState<ScanStatus>(IDLE)
    const timer = useRef<number | null>(null)

    const poll = useCallback(() => {
        if (timer.current) window.clearTimeout(timer.current)
        axios.get<ScanStatus>('/api/scan/status')
        .then(response => {
            setStatus(response.data)
            if (response.data.running) timer.current = window.setTimeout(poll, 2000)
        })
        .catch(() => setStatus(IDLE))
    }, [])

    useEffect(() => {
        poll()
        return () => { if (timer.current) window.clearTimeout(timer.current) }
    }, [poll])

    const startScan = useCallback((params: { library_id?: number, movie_id?: number, reset_metadata?: boolean, config_folder?: string }) => {
        setStatus(s => ({ ...s, running: true, pending_jobs: s.pending_jobs + 1 }))
        return axios.post('/api/scan/start', null, { params }).then(() => poll())
    }, [poll])

    return { status, startScan, refresh: poll }
}
