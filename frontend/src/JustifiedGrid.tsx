import React, { useCallback, useLayoutEffect, useMemo, useRef, useState, type Key, type ReactNode } from "react"
import './JustifiedGrid.css'

// Aspect ratios (width / height) of images, measured when they load. Kept for the session, so
// coming back to a library doesn't reflow again.
const ratioCache = new Map<string, number>()

// Extreme formats would make rows look broken: clamp them (the image is cropped a bit then)
const MIN_RATIO = 0.5
const MAX_RATIO = 2.4

const clampRatio = (ratio: number) => Math.min(MAX_RATIO, Math.max(MIN_RATIO, ratio))

/** Target row height and gap for a container width. Rows end up this high or a bit lower. */
const metrics = (width: number) => {
    if (width < 600) return { rowHeight: 150, gap: 10 }
    if (width < 1100) return { rowHeight: 200, gap: 12 }
    return { rowHeight: 250, gap: 14 }
}

type Box = { left: number, top: number, width: number, height: number }

/** Justified layout: fill a row until it would be lower than `rowHeight` when scaled to the full
 *  width, then end it with or without the last item, whichever height is closer to `rowHeight`.
 *  The last row keeps the target height and is left-aligned. */
const computeLayout = (ratios: number[], width: number, rowHeight: number, gap: number): { boxes: Box[], height: number } => {
    const boxes: Box[] = []
    let top = 0
    let start = 0
    let ratioSum = 0

    const placeRow = (end: number, height: number) => {
        let left = 0
        for (let i = start; i < end; i++) {
            const itemWidth = ratios[i]! * height
            boxes.push({ left, top, width: itemWidth, height })
            left += itemWidth + gap
        }
        top += height + gap
        start = end
        ratioSum = 0
    }

    for (let i = 0; i < ratios.length; i++) {
        const ratio = ratios[i]!
        const height = (width - gap * (i - start)) / (ratioSum + ratio)
        if (height > rowHeight) {
            ratioSum += ratio
            continue
        }
        // With item i the row gets lower than the target, without it higher: take the closer one
        // (but don't let rows grow much above the target).
        const heightWithout = i > start ? (width - gap * (i - 1 - start)) / ratioSum : Infinity
        if (heightWithout - rowHeight < rowHeight - height && heightWithout <= rowHeight * 1.3) {
            placeRow(i, heightWithout)
            i--     // item i starts the next row
        } else {
            ratioSum += ratio
            placeRow(i + 1, height)
        }
    }
    if (start < ratios.length) {
        const gaps = gap * (ratios.length - 1 - start)
        placeRow(ratios.length, Math.min(rowHeight, (width - gaps) / ratioSum))
    }

    return { boxes, height: Math.max(0, top - gap) }
}

/**
 * Rows of equal height that fill the full width, every item in its image's own aspect ratio.
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
        if (previous !== undefined && Math.abs(previous - ratio) < 0.005) return
        ratioCache.set(image, ratio)
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
        const ratios = props.items.map(item => clampRatio(ratioCache.get(getImage(item) ?? "") ?? defaultRatio))
        const { rowHeight, gap } = metrics(width)
        return computeLayout(ratios, width, rowHeight, gap)
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
