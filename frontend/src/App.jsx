import React, { useState, useEffect, useRef } from 'react';
import CrawlForm from './components/CrawlForm';
import StatusPanel from './components/StatusPanel';
import StatsPanel from './components/StatsPanel';
import LogPanel from './components/LogPanel';
import ResultsTable from './components/ResultsTable';
import { Film, RefreshCw, StopCircle, Trash2 } from 'lucide-react';

const getWsUrl = () => {
  const envWs = import.meta.env.VITE_WS_URL;
  if (envWs) {
    return envWs;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  if (import.meta.env.DEV) {
    return 'ws://localhost:8000/ws/crawl';
  }
  return `${protocol}//${window.location.host}/ws/crawl`;
};

const getApiUrl = (path) => {
  const envApi = import.meta.env.VITE_API_URL;
  if (envApi) {
    return `${envApi}${path}`;
  }
  if (import.meta.env.DEV) {
    return `http://localhost:8000${path}`;
  }
  return path;
};

export default function App() {
  const [session, setSession] = useState(null);
  const [logs, setLogs] = useState([]);
  const [videos, setVideos] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const timerRef = useRef(null);

  const isRunning = session?.status === 'running';

  // Fetch results and logs for a session
  const fetchSessionDetails = async (crawlId) => {
    try {
      const [resVideos, resLogs] = await Promise.all([
        fetch(getApiUrl(`/crawl/results?crawl_id=${crawlId}`)).then((r) => r.json()),
        fetch(getApiUrl(`/crawl/logs?crawl_id=${crawlId}`)).then((r) => r.json())
      ]);
      setVideos(resVideos || []);
      setLogs(resLogs || []);
    } catch (err) {
      console.error('Failed to load session details:', err);
    }
  };

  // Fetch initial/latest crawl status
  const fetchStatus = async () => {
    try {
      const response = await fetch(getApiUrl('/crawl/status'));
      const data = await response.json();
      if (data && data.session) {
        setSession(data.session);
        setStats(data.stats);
        setElapsed(data.elapsed_time || 0);
        await fetchSessionDetails(data.session.id);
      }
    } catch (err) {
      console.error('Error fetching crawl status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    return () => {
      stopTimer();
    };
  }, []);

  // Timer logic for elapsed time tracking
  useEffect(() => {
    if (isRunning) {
      startTimer();
    } else {
      stopTimer();
    }
    return () => {
      stopTimer();
    };
  }, [isRunning]);

  const startTimer = () => {
    stopTimer();
    timerRef.current = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  // Start crawl trigger (Serverless SSE Streaming Reader)
  const handleStartCrawl = async (formData) => {
    try {
      setLoading(true);
      setLogs([]);
      setVideos([]);
      setElapsed(0);
      setStats({
        total_pages: 0,
        total_videos: 0,
        most_common_type: 'N/A',
        avg_speed: 0.0
      });

      // Optimistically show as running
      setSession({
        status: 'running',
        pages_crawled: 0,
        pages_queued: 1,
        videos_found: 0,
        max_pages: formData.max_pages,
        start_url: formData.url
      });

      const response = await fetch(getApiUrl('/crawl/start'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      if (!response.body) {
        throw new Error('ReadableStream not supported in response');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        
        // Save the last partial line back to the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const event = JSON.parse(trimmed.substring(6));
              
              if (event.type === 'log') {
                setLogs((prev) => [...prev, event.data]);
                
                // Fetch videos dynamically when a video is found
                if (event.data.level === 'VIDEO_FOUND') {
                  const resVideos = await fetch(getApiUrl(`/crawl/results?crawl_id=${event.data.crawl_id}`)).then((r) => r.json());
                  setVideos(resVideos || []);
                }
              } else if (event.type === 'stats') {
                setSession((prev) => ({
                  ...prev,
                  id: event.data.crawl_id,
                  pages_crawled: event.data.pages_crawled,
                  pages_queued: event.data.pages_queued,
                  videos_found: event.data.videos_found,
                  status: event.data.status
                }));
                setElapsed(event.data.elapsed_time);
              } else if (event.type === 'complete') {
                setSession(event.data.session);
                setStats(event.data.stats);
                setElapsed(event.data.elapsed_time);
                
                // Final sync
                const resVideos = await fetch(getApiUrl(`/crawl/results?crawl_id=${event.data.session.id}`)).then((r) => r.json());
                setVideos(resVideos || []);
              }
            } catch (e) {
              console.error('Error parsing streaming event:', e);
            }
          }
        }
      }
    } catch (err) {
      console.error('Failed to start crawl:', err);
      setSession((prev) => prev ? { ...prev, status: 'failed' } : null);
    } finally {
      setLoading(false);
    }
  };

  // Reset/Clear crawl session
  const handleReset = async () => {
    try {
      setLoading(true);
      await fetch(getApiUrl('/crawl/reset'), { method: 'POST' });
      setSession(null);
      setLogs([]);
      setVideos([]);
      setElapsed(0);
      setStats(null);
    } catch (err) {
      console.error('Failed to reset crawl data:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-brand-500/20">
      {/* Dynamic Header */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-500/25">
              <Film className="text-white shrink-0" size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                Antigravity Crawler
              </h1>
              <p className="text-[10px] text-slate-500 font-medium">Domain Video Resource Discovery</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              disabled={loading || isRunning}
              className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-rose-950/40 hover:bg-rose-950/10 text-rose-500 hover:text-rose-400 rounded-xl transition duration-150 disabled:opacity-30 disabled:pointer-events-none flex items-center gap-1.5 text-xs font-semibold"
              title="Reset Database"
            >
              <Trash2 size={14} />
              Reset
            </button>
            <button
              onClick={fetchStatus}
              disabled={loading || isRunning}
              className="p-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200 rounded-xl transition duration-150 disabled:opacity-30 disabled:pointer-events-none"
              title="Refresh Dashboard"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {loading && !session ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-500">
            <div className="w-8 h-8 border-4 border-slate-800 border-t-brand-500 rounded-full animate-spin mb-4" />
            <span className="text-sm font-medium">Fetching crawler states...</span>
          </div>
        ) : (
          <>
            {/* Top Grid: Controls + Status & Terminal Logs */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Form & Real-time Info */}
              <div className="lg:col-span-5 space-y-6">
                <CrawlForm onSubmit={handleStartCrawl} isRunning={isRunning} />
                <StatusPanel session={session} elapsed={elapsed} />
              </div>

              {/* Right Column: Console Log */}
              <div className="lg:col-span-7">
                <LogPanel logs={logs} />
              </div>
            </div>

            {/* Bottom Grid: Historical/Real-time Analytics */}
            <StatsPanel
              videos={videos}
              pagesCrawled={session?.pages_crawled || 0}
              elapsed={elapsed}
              stats={stats}
            />

            {/* Bottom Grid: TanStack Results Table */}
            <ResultsTable videos={videos} crawlId={session?.id} />
          </>
        )}
      </main>

      {/* Sticky Footer */}
      <footer className="border-t border-slate-900/60 bg-slate-950 py-4 shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-600">
          <span>&copy; 2026 Antigravity domains-crawler application. Active domain limits configured.</span>
        </div>
      </footer>
    </div>
  );
}
