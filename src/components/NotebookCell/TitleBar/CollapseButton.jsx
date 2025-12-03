import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import styles from "./TitleBar.module.css";

export default function CollapseButton() {
  const [collapsed, setCollapsed] = useState(false);

  const handleCollapse = async () => {
    try {
      await navigator.clipboard.writeText("hello world");
      setCollapsed(true);
      setTimeout(() => setCollapsed(false), 1500);
    } catch (err) {
      console.error("Clipboard fail:", err);
    }
  };

  return (
    <button 
      className={styles.collapseCellButton}
      onClick={handleCollapse}
    >
      {collapsed ? <ChevronUp size={27} /> : <ChevronDown size={27} />}
    </button>
  );
}
