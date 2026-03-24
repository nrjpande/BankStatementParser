import React, { useEffect, useState, useRef } from 'react';
import { ledgersAPI } from '../api/client';
import { toast } from 'sonner';

export default function LedgersPage() {
  const [ledgers, setLedgers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [newGroup, setNewGroup] = useState('');
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [search, setSearch] = useState('');
  const fileRef = useRef(null);

  useEffect(() => {
    loadLedgers();
  }, []);

  const loadLedgers = () => {
    ledgersAPI.list().then((res) => {
      setLedgers(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await ledgersAPI.create({ name: newName.trim(), group: newGroup.trim() });
      toast.success(`Ledger "${newName.trim()}" added`);
      setNewName('');
      setNewGroup('');
      loadLedgers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create ledger');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete ledger "${name}"?`)) return;
    try {
      await ledgersAPI.delete(id);
      setLedgers((prev) => prev.filter((l) => l.ledger_id !== id));
      toast.success('Ledger deleted');
    } catch {
      toast.error('Delete failed');
    }
  };

  const handleImportXml = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const res = await ledgersAPI.importTallyXml(file);
      toast.success(res.data.message);
      loadLedgers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Import failed');
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const filtered = search
    ? ledgers.filter((l) =>
        l.name.toLowerCase().includes(search.toLowerCase()) ||
        (l.group || '').toLowerCase().includes(search.toLowerCase()) ||
        (l.source || '').toLowerCase().includes(search.toLowerCase())
      )
    : ledgers;

  const sourceColors = {
    default: 'bg-slate-100 text-slate-500',
    manual: 'bg-blue-50 text-blue-600',
    tally_import: 'bg-purple-50 text-purple-600',
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-6 animate-fade-in" data-testid="ledgers-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-3xl font-bold text-slate-900">Master Ledgers</h1>
          <p className="text-slate-500 mt-1">Manage ledger accounts used for mapping transactions</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".xml"
            onChange={handleImportXml}
            className="hidden"
            data-testid="tally-xml-input"
          />
          <button
            data-testid="import-tally-xml-btn"
            onClick={() => fileRef.current?.click()}
            disabled={importing}
            className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
          >
            {importing ? 'Importing...' : 'Import from Tally XML'}
          </button>
        </div>
      </div>

      {/* Add Ledger Form */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="font-heading text-sm font-semibold text-slate-900 mb-4">Add New Ledger</h3>
        <form onSubmit={handleCreate} className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1.5">Ledger Name</label>
            <input
              data-testid="ledger-name-input"
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Office Expenses"
              className="w-full h-10 px-4 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-all"
              required
            />
          </div>
          <div className="w-48">
            <label className="block text-xs font-medium text-slate-500 mb-1.5">Group (optional)</label>
            <input
              data-testid="ledger-group-input"
              type="text"
              value={newGroup}
              onChange={(e) => setNewGroup(e.target.value)}
              placeholder="e.g. Expenses"
              className="w-full h-10 px-4 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-all"
            />
          </div>
          <button
            data-testid="add-ledger-btn"
            type="submit"
            disabled={creating}
            className="h-10 bg-slate-900 hover:bg-slate-800 text-white rounded-lg px-6 text-sm font-medium transition-colors disabled:opacity-50 whitespace-nowrap"
          >
            {creating ? 'Adding...' : 'Add Ledger'}
          </button>
        </form>
      </div>

      {/* Search + Stats */}
      <div className="flex items-center justify-between">
        <input
          data-testid="ledger-search"
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search ledgers..."
          className="h-9 px-4 w-64 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-accent/30"
        />
        <span className="text-sm text-slate-400">{filtered.length} ledgers</span>
      </div>

      {/* Ledgers List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="max-h-[500px] overflow-y-auto">
          <table className="w-full" data-testid="ledgers-table">
            <thead className="sticky top-0 bg-slate-50 z-10">
              <tr className="border-b border-slate-200">
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Ledger Name</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Group</th>
                <th className="text-left px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Source</th>
                <th className="text-right px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((l) => (
                <tr key={l.ledger_id} className="hover:bg-slate-50 transition-colors" data-testid={`ledger-row-${l.ledger_id}`}>
                  <td className="px-6 py-2.5 text-sm font-medium text-slate-900">{l.name}</td>
                  <td className="px-6 py-2.5 text-sm text-slate-400">{l.group || '-'}</td>
                  <td className="px-6 py-2.5">
                    <span className={`px-2 py-0.5 text-xs rounded-md font-medium ${sourceColors[l.source] || 'bg-slate-100 text-slate-500'}`}>
                      {l.source === 'tally_import' ? 'Tally Import' : l.source === 'manual' ? 'Manual' : 'Default'}
                    </span>
                  </td>
                  <td className="px-6 py-2.5 text-right">
                    <button
                      data-testid={`delete-ledger-${l.ledger_id}`}
                      onClick={() => handleDelete(l.ledger_id, l.name)}
                      className="text-slate-300 hover:text-red-500 transition-colors p-1"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
