// src/components/ProjectFileTree/ProjectFileTree.jsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import styles from "./ProjectFileTree.module.css";
import getFileIcon, { fileIcons } from "../../assets/FileIcons.jsx";

// Utility: build stable path for a node
function nodePath(parentPath, name) {
  return parentPath ? `${parentPath}/${name}` : name;
}

// Hook: manage open folders, selection, focus
export function useFileTree({ initialOpen = [], initialSelected = null } = {}) {
  const [openFolders, setOpenFolders] = useState(() => new Set(initialOpen));
  const [selected, setSelected] = useState(initialSelected);
  const [focused, setFocused] = useState(null);

  const isOpen = useCallback((path) => openFolders.has(path), [openFolders]);
  const toggleOpen = useCallback((path) => {
    setOpenFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);
  const open = useCallback((path) => setOpenFolders((prev) => new Set(prev).add(path)), []);
  const close = useCallback((path) => setOpenFolders((prev) => {
    const next = new Set(prev);
    next.delete(path);
    return next;
  }), []);

  return {
    openFolders,
    isOpen,
    toggleOpen,
    open,
    close,
    selected,
    setSelected,
    focused,
    setFocused,
  };
}

// Hook: roving focus utilities — keeps track of visible item order and focuses by id/index
function useRovingFocus() {
  const orderRef = useRef([]);
  const setOrder = useCallback((arr) => { orderRef.current = arr; }, []);
  const focusById = useCallback((id) => {
    const el = document.getElementById(id);
    if (el) el.focus();
  }, []);
  const idForIndex = useCallback((i) => orderRef.current[i] ?? null, []);
  const indexOfId = useCallback((id) => orderRef.current.indexOf(id), []);

  return { setOrder, focusById, idForIndex, indexOfId, orderRef };
}

export default function ProjectFileTree({ projectData, onFileOpen, onSelect, className = "", style = {}, initiallyOpen = [] }) {
  const treeHook = useFileTree({ initialOpen: initiallyOpen });
  const roving = useRovingFocus();
  const rootRef = useRef(null);
  const containerRef = useRef(null);

  // Build flat visible list in render pass so keyboard navigation can use indexes
  const visibleItemsRef = useRef([]);
  visibleItemsRef.current = [];

  // Utility: push visible node id into order and return id
  const pushVisible = (path) => {
    const id = `pft-${btoa(path).replace(/=+$/g, "").replace(/[^a-zA-Z0-9_-]/g, "")}`; // short-ish stable id
    visibleItemsRef.current.push(id);
    return id;
  };

  // handle keyboard navigation at the tree level
  const handleKeyDown = useCallback((e) => {
    const { key } = e;
    const order = visibleItemsRef.current;
    if (!order.length) return;
    const activeId = document.activeElement?.id;
    const idx = order.indexOf(activeId);

    // helper: focus index with bounds and scrolling into view
    const focusIndex = (i) => {
      const clamped = Math.max(0, Math.min(order.length - 1, i));
      const el = document.getElementById(order[clamped]);
      if (el) {
        el.focus();
        el.scrollIntoView({ block: "nearest", inline: "nearest" });
      }
    };

    switch (key) {
      case "ArrowDown":
        e.preventDefault();
        focusIndex(idx + 1);
        break;
      case "ArrowUp":
        e.preventDefault();
        focusIndex(idx - 1);
        break;
      case "Home":
        e.preventDefault();
        focusIndex(0);
        break;
      case "End":
        e.preventDefault();
        focusIndex(order.length - 1);
        break;
      default:
        break;
    }
  }, []);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    root.addEventListener("keydown", handleKeyDown);
    return () => root.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Open file (callback)
  const openFile = useCallback((node, path) => {
    if (onFileOpen) onFileOpen(node, path);
  }, [onFileOpen]);

  // Select node (file or folder)
  const selectNode = useCallback((node, path) => {
    treeHook.setSelected(path);
    if (onSelect) onSelect(node, path);
  }, [onSelect, treeHook]);

  // Render: recursively produce tree with accessible attributes
  function File({ node, path, level }) {
    const id = pushVisible(path);
    const isSelected = treeHook.selected === path;

    return (
      <li role="treeitem" aria-selected={isSelected} aria-level={level} key={path} className={`${styles.projectFileTreeItem} ${styles.file}`} data-level={level}>
        <button
          id={id}
          tabIndex={0}
          className={`${styles.projectFileTreeBtn} ${isSelected ? "is-selected" : ""}`}
          onClick={(e) => {
            selectNode(node, path);
            openFile(node, path);
          }}
          onDoubleClick={() => openFile(node, path)}
          onContextMenu={(e) => {
            e.preventDefault();
            selectNode(node, path);
            // consumer may open a context menu based on onSelect or onContext (not implemented)
          }}
        >
          {getFileIcon(node)}
          <span className={styles.projectFileTreeName}>{node.name}</span>
        </button>
      </li>
    );
  }

  function Directory({ node, path, level }) {
    const id = pushVisible(path);
    const open = treeHook.isOpen(path);
    const isSelected = treeHook.selected === path;

    return (
      <li role="treeitem" aria-expanded={open} aria-level={level} key={path} className={`${styles.projectFileTreeItem} ${styles.directory}`} data-level={level}>
        <div style={{ display: "flex" }}>
          <button
            id={id}
            tabIndex={0}
            className={`${styles.projectFileTreeBtn} ${isSelected ? "is-selected" : ""}`}
            onClick={(e) => {
              // click on folder toggles open + selects
              treeHook.toggleOpen(path);
              selectNode(node, path);
            }}
            onDoubleClick={() => treeHook.toggleOpen(path)}
            onContextMenu={(e) => {
              e.preventDefault();
              selectNode(node, path);
            }}
          >
            {open ? fileIcons.folderOpen : fileIcons.folder}
            <span className={styles.projectFileTreeName}>{node.name}</span>
          </button>
        </div>

        {open && node.children && node.children.length > 0 && (
          <ul role="group" className={styles.projectFileTreeChildren}>
            {node.children.map((child) => (
              child.type === "folder" ? (
                <Directory key={child.name + Math.random()} node={child} path={nodePath(path, child.name)} level={level + 1} />
              ) : (
                <File key={child.name + Math.random()} node={child} path={nodePath(path, child.name)} level={level + 1} />
              )
            ))}
          </ul>
        )}
      </li>
    );
  }

  // Top-level evaluate
  const evaluateProjectTree = useCallback((node, path = "", level = 1) => {
    const p = path ? nodePath(path, node.name) : node.name;
    if (node.type === "folder") return <Directory key={p} node={node} path={p} level={level} />;
    return <File key={p} node={node} path={p} level={level} />;
  }, [treeHook.isOpen, treeHook.selected]);

  // Render tree
  // We'll populate visibleItemsRef during render; that's fine for a synchronous render
  visibleItemsRef.current = [];

  return (
    <div
      className={`${styles.projectFileTreeWrapper} ${className}`}
      style={style}
      ref={rootRef}
      role="tree"
      aria-label={projectData?.projectName || "Project files"}
    >
      <strong style={{ display: "block", padding: "5px 15px", height: "40px" }}>{projectData?.projectName}</strong>

      {/* scrollable container where your scrollbar styles should apply */}
      <div ref={containerRef} className={styles.projectFileTreeScroller} style={{ overflow: "auto", maxHeight: 560 }}>
        <ul className={styles.projectFileTreeRoot}>
          {projectData?.directory?.children?.map((node) => evaluateProjectTree(node, projectData.directory.name || "", 1))}
        </ul>
      </div>
    </div>
  );
}
