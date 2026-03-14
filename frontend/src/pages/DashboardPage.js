import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { dashboardAPI } from '../api/client';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#e11d48', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1'];

function StatCard({ label, value, sub, color, testId }) {
  return (
    <div data-testid={testId} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 hover:shadow-md transition-shadow duration-200">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">{label}</p>
      <p className={`font-heading text-2xl font-bold ${color || 'text-slate-900'}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardAPI.stats().then(res => {
      setStats(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const fmt = (n) => {
    if (!n) return '0';
    return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n);
  };

  const ledgerData = stats?.ledger_distribution?.map(d => ({
    name: d.ledger.length > 15 ? d.ledger.slice(0, 15) + '...' : d.ledger,
    value: d.count,
    total: d.total,
  })) || [];

  return (
    <div className="space-y-8 animate-fade-in" data-testid="dashboard-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500 mt-1">Overview of your bank statement processing</p>
        </div>
        <Link
          to="/upload"
          data-testid="upload-new-btn"
          className="bg-slate-900 hover:bg-slate-800 text-white rounded-lg px-5 py-2.5 text-sm font-medium transition-colors shadow-sm"
        >
          Upload Statement
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard testId="stat-statements" label="Statements" value={stats?.total_statements || 0} sub="Total uploaded" />
        <StatCard testId="stat-transactions" label="Transactions" value={fmt(stats?.total_transactions)} sub={`${stats?.mapped_transactions || 0} mapped`} />
        <StatCard testId="stat-withdrawals" label="Total Withdrawals" value={`₹${fmt(stats?.total_withdrawals)}`} color="text-red-600" />
        <StatCard testId="stat-deposits" label="Total Deposits" value={`₹${fmt(stats?.total_deposits)}`} color="text-emerald-600" />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ledger Distribution Bar */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h3 className="font-heading text-lg font-semibold text-slate-900 mb-4">Ledger Distribution</h3>
          {ledgerData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={ledgerData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                  formatter={(val) => [val, 'Count']}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]} fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
              No ledger data yet. Upload a statement to get started.
            </div>
          )}
        </div>

        {/* Pie Chart */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h3 className="font-heading text-lg font-semibold text-slate-900 mb-4">Category Split</h3>
          {ledgerData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={ledgerData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={50}
                  strokeWidth={2}
                  stroke="#fff"
                >
                  {ledgerData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
              Map transactions to ledgers to see category breakdown.
            </div>
          )}
          {ledgerData.length > 0 && (
            <div className="flex flex-wrap gap-3 mt-2">
              {ledgerData.slice(0, 6).map((d, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-slate-600">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                  {d.name}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Statements */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="p-6 border-b border-slate-100">
          <h3 className="font-heading text-lg font-semibold text-slate-900">Recent Statements</h3>
        </div>
        <div className="divide-y divide-slate-100">
          {stats?.recent_statements?.length > 0 ? stats.recent_statements.map((s) => (
            <Link
              key={s.statement_id}
              to={`/statements/${s.statement_id}`}
              data-testid={`recent-stmt-${s.statement_id}`}
              className="flex items-center justify-between px-6 py-4 hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-900">{s.filename}</p>
                  <p className="text-xs text-slate-400">{s.bank_detected} &middot; {s.transaction_count} transactions</p>
                </div>
              </div>
              <span className="text-xs text-slate-400">{new Date(s.uploaded_at).toLocaleDateString()}</span>
            </Link>
          )) : (
            <div className="px-6 py-12 text-center">
              <p className="text-slate-400 text-sm mb-3">No statements uploaded yet</p>
              <Link
                to="/upload"
                data-testid="empty-upload-btn"
                className="inline-flex items-center gap-2 bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Upload your first statement
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
