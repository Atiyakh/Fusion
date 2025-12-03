// src/contexts/UIComponentsContext.jsx
import { createContext, useContext, useState, useMemo } from "react";

const UIComponentsContext = createContext(null);

export function UIComponentsProvider({ children }) {
  const [tabBarRef, setTabBarRef] = useState(null);

  const value = useMemo(
    () => ({
      // accessing tab bar
      tabBarRef, setTabBarRef
    }),
    [tabBarRef]
  );

  return (
    <UIComponentsContext.Provider value={value}>
      {children}
    </UIComponentsContext.Provider>
  );
}

export function useUIComponentsContext() {
  const ctx = useContext(UIComponentsContext);
  if (!ctx) {
    throw new Error("UIComponentsContext must be used within Provider");
  }
  return ctx;
}
