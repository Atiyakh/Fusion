import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import styles from "./TitleBar.module.css";

export default function CopyButton() {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText("hello world");
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error("Clipboard fail:", err);
    }
  };

  return (
    <button 
      className={styles.copyButton}
      onClick={handleCopy}
    >
      {copied ? <Check size={21} /> : <Copy size={21} />}
    </button>
  );
}
