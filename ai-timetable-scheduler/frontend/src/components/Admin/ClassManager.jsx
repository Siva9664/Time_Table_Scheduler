import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { classAPI, departmentAPI, batchAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import ConfirmationModal from '../Layout/ConfirmationModal';
import { Edit, Trash2, Plus } from 'lucide-react';

export default function ClassManager() {
  const [classes, setClasses] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [batches, setBatches] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editData, setEditData] = useState(null);
  const { register, handleSubmit, reset, setValue } = useForm();
  const { showToast } = useToast();

  // Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [classToDelete, setClassToDelete] = useState(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const classRes = await classAPI.getAll().catch(err => { console.error('Classes fail', err); return { data: [] }; });
      setClasses(classRes.data);

      const deptRes = await departmentAPI.getAll().catch(err => { console.error('Depts fail', err); return { data: [] }; });
      setDepartments(deptRes.data);

      const batchRes = await batchAPI.getAll().catch(err => { console.error('Batch fail', err); return { data: [] }; });
      setBatches(batchRes.data);
    } catch (error) {
      console.error('Failed to load data', error);
      showToast('Failed to load data', 'error');
    }
  };

  const handleEdit = (cls) => {
    setEditData(cls);
    setValue('name', cls.name);
    setValue('section', cls.section);
    setValue('department_id', cls.department_id);
    setValue('batch_id', cls.batch_id);
    setValue('semester', cls.semester);
    setValue('student_count', cls.student_count);
    setShowForm(true);
  };

  const onSubmit = async (data) => {
    try {
      const payload = {
        ...data,
        department_id: parseInt(data.department_id),
        semester: parseInt(data.semester),
        student_count: parseInt(data.student_count),
        batch_id: data.batch_id ? parseInt(data.batch_id) : null
      };

      if (editData) {
        await classAPI.update(editData.id, payload);
        showToast('Class updated!', 'success');
      } else {
        await classAPI.create(payload);
        showToast('Class created!', 'success');
      }

      reset();
      setEditData(null);
      setShowForm(false);
      loadData();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to save class', 'error');
    }
  };

  const confirmDelete = async () => {
    if (!classToDelete) return;
    try {
      await classAPI.delete(classToDelete);
      loadData();
      showToast('Class deleted!', 'success');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to delete class', 'error');
    }
  };

  const handleDeleteClick = (id) => {
    setClassToDelete(id);
    setIsDeleteModalOpen(true);
  };

  const getBatchName = (batchId) => {
    const b = batches.find(b => b.id === batchId);
    return b ? b.name : '-';
  };

  return (
    <div>
      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="Delete Class"
        message="Are you sure you want to delete this class? This action cannot be undone."
      />

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Classes</h1>
        <button
          onClick={() => {
            setEditData(null);
            reset();
            setShowForm(!showForm);
          }}
          className="btn btn-primary flex items-center gap-2"
        >
          {showForm ? 'Cancel' : <><Plus size={20} /> Add Class</>}
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h2 className="text-xl font-bold mb-4">{editData ? 'Edit Class' : 'Add New Class'}</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-2">Name *</label><input {...register('name', { required: true })} className="input" placeholder="B.Tech 2nd Year" /></div>
            <div><label className="block text-sm font-medium mb-2">Section</label><input {...register('section')} className="input" placeholder="A" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Department *</label>
                <select {...register('department_id', { required: true })} className="input">
                  <option value="">Select</option>
                  {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Batch Config</label>
                <select {...register('batch_id')} className="input">
                  <option value="">Default (Global Settings)</option>
                  {batches.map(b => <option key={b.id} value={b.id}>{b.name} ({b.start_time}-{b.end_time})</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div><label className="block text-sm font-medium mb-2">Semester</label><input {...register('semester')} type="number" className="input" /></div>
              <div><label className="block text-sm font-medium mb-2">Students</label><input {...register('student_count')} type="number" className="input" /></div>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)} className="btn btn-secondary">Cancel</button>
              <button type="submit" className="btn btn-primary">{editData ? 'Update' : 'Create'}</button>
            </div>
          </form>
        </div>
      )}

      {classes.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-xl text-gray-600">There are no classes.</p>
          <p className="text-gray-500 mt-2">Kindly add it.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {classes.map(cls => (
            <div key={cls.id} className="card relative group hover:shadow-lg transition-shadow">
              <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleEdit(cls)}
                  className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-full transition-colors"
                  title="Edit Class"
                >
                  <Edit size={18} />
                </button>
                <button
                  onClick={() => handleDeleteClick(cls.id)}
                  className="p-1.5 text-red-600 hover:bg-red-50 rounded-full transition-colors"
                  title="Delete Class"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <h3 className="text-xl font-bold pr-16">{cls.name} {cls.section}</h3>
              <div className="mt-2 space-y-1 text-sm text-gray-600">
                <p>Semester: <span className="font-medium text-gray-800">{cls.semester}</span></p>
                <p>Students: <span className="font-medium text-gray-800">{cls.student_count}</span></p>
                <p>Batch: <span className="font-medium text-gray-800">{getBatchName(cls.batch_id)}</span></p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

