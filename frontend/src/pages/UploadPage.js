import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { uploadAPI } from '../api/client';
import { toast } from 'sonner';

export default function UploadPage() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const navigate = useNavigate();

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setSelectedFile(accepted[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024,
    onDropRejected: (rejections) => {
      const err = rejections[0]?.errors[0];
      if (err?.code === 'file-too-large') toast.error('File too large. Max 20MB.');
      else if (err?.code === 'file-invalid-type') toast.error('Unsupported file type. Use .xlsx, .xls, .csv, or .pdf');
      else toast.error('File rejected');
    },
  });

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setProgress(10);

    const interval = setInterval(() => {
      setProgress((p) => Math.min(p + 15, 85));
    }, 400);

    try {
      const res = await uploadAPI.upload(selectedFile);
      clearInterval(interval);
      setProgress(100);
      toast.success(`Parsed ${res.data.total_transactions} transactions from ${res.data.bank_detected} format`);
      setTimeout(() => {
        navigate(`/statements/${res.data.statement.statement_id}`);
      }, 600);
    } catch (err) {
      clearInterval(interval);
      setProgress(0);
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const fileExt = selectedFile?.name?.split('.').pop()?.toUpperCase() || '';
  const fileSize = selectedFile ? (selectedFile.size / 1024).toFixed(1) + ' KB' : '';

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in" data-testid="upload-page">
      <div>
        <h1 className="font-heading text-3xl font-bold text-slate-900">Upload Statement</h1>
        <p className="text-slate-500 mt-1">Upload a bank statement file to parse and process transactions</p>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        data-testid="file-dropzone"
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200
          ${isDragActive ? 'border-accent bg-blue-50' : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'}`}
      >
        <input {...getInputProps()} data-testid="file-input" />
        <div className="flex flex-col items-center gap-4">
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${isDragActive ? 'bg-accent/10' : 'bg-slate-100'}`}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={isDragActive ? '#2563eb' : '#94a3b8'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          {isDragActive ? (
            <p className="text-accent font-medium">Drop your file here</p>
          ) : (
            <>
              <div>
                <p className="text-slate-700 font-medium">Drag & drop your bank statement</p>
                <p className="text-slate-400 text-sm mt-1">or click to browse</p>
              </div>
              <div className="flex gap-2">
                {['XLSX', 'XLS', 'CSV', 'PDF'].map((ext) => (
                  <span key={ext} className="px-2.5 py-1 bg-slate-100 text-slate-500 text-xs rounded-md font-medium">{ext}</span>
                ))}
              </div>
              <p className="text-slate-400 text-xs">Max file size: 20MB</p>
            </>
          )}
        </div>
      </div>

      {/* Selected File */}
      {selectedFile && (
        <div data-testid="selected-file" className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 animate-fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center">
                <span className="text-accent font-mono text-xs font-bold">{fileExt}</span>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">{selectedFile.name}</p>
                <p className="text-xs text-slate-400">{fileSize}</p>
              </div>
            </div>
            <button
              data-testid="remove-file-btn"
              onClick={(e) => { e.stopPropagation(); setSelectedFile(null); setProgress(0); }}
              className="text-slate-400 hover:text-red-500 transition-colors p-1"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          {/* Progress Bar */}
          {uploading && (
            <div className="mt-4">
              <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-slate-400 mt-2">
                {progress < 90 ? 'Parsing statement...' : 'Finalizing...'}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Upload Button */}
      <button
        data-testid="upload-submit-btn"
        onClick={handleUpload}
        disabled={!selectedFile || uploading}
        className="w-full h-12 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
      >
        {uploading ? 'Processing...' : 'Upload & Parse Statement'}
      </button>

      {/* Supported Banks */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="font-heading text-sm font-semibold text-slate-900 mb-3">Supported Bank Formats</h3>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {['HDFC', 'ICICI', 'SBI', 'Axis', 'Kotak', 'Generic'].map((bank) => (
            <div key={bank} className="flex items-center justify-center py-2 px-3 bg-slate-50 rounded-lg text-xs font-medium text-slate-600 border border-slate-100">
              {bank}
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-3">Auto-detects bank format from column headers. Generic parser works as fallback.</p>
      </div>
    </div>
  );
}
