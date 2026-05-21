import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { subjectAPI, departmentAPI, batchAPI, facultyAPI, classAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import { useFormCache } from '../../hooks/useFormCache';
import ConfirmationModal from '../Layout/ConfirmationModal';
import { Edit, Trash2, Plus } from 'lucide-react';
import CsvUploader from '../Layout/CsvUploader';

export default function SubjectManager() {
  const [subjects, setSubjects] = useState([]);
  const [classes, setClasses] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [batches, setBatches] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editData, setEditData] = useState(null);
  const { register, handleSubmit, reset, setValue, watch } = useForm();
  const { showToast } = useToast();

  // Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [subjectToDelete, setSubjectToDelete] = useState(null);
  
  // Watch all form fields for caching
  const formValues = watch();
  
  // Use form cache hook
  const { clearCache } = useFormCache('subjectFormCache', formValues, setValue, showForm, !!editData);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const subRes = await subjectAPI.getAll().catch(err => { console.error('Subjects fail', err); return { data: [] }; });
      setSubjects(subRes.data);

      const deptRes = await departmentAPI.getAll().catch(err => { console.error('Depts fail', err); return { data: [] }; });
      setDepartments(deptRes.data);

      const batchRes = await batchAPI.getAll().catch(err => { console.error('Batches fail', err); return { data: [] }; });
      setBatches(batchRes.data);
    } catch (error) {
      console.error('Failed to load data', error);
      showToast('Failed to load data', 'error');
    }
  };

  const handleEdit = (sub) => {
    setEditData(sub);
    setValue('name', sub.name);
    setValue('code', sub.code);
    setValue('department_ids', sub.department_ids && sub.department_ids.length > 0 ? sub.department_ids : (sub.department_id ? [sub.department_id] : []));
    setValue('batch_id', sub.batch_id);
    setValue('hours_per_week', sub.hours_per_week);
    setValue('requires_lab', sub.requires_lab ? 'true' : 'false');
    setShowForm(true);
    setTimeout(() => {
        document.querySelector('.main-content')?.scrollTo({ top: 0, behavior: 'smooth' });
    }, 50);
  };

  const onSubmit = async (data) => {
    try {
      const department_ids = Array.isArray(data.department_ids)
        ? data.department_ids.filter(Boolean)
        : data.department_ids ? [data.department_ids] : [];
      const payload = {
        ...data,
        department_ids,
        department_id: department_ids.length > 0 ? department_ids[0] : null,
        batch_id: data.batch_id || null,
        faculty_id: null,
        hours_per_week: parseInt(data.hours_per_week),
        requires_lab: data.requires_lab === 'true'
      };

      if (editData) {
        await subjectAPI.update(editData.id, payload);
        showToast('Subject updated!', 'success');
      } else {
        await subjectAPI.create(payload);
        showToast('Subject created!', 'success');
      }

      reset();
      setEditData(null);
      setShowForm(false);
      clearCache();
      loadData();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to save subject', 'error');
    }
  };

  const confirmDelete = async () => {
    if (!subjectToDelete) return;
    try {
      await subjectAPI.delete(subjectToDelete);
      loadData();
      showToast('Subject deleted!', 'success');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to delete subject', 'error');
    }
  };

  const handleDeleteClick = (id) => {
    setSubjectToDelete(id);
    setIsDeleteModalOpen(true);
  };

  return (
    <div>
      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="Delete Subject"
        message="Are you sure you want to delete this subject?"
      />

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Subjects</h1>
        <div className="flex gap-2">
          <CsvUploader type="subjects" onSuccess={loadData} />
          <button
            onClick={() => {
              setEditData(null);
              reset();
              setShowForm(!showForm);
            }}
            className="btn btn-primary flex items-center gap-2"
          >
            {showForm ? 'Cancel' : <><Plus size={20} /> Add Subject</>}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h2 className="text-xl font-bold mb-4">{editData ? 'Edit Subject' : 'Add New Subject'}</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-2">Name *</label><input {...register('name', { required: true })} className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Code *</label><input {...register('code', { required: true })} className="input" /></div>
            <div>
              <label className="block text-sm font-medium mb-2">Departments *</label>
              <select {...register('department_ids', { required: true })} multiple size={4} className="input h-32">
                {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Batch *</label>
              <select {...register('batch_id', { required: true })} className="input"><option value="">Select</option>{batches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select>
            </div>
            <div><label className="block text-sm font-medium mb-2">Hours/Week *</label><input {...register('hours_per_week', { required: true })} type="number" className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Lab?</label><select {...register('requires_lab')} className="input"><option value="false">No</option><option value="true">Yes</option></select></div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)} className="btn btn-secondary">Cancel</button>
              <button type="submit" className="btn btn-primary">{editData ? 'Update' : 'Create'}</button>
            </div>
          </form>
        </div>
      )}

      {subjects.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-xl text-gray-600">There are no subjects.</p>
          <p className="text-gray-500 mt-2">Kindly add it.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {subjects.map(sub => (
            <div key={sub.id} className="card relative group hover:shadow-lg transition-shadow">
              <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleEdit(sub)}
                  className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-full transition-colors"
                  title="Edit Subject"
                >
                  <Edit size={18} />
                </button>
                <button
                  onClick={() => handleDeleteClick(sub.id)}
                  className="p-1.5 text-red-600 hover:bg-red-50 rounded-full transition-colors"
                  title="Delete Subject"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <h3 className="text-xl font-bold pr-16">{sub.name}</h3>
              <p>Code: {sub.code}</p>
              <p className="text-sm text-gray-600">
                Departments: {sub.department_ids && sub.department_ids.length > 0 ? sub.department_ids.map(id => departments.find(d => d.id === id)?.name || id).filter(Boolean).join(', ') : departments.find(d => d.id === sub.department_id)?.name}
              </p>
              <p className="text-sm text-gray-600">Batch: {batches.find(b => b.id === sub.batch_id)?.name}</p>
              <p>Hours/Week: {sub.hours_per_week}</p>
              <p>Lab: {sub.requires_lab ? 'Yes' : 'No'}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
