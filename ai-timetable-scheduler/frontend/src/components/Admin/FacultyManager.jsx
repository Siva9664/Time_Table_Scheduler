import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { facultyAPI, departmentAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import ConfirmationModal from '../Layout/ConfirmationModal';

export default function FacultyManager() {
  const [faculty, setFaculty] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset } = useForm();
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

  const onSubmit = async (data) => {
    try {
      await facultyAPI.create({
        ...data,
        department_id: parseInt(data.department_id),
        max_hours_per_week: parseInt(data.max_hours_per_week),
        unavailable_slots: []
      });
      reset();
      setShowForm(false);
      loadData();
      showToast('Faculty created!', 'success');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to create faculty', 'error');
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

      <div className="flex justify-between mb-6">
        <h1 className="text-3xl font-bold">Faculty</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">{showForm ? 'Cancel' : '+ Add'}</button>
      </div>
      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-2">Name *</label><input {...register('name', { required: true })} className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Email *</label><input {...register('email', { required: true })} type="email" className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Department *</label><select {...register('department_id', { required: true })} className="input"><option value="">Select</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
            <div><label className="block text-sm font-medium mb-2">Max Hours/Week</label><input {...register('max_hours_per_week')} type="number" defaultValue="20" className="input" /></div>
            <button type="submit" className="btn btn-primary">Add</button>
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
            <div key={f.id} className="card relative group">
              <button
                onClick={() => handleDeleteClick(f.id)}
                className="absolute top-2 right-2 text-red-500 hover:text-red-700 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete Faculty"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </button>
              <h3 className="text-xl font-bold">{f.name}</h3>
              <p>Email: {f.email}</p>
              <p className="text-sm text-gray-600">Dept: {departments.find(d => d.id === f.department_id)?.name || 'Utility/Common'}</p>
              <p>Max Hours: {f.max_hours_per_week}/week</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
