import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { classAPI, departmentAPI, batchAPI } from '../../services/api';

export default function ClassManager() {
  const [classes, setClasses] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [batches, setBatches] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset } = useForm();

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
    }
  };

  const onSubmit = async (data) => {
    try {
      await classAPI.create({
        ...data,
        department_id: parseInt(data.department_id),
        semester: parseInt(data.semester),
        student_count: parseInt(data.student_count),
        batch_id: data.batch_id ? parseInt(data.batch_id) : null
      });
      reset();
      setShowForm(false);
      loadData();
      alert('Class created!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to create class');
    }
  };

  const handleDelete = async (id) => {
    if (confirm('Delete?')) {
      await classAPI.delete(id);
      loadData();
    }
  };

  const getBatchName = (batchId) => {
    const b = batches.find(b => b.id === batchId);
    return b ? b.name : '-';
  };

  return (
    <div>
      <div className="flex justify-between mb-6">
        <h1 className="text-3xl font-bold">Classes</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">{showForm ? 'Cancel' : '+ Add Class'}</button>
      </div>
      {showForm && (
        <div className="card mb-6">
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
            <button type="submit" className="btn btn-primary">Create</button>
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
            <div key={cls.id} className="card">
              <div className="flex justify-between mb-2">
                <h3 className="text-xl font-bold">{cls.name} {cls.section}</h3>
                <button onClick={() => handleDelete(cls.id)} className="text-red-600 hover:text-red-800 font-semibold">Delete</button>
              </div>
              <p>Semester: {cls.semester}</p>
              <p>Students: {cls.student_count}</p>
              <p className="text-sm text-gray-500 mt-2">Batch: {getBatchName(cls.batch_id)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

