import React, { useEffect, useState } from "react"
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined'
import FolderOpenOutlinedIcon from '@mui/icons-material/FolderOpenOutlined'
import axios from "axios"

import './Folder.css'
import type { FolderEntry } from "./types/FolderEntry"

/** One row of the folder tree in the library dialog. Loads its subfolders when opened. */
export const Folder = (props: { name: string, path: string, libraryMediaFolder: string, setLibraryMediaFolder: (path: string) => void }) => {
    const [ subFolders, setSubFolders ] = useState<FolderEntry[]>([])
    const [ open, setOpen ] = useState<boolean>(false)

    const fetchSubFolders = () => {
        axios.get('/api/filesystem/list', { params: { current_directory: props.path } })
        .then(response => {
            setSubFolders(response.data.entries as FolderEntry[])
            setOpen(true)
        })
        .catch(() => setSubFolders([]))
    }

    const select = () => {
        props.setLibraryMediaFolder(props.path)
        if (!open) fetchSubFolders()
        else if (props.path === props.libraryMediaFolder) setOpen(false)
    }

    // Open the tree down to the currently selected folder
    useEffect(() => {
        const isAncestor = props.path === "" || props.libraryMediaFolder === props.path || props.libraryMediaFolder.startsWith(props.path + "/")
        if (isAncestor) fetchSubFolders()
    }, [])

    const selected = props.path === props.libraryMediaFolder

    return (
        <div className="folder">
            <button type="button" className={`folderRow${selected ? " selected" : ""}`} onClick={select}>
                { open && subFolders.length > 0 ? <FolderOpenOutlinedIcon /> : <FolderOutlinedIcon /> }
                <span>{props.name}</span>
            </button>
            {
                open && subFolders.length > 0 && (
                    <div className="folderChildren">
                        { subFolders.map(folder => <Folder key={folder.path} name={folder.name} path={folder.path} libraryMediaFolder={props.libraryMediaFolder} setLibraryMediaFolder={props.setLibraryMediaFolder} />) }
                    </div>
                )
            }
        </div>
    )
}
