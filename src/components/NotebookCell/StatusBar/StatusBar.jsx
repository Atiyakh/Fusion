import styles from "./StatusBar.module.css";

export default function StatusBar() {
    // title bar implementation goes here...
    return (
        <div className={styles.cellStatusBar} tabIndex="0" >
            {/* <QuickCellStats />
            <div style={{ flexGrow: 1 }}></div> */}
        </div>
    )
}
