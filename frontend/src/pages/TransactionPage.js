import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AllCommunityModule, provideGlobalGridOptions } from 'ag-grid-community';
import { AgGridReact } from 'ag-grid-react';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import { transactionsAPI, ledgersAPI, rulesAPI, exportAPI } from '../api/client';
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
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    Promise.all([
      transactionsAPI.get(statementId),
      ledgersAPI.list(),
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

        // Auto-create rule when ledger is mapped
        if (colDef.field === 'ledger' && data.ledger && data.original_description) {
          const keyword = data.merchant || data.original_description.split(/[\s/]+/)[0];
          if (keyword && keyword.length > 2) {
            try {
              await rulesAPI.create({ keyword: keyword.toLowerCase(), ledger: data.ledger });
            } catch { /* ignore rule creation errors */ }
          }
        }
        toast.success('Updated');
      } catch {
        toast.error('Update failed');
      }
    }
  }, []);

  const onSelectionChanged = useCallback(() => {
    const selected = gridRef.current?.api?.getSelectedRows() || [];
    setSelectedRows(selected);
  }, []);

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
    } catch {
      toast.error('Bulk update failed');
    }
  };

  const handleApplyRules = async () => {
    try {
      const res = await rulesAPI.apply(statementId);
      toast.success(res.data.message);
      // Refresh data
      const txnRes = await transactionsAPI.get(statementId);
      setRowData(txnRes.data);
    } catch {
      toast.error('Failed to apply rules');
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await exportAPI.tally(statementId, { company_name: 'My Company', bank_ledger: 'Bank Account' });
      const blob = new Blob([res.data], { type: 'application/xml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tally_export_${statementId.slice(0, 8)}.xml`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Tally XML exported successfully');
    } catch {
      toast.error('Export failed');
    } finally {
      setExporting(false);
    }
  };

  const columnDefs = useMemo(() => [
    {
      headerCheckboxSelection: true,
      checkboxSelection: true,
      width: 50,
      pinned: 'left',
      suppressMenu: true,
      headerClass: 'ag-header-cell-checkbox',
    },
    {
      field: 'date',
      headerName: 'Date',
      width: 115,
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
      field: 'original_description',
      headerName: 'Original',
      flex: 1.5,
      minWidth: 160,
      cellClass: 'text-slate-400 text-xs',
    },
    {
      field: 'merchant',
      headerName: 'Merchant',
      width: 120,
      cellRenderer: (params) => {
        if (!params.value) return <span className="text-slate-300">-</span>;
        return <span className="px-2 py-0.5 bg-blue-50 text-accent text-xs rounded-md font-medium">{params.value}</span>;
      },
    },
    {
      field: 'withdrawal',
      headerName: 'Withdrawal',
      width: 130,
      type: 'numericColumn',
      cellClass: 'amount-debit font-mono text-xs',
      valueFormatter: (p) => p.value > 0 ? `₹${Number(p.value).toLocaleString('en-IN')}` : '',
    },
    {
      field: 'deposit',
      headerName: 'Deposit',
      width: 130,
      type: 'numericColumn',
      cellClass: 'amount-credit font-mono text-xs',
      valueFormatter: (p) => p.value > 0 ? `₹${Number(p.value).toLocaleString('en-IN')}` : '',
    },
    {
      field: 'ledger',
      headerName: 'Ledger',
      flex: 1,
      minWidth: 160,
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
      width: 110,
      editable: true,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: voucherTypes },
      cellRenderer: (params) => {
        const colors = {
          Payment: 'bg-red-50 text-red-600',
          Receipt: 'bg-emerald-50 text-emerald-600',
          Contra: 'bg-amber-50 text-amber-600',
          Journal: 'bg-blue-50 text-blue-600',
        };
        const cls = colors[params.value] || 'bg-slate-50 text-slate-600';
        return <span className={`px-2 py-0.5 ${cls} text-xs rounded-md font-medium`}>{params.value}</span>;
      },
    },
    {
      field: 'is_duplicate',
      headerName: 'Dup',
      width: 60,
      cellRenderer: (params) => {
        if (params.value) return <span className="w-2 h-2 bg-amber-400 rounded-full inline-block" title="Potential duplicate" />;
        return null;
      },
    },
  ], [ledgers]);

  const defaultColDef = useMemo(() => ({
    sortable: true,
    filter: true,
    resizable: true,
    suppressMovable: true,
  }), []);

  const mappedCount = rowData.filter((r) => r.is_mapped).length;
  const totalWithdrawal = rowData.reduce((s, r) => s + (r.withdrawal || 0), 0);
  const totalDeposit = rowData.reduce((s, r) => s + (r.deposit || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in" data-testid="transaction-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            data-testid="back-to-statements"
            onClick={() => navigate('/statements')}
            className="text-slate-400 hover:text-slate-600 text-sm mb-1 flex items-center gap-1 transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
            Back to Statements
          </button>
          <h1 className="font-heading text-2xl font-bold text-slate-900">Transactions</h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            data-testid="apply-rules-btn"
            onClick={handleApplyRules}
            className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-lg px-4 py-2 text-sm font-medium transition-colors shadow-sm"
          >
            Apply Rules
          </button>
          <button
            data-testid="export-tally-btn"
            onClick={handleExport}
            disabled={exporting}
            className="bg-accent hover:bg-blue-700 text-white rounded-lg px-5 py-2 text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
          >
            {exporting ? 'Exporting...' : 'Export Tally XML'}
          </button>
        </div>
      </div>

      {/* Summary Strip */}
      <div className="flex items-center gap-6 bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-3">
        <div className="text-sm">
          <span className="text-slate-500">Total: </span>
          <span className="font-semibold text-slate-900">{rowData.length}</span>
        </div>
        <div className="w-px h-5 bg-slate-200" />
        <div className="text-sm">
          <span className="text-slate-500">Mapped: </span>
          <span className="font-semibold text-emerald-600">{mappedCount}</span>
          <span className="text-slate-400"> / {rowData.length}</span>
        </div>
        <div className="w-px h-5 bg-slate-200" />
        <div className="text-sm">
          <span className="text-slate-500">Withdrawals: </span>
          <span className="font-mono text-red-600 font-medium">₹{totalWithdrawal.toLocaleString('en-IN')}</span>
        </div>
        <div className="w-px h-5 bg-slate-200" />
        <div className="text-sm">
          <span className="text-slate-500">Deposits: </span>
          <span className="font-mono text-emerald-600 font-medium">₹{totalDeposit.toLocaleString('en-IN')}</span>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedRows.length > 0 && (
        <div data-testid="bulk-actions" className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-xl px-5 py-3 animate-fade-in">
          <span className="text-sm font-medium text-accent">{selectedRows.length} selected</span>
          <select
            data-testid="bulk-ledger-select"
            value={bulkLedger}
            onChange={(e) => setBulkLedger(e.target.value)}
            className="h-9 px-3 rounded-lg border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            <option value="">Select ledger...</option>
            {ledgers.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
          <button
            data-testid="bulk-apply-btn"
            onClick={handleBulkUpdate}
            disabled={!bulkLedger}
            className="bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-40"
          >
            Apply to Selected
          </button>
        </div>
      )}

      {/* AG Grid */}
      <div className="ag-theme-alpine rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 'calc(100vh - 320px)', width: '100%' }}>
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
          animateRows={true}
          enableCellTextSelection={true}
          getRowId={(params) => params.data.transaction_id}
          overlayNoRowsTemplate='<span class="text-slate-400 text-sm">No transactions found</span>'
        />
      </div>
    </div>
  );
}
