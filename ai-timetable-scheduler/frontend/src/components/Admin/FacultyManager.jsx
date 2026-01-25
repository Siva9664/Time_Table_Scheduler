import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { facultyAPI, departmentAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import ConfirmationModal from '../Layout/ConfirmationModal';
import { Edit, Trash2, Plus } from 'lucide-react';

export default function FacultyManager() {
  const [faculty, setFaculty] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editData, setEditData] = useState(null); // Track item being edited
  const { register, handleSubmit, reset, setValue } = useForm();
  const { showToast } = useToast();

  // Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [facultyToDelete, setFacultyToDelete] = useState(null);

  useEffect(() => { loadData(); }, []);

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
    setShowForm(true);
  };

  const onSubmit = async (data) => {
    try {
      const payload = {
        ...data,
        department_id: parseInt(data.department_id),
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
      loadData();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to save faculty', 'error');
    }
  };

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
        <h1 className="text-3xl font-bold">Faculty</h1>
        <button
          onClick={() => {
            setEditData(null);
            reset();
            setShowForm(!showForm);
          }}
          className="btn btn-primary flex items-center gap-2"
        >
          {showForm ? 'Cancel' : <><Plus size={20} /> Add Faculty</>}
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h2 className="text-xl font-bold mb-4">{editData ? 'Edit Faculty' : 'Add New Faculty'}</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-2">Name *</label><input {...register('name', { required: true })} className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Email *</label><input {...register('email', { required: true })} type="email" className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Department *</label><select {...register('department_id', { required: true })} className="input"><option value="">Select</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
            <div><label className="block text-sm font-medium mb-2">Max Hours/Week</label><input {...register('max_hours_per_week')} type="number" defaultValue="20" className="input" /></div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)} className="btn btn-secondary">Cancel</button>
              <button type="submit" className="btn btn-primary">{editData ? 'Update' : 'Add'}</button>
            </div>
          </form>
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
    </div>
  );
}
