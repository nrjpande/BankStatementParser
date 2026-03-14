import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { statementsAPI } from '../api/client';
import { toast } from 'sonner';

export default function StatementsPage() {
  const [statements, setStatements] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    statementsAPI.list().then((res) => {
      setStatements(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this statement and all its transactions?')) return;
    try {
      await statementsAPI.delete(id);
      setStatements((prev) => prev.filter((s) => s.statement_id !== id));
      toast.success('Statement deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="statements-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-bold text-slate-900">Statements</h1>
          <p className="text-slate-500 mt-1">Manage your uploaded bank statements</p>
        </div>
        <Link
          to="/upload"
          data-testid="upload-new-stmt-btn"
          className="bg-slate-900 hover:bg-slate-800 text-white rounded-lg px-5 py-2.5 text-sm font-medium transition-colors shadow-sm"
        >
          Upload New
        </Link>
      </div>

      {statements.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-16 text-center">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <p className="text-slate-600 font-medium mb-2">No statements yet</p>
          <p className="text-slate-400 text-sm mb-4">Upload your first bank statement to get started</p>
          <Link to="/upload" className="inline-flex items-center gap-2 bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors">
            Upload Statement
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full" data-testid="statements-table">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">File</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Bank</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Transactions</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Uploaded</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {statements.map((s) => (
                <tr key={s.statement_id} className="hover:bg-slate-50 transition-colors" data-testid={`stmt-row-${s.statement_id}`}>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <span className="text-[10px] font-mono font-bold text-slate-500">
                          {s.filename?.split('.').pop()?.toUpperCase()}
                        </span>
                      </div>
                      <span className="text-sm font-medium text-slate-900 truncate max-w-[200px]">{s.filename}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 bg-blue-50 text-accent text-xs rounded-md font-medium">{s.bank_detected}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600 font-mono">{s.transaction_count}</td>
                  <td className="px-6 py-4 text-sm text-slate-400">{new Date(s.uploaded_at).toLocaleDateString()}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link
                        to={`/statements/${s.statement_id}`}
                        data-testid={`view-stmt-${s.statement_id}`}
                        className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
                      >
                        View
                      </Link>
                      <button
                        data-testid={`delete-stmt-${s.statement_id}`}
                        onClick={() => handleDelete(s.statement_id)}
                        className="bg-white hover:bg-red-50 text-red-500 border border-slate-200 hover:border-red-200 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
