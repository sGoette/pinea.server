import React, { useEffect, type ReactNode } from "react"
import ChevronLeftRoundedIcon from '@mui/icons-material/ChevronLeftRounded'
import './DetailPage.css'

/** Frame of a detail page: back button and (like tvOS) a faint tint from the poster behind everything. */
export const DetailPage = (props: { onBack: () => void, tintImage?: string | null, children: ReactNode }) => {
    useEffect(() => { window.scrollTo(0, 0) }, [])

    return (
        <div className="detailPage">
            { props.tintImage && <div className="detailTint" aria-hidden="true" style={{ backgroundImage: `url("${props.tintImage}")` }} key={props.tintImage} /> }
            <button className="btn btn-ghost detailBack" onClick={props.onBack}><ChevronLeftRoundedIcon /> Back</button>
            {props.children}
        </div>
    )
}

/** tvOS ItemHeaderView: big artwork on the left, text column aligned to its bottom edge.
 *  The artwork keeps its own aspect ratio (portrait or landscape): fixed height, natural width.
 *  `landscape` only sets the shape of the placeholder when there is no image. */
export const DetailHeader = (props: {
    image: string | null
    landscape?: boolean
    placeholderIcon: ReactNode
    eyebrow?: string | null
    title: string
    meta: (string | null)[]
    actions?: ReactNode
}) => {
    const meta = props.meta.filter(Boolean).join(" · ")
    return (
        <header className={`detailHeader${props.landscape ? " landscape" : ""}`}>
            <div className={`detailArt${props.image ? "" : " empty"}`}>
                { props.image ? <img src={props.image} alt="" /> : <div className="artPlaceholder">{props.placeholderIcon}</div> }
            </div>
            <div className="detailInfo">
                { props.eyebrow && <p className="detailEyebrow">{props.eyebrow}</p> }
                <h1>{props.title}</h1>
                { meta && <p className="detailMeta">{meta}</p> }
                { props.actions && <div className="detailActions">{props.actions}</div> }
            </div>
        </header>
    )
}
