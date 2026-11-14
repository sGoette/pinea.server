export type VersionInfo = {
    name: string
    commit: string | null
    commit_date: string | null
    message: string | null
    built_at: string | null
}

export type UpdateState = 'IDLE' | 'CHECKING' | 'DOWNLOADING' | 'INSTALLING' | 'RESTARTING' | 'ERROR'

export type UpdateResult = {
    success: boolean
    version: string | null
    message: string
    at: number
}

export type UpdateStatus = {
    supported: boolean
    unsupported_reason: string | null
    current: VersionInfo | null
    latest: VersionInfo | null
    update_available: boolean
    last_checked: number | null
    state: UpdateState
    message: string | null
    log: string[]
    last_result: UpdateResult | null
}
