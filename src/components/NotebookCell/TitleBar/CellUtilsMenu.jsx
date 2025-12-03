import { useState, useRef, useEffect } from "react";
import { Menu, History, Sparkles, Repeat, MessageSquare } from "lucide-react";

export default function CellUtilsMenu({ onSelect = () => {} }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const ITEMS = [
    { id: "version", label: "Cell version control", Icon: History },
    { id: "explain", label: "Explain with AI", Icon: Sparkles },
    { id: "refactor", label: "Refactor with AI", Icon: Repeat },
    { id: "comments", label: "View comments", Icon: MessageSquare },
  ];

  useEffect(() => {
    function handleClick(e) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="cell-utils-menu">
      <button
        onClick={() => setOpen(!open)}
        className="utils-trigger"
      >
        <Menu size={16} />
      </button>


      {open && (
        <ul className="utils-menu">
          {ITEMS.map(({ id, label, Icon }) => (
            <li key={id} onClick={() => { onSelect(id); setOpen(false); }}>
              <Icon size={16} />
              <span>{label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
