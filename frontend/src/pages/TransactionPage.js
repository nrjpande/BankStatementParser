import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AllCommunityModule, provideGlobalGridOptions } from 'ag-grid-community';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { transactionsAPI, ledgersAPI, rulesAPI, tallyAPI } from '../api/client';
import { toast } from 'sonner';

provideGlobalGridOptions({ theme: 'legacy' });

export default function TransactionPage() {
  const { statementId } = useParams();
  const navigate = useNavigate();
  const gridRef = useRef(null);
  const [rowData, setRowData] = useState([]);
  const [ledgers, setLedgers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRows, setSelectedRows] = useState([]);
  const [bulkLedger, setBulkLedger] = useState('');
  const [marking, setMarking] = useState(false);

  // Filter states
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [txnType, setTxnType] = useState('all');
  const [keyword, setKeyword] = useState('');
  const [mappedFilter, setMappedFilter] = useState('all');

  // Filtered KPI
  const [filteredDebits, setFilteredDebits] = useState(0);
  const [filteredCredits, setFilteredCredits] = useState(0);
  const [filteredCount, setFilteredCount] = useState(0);

  useEffect(() => {
    Promise.all([
      transactionsAPI.get(statementId),
      ledgersAPI.names(),
    ]).then(([txnRes, ledgerRes]) => {
      setRowData(txnRes.data);
      setLedgers(ledgerRes.data);
      setLoading(false);
    }).catch(() => {
      toast.error('Failed to load transactions');
      setLoading(false);
    });
  }, [statementId]);

  const voucherTypes = ['Payment', 'Receipt', 'Contra', 'Journal'];

  const onCellValueChanged = useCallback(async (params) => {
    const { data, colDef } = params;
    if (colDef.field === 'ledger' || colDef.field === 'voucher_type') {
      try {
        await transactionsAPI.update(data.transaction_id, {
          ledger: data.ledger,
          voucher_type: data.voucher_type,
        });
        if (colDef.field === 'ledger' && data.ledger && data.original_description) {
          const kw = data.merchant || data.original_description.split(/[\s/]+/)[0];
          if (kw && kw.length > 2) {
            try { await rulesAPI.create({ keyword: kw.toLowerCase(), ledger: data.ledger }); } catch {}
          }
        }
        toast.success('Updated');
      } catch { toast.error('Update failed'); }
    }
  }, []);

  const onSelectionChanged = useCallback(() => {
    const sel = gridRef.current?.api?.getSelectedRows() || [];
    setSelectedRows(sel);
  }, []);

  // Recalculate filtered KPIs when grid filters change
  const onFilterChanged = useCallback(() => {
    const api = gridRef.current?.api;
    if (!api) return;
    let debits = 0, credits = 0, count = 0;
    api.forEachNodeAfterFilter((node) => {
      if (node.data) {
        debits += node.data.withdrawal || 0;
        credits += node.data.deposit || 0;
        count++;
      }
    });
    setFilteredDebits(debits);
    setFilteredCredits(credits);
    setFilteredCount(count);
  }, []);

  // Apply external filters
  const isExternalFilterPresent = useCallback(() => {
    return dateFrom || dateTo || txnType !== 'all' || keyword || mappedFilter !== 'all';
  }, [dateFrom, dateTo, txnType, keyword, mappedFilter]);

  const doesExternalFilterPass = useCallback((node) => {
    const d = node.data;
    if (dateFrom && d.date < dateFrom) return false;
    if (dateTo && d.date > dateTo) return false;
    if (txnType === 'debit' && !(d.withdrawal > 0)) return false;
    if (txnType === 'credit' && !(d.deposit > 0)) return false;
    if (mappedFilter === 'mapped' && !d.is_mapped) return false;
    if (mappedFilter === 'unmapped' && d.is_mapped) return false;
    if (keyword) {
      const kw = keyword.toLowerCase();
      const match = (d.description || '').toLowerCase().includes(kw) ||
        (d.original_description || '').toLowerCase().includes(kw) ||
        (d.merchant || '').toLowerCase().includes(kw) ||
        (d.ledger || '').toLowerCase().includes(kw);
      if (!match) return false;
    }
    return true;
  }, [dateFrom, dateTo, txnType, keyword, mappedFilter]);

  // Refresh external filter when filter states change
  useEffect(() => {
    gridRef.current?.api?.onFilterChanged();
  }, [dateFrom, dateTo, txnType, keyword, mappedFilter]);

  const clearFilters = () => {
    setDateFrom('');
    setDateTo('');
    setTxnType('all');
    setKeyword('');
    setMappedFilter('all');
    gridRef.current?.api?.setFilterModel(null);
  };

  const handleBulkUpdate = async () => {
    if (!bulkLedger || selectedRows.length === 0) return;
    try {
      const ids = selectedRows.map((r) => r.transaction_id);
      await transactionsAPI.bulkUpdate({ transaction_ids: ids, ledger: bulkLedger });
      setRowData((prev) =>
        prev.map((r) => ids.includes(r.transaction_id) ? { ...r, ledger: bulkLedger, is_mapped: true } : r)
      );
      toast.success(`Updated ${ids.length} transactions`);
      setBulkLedger('');
      gridRef.current?.api?.deselectAll();
    } catch { toast.error('Bulk update failed'); }
  };

  const handleApplyRules = async () => {
    try {
      const res = await rulesAPI.apply(statementId);
      toast.success(res.data.message);
      const txnRes = await transactionsAPI.get(statementId);
      setRowData(txnRes.data);
    } catch { toast.error('Failed to apply rules'); }
  };

  const handleMarkReady = async () => {
    setMarking(true);
    try {
      const res = await tallyAPI.markReady(statementId, {
        company_name: 'My Company',
        bank_ledger: 'Bank Account',
      });
      toast.success(res.data.message);
      const txnRes = await transactionsAPI.get(statementId);
      setRowData(txnRes.data);
    } catch { toast.error('Failed to mark for Tally'); }
    finally { setMarking(false); }
  };

  let rowCounter = 0;
  const columnDefs = useMemo(() => [
    {
      headerName: '#',
      width: 60,
      pinned: 'left',
      valueGetter: (params) => params.node.rowIndex + 1,
      suppressMenu: true,
      sortable: false,
      filter: false,
      cellClass: 'text-slate-400 text-xs font-mono',
    },
    {
      headerName: '',
      checkboxSelection: true,
      headerCheckboxSelection: true,
      width: 45,
      pinned: 'left',
      suppressMenu: true,
      sortable: false,
      filter: false,
    },
    {
      field: 'date',
      headerName: 'Date',
      width: 110,
      sort: 'asc',
      cellClass: 'font-mono text-xs',
    },
    {
      field: 'description',
      headerName: 'Description',
      flex: 2,
      minWidth: 200,
      cellRenderer: (params) => {
        const isDirty = params.data.description !== params.data.original_description;
        return (
          <div className="flex items-center gap-2">
            {isDirty && <span className="w-1.5 h-1.5 bg-purple-500 rounded-full flex-shrink-0" title="AI cleaned" />}
            <span className="truncate">{params.value}</span>
          </div>
        );
      },
    },
    {
      field: 'merchant',
      headerName: 'Merchant',
      width: 110,
      cellRenderer: (params) => {
        if (!params.value) return <span className="text-slate-300">-</span>;
        return <span className="px-2 py-0.5 bg-blue-50 text-accent text-xs rounded-md font-medium">{params.value}</span>;
      },
    },
    {
      field: 'withdrawal',
      headerName: 'Debit',
      width: 120,
      type: 'numericColumn',
      cellClass: 'amount-debit font-mono text-xs',
      valueFormatter: (p) => p.value > 0 ? `₹${Number(p.value).toLocaleString('en-IN')}` : '',
    },
    {
      field: 'deposit',
      headerName: 'Credit',
      width: 120,
      type: 'numericColumn',
      cellClass: 'amount-credit font-mono text-xs',
      valueFormatter: (p) => p.value > 0 ? `₹${Number(p.value).toLocaleString('en-IN')}` : '',
    },
    {
      field: 'ledger',
      headerName: 'Ledger',
      flex: 1,
      minWidth: 155,
      editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: ['', ...ledgers] },
      cellRenderer: (params) => {
        if (!params.value) return <span className="text-slate-300 italic text-xs">Click to map...</span>;
        return <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded-md font-medium">{params.value}</span>;
      },
    },
    {
      field: 'voucher_type',
      headerName: 'Voucher',
      width: 100,
      editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: voucherTypes },
      cellRenderer: (params) => {
        const colors = { Payment: 'bg-red-50 text-red-600', Receipt: 'bg-emerald-50 text-emerald-600', Contra: 'bg-amber-50 text-amber-600', Journal: 'bg-blue-50 text-blue-600' };
        const cls = colors[params.value] || 'bg-slate-50 text-slate-600';
        return <span className={`px-2 py-0.5 ${cls} text-xs rounded-md font-medium`}>{params.value}</span>;
      },
    },
    {
      field: 'sync_status',
      headerName: 'Sync',
      width: 75,
      cellRenderer: (params) => {
        const s = params.value;
        if (s === 'pending_sync') return <span className="w-2 h-2 bg-amber-400 rounded-full inline-block" title="Pending sync" />;
        if (s === 'synced') return <span className="w-2 h-2 bg-emerald-500 rounded-full inline-block" title="Synced to Tally" />;
        return <span className="w-2 h-2 bg-slate-200 rounded-full inline-block" title="Not synced" />;
      },
    },
  ], [ledgers]);

  const defaultColDef = useMemo(() => ({
    sortable: true,
    resizable: true,
    suppressMovable: true,
  }), []);

  const totalDebit = rowData.reduce((s, r) => s + (r.withdrawal || 0), 0);
  const totalCredit = rowData.reduce((s, r) => s + (r.deposit || 0), 0);
  const mappedCount = rowData.filter((r) => r.is_mapped).length;
  const hasActiveFilters = dateFrom || dateTo || txnType !== 'all' || keyword || mappedFilter !== 'all';
  const fmt = (n) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(n);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-3 animate-fade-in" data-testid="transaction-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button data-testid="back-to-statements" onClick={() => navigate('/statements')}
            className="text-slate-400 hover:text-slate-600 text-sm mb-1 flex items-center gap-1 transition-colors">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
            Back to Statements
          </button>
          <h1 className="font-heading text-2xl font-bold text-slate-900">Transactions</h1>
        </div>
        <div className="flex items-center gap-3">
          <button data-testid="apply-rules-btn" onClick={handleApplyRules}
            className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-lg px-4 py-2 text-sm font-medium transition-colors shadow-sm">
            Apply Rules
          </button>
          <button data-testid="mark-tally-btn" onClick={handleMarkReady} disabled={marking}
            className="bg-accent hover:bg-blue-700 text-white rounded-lg px-5 py-2 text-sm font-medium transition-colors shadow-sm disabled:opacity-50">
            {marking ? 'Marking...' : 'Mark as Ready for Tally'}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-3">
        <div data-testid="kpi-total" className="bg-white rounded-xl border border-slate-200 shadow-sm px-4 py-3">
          <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Rows</p>
          <p className="font-heading text-lg font-bold text-slate-900">{rowData.length}</p>
          {hasActiveFilters && <p className="text-[10px] text-blue-500 font-medium mt-0.5">Filtered: {filteredCount}</p>}
          <p className="text-[10px] text-slate-400">Mapped: {mappedCount}</p>
        </div>
        <div data-testid="kpi-debits" className="bg-white rounded-xl border border-slate-200 shadow-sm px-4 py-3">
          <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Total Debits</p>
          <p className="font-heading text-lg font-bold text-red-600">₹{fmt(totalDebit)}</p>
          {hasActiveFilters && <p className="text-[10px] text-blue-500 font-medium mt-0.5">Filtered: ₹{fmt(filteredDebits)}</p>}
        </div>
        <div data-testid="kpi-credits" className="bg-white rounded-xl border border-slate-200 shadow-sm px-4 py-3">
          <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Total Credits</p>
          <p className="font-heading text-lg font-bold text-emerald-600">₹{fmt(totalCredit)}</p>
          {hasActiveFilters && <p className="text-[10px] text-blue-500 font-medium mt-0.5">Filtered: ₹{fmt(filteredCredits)}</p>}
        </div>
        <div data-testid="kpi-net" className="bg-white rounded-xl border border-slate-200 shadow-sm px-4 py-3">
          <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Net</p>
          <p className={`font-heading text-lg font-bold ${totalCredit - totalDebit >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
            ₹{fmt(Math.abs(totalCredit - totalDebit))}
          </p>
          {hasActiveFilters && <p className="text-[10px] text-blue-500 font-medium mt-0.5">Filtered: ₹{fmt(Math.abs(filteredCredits - filteredDebits))}</p>}
        </div>
      </div>

      {/* Advanced Filter Panel */}
      <div data-testid="filter-panel" className="bg-white rounded-xl border border-slate-200 shadow-sm px-5 py-3">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Filters</span>
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400">From:</label>
            <input data-testid="filter-date-from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
              className="h-8 px-2 rounded-md border border-slate-200 text-xs focus:outline-none focus:ring-1 focus:ring-accent/30" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400">To:</label>
            <input data-testid="filter-date-to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
              className="h-8 px-2 rounded-md border border-slate-200 text-xs focus:outline-none focus:ring-1 focus:ring-accent/30" />
          </div>
          <select data-testid="filter-type" value={txnType} onChange={(e) => setTxnType(e.target.value)}
            className="h-8 px-2 rounded-md border border-slate-200 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-accent/30">
            <option value="all">All Types</option>
            <option value="debit">Debits Only</option>
            <option value="credit">Credits Only</option>
          </select>
          <select data-testid="filter-mapped" value={mappedFilter} onChange={(e) => setMappedFilter(e.target.value)}
            className="h-8 px-2 rounded-md border border-slate-200 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-accent/30">
            <option value="all">All Status</option>
            <option value="mapped">Mapped</option>
            <option value="unmapped">Unmapped</option>
          </select>
          <input data-testid="filter-keyword" type="text" value={keyword} onChange={(e) => setKeyword(e.target.value)}
            placeholder="Search keyword..." className="h-8 px-3 rounded-md border border-slate-200 text-xs w-40 focus:outline-none focus:ring-1 focus:ring-accent/30" />
          {hasActiveFilters && (
            <button data-testid="clear-filters-btn" onClick={clearFilters}
              className="h-8 px-3 bg-red-50 text-red-600 rounded-md text-xs font-medium hover:bg-red-100 transition-colors">
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedRows.length > 0 && (
        <div data-testid="bulk-actions" className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-xl px-5 py-3 animate-fade-in">
          <span className="text-sm font-medium text-accent">{selectedRows.length} selected</span>
          <select data-testid="bulk-ledger-select" value={bulkLedger} onChange={(e) => setBulkLedger(e.target.value)}
            className="h-9 px-3 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-accent/30">
            <option value="">Select ledger...</option>
            {ledgers.map((l) => (<option key={l} value={l}>{l}</option>))}
          </select>
          <button data-testid="bulk-apply-btn" onClick={handleBulkUpdate} disabled={!bulkLedger}
            className="bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-40">
            Apply to Selected
          </button>
        </div>
      )}

      {/* AG Grid */}
      <div className="ag-theme-alpine rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 'calc(100vh - 380px)', width: '100%' }}>
        <AgGridReact
          ref={gridRef}
          modules={[AllCommunityModule]}
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          rowSelection={{ mode: 'multiRow' }}
          suppressRowClickSelection={true}
          onSelectionChanged={onSelectionChanged}
          onCellValueChanged={onCellValueChanged}
          onFilterChanged={onFilterChanged}
          onFirstDataRendered={onFilterChanged}
          isExternalFilterPresent={isExternalFilterPresent}
          doesExternalFilterPass={doesExternalFilterPass}
          animateRows={true}
          enableCellTextSelection={true}
          getRowId={(params) => params.data.transaction_id}
        />
      </div>
    </div>
  );
}
