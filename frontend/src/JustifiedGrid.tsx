import React, { useCallback, useLayoutEffect, useMemo, useRef, useState, type Key, type ReactNode } from "react"
import './JustifiedGrid.css'

// Aspect ratios (width / height) of images, measured when they load. Kept for the session, so
// coming back to a library doesn't reflow again.
const ratioCache = new Map<string, number>()

// Two base formats (design/DESIGN.md): portrait like movie posters, or 16:9 like video frames.
// Every image is snapped to the closer one; in a row the cards then stretch a bit to fill it.
export const PORTRAIT_RATIO = 0.6748
export const LANDSCAPE_RATIO = 16 / 9

const snapRatio = (ratio: number) => ratio < 1 ? PORTRAIT_RATIO : LANDSCAPE_RATIO

/** Card height, gap between cards and gap between rows for a container width. The row gap is
 *  larger, so rows read as rows (and the hover label has room). */
const metrics = (width: number) => {
    if (width < 600) return { rowHeight: 150, gap: 10, rowGap: 28 }
    if (width < 1100) return { rowHeight: 200, gap: 12, rowGap: 36 }
    return { rowHeight: 240, gap: 14, rowGap: 40 }
}

type Box = { left: number, top: number, width: number, height: number }

/** Rows like an image search: fixed height, fixed gaps, the card widths flex. A row ends with or
 *  without the next card, whichever needs less stretching/squeezing of the cards to fill the width
 *  exactly. Images are cropped into their card. The last row keeps the base widths, left-aligned. */
const computeLayout = (ratios: number[], width: number, rowHeight: number, gap: number, rowGap: number): { boxes: Box[], height: number } => {
    const boxes: Box[] = []
    let top = 0
    let start = 0
    let rowWidth = 0      // base card widths of the current row, without gaps

    const placeRow = (end: number, isLast: boolean) => {
        const gaps = gap * (end - start - 1)
        const scale = isLast ? Math.min(1, (width - gaps) / rowWidth) : (width - gaps) / rowWidth
        let left = 0
        for (let i = start; i < end; i++) {
            const itemWidth = Math.min(width, ratios[i]! * rowHeight * scale)
            boxes.push({ left, top, width: itemWidth, height: rowHeight })
            left += itemWidth + gap
        }
        top += rowHeight + rowGap
        start = end
        rowWidth = 0
    }

    for (let i = 0; i < ratios.length; i++) {
        const itemWidth = ratios[i]! * rowHeight
        const space = width - gap * (i - start)          // room for card widths if card i joins the row
        if (i > start && rowWidth + itemWidth > space) {
            // With card i the cards get squeezed by `squeeze`, without it stretched by `stretch`
            const squeeze = (rowWidth + itemWidth) / space
            const stretch = (space + gap) / rowWidth
            if (stretch <= squeeze) {
                placeRow(i, false)       // card i starts the next row
            } else {
                rowWidth += itemWidth
                placeRow(i + 1, false)
                continue
            }
        }
        rowWidth += itemWidth
    }
    if (start < ratios.length) placeRow(ratios.length, true)

    return { boxes, height: Math.max(0, top - rowGap) }
}

/**
 * Rows of equal height that fill the full width (like an image search). Every card starts as portrait
 * or 16:9, whichever is closer to its image, and its width flexes a bit so the row fills exactly.
 * Items are positioned absolutely and keep their React key, so a reflow (resize, an image's real
 * size becoming known) never remounts them.
 */
export const JustifiedGrid = <T,>(props: {
    items: T[]
    getKey: (item: T) => Key
    getImage: (item: T) => string | null
    defaultRatio: number                                     // until an image has loaded, and for items without one
    renderItem: (item: T, onImageRatio: (ratio: number) => void) => ReactNode
}) => {
    const container = useRef<HTMLDivElement>(null)
    const [ width, setWidth ] = useState(0)
    const [ ratioVersion, setRatioVersion ] = useState(0)
    const frame = useRef<number | null>(null)

    useLayoutEffect(() => {
        const element = container.current
        if (!element) return
        setWidth(element.getBoundingClientRect().width)
        const observer = new ResizeObserver(entries => setWidth(entries[0]!.contentRect.width))
        observer.observe(element)
        return () => {
            observer.disconnect()
            if (frame.current) cancelAnimationFrame(frame.current)
        }
    }, [])

    // Many images load at once: reflow at most once per frame
    const reportRatio = useCallback((image: string | null, ratio: number) => {
        if (!image || !Number.isFinite(ratio) || ratio <= 0) return
        const previous = ratioCache.get(image)
        ratioCache.set(image, ratio)
        // Only a change of the format (portrait <-> landscape) moves cards
        if (previous !== undefined && snapRatio(previous) === snapRatio(ratio)) return
        if (frame.current === null) {
            frame.current = requestAnimationFrame(() => {
                frame.current = null
                setRatioVersion(version => version + 1)
            })
        }
    }, [])

    const { getImage, defaultRatio } = props
    const layout = useMemo(() => {
        if (width <= 0) return { boxes: [], height: 0 }
        const ratios = props.items.map(item => snapRatio(ratioCache.get(getImage(item) ?? "") ?? defaultRatio))
        const { rowHeight, gap, rowGap } = metrics(width)
        return computeLayout(ratios, width, rowHeight, gap, rowGap)
    // ratioVersion: recompute when measured ratios changed
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [props.items, width, ratioVersion, getImage, defaultRatio])

    return (
        <div ref={container} className="justifiedGrid" style={{ height: layout.height }}>
            {
                layout.boxes.length === props.items.length &&
                props.items.map((item, index) => {
                    const box = layout.boxes[index]!
                    const image = getImage(item)
                    return (
                        <div key={props.getKey(item)} className="justifiedItem" style={{ left: box.left, top: box.top, width: box.width, height: box.height }}>
                            {props.renderItem(item, ratio => reportRatio(image, ratio))}
                        </div>
                    )
                })
            }
        </div>
    )
}
