/** Content of a __pinea.json (missing keys have their defaults). */
export type FolderCollectionConfig = {
    subfoldersAreCollections: boolean
    subfoldersArePeople: boolean
    folderPeople: string[]
    useScraper: boolean
    potential_collections: string[]
    folder_is_collection: boolean
}

/** A __pinea.json that decides how files of a library are scanned (GET /api/library/{id}/configs). */
export type LibraryFolderConfig = {
    folder: string              // relative to the media root ("" = media root)
    above_library: boolean
    config: FolderCollectionConfig | null
    error: string | null
    has_scraper_file: boolean
}
