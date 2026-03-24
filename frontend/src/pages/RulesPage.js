import React, { useEffect, useState } from 'react';
import { rulesAPI, ledgersAPI } from '../api/client';
import { toast } from 'sonner';

export default function RulesPage() {
  const [rules, setRules] = useState([]);
  const [ledgers, setLedgers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState('');
  const [ledger, setLedger] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    Promise.all([
      rulesAPI.list(),
      ledgersAPI.names(),
    ]).then(([rulesRes, ledgerRes]) => {
      setRules(rulesRes.data);
      setLedgers(ledgerRes.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!keyword.trim() || !ledger) return;
    setCreating(true);
    try {
      const res = await rulesAPI.create({ keyword: keyword.trim(), ledger });
      toast.success('Rule created');
      setRules((prev) => [...prev.filter(r => r.keyword !== keyword.trim().toLowerCase()), { rule_id: res.data.rule_id, keyword: keyword.trim().toLowerCase(), ledger }]);
      setKeyword('');
      setLedger('');
    } catch { toast.error('Failed to create rule'); }
    finally { setCreating(false); }
  };

  const handleDelete = async (ruleId) => {
    try {
      await rulesAPI.delete(ruleId);
      setRules((prev) => prev.filter((r) => r.rule_id !== ruleId));
      toast.success('Rule deleted');
    } catch { toast.error('Delete failed'); }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl" data-testid="rules-page">
      <div>
        <h1 className="font-heading text-3xl font-bold text-slate-900">Mapping Rules</h1>
        <p className="text-slate-500 mt-1">Auto-map transactions to ledgers based on keywords in the narration</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="font-heading text-sm font-semibold text-slate-900 mb-4">Create New Rule</h3>
        <form onSubmit={handleCreate} className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1.5">Keyword</label>
            <input data-testid="rule-keyword-input" type="text" value={keyword}
              onChange={(e) => setKeyword(e.target.value)} placeholder='e.g. "swiggy", "uber", "rent"'
              className="w-full h-10 px-4 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-all" required />
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1.5">Map to Ledger</label>
            <select data-testid="rule-ledger-select" value={ledger} onChange={(e) => setLedger(e.target.value)}
              className="w-full h-10 px-4 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-all" required>
              <option value="">Select ledger...</option>
              {ledgers.map((l) => (<option key={l} value={l}>{l}</option>))}
            </select>
          </div>
          <button data-testid="create-rule-btn" type="submit" disabled={creating}
            className="h-10 bg-slate-900 hover:bg-slate-800 text-white rounded-lg px-6 text-sm font-medium transition-colors disabled:opacity-50 whitespace-nowrap">
            {creating ? 'Creating...' : 'Add Rule'}
          </button>
        </form>
        <p className="text-xs text-slate-400 mt-3">Rules use ledgers from your Master Ledgers list. Add more in the Ledgers page.</p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h3 className="font-heading text-sm font-semibold text-slate-900">Active Rules ({rules.length})</h3>
        </div>
        {rules.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-slate-500 text-sm mb-1">No mapping rules yet</p>
            <p className="text-slate-400 text-xs">Create rules above or map transactions in the table.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {rules.map((rule) => (
              <div key={rule.rule_id} data-testid={`rule-${rule.rule_id}`}
                className="flex items-center justify-between px-6 py-3.5 hover:bg-slate-50 transition-colors">
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">IF contains</span>
                    <span className="px-3 py-1 bg-slate-100 text-slate-700 text-sm font-mono rounded-md">{rule.keyword}</span>
                  </div>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><polyline points="9 6 15 12 9 18"/></svg>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">THEN map to</span>
                    <span className="px-3 py-1 bg-emerald-50 text-emerald-700 text-sm font-medium rounded-md">{rule.ledger}</span>
                  </div>
                </div>
                <button data-testid={`delete-rule-${rule.rule_id}`} onClick={() => handleDelete(rule.rule_id)}
                  className="text-slate-300 hover:text-red-500 transition-colors p-1">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
