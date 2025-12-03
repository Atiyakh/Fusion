import styles from "./TitleBar.module.css";

export default function CellTitle({ cellTitle = "" }) {
    return (
        <div className="cell-title">
            <p className={styles.cellTitleText}><strong>{cellTitle}</strong></p>
        </div>
    )
}
