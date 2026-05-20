import React, { useRef, useState } from 'react';
import { useToast } from '../../context/ToastContext';

export default function CsvUploader({ type }) {
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
      const res = await fetch('/imports/upload', { method: 'POST', body: form });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      showToast(`Imported ${data.imported} ${data.type}`, 'success');
      window.location.reload();
    } catch (err) {
      console.error(err);
      showToast('CSV upload failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ml-2">
      <input ref={inputRef} type="file" accept=".csv" onChange={handleFile} style={{ display: 'none' }} />
      <button
        onClick={() => inputRef.current && inputRef.current.click()}
        className="btn btn-primary"
        title={`Upload ${type} CSV`}
        disabled={loading}
      >
        {loading ? 'Uploading...' : 'Upload CSV'}
      </button>
    </div>
  );
}
