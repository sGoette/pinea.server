import React, { useContext, useEffect, useState } from "react"
import MovieCard from "./MovieCard"
import type { Movie } from "./types/Movie"
import axios from "axios"
import { WebSocketContext } from "./App"
import { NotificationType } from "./types/NotificationType"

const MovieList = (props: { currentLibraryId: number | null}) => {
    const [ movies, setMovies ] = useState<Movie[]>([])
    const websocketMessage = useContext(WebSocketContext)

    const fetchMovies = () => {
        if(props.currentLibraryId) {
            axios.get(`/api/movies/${props.currentLibraryId}`)
            .then(response => {
                if (response.status === 200) {
                    setMovies(response.data)
                }
            })
        }
    }

    useEffect(() => {
        fetchMovies()
    }, [props.currentLibraryId])

    useEffect(() => {
            switch(websocketMessage.message) {
                case NotificationType.MOVIES_UPDATED: 
                    fetchMovies()
                    break
            }
        }, [websocketMessage])

    return (
        <>
        { 
            movies.map(movie => {
                return (
                    <MovieCard movie={movie} key={movie.id} />
                )
            })
        }
        </>
    )
}

export default MovieList