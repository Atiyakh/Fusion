import CollapseButton from "./CollapseButton.jsx";
import CellTitle from "./CellTitle.jsx";
import styles from "./TitleBar.module.css";

export default function TitleBar({ cellTitle = "New NotebookCell" }) {
    // title bar implementation goes here...
    return (
        <div className={styles.cellTitleBar} tabIndex="0">
            <CellTitle tabIndex="0" cellTitle={cellTitle} />
            <CollapseButton tabIndex="0" />
            <div style={{ flexGrow: 1 }} tabIndex="0" ></div>
            <div className={styles.cellControlsContainer} tabIndex="0" >
                <span className={styles.inputCountDisplay} tabIndex="0" >[12]</span>
            </div>
        </div>
    )
}
