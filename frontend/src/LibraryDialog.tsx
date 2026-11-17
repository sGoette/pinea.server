import React, { useEffect, useState } from "react"
import axios from "axios"
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import RestartAltRoundedIcon from '@mui/icons-material/RestartAltRounded'
import { Dialog } from "./Dialog"
import { Folder } from "./Folder"
import { LibraryType, type Library } from "./types/Library"

const TYPE_LABELS: Record<LibraryType, string> = {
    [LibraryType.MOVIES]: "Movies",
    [LibraryType.SERIES]: "Series",
    [LibraryType.VIDEOS]: "Videos (home videos, clips)",
}

export const LibraryDialog = (props: { libraryId: number | null, onClose: () => void, onSaved: (libraryId: number | null) => void, onRebuild: (libraryId: number) => Promise<void>, scanRunning: boolean }) => {
    const isNew = props.libraryId === null
    const [ name, setName ] = useState<string>("")
    const [ type, setType ] = useState<LibraryType>(LibraryType.MOVIES)
    const [ mediaFolder, setMediaFolder ] = useState<string>("")
    const [ loaded, setLoaded ] = useState<boolean>(isNew)
    const [ busy, setBusy ] = useState<boolean>(false)
    const [ error, setError ] = useState<string | null>(null)

    useEffect(() => {
        if (isNew) return
        axios.get<Library>(`/api/library/${props.libraryId}`)
        .then(response => {
            setName(response.data.name)
            setType(response.data.type)
            setMediaFolder(response.data.media_folder)
            setLoaded(true)
        })
        .catch(() => setError("Could not load the library."))
    }, [props.libraryId, isNew])

    const save = () => {
        setBusy(true)
        setError(null)
        const payload = { id: props.libraryId, name: name.trim(), media_folder: mediaFolder, type }
        const request = isNew ? axios.put<Library>('/api/library', payload) : axios.post<Library>('/api/library', payload)
        request
        .then(response => {
            props.onSaved(response.data.id)
            props.onClose()
        })
        .catch(() => {
            setError("Could not save the library. Is this folder already used by another library?")
            setBusy(false)
        })
    }

    const remove = () => {
        if (!window.confirm(`Delete the library “${name}”?\n\nYour media files are not touched. Only the library and its metadata in pinea are removed.`)) return
        setBusy(true)
        axios.delete(`/api/library/${props.libraryId}`)
        .then(() => {
            props.onSaved(null)
            props.onClose()
        })
        .catch(() => {
            setError("Could not delete the library.")
            setBusy(false)
        })
    }

    const rebuild = () => {
        if (props.libraryId === null) return
        if (!window.confirm(
            `Rebuild the metadata of “${name}”?\n\n` +
            "Titles, posters, release dates, people, collections and series of this library are removed " +
            "and fetched again with the current scraper and folder configs. Titles you picked with “Find match” are searched again.\n\n" +
            "Your media files are not touched. This can take a while for large libraries."
        )) return
        setBusy(true)
        props.onRebuild(props.libraryId)
        .then(() => props.onClose())
        .catch(() => {
            setError("Could not start the rebuild.")
            setBusy(false)
        })
    }

    const canSave = loaded && !busy && name.trim() !== "" && mediaFolder !== ""

    return (
        <Dialog
            title={isNew ? "Add library" : "Edit library"}
            onClose={props.onClose}
            footer={<>
                { !isNew && <button className="btn btn-danger" onClick={remove} disabled={busy || !loaded}><DeleteOutlineRoundedIcon /> Delete</button> }
                <span className="spacer" />
                <button className="btn btn-ghost" onClick={props.onClose}>Cancel</button>
                <button className="btn btn-primary" onClick={save} disabled={!canSave}>{isNew ? "Add library" : "Save"}</button>
            </>}
        >
            {
                loaded && <>
                    <div className="field">
                        <label htmlFor="libraryName">Name</label>
                        <input id="libraryName" type="text" value={name} onChange={event => setName(event.target.value)} autoFocus={isNew} placeholder="e.g. Movies" />
                    </div>

                    <div className="field">
                        <label htmlFor="libraryType">Type</label>
                        <select id="libraryType" value={type} onChange={event => setType(event.target.value as LibraryType)}>
                            { Object.values(LibraryType).map(value => <option key={value} value={value}>{TYPE_LABELS[value]}</option>) }
                        </select>
                    </div>

                    <div className="field">
                        <label>Folder</label>
                        <div className="folderPicker">
                            <Folder name="Media root" path="" libraryMediaFolder={mediaFolder} setLibraryMediaFolder={setMediaFolder} />
                        </div>
                        <span className="fieldHint">
                            { mediaFolder ? <>Selected: <code>{mediaFolder}</code></> : "Choose the folder that contains this library's media." }
                            { isNew && " A scan starts automatically after adding." }
                        </span>
                    </div>
                </>
            }
            {
                !isNew && loaded &&
                <section className="dialogSection">
                    <h3>Rebuild metadata</h3>
                    <span className="fieldHint">
                        Removes all titles, posters, people and collections of this library and scans it again from scratch,
                        e.g. after switching to another scraper. The library and your files stay.
                    </span>
                    <div>
                        <button className="btn" onClick={rebuild} disabled={busy || props.scanRunning} title={props.scanRunning ? "Wait until the current scan has finished" : undefined}>
                            <RestartAltRoundedIcon /> Rebuild metadata
                        </button>
                    </div>
                </section>
            }
            { error && <p className="formError">{error}</p> }
        </Dialog>
    )
}
