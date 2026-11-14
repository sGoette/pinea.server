export const posterUrl = (fileName: string | null) => fileName ? `/api/poster/${encodeURIComponent(fileName)}` : null

export const formatDuration = (seconds: number | null): string | null => {
    if (!seconds || seconds <= 0) return null
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) return `${hours} h ${minutes} min`
    return `${minutes}:${secs.toString().padStart(2, "0")}`
}

// release_date is stored as unix seconds, older data may contain a plain year
export const formatYear = (releaseDate: number | null): string | null => {
    if (!releaseDate) return null
    if (releaseDate < 10000) return String(releaseDate)
    return String(new Date(releaseDate * 1000).getFullYear())
}

export const pluralize = (count: number, singular: string, plural: string = `${singular}s`) =>
    `${count.toLocaleString()} ${count === 1 ? singular : plural}`
