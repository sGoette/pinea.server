import { useEffect, type ReactNode } from "react"
import CloseRoundedIcon from '@mui/icons-material/CloseRounded'
import './Dialog.css'

export const Dialog = (props: {
    title: string
    onClose: () => void
    children: ReactNode
    footer?: ReactNode
    width?: number
}) => {
    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") props.onClose()
        }
        window.addEventListener("keydown", onKeyDown)
        const previousOverflow = document.body.style.overflow
        document.body.style.overflow = "hidden"
        return () => {
            window.removeEventListener("keydown", onKeyDown)
            document.body.style.overflow = previousOverflow
        }
    }, [props.onClose])

    return (
        <div className="dialogBackdrop" onMouseDown={event => { if (event.target === event.currentTarget) props.onClose() }}>
            <div className="dialog" role="dialog" aria-modal="true" aria-label={props.title} style={{ maxWidth: props.width ?? 560 }}>
                <header className="dialogHeader">
                    <h2>{props.title}</h2>
                    <button className="iconButton" onClick={props.onClose} aria-label="Close"><CloseRoundedIcon /></button>
                </header>
                <div className="dialogBody">{props.children}</div>
                { props.footer && <footer className="dialogFooter">{props.footer}</footer> }
            </div>
        </div>
    )
}
