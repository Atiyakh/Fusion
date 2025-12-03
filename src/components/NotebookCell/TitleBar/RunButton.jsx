import { useState } from 'react';
import { Play, Square } from 'lucide-react';

export default function RunButton() {
  const [run, setRun] = useState(false);

  const handleRun = async () => {
    try {
      // do something...
      setRun(true);
      setTimeout(() => setRun(false), 1500);
    } catch (err) {
      console.error("running cell fail:", err);
    }
  };

  return (
    <button
      className="run-button"
      onClick={handleRun}
    >
      {run ? (
        <Square size={21} /> // nice light red
      ) : (
        <Play size={21} />   // fresh light green
      )}
    </button>
  );
}
