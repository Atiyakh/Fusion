// src/context/TabBarContext.jsx
import { createContext, useContext, useState, useMemo } from "react";

const TabBarContext = createContext(null);

export function TabBarProvider({ children }) {
  const [tabsData, setTabsData] = useState([]);
  const [activeTabRef, setActiveTabRef] = useState(null);
  const [tabsRefs, setTabsRefs] = useState({
    // filePath (unique): Tab ref
  });

  const value = useMemo(
    () => ({
      tabsData, setTabsData,
      tabsRefs, setTabsRefs,
      activeTabRef, setActiveTabRef
    }),
    [tabsData, tabsRefs, activeTabRef]
  );

  return (
    <TabBarContext.Provider value={value}>{children}</TabBarContext.Provider>
  );
}

export function useTabBarContext() {
  const ctx = useContext(TabBarContext);
  if (!ctx) {
    throw new Error("TabBarContext must be used within Provider");
  }
  return ctx;
}
