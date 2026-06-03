import React, { useState } from 'react';
import { Play, RotateCcw, AlertCircle } from 'lucide-react';

export default function CrawlForm({ onSubmit, isRunning }) {
  const [url, setUrl] = useState('');
  const [depth, setDepth] = useState(3);
  const [maxPages, setMaxPages] = useState(100);
  const [workers, setWorkers] = useState(5);
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!url) {
      setError('Start URL is required.');
      return;
    }

    try {
      new URL(url);
    } catch (_) {
      setError('Please enter a valid absolute URL (e.g. https://example.com).');
      return;
    }

    onSubmit({ url, depth: parseInt(depth), max_pages: parseInt(maxPages), concurrent_workers: parseInt(workers) });
  };

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl relative overflow-hidden transition-all duration-300 hover:border-slate-800">
      {/* Background radial accent */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-brand-500/5 rounded-full blur-3xl pointer-events-none" />

      <h2 className="text-xl font-bold text-slate-100 mb-6 flex items-center gap-2">
        <span className="p-2 bg-brand-500/10 rounded-lg text-brand-400">📹</span>
        Configure Crawler
      </h2>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="url" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Start URL
          </label>
          <div className="relative rounded-xl shadow-sm">
            <input
              type="text"
              name="url"
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              disabled={isRunning}
              className="block w-full rounded-xl bg-slate-900/50 border border-slate-800 px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 transition duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="depth" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Max Depth
            </label>
            <input
              type="number"
              name="depth"
              id="depth"
              min="0"
              max="10"
              value={depth}
              onChange={(e) => setDepth(e.target.value)}
              disabled={isRunning}
              className="block w-full rounded-xl bg-slate-900/50 border border-slate-800 px-4 py-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 transition duration-150 disabled:opacity-50"
            />
          </div>

          <div>
            <label htmlFor="maxPages" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Max Pages
            </label>
            <input
              type="number"
              name="maxPages"
              id="maxPages"
              min="1"
              max="1000"
              value={maxPages}
              onChange={(e) => setMaxPages(e.target.value)}
              disabled={isRunning}
              className="block w-full rounded-xl bg-slate-900/50 border border-slate-800 px-4 py-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 transition duration-150 disabled:opacity-50"
            />
          </div>

          <div>
            <label htmlFor="workers" className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Workers (Max 10)
            </label>
            <input
              type="number"
              name="workers"
              id="workers"
              min="1"
              max="10"
              value={workers}
              onChange={(e) => setWorkers(e.target.value)}
              disabled={isRunning}
              className="block w-full rounded-xl bg-slate-900/50 border border-slate-800 px-4 py-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 transition duration-150 disabled:opacity-50"
            />
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl p-3.5 text-sm">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={isRunning}
          className={`glow-btn w-full rounded-xl py-3.5 px-4 font-semibold text-sm flex items-center justify-center gap-2 transition duration-200 ${
            isRunning
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
              : 'bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/25'
          }`}
        >
          {isRunning ? (
            <>
              <div className="w-5 h-5 border-2 border-slate-500 border-t-brand-400 rounded-full animate-spin" />
              Crawl Running...
            </>
          ) : (
            <>
              <Play size={16} fill="currentColor" />
              Start Crawl
            </>
          )}
        </button>
      </form>
    </div>
  );
}
