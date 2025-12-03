import { useEffect, useLayoutEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { useCellAreaContext } from "../../contexts/CellAreaContext";
import { Plus, FileText, Database, Menu, Zap, DatabaseZap, Server, Terminal } from "lucide-react";
import styles from "./NotebookCellToolBar.module.css";

export default function FloatingCellToolbar({
  cellId,
  onInsertCode = () => {},
  onInsertMarkdown = () => {},
  onInsertSQL = () => {},
  onAI = () => {},
  onAddToDAG = () => {},
  onInlineDBToPandas = () => {},
  onLaunchTerminal = () => {},
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState(null); // { top, left, width, height }
  const [placement, setPlacement] = useState("above"); // "above" | "below"
  const advRef = useRef(null);
  const gearBtnRef = useRef(null);
  const firstItemRef = useRef(null);
  const { cellEditorWidth } = useCellAreaContext();

  const updateAnchor = useCallback(() => {
    const btn = gearBtnRef.current;
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    setMenuAnchor({
      top: rect.top,
      left: rect.left + rect.width / 2, // center X
      width: rect.width,
      height: rect.height,
    });
  }, []);

  // open: compute anchor and focus first item
  useEffect(() => {
    if (advancedOpen) {
      updateAnchor();
      // focus after render
      requestAnimationFrame(() => firstItemRef.current?.focus());
    }
  }, [advancedOpen, updateAnchor]);

  // keep menu position updated on scroll/resize
  useEffect(() => {
    if (!advancedOpen) return;
    const onRp = () => updateAnchor();
    window.addEventListener("resize", onRp);
    window.addEventListener("scroll", onRp, true);
    return () => {
      window.removeEventListener("resize", onRp);
      window.removeEventListener("scroll", onRp, true);
    };
  }, [advancedOpen, updateAnchor]);

  // click outside + escape handling
  useEffect(() => {
    function onDocDown(e) {
      if (!advancedOpen) return;
      const target = e.target;
      if (
        advRef.current &&
        !advRef.current.contains(target) &&
        gearBtnRef.current &&
        !gearBtnRef.current.contains(target)
      ) {
        setAdvancedOpen(false);
      }
    }

    function onKey(e) {
      if (!advancedOpen) return;
      if (e.key === "Escape") setAdvancedOpen(false);
    }

    document.addEventListener("mousedown", onDocDown);
    document.addEventListener("touchstart", onDocDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocDown);
      document.removeEventListener("touchstart", onDocDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [advancedOpen]);

  // toggle handler that computes anchor before opening
  const toggleAdvanced = useCallback(() => {
    if (!advancedOpen) {
      updateAnchor();
      setAdvancedOpen(true);
    } else {
      setAdvancedOpen(false);
    }
  }, [advancedOpen, updateAnchor]);

  // After the portal mounts, measure it and decide whether it fits above; if not, place below
  useLayoutEffect(() => {
    if (!advancedOpen || !menuAnchor) return;
    const el = advRef.current;
    if (!el) return;
    const menuRect = el.getBoundingClientRect();

    // gap between button and menu
    const GAP = 8;

    const fitsAbove = menuAnchor.top - menuRect.height - GAP >= 0;
    setPlacement(fitsAbove ? "above" : "below");
  }, [advancedOpen, menuAnchor]);

  // menu element rendered into a portal
  const MenuPortal = () => {
    if (!advancedOpen || !menuAnchor) return null;
    const style =
      placement === "above"
        ? {
            position: "fixed",
            left: `${menuAnchor.left}px`,
            top: `${menuAnchor.top}px`,
            transform: "translate(-50%, calc(-100% - 8px))",
            zIndex: 9999,
            minWidth: "10rem",
            // keep default visuals controlled by CSS class
          }
        : {
            position: "fixed",
            left: `${menuAnchor.left}px`,
            top: `${menuAnchor.top + menuAnchor.height}px`,
            transform: "translate(-50%, 8px)",
            zIndex: 9999,
            minWidth: "10rem",
          };

    return createPortal(
      <div
        id="advanced-menu"
        ref={advRef}
        className={`${styles.fctAdvancedMenu} ${styles.fctAdvancedMenu_Portal}`}
        role="menu"
        aria-label="Advanced actions"
        style={style}
      >
        <ul className={styles.fctAdvancedList} >
          <li>
            <button
              ref={firstItemRef}
              onClick={() => {
                setAdvancedOpen(false);
                onInlineDBToPandas();
              }}
              role="menuitem"
              className={styles.fctAdvancedItem}
              type="button"
            >
              <DatabaseZap size={14} />
              <span className={styles.fctLabel}>DB interface cell</span>
            </button>
          </li>

          <li>
            <button
              onClick={() => {
                setAdvancedOpen(false);
                onAddToDAG();
              }}
              role="menuitem"
              className={styles.fctAdvancedItem}
              type="button"
            >
              <Server size={14} />
              <span className={styles.fctLabel}>S3 interface cell</span>
            </button>
          </li>

          <li>
            <button
              onClick={() => {
                setAdvancedOpen(false);
                onLaunchTerminal();
              }}
              role="menuitem"
              className={styles.fctAdvancedItem}
              type="button"
            >
              <Terminal size={14} />
              <span className={styles.fctLabel}>Launch terminal</span>
            </button>
          </li>
        </ul>
      </div>,
      document.body
    );
  };

  return (
    <div className={styles.fctWrapper} aria-labelledby={cellId} style={{ width: `${cellEditorWidth}px` }} >
      <div className={styles.fctToolbar} role="toolbar" aria-label="Cell actions">
        <div className={styles.fctLeftGroup}>
          <button
            onClick={onInsertCode}
            aria-label="Insert code cell"
            title="Insert code cell"
            className={styles.fctIconBtn}
            type="button"
          >
            <Plus size={14} />
          </button>

          <button
            onClick={onInsertMarkdown}
            className={styles.fctBtn}
            aria-label="Insert Markdown cell"
            type="button"
          >
            <FileText size={14} />
            <span className={styles.fctLabel}>Markdown</span>
          </button>

          <button
            onClick={onInsertSQL}
            className={styles.fctBtn}
            aria-label="Insert SQL cell"
            title="Insert SQL cell"
            type="button"
          >
            <Database size={14} />
            <span className={styles.fctLabel}>SQL</span>
          </button>
        </div>

        <div className={styles.fctRightGroup}>
          <button
            onClick={onAI}
            aria-label="AI assistant"
            title="Generate cells in the context of your workspace"
            className={styles.fctAiBtn}
            type="button"
          >
            <Zap size={14} />
            <span className={styles.fctLabel}>Prompt AI</span>
          </button>

          <div className={styles.fctAdvancedWrapper}>
            <button
              ref={gearBtnRef}
              onClick={toggleAdvanced}
              aria-haspopup="menu"
              aria-expanded={advancedOpen}
              aria-controls="advanced-menu"
              title="More options"
              className={styles.fctIconBtn}
              type="button"
            >
              <Menu size={14} />
            </button>

            {/* portal renders the floating menu into document.body */}
            <MenuPortal />
          </div>
        </div>
      </div>
    </div>
  );
}
