import React, { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Film, Zap, Award, Layers } from 'lucide-react';

export default function StatsPanel({ videos, pagesCrawled, elapsed, stats }) {
  // Compute video type breakdown dynamically
  const chartData = useMemo(() => {
    const counts = {};
    videos.forEach((v) => {
      const t = v.type || 'UNKNOWN';
      counts[t] = (counts[t] || 0) + 1;
    });

    return Object.keys(counts).map((type) => ({
      name: type,
      value: counts[type]
    })).sort((a, b) => b.value - a.value);
  }, [videos]);

  const mostCommonType = useMemo(() => {
    if (chartData.length === 0) return 'N/A';
    return chartData[0].name;
  }, [chartData]);

  const speed = useMemo(() => {
    if (stats?.avg_speed !== undefined) return stats.avg_speed;
    if (!elapsed || !pagesCrawled) return 0;
    return (pagesCrawled / elapsed).toFixed(2);
  }, [pagesCrawled, elapsed, stats]);

  const COLORS = ['#5272ff', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl relative overflow-hidden transition-all duration-300 hover:border-slate-800">
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      <h2 className="text-xl font-bold text-slate-100 mb-6 flex items-center gap-2">
        <span className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">📈</span>
        Crawl Analytics
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Statistics Cards */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 bg-brand-500/10 text-brand-400 rounded-xl border border-brand-500/20">
              <Film size={20} />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Total Videos Discovered</p>
              <p className="text-xl font-bold text-slate-100 font-mono mt-0.5">{videos.length}</p>
            </div>
          </div>

          <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/20">
              <Zap size={20} />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Average Crawl Speed</p>
              <p className="text-xl font-bold text-slate-100 font-mono mt-0.5">{speed} pages/sec</p>
            </div>
          </div>

          <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex items-center gap-4">
            <div className="p-3 bg-violet-500/10 text-violet-400 rounded-xl border border-violet-500/20">
              <Award size={20} />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Most Common Format</p>
              <p className="text-xl font-bold text-slate-100 font-mono mt-0.5">{mostCommonType}</p>
            </div>
          </div>
        </div>

        {/* Video Formats Chart */}
        <div className="lg:col-span-2 bg-slate-900/30 border border-slate-900/60 rounded-xl p-4 flex flex-col justify-between min-h-[220px]">
          <div className="flex justify-between items-center mb-4">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Video Format Distribution</span>
            <span className="text-[10px] text-slate-500 font-mono">Count by Extension</span>
          </div>

          {chartData.length > 0 ? (
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#f8fafc'
                    }}
                    cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={32}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-44 text-slate-500 border border-dashed border-slate-800 rounded-lg">
              <Layers size={24} className="stroke-[1.5] mb-2" />
              <span className="text-sm">No video format data available</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
