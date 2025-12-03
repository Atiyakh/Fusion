// src/components/TabBar/TabBar.jsx
import React, { forwardRef, useEffect, useState } from 'react';
import styles from './TabBar.module.css';
import Tab from './Tab/Tab.jsx';
import { useTabBarContext } from '../../contexts/TabBarContext.jsx';
import { useUIComponentsContext } from '../../contexts/UIComponentsContext.jsx';

// generate Data Science related tabs (file names and extensions)
const testTabsData = [
  { fileName: 'training.csv', filePath: './training.ipynb' },
  { fileName: 'data_exploration.ipynb', filePath: './data_exploration.ipynb' },
  { fileName: 'feature_engineering.ipynb', filePath: './feature_engineering.ipynb' },
  { fileName: 'model_training.ipynb', filePath: './model_training.ipynb' },
  { fileName: 'evaluation.ipynb', filePath: './evaluation.ipynb' },
  { fileName: 'report.ipynb', filePath: './report.ipynb' },
  { fileName: 'README.md', filePath: './README.md' }
];

export default forwardRef(function TabBar(props, ref) {
  const { tabsData, setTabsData, tabsRefs, setTabsRefs } = useTabBarContext();
  const { setTabBarRef } = useUIComponentsContext();
  const [childrenMapping, setChildrenMapping] = useState({});

  // share TabBar ref with UI components context
  useEffect(() => {
    if (ref && typeof setTabBarRef === 'function') setTabBarRef(ref);
  }, [ref, setTabBarRef]);

  // initialize placeholder tabs once if none exist
  useEffect(() => {
    if ((!Array.isArray(tabsData) || tabsData.length === 0) && typeof setTabsData === 'function') {
      setTabsData(testTabsData);
    }
    // run only once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync refs state and children mapping with tabsData
  useEffect(() => {
    if (!Array.isArray(tabsData)) return;

    const desiredPaths = new Set(tabsData.map((t) => t.filePath));

    // Build a new refs object based on current tabsRefs (preserve existing refs)
    const newRefs = { ...(tabsRefs || {}) };
    let refsChanged = false;

    // remove stale refs
    for (const existing of Object.keys(newRefs)) {
      if (!desiredPaths.has(existing)) {
        delete newRefs[existing];
        refsChanged = true;
      }
    }

    // add missing refs
    for (const tab of tabsData) {
      if (!(tab.filePath in newRefs)) {
        newRefs[tab.filePath] = React.createRef();
        refsChanged = true;
      }
    }

    // update refs state only if something changed
    if (refsChanged && typeof setTabsRefs === 'function') {
      setTabsRefs(newRefs);
    }

    // use the up-to-date refs object for mapping (if we changed refs, use newRefs; else use current tabsRefs)
    const refsToUse = refsChanged ? newRefs : (tabsRefs || {});

    // Build children mapping in a single pass (preserve existing mapping to avoid unnecessary remounts)
    setChildrenMapping((prev) => {
      const next = { ...prev };

      // remove stale components
      for (const existing of Object.keys(next)) {
        if (!desiredPaths.has(existing)) {
          delete next[existing];
        }
      }

      // add new components
      for (const tab of tabsData) {
        if (!(tab.filePath in next)) {
          const tabRef = refsToUse[tab.filePath];
          next[tab.filePath] = <Tab key={tab.filePath} ref={tabRef} TabData={tab} />;
        }
      }
      return next;
    });
  }, [tabsData, tabsRefs, setTabsRefs]);

  return <div ref={ref} className={styles.tabBar}>{Object.values(childrenMapping)}</div>;
});
