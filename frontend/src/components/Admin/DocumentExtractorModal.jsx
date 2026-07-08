import React, { useState, useRef } from 'react';
import {
  X,
  Upload,
  Loader2,
  FileSpreadsheet,
  Download,
  Database,
  AlertTriangle,
  CheckCircle,
  Info,
  ChevronRight,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import api from '../../services/api';
import { useToast } from '../../context/ToastContext';

const TABS = [
  { id: 'departments', label: 'Departments', icon: Sparkles, fields: ['name', 'code'] },
  { id: 'batches', label: 'Batches', icon: Sparkles, fields: ['name', 'start_time', 'end_time', 'period_duration'] },
  { id: 'classes', label: 'Classes', icon: Sparkles, fields: ['name', 'section', 'semester', 'student_count', 'department_code', 'batch_name'] },
  { id: 'rooms', label: 'Rooms', icon: Sparkles, fields: ['name', 'code', 'room_type', 'capacity', 'department_code'] },
  { id: 'subjects', label: 'Subjects', icon: Sparkles, fields: ['name', 'code', 'hours_per_week', 'requires_lab', 'department_codes', 'batch_name'] },
  { id: 'faculty', label: 'Faculty', icon: Sparkles, fields: ['name', 'email', 'department_code'] },
  { id: 'mappings', label: 'Mappings', icon: Sparkles, fields: ['subject_code', 'class_name', 'class_section', 'faculty_email', 'room_code'] }
];

const REQUIRED_FIELDS = {
  departments: ['name', 'code'],
  batches: ['name'],
  classes: ['name'],
  rooms: ['name'],
  subjects: ['name', 'code'],
  faculty: ['name', 'email'],
  mappings: ['subject_code', 'class_name', 'faculty_email']
};

export default function DocumentExtractorModal({ isOpen, onClose, onImportSuccess }) {
  const { showToast } = useToast();
  const fileInputRef = useRef(null);
  
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState('');
  const [progress, setProgress] = useState(0);
  const [modelLogs, setModelLogs] = useState('');
  const [extractedData, setExtractedData] = useState(null);
  const [activeTab, setActiveTab] = useState('departments');
  const [warnings, setWarnings] = useState([]);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [useGemini, setUseGemini] = useState(false);
  
  const logsEndRef = useRef(null);

  // Auto-scroll logs
  React.useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [modelLogs]);

  if (!isOpen) return null;

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const resetState = () => {
    setFile(null);
    setExtractedData(null);
    setLoading(false);
    setLoadingStage('');
    setProgress(0);
    setModelLogs('');
    setWarnings([]);
  };

  const startExtraction = async () => {
    if (!file) return;

    setLoading(true);
    setLoadingStage('Starting extraction...');
    setProgress(0);
    setModelLogs('');
    
    const form = new FormData();
    form.append('file', file);
    if (useGemini) {
      form.append('use_gemini', 'true');
    }

    try {
      const token = localStorage.getItem('token');
      // Step 1: Call extract endpoint with fetch to read stream
      const response = await fetch(`${import.meta.env.VITE_API_URL || '/api'}/imports/extract-academic-data`, {
        method: 'POST',
        body: form,
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      });

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch (e) {
          errorData = { detail: response.statusText };
        }
        throw new Error(errorData.detail || 'Failed to extract data');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep last incomplete line in buffer

        for (const line of lines) {
          if (!line.trim()) continue;
          
          try {
            const data = JSON.parse(line);
            
            if (data.status === 'log') {
              setModelLogs(prev => prev + data.text);
            } else if (data.status === 'progress') {
              setLoadingStage(data.message);
              setProgress(data.progress);
            } else if (data.status === 'error') {
              throw new Error(data.error);
            } else if (data.status === 'success') {
              const { extracted_data, warnings: serverWarnings, extractor } = data.data;
              setExtractedData(extracted_data);
              setWarnings(serverWarnings || []);
              const totalItems = Object.values(extracted_data).reduce((sum, arr) => sum + arr.length, 0);
              showToast(`Extracted ${totalItems} items from all sheets using ${extractor}!`, 'success');
              return; // End extraction on success
            }
          } catch (e) {
            console.error('Error parsing stream line:', e, line);
          }
        }
      }
    } catch (err) {
      console.error(err);
      showToast(err.message || 'Data extraction failed', 'error');
    } finally {
      setLoading(false);
      setLoadingStage('');
      setProgress(0);
    }
  };

  const handleCellChange = (tabId, rowIndex, fieldName, value) => {
    const updatedData = { ...extractedData };
    updatedData[tabId][rowIndex][fieldName] = value;
    setExtractedData(updatedData);
  };

  const addRow = (tabId) => {
    const updatedData = { ...extractedData };
    const tabObj = TABS.find(t => t.id === tabId);
    const newRow = {};
    tabObj.fields.forEach(f => {
      newRow[f] = f === 'capacity' || f === 'semester' || f === 'student_count' || f === 'hours_per_week' || f === 'period_duration' ? 0 : '';
    });
    updatedData[tabId] = [...updatedData[tabId], newRow];
    setExtractedData(updatedData);
  };

  const deleteRow = (tabId, rowIndex) => {
    const updatedData = { ...extractedData };
    updatedData[tabId] = updatedData[tabId].filter((_, idx) => idx !== rowIndex);
    setExtractedData(updatedData);
  };

  const downloadCSVs = async () => {
    if (!extractedData) return;
    try {
      showToast('Generating zip file...', 'info');
      const response = await api.post('/imports/download-filled-templates', extractedData, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'extracted_academic_templates.zip');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      showToast('CSV templates downloaded successfully!', 'success');
    } catch (err) {
      showToast('Failed to download ZIP file.', 'error');
    }
  };

  const getMissingFieldsCount = () => {
    if (!extractedData) return 0;
    let count = 0;
    Object.keys(REQUIRED_FIELDS).forEach(tabId => {
      const rows = extractedData[tabId] || [];
      const reqs = REQUIRED_FIELDS[tabId];
      rows.forEach(row => {
        reqs.forEach(field => {
          const val = row[field];
          if (val === undefined || val === null || (typeof val === 'string' && val.trim() === '')) {
            count++;
          }
        });
      });
    });
    return count;
  };

  const importToDatabase = async () => {
    if (!extractedData) return;
    
    const missingCount = getMissingFieldsCount();
    if (missingCount > 0) {
      showToast(`Please fill in all ${missingCount} highlighted required fields before syncing.`, 'error');
      return;
    }

    setImporting(true);
    try {
      const res = await api.post('/imports/import-extracted-data', extractedData);
      setImportResult(res.data);
      if (res.data.error_count === 0) {
        showToast(`Imported ${res.data.imported} records successfully!`, 'success');
        if (onImportSuccess) onImportSuccess();
      } else {
        showToast(`Imported ${res.data.imported} records with some errors.`, 'warning');
      }
    } catch (err) {
      showToast(err.response?.data?.detail || 'Import process encountered an error', 'error');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-6xl h-[90vh] bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden border border-slate-100 animate-scale-up">
        
        {/* Header */}
        <header className="px-8 py-5 border-b border-slate-100 flex justify-between items-center bg-gradient-to-r from-violet-50/50 to-indigo-50/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-violet-600 rounded-xl flex items-center justify-center text-white shadow-md">
              <Sparkles size={20} />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-800 tracking-tight">AI Document Extractor & Template Filler</h2>
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Powered by PaddleOCR & Ollama</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-full border border-slate-100 flex items-center justify-center hover:bg-slate-50 hover:text-rose-500 transition-colors shadow-sm bg-white"
          >
            <X size={18} />
          </button>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          {!extractedData && !loading && (
            <div className="max-w-2xl mx-auto mt-10">
              {/* Upload Dropzone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-3 border-dashed rounded-3xl p-12 text-center cursor-pointer transition-all duration-300 ${
                  dragging
                    ? 'border-violet-500 bg-violet-50/50 scale-[1.01]'
                    : file
                    ? 'border-emerald-500 bg-emerald-50/10'
                    : 'border-slate-200 hover:border-violet-400 hover:bg-slate-50/50'
                }`}
              >
                 <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="flex flex-col items-center gap-4">
                  <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-lg transition-transform ${
                    file ? 'bg-emerald-500 text-white' : 'bg-violet-100 text-violet-600'
                  }`}>
                    <Upload size={30} />
                  </div>
                  {file ? (
                    <div>
                      <p className="text-lg font-bold text-emerald-800">{file.name}</p>
                      <p className="text-sm font-medium text-emerald-600 mt-1">{(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to Extract</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-lg font-extrabold text-slate-700">Drag & Drop Academic File or Scanned Image</p>
                      <p className="text-sm font-medium text-slate-400 mt-2">Supports PDF, Images, Excel, Word, or Text files up to 15MB</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Action Button */}
              {file && (
                <div className="mt-8 flex flex-col items-center">
                  
                  {/* Gemini API Toggle */}
                  <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl p-4 mb-6 shadow-sm">
                    <label className="flex items-center justify-between cursor-pointer">
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-slate-700">Use Gemini API</span>
                        <span className="text-xs text-slate-500 mt-0.5">Much faster extraction using Gemini API</span>
                      </div>
                      <div className="relative">
                        <input
                          type="checkbox"
                          className="sr-only"
                          checked={useGemini}
                          onChange={(e) => setUseGemini(e.target.checked)}
                        />
                        <div className={`block w-10 h-6 rounded-full transition-colors ${useGemini ? 'bg-violet-500' : 'bg-slate-300'}`}></div>
                        <div className={`absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${useGemini ? 'transform translate-x-4' : ''}`}></div>
                      </div>
                    </label>
                  </div>

                  <button
                    onClick={startExtraction}
                    className="flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white text-base font-black rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-200 active:scale-95 group"
                  >
                    Start Extraction Pipeline
                    <ArrowRight size={18} className="transform group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Loading state */}
          {/* Loading state */}
          {loading && (
            <div className="flex flex-col items-center justify-center p-8 space-y-6 w-full max-w-2xl mx-auto">
              <Loader2 className="animate-spin text-violet-600" size={48} />
              <div className="text-center w-full">
                <p className="text-xl font-black text-slate-800 mb-2">Extracting Data...</p>
                <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden my-4 shadow-inner">
                  <div 
                    className="bg-gradient-to-r from-violet-500 to-indigo-500 h-full rounded-full transition-all duration-300 ease-out relative"
                    style={{ width: `${progress}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                  </div>
                </div>
                <div className="flex justify-between text-xs font-bold text-slate-400 mb-6">
                  <span>{loadingStage}</span>
                  <span>{progress}%</span>
                </div>
                
                {/* Live Model Logs */}
                <div className="w-full bg-slate-900 rounded-xl overflow-hidden shadow-xl border border-slate-700 flex flex-col h-48">
                  <div className="bg-slate-800 px-4 py-2 flex items-center justify-between text-xs font-bold text-slate-400 border-b border-slate-700">
                    <span className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                      Live AI Logs
                    </span>
                    <span>Qwen2.5-VL</span>
                  </div>
                  <div className="p-4 text-emerald-400 font-mono text-xs overflow-y-auto h-full text-left whitespace-pre-wrap flex-1 custom-scrollbar">
                    {modelLogs || 'Waiting for AI response stream...'}
                    <div ref={logsEndRef} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Results display */}
          {extractedData && (
            <div className="h-full flex flex-col space-y-6">
              
              {/* Warnings Banner if any */}
              {warnings.length > 0 && (
                <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 flex gap-3 text-amber-800 text-sm">
                  <AlertTriangle size={20} className="shrink-0 text-amber-500" />
                  <div>
                    <p className="font-extrabold">OCR Warnings / Remarks</p>
                    <ul className="list-disc pl-5 mt-1 space-y-0.5 font-medium">
                      {warnings.map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Tab Navigation */}
              <div className="flex overflow-x-auto gap-2 pb-1 border-b border-slate-100">
                {TABS.map(tab => {
                  const count = extractedData[tab.id]?.length || 0;
                  const isActive = activeTab === tab.id;
                  
                  // Count missing fields in this tab
                  let missingInTab = 0;
                  const reqs = REQUIRED_FIELDS[tab.id] || [];
                  (extractedData[tab.id] || []).forEach(row => {
                    reqs.forEach(f => {
                      const val = row[f];
                      if (val === undefined || val === null || (typeof val === 'string' && val.trim() === '')) {
                        missingInTab++;
                      }
                    });
                  });

                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center gap-2 px-5 py-3 rounded-t-xl font-bold text-sm transition-all duration-200 border-b-2 whitespace-nowrap ${
                        isActive
                          ? 'border-violet-600 text-violet-600 bg-violet-50/30'
                          : 'border-transparent text-slate-400 hover:text-slate-600 hover:bg-slate-50/50'
                      }`}
                    >
                      {tab.label}
                      <span className={`px-2 py-0.5 text-xs font-black rounded-full ${
                        isActive ? 'bg-violet-100 text-violet-600' : 'bg-slate-100 text-slate-500'
                      }`}>
                        {count}
                      </span>
                      {missingInTab > 0 && (
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse border border-white" title={`${missingInTab} missing required value(s)`} />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Active Tab Preview Table */}
              <div className="flex-1 min-h-[300px] border border-slate-100 rounded-2xl overflow-hidden bg-white flex flex-col">
                <div className="flex justify-between items-center px-6 py-4 bg-slate-50 border-b border-slate-100">
                  <span className="text-xs font-black uppercase text-slate-400 tracking-wider">
                    Extracted {TABS.find(t => t.id === activeTab).label} List
                  </span>
                  <button
                    onClick={() => addRow(activeTab)}
                    className="text-xs font-extrabold text-violet-600 hover:text-violet-700 bg-violet-50 hover:bg-violet-100 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    + Add Row
                  </button>
                </div>
                
                <div className="flex-1 overflow-auto max-h-[350px]">
                  <table className="w-full text-left border-collapse text-sm">
                    <thead>
                      <tr className="bg-slate-50/50 text-slate-500 font-extrabold border-b border-slate-100">
                        {TABS.find(t => t.id === activeTab).fields.map(field => (
                          <th key={field} className="px-6 py-3 border-r border-slate-100 capitalize">{field.replace('_', ' ')}</th>
                        ))}
                        <th className="px-6 py-3 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {extractedData[activeTab]?.length === 0 ? (
                        <tr>
                          <td colSpan={TABS.find(t => t.id === activeTab).fields.length + 1} className="px-6 py-10 text-center font-bold text-slate-400">
                            No records extracted for this template category. Use the "+ Add Row" button above to insert one manually.
                          </td>
                        </tr>
                      ) : (
                        extractedData[activeTab]?.map((row, rowIndex) => (
                          <tr key={rowIndex} className="hover:bg-slate-50/40 transition-colors">
                            {TABS.find(t => t.id === activeTab).fields.map(field => {
                              const isRequired = REQUIRED_FIELDS[activeTab]?.includes(field);
                              const isEmpty = row[field] === undefined || row[field] === null || (typeof row[field] === 'string' && row[field].trim() === '');
                              const hasError = isRequired && isEmpty;
                              
                              return (
                                <td key={field} className={`px-4 py-2 border-r border-slate-100 ${hasError ? 'bg-rose-50/10' : ''}`}>
                                  <input
                                    type={typeof row[field] === 'number' ? 'number' : 'text'}
                                    value={row[field] ?? ''}
                                    onChange={(e) => handleCellChange(activeTab, rowIndex, field, e.target.type === 'number' ? Number(e.target.value) : e.target.value)}
                                    placeholder={isRequired ? 'Required' : ''}
                                    className={`w-full px-2 py-1 bg-transparent border rounded font-semibold text-slate-700 outline-none transition-all ${
                                      hasError
                                        ? 'border-rose-400 bg-rose-50/30 hover:border-rose-500 focus:border-rose-500 placeholder-rose-400'
                                        : 'border-transparent hover:border-slate-200 focus:bg-white focus:border-violet-500'
                                    }`}
                                  />
                                </td>
                              );
                            })}
                            <td className="px-4 py-2 text-center">
                              <button
                                onClick={() => deleteRow(activeTab, rowIndex)}
                                className="text-xs font-bold text-rose-500 hover:text-rose-700 px-2 py-1 rounded bg-rose-50 hover:bg-rose-100 transition-colors"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Import Results Banner */}
              {importResult && (
                <div className={`p-5 rounded-2xl border flex gap-4 ${
                  importResult.error_count === 0
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : 'bg-amber-50 border-amber-200 text-amber-800'
                }`}>
                  {importResult.error_count === 0 ? (
                    <CheckCircle className="text-emerald-500 shrink-0" size={24} />
                  ) : (
                    <Info className="text-amber-500 shrink-0" size={24} />
                  )}
                  <div className="flex-1">
                    <p className="font-extrabold text-base">Database Sync Completed</p>
                    <p className="text-sm font-semibold mt-1">
                      Successfully imported <strong className="font-black text-slate-900">{importResult.imported}</strong> record(s) across all active tables ({importResult.skipped} skipped).
                    </p>
                    {importResult.error_count > 0 && (
                      <div className="mt-3">
                        <p className="font-extrabold text-xs uppercase tracking-wider text-rose-700">Errors Encountered ({importResult.error_count}):</p>
                        <div className="mt-1 space-y-1 max-h-24 overflow-y-auto text-xs font-mono bg-white/60 p-3 rounded-lg border border-slate-200">
                          {Object.entries(importResult.results || {}).map(([key, res]) => (
                            res.errors?.map((err, i) => {
                              const msg = typeof err === 'object' ? err.message : err;
                              const row = typeof err === 'object' && err.row ? ` (row ${err.row})` : '';
                              return (
                                <div key={`${key}-${i}`} className="text-rose-600">[{key.toUpperCase()}]{row} {msg}</div>
                              );
                            })
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <footer className="px-8 py-5 border-t border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div className="flex items-center gap-4">
            {extractedData && (
              <button
                onClick={() => {
                  setExtractedData(null);
                  setFile(null);
                  setImportResult(null);
                }}
                className="text-sm font-extrabold text-slate-400 hover:text-slate-600 px-4 py-2 hover:bg-slate-100 rounded-xl transition-all"
              >
                Clear / Upload Another File
              </button>
            )}
            
            {extractedData && (() => {
              const missingCount = getMissingFieldsCount();
              if (missingCount > 0) {
                return (
                  <span className="flex items-center gap-1.5 text-xs font-black text-rose-600 bg-rose-50 border border-rose-100 px-3 py-1.5 rounded-xl animate-pulse">
                    <AlertTriangle size={14} className="shrink-0" />
                    {missingCount} required field(s) empty
                  </span>
                );
              }
              return null;
            })()}
          </div>
          <div className="flex gap-3">
            {extractedData ? (
              <>
                <button
                  onClick={downloadCSVs}
                  className="flex items-center gap-2 px-6 py-3 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-extrabold text-sm rounded-xl shadow-sm transition-all duration-150 active:scale-95"
                >
                  <Download size={16} />
                  Download Filled CSVs
                </button>
                <button
                  onClick={importToDatabase}
                  disabled={importing}
                  className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white font-black text-sm rounded-xl shadow-md hover:shadow-lg transition-all duration-150 active:scale-95 disabled:opacity-55 disabled:active:scale-100"
                >
                  {importing ? (
                    <>
                      <Loader2 className="animate-spin" size={16} />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <Database size={16} />
                      Sync to Database
                    </>
                  )}
                </button>
              </>
            ) : (
              <button
                onClick={onClose}
                className="px-6 py-3 border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 font-extrabold text-sm rounded-xl shadow-sm transition-all duration-150 active:scale-95"
              >
                Cancel
              </button>
            )}
          </div>
        </footer>

      </div>
    </div>
  );
}
