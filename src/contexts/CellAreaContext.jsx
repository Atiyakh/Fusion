// src/contexts/CellAreaContext.jsx
import { createContext, useContext, useState, useMemo } from "react";

const CellAreaContext = createContext(null);

export function CellAreaProvider({ children }) {
  const [cellEditorWidth, setCellEditorWidth] = useState(null);

  const value = useMemo(
    () => ({ cellEditorWidth, setCellEditorWidth }),
    [cellEditorWidth]
  );

  return (
    <CellAreaContext.Provider value={value}>
      {children}
    </CellAreaContext.Provider>
  );
}

export function useCellAreaContext() {
  const ctx = useContext(CellAreaContext);
  if (!ctx) {
    throw new Error("CellAreaContext must be used within Provider");
  }
  return ctx;
}
