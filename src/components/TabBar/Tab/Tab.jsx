// src/components/TabBar/Tab/Tab.jsx
import React, { forwardRef, useEffect, useRef, useState } from 'react';
import getFileIcon from '../../../assets/FileIcons.jsx';
import { X } from 'lucide-react';
import styles from './Tab.module.css';
import { useTabBarContext } from '../../../contexts/TabBarContext.jsx';

const Tab = forwardRef(function Tab({ TabData = { filePath: './FilePath', fileName: 'File Name' } }, forwardedRef) {
  // If parent didn't pass a ref, keep a local one so we can operate on the DOM.
  const localRef = useRef(null);
  const ref = forwardedRef ?? localRef;

  const [active, setActive] = useState(false);
  const { setTabsData, setActiveTabRef, activeTabRef } = useTabBarContext();

  function clickTabCallback() {
    if (typeof setActiveTabRef === 'function') setActiveTabRef(ref);
  }

  useEffect(() => {
    if (ref === activeTabRef) {
      setActive(true);
    } else {
      setActive(false);
    }
  }, [activeTabRef]);

  function closeTabCallback(e) {
    e.stopPropagation();

    const filePath = TabData.filePath;

    // remove from tabsData
    if (typeof setTabsData === 'function') {
        setTabsData((prev = []) => prev.filter((t) => t.filePath !== filePath));
    }

    // remove from tabsRefs
    if (typeof setTabsRefs === 'function') {
        setTabsRefs((prev = {}) => {
        const newRefs = { ...prev };
        delete newRefs[filePath];
        return newRefs;
        });
    }
  }

  return (
    <button
      ref={ref}
      type="button"
      className={`${styles.tabButton} ${active ? styles.active : ''}`}
      onClick={clickTabCallback}
      aria-pressed={active}
    >
      <div className={`${styles.tabTopStripe} ${active ? styles.active : ''}`} />
      {getFileIcon(null, TabData.fileName)}
      <span className={styles.tabLabel}>{TabData.fileName}</span>
      <X className={styles.tabClose} onClick={closeTabCallback} />
    </button>
  );
});

export default Tab;
