// src/components/NotebookCell/NotebookCell/NotebookCell.jsx
import { useRef, useEffect } from "react";
import TitleBar from "../TitleBar/TitleBar.jsx";
import Editor from "../Editor/Editor.jsx";
import StatusBar from "../StatusBar/StatusBar.jsx";
import FloatingCellMenu from "../FloatingCellMenu/FloatingCellMenu.jsx";
import styles from "./NotebookCell.module.css";
import cellMenuStyles from "../../NotebookCell/FloatingCellMenu/FloatingCellMenu.module.css";
import { useCellAreaContext } from "../../../contexts/CellAreaContext.jsx";

export default function NotebookCell({cellData}) {
  const { setCellEditorWidth, cellEditorWidth } = useCellAreaContext();
  const cellEditorRef = useRef(null);
  const { initialValue, cellTitle } = cellData;
  const cellRef = useRef(null);
  const floatingCellMenuRef = useRef(null);
  const notebookCellRef = useRef(null);

  useEffect(() => { // adjust 
    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setCellEditorWidth(entry.contentRect.width + 4); // +4 for border
      }
    });

    if (cellRef.current) observer.observe(cellRef.current);

    return () => observer.disconnect();
  }, [cellEditorWidth]);

  useEffect(() => { // manage focus border color
    const wrapper = notebookCellRef.current;
    if (!wrapper) return;

    const handleFocus = (e) => {
      wrapper.querySelectorAll(".notebook-cell").forEach(cell => {
        cell.style.borderColor = "var(--accent)";
      });
    };

    const handleBlur = (e) => {
      wrapper.querySelectorAll(".notebook-cell").forEach(cell => {
        cell.style.borderColor = "var(--border)"; // reset to default
      });
    };

    // Listen to focus and blur on any child that matches your selectors
    wrapper.addEventListener("focusin", handleFocus);
    wrapper.addEventListener("focusout", handleBlur);

    return () => {
      wrapper.removeEventListener("focusin", handleFocus);
      wrapper.removeEventListener("focusout", handleBlur);
    };
  }, []);

  function focusCell() {
    cellEditorRef.current.focus();
  }

  function enableFloatingCellMenu() {
    const wrapper = floatingCellMenuRef.current;
    if (!wrapper) return;

    // select the inner menu using the hashed class from CSS modules
    const menu = wrapper.querySelector(`.${cellMenuStyles.menu}`);
    if (!menu) return;

    menu.style.opacity = wrapper.style.opacity = '1';
    menu.style.pointerEvents = wrapper.style.pointerEvents = 'auto';
    menu.style.height = 'auto';
  }

  function disableFloatingCellMenu() {
    const wrapper = floatingCellMenuRef.current;
    if (!wrapper) return;

    const menu = wrapper.querySelector(`.${cellMenuStyles.menu}`);
    if (!menu) return;

    menu.style.opacity = wrapper.style.opacity = '0';
    menu.style.pointerEvents = wrapper.style.pointerEvents = 'none';
    menu.style.height = '0';
  }

  function retainBorderColor() {
    cellRef.current.style.borderColor = 'var(--accent)';
  }

  return (
    <div 
      className={styles.notebookCellWrapper}
      ref={notebookCellRef}
      tabIndex={-1}
      onFocus={enableFloatingCellMenu}
      onBlur={disableFloatingCellMenu}
    >
      <div ref={cellRef} className="notebook-cell" role="group" aria-label="Notebook cell">
        <TitleBar tabIndex="0" cellTitle={ cellTitle } />
        <Editor tabIndex="0" initialValue={initialValue} ref={cellEditorRef} />
        <StatusBar tabIndex="0" />
      </div>
      {/* floating menu aligned to the cell */}
      <FloatingCellMenu
        ref={floatingCellMenuRef}
        focusCellCallback={focusCell}
        borderColorCallback={retainBorderColor}
      />
    </div>
  );
}
