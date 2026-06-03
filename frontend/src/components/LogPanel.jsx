import React, { useEffect, useRef, useState } from 'react';
import { Terminal, ShieldAlert, CircleDot } from 'lucide-react';

const getLogLevelStyle = (level) => {
  switch (level) {
    case 'VISIT':
      return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
    case 'VIDEO_FOUND':
      return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold';
    case 'SKIP_EXTERNAL':
      return 'bg-amber-500/10 text-amber-500/70 border border-amber-500/10';
    case 'SKIP_DUPLICATE':
      return 'bg-slate-800 text-slate-500 border border-slate-700/30';
    case 'ERROR':
      return 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
    default:
      return 'bg-slate-800 text-slate-400';
  }
};

export default function LogPanel({ logs }) {
  const containerRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto scroll to bottom
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Handle manual scroll to toggle autoscroll
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // If user scrolled up by more than 30px, disable autoscroll
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 30;
    setAutoScroll(isAtBottom);
  };

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl relative overflow-hidden transition-all duration-300 hover:border-slate-800 flex flex-col h-[350px]">
      <div className="flex justify-between items-center mb-4 shrink-0">
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <span className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-400">
            <Terminal size={18} />
          </span>
          Live Crawl Logs
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoScroll(true)}
            className={`text-xs px-2.5 py-1 rounded-lg border transition duration-150 flex items-center gap-1 ${
              autoScroll
                ? 'bg-brand-500/10 border-brand-500/30 text-brand-400'
                : 'bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300'
            }`}
          >
            <CircleDot size={10} className={autoScroll ? 'fill-brand-400 animate-pulse' : ''} />
            Auto-Scroll
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 bg-slate-950/70 border border-slate-900 rounded-xl p-4 overflow-y-auto font-mono text-xs space-y-2 select-text"
      >
        {logs.length > 0 ? (
          logs.map((log, idx) => (
            <div key={idx} className="flex items-start gap-3 animate-slide-in text-slate-300 hover:bg-slate-900/40 py-0.5 rounded px-1 transition duration-100">
              <span className="text-[10px] text-slate-600 shrink-0 select-none">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold shrink-0 uppercase tracking-wider ${getLogLevelStyle(log.level)}`}>
                {log.level}
              </span>
              <span className="break-all whitespace-pre-wrap leading-relaxed">
                {log.message}
              </span>
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-600">
            <ShieldAlert size={28} className="stroke-[1.5] mb-2 text-slate-700" />
            <span>Terminal ready. Awaiting crawl initiation...</span>
          </div>
        )}
      </div>
    </div>
  );
}
