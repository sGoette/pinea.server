# Feature ideas

Ideas for after v1, sorted by rating. Concrete open issues are in [BACKLOG.md](BACKLOG.md).

★ = next up, ○ = later, – = probably not worth it for a home network server

| Rating | Feature | Notes |
|---|---|---|
| ★ | Resume playback | Store the playback position on the server, so it syncs between the Apple TV and the web UI. Today neither server nor client store anything per viewer. |
| ★ | Watched / unwatched | Mark titles as watched (automatically near the end, or by hand), checkmark on cards. |
| ★ | Continue watching | Row with started titles and the next episode of series in progress. |
| ★ | Autoplay next episode | Also across seasons, with a short "up next" screen at the end of an episode. |
| ★ | Play any container on tvOS | AVPlayer only plays mp4/mov/m4v and HLS, so mkv files don't play. Repackage on the fly into HLS with `ffmpeg -c copy` (no re-encoding, cheap). Real transcoding (unsupported codecs) is a separate, bigger step. |
| ★ | Audio and subtitle track selection | Comes almost for free with HLS (the native track menu of the player). |
| ★ | External subtitles | `.srt` / `.ass` files next to the video, served as WebVTT in the HLS playlist. The scanner ignores them today. |
| ★ | Richer metadata | Plot summary, tagline, genres, rating, age rating. The scraper can deliver them, the schema has no columns yet (change `SCHEMA` + `scripts/migrate-data.py`). |
| ★ | Automatic scans | Scan when files change and/or on a schedule. Today scans only start by hand or when a library is created. |
| ★ | Skip intro / skip credits | Detect credits by analysing the video, intros by matching the audio of the episodes of a season. Button in the player. |
| ○ | Scrubbing thumbnails | Preview images while seeking, generated with ffmpeg at scan time. |
| ○ | Chapters | ffprobe already reads them: store, expose in the API, jump to them in the player. |
| ○ | Frame rate and dynamic range matching | tvOS switches the display mode to the video's frame rate and HDR / Dolby Vision (`AVDisplayCriteria`). |
| ○ | Multiple versions of a title | 4K and 1080p, or different cuts, as one title. Pick the version when playing. |
| ○ | tvOS Top Shelf | Continue watching on the Apple TV home screen. |
| ○ | Hide from "Recently added" | Remove single titles from the list. |
| ○ | Background art and title logos | For detail pages, from the scraper. |
| ○ | Sorting and filtering | Genre, year, resolution, combined filters, a letter index, a sort order per library, a separate sort title. |
| ○ | Playlists and watchlist | Including smart playlists (e.g. all titles with one person). |
| ○ | More details for people and seasons | Person bios, season posters and summaries. |
| ○ | Local metadata files | Read `.nfo` files next to the media, as one more scraper. |
| ○ | Scan a single folder by API | Lets download tools trigger a scan as soon as a new file arrives. |
| ○ | Dashboard | What's playing right now, playback history, library stats. |
| ○ | Database backups | Automatic, with a few versions kept. |
| ○ | Household profiles | One profile per person, each with their own watch state. No passwords. |
| ○ | Kids profile | Age limit per profile. Needs age ratings from the metadata. |
| ○ | Sync watch history with external services | Needs watch state first. |
| – | Voice search and smart home scenes | Siri search and seeking, light scenes on play / pause. |
| – | Remote playback | Playback outside the home network: needs logins, bandwidth limits, quality settings, pre-converted versions. |
| – | Sharing with other households | Logins and access rights per library. |
| – | Live TV / DVR | Needs a TV tuner. |
| – | Watching together | Synced playback across locations. |
| – | Offline downloads | Only useful for mobile clients. |
| – | Music and photo libraries | |
