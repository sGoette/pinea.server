import { useLayoutEffect, useState, type RefObject } from "react"

/** Part of an element that is near the viewport, in px from the element's top edge. */
export type VisibleWindow = { top: number, bottom: number }

// Rounded to this step, so scrolling re-renders a list only every few hundred px, not every frame
const STEP = 300

/**
 * The window of `ref` that is visible (page scroll) plus `overscan` px above and below. Updates on
 * scroll and resize, at most once per frame. Stays unchanged while the element is hidden (e.g. the grid
 * behind a detail page), so hidden lists don't re-render.
 */
export const useVisibleWindow = (ref: RefObject<HTMLElement | null>, overscan: number = 800): VisibleWindow => {
    const [ visible, setVisible ] = useState<VisibleWindow>({ top: 0, bottom: window.innerHeight + overscan })

    // Layout effect: the first paint already shows the right rows (e.g. after a reload far down the page)
    useLayoutEffect(() => {
        const element = ref.current
        if (!element) return
        let frame: number | null = null

        const update = () => {
            frame = null
            if (element.offsetParent === null) return   // display: none
            const offset = -element.getBoundingClientRect().top
            const top = Math.floor((offset - overscan) / STEP) * STEP
            const bottom = Math.ceil((offset + window.innerHeight + overscan) / STEP) * STEP
            setVisible(previous => previous.top === top && previous.bottom === bottom ? previous : { top, bottom })
        }
        const schedule = () => { if (frame === null) frame = requestAnimationFrame(update) }

        update()
        window.addEventListener("scroll", schedule, { passive: true })
        window.addEventListener("resize", schedule)
        // Size changes (more items, shown again after a detail page) move what is visible too
        const observer = new ResizeObserver(schedule)
        observer.observe(element)
        return () => {
            window.removeEventListener("scroll", schedule)
            window.removeEventListener("resize", schedule)
            observer.disconnect()
            if (frame !== null) cancelAnimationFrame(frame)
        }
    }, [ref, overscan])

    return visible
}
