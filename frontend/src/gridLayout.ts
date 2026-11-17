import { LibraryType } from "./types/Library"

/**
 * "grid":      fixed columns, every poster cropped to the library's card ratio.
 * "justified": rows of equal height that fill the full width, every poster in its own aspect ratio
 *              (good for libraries with mixed portrait and landscape posters).
 */
export type GridLayout = "grid" | "justified"

/** Layout per library type. Roll the justified layout out (or back) here. */
export const GRID_LAYOUT: Record<LibraryType, GridLayout> = {
    [LibraryType.MOVIES]: "justified",
    [LibraryType.SERIES]: "justified",
    [LibraryType.VIDEOS]: "justified",
}

/** `override` comes from the URL (?layout=grid|justified) to compare both on any library. */
export const gridLayoutFor = (type: LibraryType | undefined, override: string | null): GridLayout => {
    if (override === "grid" || override === "justified") return override
    return type ? GRID_LAYOUT[type] : "grid"
}
