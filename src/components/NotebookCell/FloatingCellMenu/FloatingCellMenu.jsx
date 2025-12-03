import { Play, Trash, History, Sparkles, Repeat } from "lucide-react";
import styles from "./FloatingCellMenu.module.css";
import { forwardRef } from "react";

const FloatingCellMenu = forwardRef(function FloatingCellMenu(
  { focusCellCallback, borderColorCallback, removeBorderColorCallback }, ref
) {
  return (
    <div
      ref={ref}
      className={styles.menuWrapper}
      onClick={focusCellCallback}
      onMouseDown={borderColorCallback}
      onMouseUp={removeBorderColorCallback}
    >
      <div className={styles.menu} role="toolbar">
        <button className={styles.button}>
          <Play size={16} /> Run Cell
        </button>
        <button className={styles.button}>
          <Trash size={16} /> Delete cell
        </button>
        <button className={styles.button}>
          <Sparkles size={16} /> Explain with AI
        </button>
        <button className={styles.button}>
          <Repeat size={16} /> Refactor with AI
        </button>
        <button className={styles.button}>
          <History size={16} /> Cell version control
        </button>
      </div>
    </div>
  );
});

export default FloatingCellMenu;
