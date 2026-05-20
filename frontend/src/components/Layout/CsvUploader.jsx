import React, { useRef, useState } from 'react';
import { useToast } from '../../context/ToastContext';
import { Upload } from 'lucide-react';

export default function CsvUploader({ type, onSuccess, className, style }) {
  const inputRef = useRef();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);

  const handleFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('type', type);
    form.append('file', file);
    setLoading(true);
    try {
      const res = await fetch('/api/imports/upload', { method: 'POST', body: form });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      showToast(`Imported ${data.imported} ${data.type}`, 'success');
      // Prefer callback (no full-page reload), fall back to reload if none provided
      if (onSuccess) {
        onSuccess();
      } else {
        window.location.reload();
      }
    } catch (err) {
      console.error(err);
      showToast('CSV upload failed', 'error');
    } finally {
      setLoading(false);
      // Reset file input so same file can be re-uploaded
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div>
      <input ref={inputRef} type="file" accept=".csv" onChange={handleFile} style={{ display: 'none' }} />
      <button
        onClick={() => inputRef.current && inputRef.current.click()}
        className={className || "btn btn-secondary flex items-center gap-2"}
        style={style}
        title={`Upload ${type} CSV`}
        disabled={loading}
      >
        <Upload size={16} />
        {loading ? 'Uploading...' : 'Upload CSV'}
      </button>
    </div>
  );
}
