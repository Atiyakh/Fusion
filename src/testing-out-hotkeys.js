// HotkeysProvider.jsx
import { createContext, useContext, useEffect, useRef } from "react";

// utils
function normalizeKey(e) {
  const parts = [];
  // Normalize on mac: use meta for Command
  if (e.ctrlKey) parts.push("ctrl");
  if (e.metaKey) parts.push("meta");
  if (e.altKey) parts.push("alt");
  if (e.shiftKey) parts.push("shift");

  // Some keys are multi-word; normalize to lowercase simple token
  const key = (e.key || "").toLowerCase();
  // map " " => "space", ArrowLeft => arrowleft etc.
  const map = {
    " ": "space",
    "arrowleft": "arrowleft",
    "arrowright": "arrowright",
    "arrowup": "arrowup",
    "arrowdown": "arrowdown",
    "esc": "escape",
    "del": "delete",
  };
  parts.push(map[key] || key);
  return parts.join("+");
}

// context
const HotkeysContext = createContext(null);

export function HotkeysProvider({ children }) {
  // Map<id, { ref, getMapping, priority }>
  const registryRef = useRef(new Map());
  const idCounter = useRef(0);

  // register / unregister
  const register = (ref, getMapping, options = {}) => {
    const id = ++idCounter.current;
    const entry = { ref, getMapping, priority: options.priority || 0 };
    registryRef.current.set(id, entry);
    return () => registryRef.current.delete(id);
  };

  // find the best-matching registered entry for an active element.
  function findClosestMatch(active) {
    if (!active) return null;
    let best = null;
    let bestDistance = Infinity;

    // iterate over registered roots
    for (const entry of registryRef.current.values()) {
      const root = entry.ref.current;
      if (!root) continue;
      if (!root.contains(active)) continue;

      // compute distance (number of steps up from active to root)
      let distance = 0;
      let node = active;
      while (node && node !== root) {
        node = node.parentElement;
        distance++;
        if (distance > 10000) break; // safety
      }

      if (node === root) {
        // tie-breaker: prefer lower distance (deeper node), then higher priority
        if (
          distance < bestDistance ||
          (distance === bestDistance && entry.priority > (best?.priority ?? -Infinity))
        ) {
          best = entry;
          bestDistance = distance;
        }
      }
    }
    return best;
  }

  useEffect(() => {
    function onKeyDown(e) {
      const active = document.activeElement;
      const combo = normalizeKey(e);

      // If no active element, you could optionally match "global" entries
      const match = findClosestMatch(active);

      // Option: allow a global fallback entry (root === document.body)
      if (match) {
        const mapping = match.getMapping();
        const handler = mapping && mapping[combo];
        if (handler) {
          // stop browser default & call handler
          e.preventDefault();
          handler(e);
          return;
        }
      }

      // if no scoped match, optionally check global entries (priority 0 or flagged)
      // e.g., iterate registry again for entries flagged as global
      for (const entry of registryRef.current.values()) {
        const mapping = entry.getMapping();
        if (!mapping) continue;
        if (entry.ref.current === null) {
          const handler = mapping[combo];
          if (handler) {
            e.preventDefault();
            handler(e);
            return;
          }
        }
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const ctx = useRef({ register }).current;

  return <HotkeysContext.Provider value={ctx}>{children}</HotkeysContext.Provider>;
}

/* ---------- hook to register from components ---------- */
export function useRegisterHotkeys(ref, mapping, options = {}) {
  const ctx = useContext(HotkeysContext);
  if (!ctx) {
    throw new Error("useRegisterHotkeys must be used inside HotkeysProvider");
  }

  // Keep mapping stable using a ref to avoid re-register churn
  const mappingRef = useRef(mapping);
  mappingRef.current = mapping;

  useEffect(() => {
    const unregister = ctx.register(ref, () => mappingRef.current, options);
    return unregister;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // register once
}
