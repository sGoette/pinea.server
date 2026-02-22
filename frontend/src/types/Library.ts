export enum LibraryType {
    MOVIES = 'MOVIES',
    SERIES = 'SERIES',
    VIDEOS = 'VIDEOS'
}

export type Library = {
    id: number
    name: string
    media_folder: string
    type: LibraryType
}