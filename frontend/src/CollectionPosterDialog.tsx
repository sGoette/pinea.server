import React, { useEffect, useRef, useState } from "react"
import axios from "axios"
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined'
import FileUploadOutlinedIcon from '@mui/icons-material/FileUploadOutlined'
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded'
import { Dialog } from "./Dialog"
import type { Collection } from "./types/Collection"
import { posterUrl } from "./format"
import './CollectionPosterDialog.css'

const MAX_BYTES = 25 * 1024 * 1024  // same limit as the server

/** Change or remove the poster of a collection. A new image is previewed first and uploaded on "Save". */
export const CollectionPosterDialog = (props: { collection: Collection, onClose: () => void, onSaved: () => void }) => {
    const [ file, setFile ] = useState<File | null>(null)
    const [ preview, setPreview ] = useState<string | null>(null)
    const [ dragging, setDragging ] = useState<boolean>(false)
    const [ busy, setBusy ] = useState<boolean>(false)
    const [ error, setError ] = useState<string | null>(null)
    const input = useRef<HTMLInputElement>(null)

    useEffect(() => {
        if (!file) return setPreview(null)
        const url = URL.createObjectURL(file)
        setPreview(url)
        return () => URL.revokeObjectURL(url)
    }, [file])

    const pick = (picked: File | undefined) => {
        if (!picked) return
        setError(null)
        if (!picked.type.startsWith("image/")) return setError("Please choose an image file.")
        if (picked.size > MAX_BYTES) return setError("The image is larger than 25 MB.")
        setFile(picked)
    }

    const run = (request: Promise<unknown>) => {
        setBusy(true)
        setError(null)
        request
        .then(() => {
            props.onSaved()
            props.onClose()
        })
        .catch(reason => {
            setError(axios.isAxiosError(reason) && typeof reason.response?.data?.detail === "string" ? reason.response.data.detail : "Could not save the poster.")
            setBusy(false)
        })
    }

    const save = () => {
        if (file) run(axios.put(`/api/collection/${props.collection.id}/poster`, file, { headers: { "Content-Type": file.type || "application/octet-stream" } }))
    }

    const remove = () => {
        if (!window.confirm(`Remove the poster of “${props.collection.title}”?\n\nThe next scan of its movies picks one again (folder image or scraper).`)) return
        run(axios.delete(`/api/collection/${props.collection.id}/poster`))
    }

    const image = preview ?? posterUrl(props.collection.poster_file_name)

    return (
        <Dialog
            title="Collection poster"
            onClose={props.onClose}
            width={460}
            footer={<>
                {
                    props.collection.poster_file_name &&
                    <button className="btn btn-danger" onClick={remove} disabled={busy}><DeleteOutlineRoundedIcon /> Remove</button>
                }
                <span className="spacer" />
                <button className="btn btn-ghost" onClick={props.onClose}>Cancel</button>
                <button className="btn btn-primary" onClick={save} disabled={!file || busy}>{busy ? "Saving…" : "Save"}</button>
            </>}
        >
            <div className="posterPickerRow">
                <button
                    className={`posterDrop${dragging ? " dragging" : ""}`}
                    onClick={() => input.current?.click()}
                    onDragOver={event => { event.preventDefault(); setDragging(true) }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={event => { event.preventDefault(); setDragging(false); pick(event.dataTransfer.files[0]) }}
                    aria-label="Choose an image"
                >
                    { image ? <img src={image} alt="" /> : <span className="artPlaceholder"><FolderOutlinedIcon /></span> }
                </button>
                <div className="posterPickerText">
                    <h3>{props.collection.title}</h3>
                    <span className="fieldHint">Drop an image on the poster or choose one. Portrait images (2:3) fit best.</span>
                    <div>
                        <button className="btn" onClick={() => input.current?.click()} disabled={busy}><FileUploadOutlinedIcon /> Choose image…</button>
                    </div>
                    { file && <span className="fieldHint">New: {file.name}</span> }
                </div>
            </div>
            <input ref={input} type="file" accept="image/*" hidden onChange={event => { pick(event.target.files?.[0]); event.target.value = "" }} />
            { error && <p className="formError">{error}</p> }
        </Dialog>
    )
}
