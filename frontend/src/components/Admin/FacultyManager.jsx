import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { facultyAPI, departmentAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import { useFormCache } from '../../hooks/useFormCache';
import ConfirmationModal from '../Layout/ConfirmationModal';
import CsvUploader from '../Layout/CsvUploader';
import { Edit, Trash2, Plus, Users, Key } from 'lucide-react';
import FacultyAccounts from './FacultyAccounts';

export default function FacultyManager() {
  const [faculty, setFaculty] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editData, setEditData] = useState(null);
  const [activeTab, setActiveTab] = useState('resources'); // 'resources' | 'accounts'
  const { register, handleSubmit, reset, setValue, watch, formState: { errors, isSubmitting } } = useForm();
  const { showToast } = useToast();
  const [serverError, setServerError] = useState('');

  // Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [facultyToDelete, setFacultyToDelete] = useState(null);

  // Watch all form fields for caching
  const formValues = watch();
  
  // Use form cache hook
  const { clearCache } = useFormCache('facultyFormCache', formValues, setValue, showForm, !!editData);

  useEffect(() => { 
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const facRes = await facultyAPI.getAll().catch(err => { console.error('Faculty fail', err); return { data: [] }; });
      setFaculty(facRes.data);

      const deptRes = await departmentAPI.getAll().catch(err => { console.error('Depts fail', err); return { data: [] }; });
      setDepartments(deptRes.data);
    } catch (error) {
      console.error('Failed to load data', error);
      showToast('Failed to load data', 'error');
    }
  };

  const handleDeleteClick = (id) => {
    setFacultyToDelete(id);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!facultyToDelete) return;
    try {
      await facultyAPI.delete(facultyToDelete);
      loadData();
      showToast('Faculty deleted!', 'success');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to delete faculty', 'error');
    }
  };

  const handleEdit = (facultyMember) => {
    setEditData(facultyMember);
    setValue('name', facultyMember.name);
    setValue('email', facultyMember.email);
    setValue('department_id', facultyMember.department_id);
    setValue('max_hours_per_week', facultyMember.max_hours_per_week);
    setServerError('');
    setShowForm(true);
    setTimeout(() => {
        document.querySelector('.main-content')?.scrollTo({ top: 0, behavior: 'smooth' });
    }, 50);
  };

  const onSubmit = async (data) => {
    try {
      setServerError('');
      const payload = {
        ...data,
        department_id: data.department_id || null,
        max_hours_per_week: parseInt(data.max_hours_per_week),
        unavailable_slots: editData ? editData.unavailable_slots : []
      };

      if (editData) {
        await facultyAPI.update(editData.id, payload);
        showToast('Faculty updated!', 'success');
      } else {
        await facultyAPI.create(payload);
        showToast('Faculty created!', 'success');
      }

      reset();
      setEditData(null);
      setShowForm(false);
      clearCache();
      setServerError('');
      loadData();
    } catch (error) {
      const msg = error?.response?.data?.detail || error?.message || 'Failed to save faculty';
      setServerError(msg);
      showToast(msg, 'error');
    }
  };

  // Focus first field with validation error for better UX
  useEffect(() => {
    if (errors && Object.keys(errors).length > 0) {
      const first = Object.keys(errors)[0];
      const el = document.querySelector(`[name="${first}"]`);
      if (el && typeof el.focus === 'function') el.focus();
    }
  }, [errors]);

  return (
    <div>
      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="Delete Faculty"
        message="Are you sure you want to delete this faculty member?"
      />

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Faculty Management</h1>
        
        {/* Tabs */}
        <div className="flex bg-slate-100 p-1 rounded-xl">
           <button 
             onClick={() => setActiveTab('resources')}
             className={`px-4 py-2 flex items-center gap-2 rounded-lg font-bold text-sm transition-all ${activeTab === 'resources' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
           >
             <Users size={16} /> Faculty Staff
           </button>
           <button 
             onClick={() => setActiveTab('accounts')}
             className={`px-4 py-2 flex items-center gap-2 rounded-lg font-bold text-sm transition-all ${activeTab === 'accounts' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
           >
             <Key size={16} /> Login Accounts
           </button>
        </div>
      </div>

      {activeTab === 'resources' ? (
        <>
          <div className="flex justify-end mb-4 gap-2">
            <CsvUploader type="faculty" onSuccess={loadData} />
            <button
              onClick={() => {
                setEditData(null);
                setShowForm(!showForm);
              }}
              className="btn btn-primary flex items-center gap-2"
            >
              {showForm ? 'Cancel' : <><Plus size={20} /> Add Faculty Resource</>}
            </button>
          </div>

      {showForm && (
        <div className="card mb-6">
          <h2 className="text-xl font-bold mb-4">{editData ? 'Edit Faculty' : 'Add New Faculty'}</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Name *</label>
              <input {...register('name', { required: 'Name is required' })} className="input" />
              {errors.name && <p className="text-red-500 text-sm mt-1">{errors.name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Email *</label>
              <input {...register('email', { required: 'Email is required', pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email' } })} type="email" className="input" />
              {errors.email && <p className="text-red-500 text-sm mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Department *</label>
              <select {...register('department_id', { required: 'Department is required' })} className="input"><option value="">Select</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select>
              {errors.department_id && <p className="text-red-500 text-sm mt-1">{errors.department_id.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Max Hours/Week</label>
              <input {...register('max_hours_per_week', { valueAsNumber: true, min: { value: 0, message: 'Must be 0 or more' } })} type="number" defaultValue="20" className="input" />
              {errors.max_hours_per_week && <p className="text-red-500 text-sm mt-1">{errors.max_hours_per_week.message}</p>}
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setEditData(null);
                  reset();
                }}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button type="submit" disabled={isSubmitting} className="btn btn-primary">{isSubmitting ? (editData ? 'Updating...' : 'Adding...') : (editData ? 'Update' : 'Add')}</button>
            </div>
          </form>
          {serverError && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 text-sm text-red-700 rounded">
              <div><strong>Oops — could not save faculty:</strong></div>
              <div className="mt-1">{serverError}</div>
              <div className="mt-2 flex gap-2">
                <button onClick={() => setServerError('')} className="btn btn-secondary">Dismiss</button>
                <button onClick={() => document.querySelector('form')?.scrollIntoView({ behavior: 'smooth' })} className="btn btn-outline">Review form</button>
              </div>
            </div>
          )}
        </div>
      )}

      {faculty.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-xl text-gray-600">There are no faculty members.</p>
          <p className="text-gray-500 mt-2">Kindly add it.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {faculty.map(f => (
            <div key={f.id} className="card relative group hover:shadow-lg transition-shadow">
              <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleEdit(f)}
                  className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-full transition-colors"
                  title="Edit Faculty"
                >
                  <Edit size={18} />
                </button>
                <button
                  onClick={() => handleDeleteClick(f.id)}
                  className="p-1.5 text-red-600 hover:bg-red-50 rounded-full transition-colors"
                  title="Delete Faculty"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <h3 className="text-xl font-bold pr-16">{f.name}</h3>
              <p className="text-gray-600 truncate">{f.email}</p>
              <div className="mt-2 space-y-1 text-sm text-gray-500">
                <p>Dept: <span className="font-medium text-gray-700">{departments.find(d => d.id === f.department_id)?.name || 'Utility/Common'}</span></p>
                <p>Max Hours: <span className="font-medium text-gray-700">{f.max_hours_per_week}/week</span></p>
              </div>
            </div>
          ))}
        </div>
      )}
        </>
      ) : (
        <FacultyAccounts />
      )}
    </div>
  );
}
