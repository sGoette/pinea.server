import { Fragment, useLayoutEffect, useRef, useState, type Key, type ReactNode } from "react"
import { useVisibleWindow } from "./useVisibleWindow"

/**
 * A CSS grid (`className`, e.g. mediaGrid / personGrid) that only renders the rows near the viewport.
 * Libraries have thousands of titles: rendering every card makes layout, paint and hover slow.
 *
 * The CSS stays in charge of the layout. After rendering, the column count is read from the grid's
 * computed `grid-template-columns` and the row height from the first card, so the virtual rows match
 * the real ones exactly. All rows must have the same height (cards with a fixed aspect ratio / size).
 */
export const VirtualGrid = <T,>(props: {
    items: T[]
    getKey: (item: T) => Key
    renderItem: (item: T) => ReactNode
    className: string
}) => {
    const outer = useRef<HTMLDivElement>(null)
    const grid = useRef<HTMLDivElement>(null)
    const visible = useVisibleWindow(outer)
    // Guesses until the first measurement (one frame): a typical desktop grid
    const [ metrics, setMetrics ] = useState({ columns: 6, rowHeight: 260, rowGap: 40 })

    useLayoutEffect(() => {
        const element = grid.current
        const first = element?.firstElementChild as HTMLElement | null
        if (!element || !first || element.offsetParent === null) return
        const style = getComputedStyle(element)
        const columns = Math.max(1, style.gridTemplateColumns.split(" ").filter(Boolean).length)
        const rowGap = parseFloat(style.rowGap) || 0
        const rowHeight = first.offsetHeight
        setMetrics(previous => previous.columns === columns && previous.rowHeight === rowHeight && previous.rowGap === rowGap
            ? previous
            : { columns, rowHeight, rowGap })
    })

    const { columns, rowHeight, rowGap } = metrics
    const pitch = rowHeight + rowGap
    const rows = Math.ceil(props.items.length / columns)
    const firstRow = Math.max(0, Math.floor(visible.top / pitch))
    const lastRow = Math.min(rows, Math.ceil(visible.bottom / pitch))
    const slice = props.items.slice(firstRow * columns, lastRow * columns)

    return (
        <div ref={outer} className="virtualGrid" style={{ height: Math.max(0, rows * pitch - rowGap) }}>
            <div ref={grid} className={props.className} style={{ top: firstRow * pitch }}>
                { slice.map(item => <Fragment key={props.getKey(item)}>{props.renderItem(item)}</Fragment>) }
            </div>
        </div>
    )
}
