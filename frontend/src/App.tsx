// src/App.tsx
import { createContext, useEffect, useState } from "react"
import { Routes, Route } from "react-router"
import useWebSocket from "react-use-websocket"
import { LibraryBrowser } from "./LibraryBrowser"
import { ToastProvider } from "./Toast"
import { NotificationType, type Notification } from "./types/NotificationType"

export const WebSocketContext = createContext({ timestamp: Date.now(), message: NotificationType.NONE })
const SOCKET_URL = __WSURL__

const App = () => {
    const [ websocketMessage, setWebsocketMessage ] = useState<{ timestamp: number, message: NotificationType }>({ timestamp: Date.now(), message: NotificationType.NONE })
    const { lastMessage } = useWebSocket(SOCKET_URL, { retryOnError: true, shouldReconnect: () => true })

    useEffect(() => {
        if (lastMessage !== null) {
            const newMessage = JSON.parse(lastMessage.data) as Notification
            setWebsocketMessage({ timestamp: Date.now(), message: newMessage.type })
        }
    }, [lastMessage])

    return (
        <WebSocketContext.Provider value={websocketMessage}>
            <ToastProvider>
                <Routes>
                    <Route path="*" element={<LibraryBrowser />} />
                </Routes>
            </ToastProvider>
        </WebSocketContext.Provider>
    )
}

export default App
