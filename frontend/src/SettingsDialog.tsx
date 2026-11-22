import { useEffect, useState } from "react"
import axios from "axios"
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'
import { Dialog } from "./Dialog"
import { UpdatePanel } from "./UpdatePanel"
import type { Setting } from "./types/Setting"

const SETTING_INFO: Record<string, { label: string, hint: string }> = {
    SERVER_NAME: {
        label: "Server name",
        hint: "Shown in the tvOS app. Changes apply immediately. The web address stays the same (the machine's host name).",
    },
    MEDIA_ROOT_FOLDER: {
        label: "Media root folder",
        hint: "Absolute path under which all media folders are mounted. All libraries are relative to it.",
    },
}

export const SettingsDialog = (props: { onClose: () => void, scanAll: () => void, scanRunning: boolean }) => {
    const [ settings, setSettings ] = useState<Setting[] | null>(null)
    const [ saving, setSaving ] = useState<boolean>(false)
    const [ error, setError ] = useState<string | null>(null)

    useEffect(() => {
        axios.get<Setting[]>('/api/settings')
        .then(response => setSettings(response.data))
        .catch(() => setError("Could not load the settings."))
    }, [])

    const setValue = (key: string, value: string) =>
        setSettings(current => current?.map(setting => setting.key === key ? { ...setting, value } : setting) ?? null)

    const save = () => {
        if (!settings) return
        setSaving(true)
        axios.post('/api/settings', settings)
        .then(() => props.onClose())
        .catch(e => {
            setError(e.response?.data?.detail ?? "Could not save the settings.")
            setSaving(false)
        })
    }

    const valid = settings !== null && settings.every(setting => (setting.value ?? "").trim() !== "")

    return (
        <Dialog
            title="Settings"
            onClose={props.onClose}
            width={600}
            footer={<>
                <button className="btn btn-ghost" onClick={props.onClose}>Cancel</button>
                <button className="btn btn-primary" onClick={save} disabled={!valid || saving}>Save</button>
            </>}
        >
            {
                settings?.map(setting => {
                    const info = SETTING_INFO[setting.key]
                    return (
                        <div className="field" key={setting.key}>
                            <label htmlFor={`setting-${setting.key}`}>{info?.label ?? setting.key}</label>
                            <input id={`setting-${setting.key}`} type="text" value={setting.value ?? ""} onChange={event => setValue(setting.key, event.target.value)} />
                            { info && <span className="fieldHint">{info.hint}</span> }
                        </div>
                    )
                })
            }
            { error && <p className="formError">{error}</p> }

            <section className="dialogSection">
                <h3>Libraries</h3>
                <p className="fieldHint">Scans every library for new and removed media. Existing metadata is kept.</p>
                <div>
                    <button className="btn" onClick={props.scanAll} disabled={props.scanRunning}>
                        <RefreshRoundedIcon className={props.scanRunning ? "spinning" : ""} />
                        { props.scanRunning ? "Scanning…" : "Scan all libraries" }
                    </button>
                </div>
            </section>

            <section className="dialogSection">
                <h3>Server updates</h3>
                <UpdatePanel />
            </section>
        </Dialog>
    )
}
