import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { departmentAPI } from '../../services/api';

export default function DepartmentManager() {
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  useEffect(() => {
    loadDepartments();
  }, []);

  const loadDepartments = async () => {
    try {
      const response = await departmentAPI.getAll();
      setDepartments(response.data);
    } catch (error) {
      console.error('Failed to load departments', error);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (data) => {
    try {
      await departmentAPI.create(data);
      reset();
      setShowForm(false);
      loadDepartments();
      alert('Department created!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to create');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this department?')) return;
    try {
      await departmentAPI.delete(id);
      loadDepartments();
      alert('Deleted!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to delete');
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Departments</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">
          {showForm ? 'Cancel' : '+ Add Department'}
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h2 className="text-xl font-semibold mb-4">Add New Department</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Name *</label>
              <input {...register('name', { required: true })} className="input" placeholder="Computer Science" />
              {errors.name && <p className="text-red-500 text-sm">Name required</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Code *</label>
              <input {...register('code', { required: true })} className="input" placeholder="CSE" />
              {errors.code && <p className="text-red-500 text-sm">Code required</p>}
            </div>
            <button type="submit" className="btn btn-primary">Create</button>
          </form>
        </div>
      )}

      {loading ? <div className="text-center py-12">Loading...</div> : departments.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-xl text-gray-600">There are no departments.</p>
          <p className="text-gray-500 mt-2">Kindly add it.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {departments.map((dept) => (
            <div key={dept.id} className="card">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-xl font-bold">{dept.name}</h3>
                <button onClick={() => handleDelete(dept.id)} className="text-red-600 hover:text-red-800 font-semibold">Delete</button>
              </div>
              <p>Code: <span className="font-semibold">{dept.code}</span></p>
              <p className="text-sm text-gray-500 mt-2">Created: {new Date(dept.created_at).toLocaleDateString()}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
