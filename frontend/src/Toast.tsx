import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react"
import './Toast.css'

const ToastContext = createContext<(message: string) => void>(() => {})

export const useToast = () => useContext(ToastContext)

export const ToastProvider = (props: { children: ReactNode }) => {
    const [ message, setMessage ] = useState<string | null>(null)
    const timer = useRef<number | null>(null)

    const showToast = useCallback((newMessage: string) => {
        setMessage(newMessage)
        if (timer.current) window.clearTimeout(timer.current)
        timer.current = window.setTimeout(() => setMessage(null), 3500)
    }, [])

    return (
        <ToastContext.Provider value={showToast}>
            {props.children}
            <div className="toastRegion" aria-live="polite">
                { message && <div className="toast" key={message}>{message}</div> }
            </div>
        </ToastContext.Provider>
    )
}
