// src/App.tsx
import React, { useEffect, useState } from "react"
import { Routes, Route } from "react-router"
import { MovieOverview } from "./MovieOverview"
import { MoviePlayer } from "./MoviePlayer"
import useWebSocket from "react-use-websocket"
import { NotificationType, type Notification } from "./types/NotificationType"

export const WebSocketContext= React.createContext({timestamp: Date.now(), message: NotificationType.NONE})
const SOCKET_URL = __WSURL__

const App = () => {
  const [ websocketMessage, setWebsocketMessage ] = useState<{timestamp: number, message: NotificationType}>({timestamp: Date.now(), message: NotificationType.NONE})
  const { sendMessage, lastMessage, readyState } = useWebSocket(SOCKET_URL, { retryOnError: true, shouldReconnect: (closeEvent) => { return true } })

  useEffect(() => {
    if(lastMessage !== null) {
      const newMessage = JSON.parse(lastMessage.data) as Notification
      setWebsocketMessage({ timestamp: Date.now(), message: newMessage.type })
    }
  }, [lastMessage])
  
  return (
    <WebSocketContext.Provider value={websocketMessage}>
      <Routes>
        <Route index path="" element={<MovieOverview />} />
        <Route path="player/:movieId" element={<MoviePlayer />} />
      </Routes>
    </WebSocketContext.Provider>
  )
}

export default App