import React from 'react';
import { Activity, Layers, PlayCircle, Video, Clock } from 'lucide-react';

const formatTime = (seconds) => {
  if (!seconds && seconds !== 0) return '00:00:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [
    String(h).padStart(2, '0'),
    String(m).padStart(2, '0'),
    String(s).padStart(2, '0')
  ].join(':');
};

const getStatusBadge = (status) => {
  switch (status) {
    case 'running':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 pulsing-glow">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
          Running
        </span>
      );
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          Completed
        </span>
      );
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <span className="w-2 h-2 rounded-full bg-rose-400" />
          Failed
        </span>
      );
    case 'stopped':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
          <span className="w-2 h-2 rounded-full bg-slate-400" />
          Stopped
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
          <span className="w-2 h-2 rounded-full bg-slate-500" />
          Idle
        </span>
      );
  }
};

export default function StatusPanel({ session, elapsed }) {
  const isRunning = session?.status === 'running';

  const stats = [
    {
      label: 'Pages Crawled',
      value: session?.pages_crawled ?? 0,
      max: session?.max_pages ?? 100,
      icon: <Activity size={18} className="text-sky-400" />,
      color: 'bg-sky-500'
    },
    {
      label: 'Pages Queued',
      value: session?.pages_queued ?? 0,
      icon: <Layers size={18} className="text-amber-400" />,
      color: 'bg-amber-500'
    },
    {
      label: 'Videos Found',
      value: session?.videos_found ?? 0,
      icon: <Video size={18} className="text-brand-400" />,
      color: 'bg-brand-500'
    },
    {
      label: 'Elapsed Time',
      value: formatTime(elapsed),
      icon: <Clock size={18} className="text-indigo-400" />,
      color: 'bg-indigo-500'
    }
  ];

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl relative overflow-hidden transition-all duration-300 hover:border-slate-800">
      <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span className="p-2 bg-blue-500/10 rounded-lg text-blue-400">📊</span>
            Crawl Live Status
          </h2>
          {session?.start_url && (
            <p className="text-xs text-slate-400 mt-1 max-w-md truncate" title={session.start_url}>
              Start URL: <span className="text-slate-300 font-mono">{session.start_url}</span>
            </p>
          )}
        </div>
        <div>
          {getStatusBadge(session?.status)}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-slate-400">{stat.label}</span>
              <div className="p-1.5 bg-slate-950 rounded-lg border border-slate-800/40">
                {stat.icon}
              </div>
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-100 font-mono tracking-tight">
                {stat.value}
              </div>
              {stat.max && (
                <div className="w-full bg-slate-950 rounded-full h-1.5 mt-3 border border-slate-800/50 overflow-hidden">
                  <div
                    className={`h-full ${stat.color} rounded-full transition-all duration-500`}
                    style={{ width: `${Math.min(100, (stat.value / stat.max) * 100)}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
