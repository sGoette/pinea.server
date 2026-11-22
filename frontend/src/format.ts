/** size "thumb": small cached version (max 800 × 600) for grids, rows and cast. Full size only for detail headers. */
export const posterUrl = (fileName: string | null, size?: "thumb") =>
    fileName ? `/api/poster/${encodeURIComponent(fileName)}${size ? `?size=${size}` : ""}` : null

export const formatDuration = (seconds: number | null): string | null => {
    if (!seconds || seconds <= 0) return null
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) return `${hours} h ${minutes} min`
    return `${minutes}:${secs.toString().padStart(2, "0")}`
}

// Dates are unix seconds (release_date is negative before 1970)
export const formatYear = (releaseDate: number | null): string | null => {
    if (releaseDate === null) return null
    return String(new Date(releaseDate * 1000).getUTCFullYear())
}

export const pluralize = (count: number, singular: string, plural: string = `${singular}s`) =>
    `${count.toLocaleString()} ${count === 1 ? singular : plural}`

export const formatDate = (releaseDate: number | null): string | null => {
    if (releaseDate === null) return null
    return new Date(releaseDate * 1000).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })
}

/** "4K", "1080p", "720p", ... Uses the width too, so cropped cinema formats (1920 × 800) count as 1080p. */
export const formatResolution = (width: number | null, height: number | null): string | null => {
    if (!width || !height) return null
    if (width >= 3800 || height >= 2100) return "4K"
    if (width >= 2500 || height >= 1400) return "1440p"
    if (width >= 1900 || height >= 1060) return "1080p"
    if (width >= 1260 || height >= 700) return "720p"
    return "SD"
}

/** "Season 2", "Specials" (season 0), "Other episodes" (no season) */
export const seasonLabel = (season: string | null): string => {
    if (season === null || season === "") return "Other episodes"
    if (/^0+$/.test(season)) return "Specials"
    return /^\d+$/.test(season) ? `Season ${Number(season)}` : season
}
