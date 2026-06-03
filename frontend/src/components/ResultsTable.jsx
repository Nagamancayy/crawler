import React, { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  flexRender,
} from '@tanstack/react-table';
import {
  Search,
  Copy,
  ExternalLink,
  Download,
  Check,
  ChevronLeft,
  ChevronRight,
  Video,
  FileJson,
  FileSpreadsheet
} from 'lucide-react';

export default function ResultsTable({ videos, crawlId }) {
  const [globalFilter, setGlobalFilter] = useState('');
  const [copiedId, setCopiedId] = useState(null);

  const downloadUrl = (url) => {
    const envApi = import.meta.env.VITE_API_URL;
    const baseUrl = envApi ? envApi : (import.meta.env.DEV ? 'http://localhost:8000' : '');
    return `${baseUrl}/crawl/download?url=${encodeURIComponent(url)}&referer=https://vidzp.com/`;
  };

  const handleCopy = (url, id) => {
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const columns = useMemo(
    () => [
      {
        accessorKey: 'thumbnail_url',
        header: 'Thumbnail',
        cell: (info) => {
          const val = info.getValue();
          return (
            <div className="w-16 h-10 rounded-lg overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center text-slate-600 shrink-0">
              {val ? (
                <img
                  src={val}
                  alt="Thumbnail"
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    const parent = e.target.parentElement;
                    if (parent) {
                      const icon = parent.querySelector('.fallback-icon');
                      if (icon) icon.classList.remove('hidden');
                    }
                  }}
                />
              ) : null}
              <Video size={16} className={`fallback-icon ${val ? 'hidden' : ''}`} />
            </div>
          );
        },
      },
      {
        accessorKey: 'page_url',
        header: 'Source Page',
        cell: (info) => {
          const val = info.getValue();
          try {
            const parsed = new URL(val);
            const path = parsed.pathname + parsed.search;
            return (
              <div className="flex items-center gap-2 group max-w-xs md:max-w-md">
                <a
                  href={val}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-300 hover:text-brand-400 font-medium truncate block leading-relaxed"
                  title={val}
                >
                  {path === '/' ? parsed.hostname : path}
                </a>
                <a
                  href={val}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-slate-500 hover:text-slate-300 p-1 hover:bg-slate-900 rounded transition"
                  title="Open Source Page"
                >
                  <ExternalLink size={14} />
                </a>
              </div>
            );
          } catch (_) {
            return <span className="text-slate-400 truncate max-w-xs block">{val}</span>;
          }
        },
      },
      {
        accessorKey: 'video_url',
        header: 'Video URL',
        cell: (info) => {
          const val = info.getValue();
          const rowId = info.row.id;
          return (
            <div className="flex items-center gap-3 max-w-md md:max-w-2xl">
              <span className="text-slate-400 font-mono text-xs truncate block select-all flex-1" title={val}>
                {val}
              </span>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => handleCopy(val, rowId)}
                  className="p-1.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition"
                  title="Copy Video URL"
                >
                  {copiedId === rowId ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                </button>
                <a
                  href={val}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition"
                  title="Open Video URL"
                >
                  <ExternalLink size={14} />
                </a>
                {info.row.original.type !== 'EMBED' && (
                  <a
                    href={downloadUrl(val)}
                    download
                    className="p-1.5 bg-emerald-950/40 border border-emerald-800/30 hover:bg-emerald-900/40 rounded-lg text-emerald-400 hover:text-emerald-300 transition"
                    title="Download Pure Video"
                  >
                    <Download size={14} />
                  </a>
                )}
              </div>
            </div>
          );
        },
      },
      {
        accessorKey: 'type',
        header: 'Type',
        cell: (info) => {
          const val = info.getValue() || 'MP4';
          const colors = {
            MP4: 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
            HLS: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
            DASH: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
            WEBM: 'bg-violet-500/10 text-violet-400 border border-violet-500/20',
            EMBED: 'bg-pink-500/10 text-pink-400 border border-pink-500/20',
          };
          const style = colors[val.toUpperCase()] || 'bg-slate-800 text-slate-400 border border-slate-700';
          return (
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${style}`}>
              {val}
            </span>
          );
        },
      },
    ],
    [copiedId]
  );

  const table = useReactTable({
    data: videos,
    columns,
    state: {
      globalFilter,
    },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageSize: 10,
      },
    },
  });

  const exportUrl = (format) => {
    const envApi = import.meta.env.VITE_API_URL;
    const baseUrl = envApi ? envApi : (import.meta.env.DEV ? 'http://localhost:8000' : '');
    const suffix = crawlId ? `?crawl_id=${crawlId}` : '';
    return `${baseUrl}/crawl/export/${format}${suffix}`;
  };

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-xl relative overflow-hidden transition-all duration-300 hover:border-slate-800 flex flex-col gap-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shrink-0">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-brand-400">
              <Video size={18} />
            </span>
            Discovered Videos
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Displaying {table.getFilteredRowModel().rows.length} of {videos.length} videos found
          </p>
        </div>

        {/* Controls: Search and Exports */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Search Box */}
          <div className="relative flex-1 md:w-64 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input
              type="text"
              value={globalFilter ?? ''}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder="Search source or video URL..."
              className="w-full bg-slate-950/70 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 transition"
            />
          </div>

          {/* Export JSON */}
          <a
            href={exportUrl('json')}
            download
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-850 border border-slate-800 text-slate-300 hover:text-slate-200 transition"
          >
            <FileJson size={14} className="text-amber-500" />
            JSON
          </a>

          {/* Export CSV */}
          <a
            href={exportUrl('csv')}
            download
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-900 hover:bg-slate-850 border border-slate-800 text-slate-300 hover:text-slate-200 transition"
          >
            <FileSpreadsheet size={14} className="text-emerald-500" />
            CSV
          </a>
        </div>
      </div>

      {/* Table Element */}
      <div className="overflow-x-auto border border-slate-900 rounded-xl bg-slate-950/30">
        <table className="w-full text-left border-collapse">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-slate-900 bg-slate-900/10">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer select-none hover:text-slate-200 transition"
                  >
                    <div className="flex items-center gap-2">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{
                        asc: ' 🔼',
                        desc: ' 🔽',
                      }[header.column.getIsSorted()] ?? null}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-slate-900/40 hover:bg-slate-900/10 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="p-4 text-sm align-middle">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="text-center p-8 text-slate-500">
                  No video sources match search query
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between shrink-0 select-none">
          <span className="text-xs text-slate-500">
            Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-850 text-slate-400 disabled:opacity-30 disabled:pointer-events-none transition"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-850 text-slate-400 disabled:opacity-30 disabled:pointer-events-none transition"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
