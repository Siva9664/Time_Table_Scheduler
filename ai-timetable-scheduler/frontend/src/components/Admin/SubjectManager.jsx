import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { subjectAPI, departmentAPI, batchAPI, facultyAPI, classAPI } from '../../services/api';

export default function SubjectManager() {
  const [subjects, setSubjects] = useState([]);
  const [classes, setClasses] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [batches, setBatches] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset } = useForm();

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
    }
  };

  const onSubmit = async (data) => {
    try {
      await subjectAPI.create({
        ...data,
        department_id: parseInt(data.department_id),
        batch_id: parseInt(data.batch_id),
        faculty_id: null, // explicit null
        hours_per_week: parseInt(data.hours_per_week),
        requires_lab: data.requires_lab === 'true'
      });
      reset();
      setShowForm(false);
      loadData();
      alert('Subject created!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to create subject');
    }
  };

  return (
    <div>
      <div className="flex justify-between mb-6">
        <h1 className="text-3xl font-bold">Subjects</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">{showForm ? 'Cancel' : '+ Add'}</button>
      </div>
      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-2">Name *</label><input {...register('name', { required: true })} className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Code *</label><input {...register('code', { required: true })} className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Department *</label><select {...register('department_id', { required: true })} className="input"><option value="">Select</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
            <div><label className="block text-sm font-medium mb-2">Batch *</label><select {...register('batch_id', { required: true })} className="input"><option value="">Select</option>{batches.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
            <div><label className="block text-sm font-medium mb-2">Hours/Week *</label><input {...register('hours_per_week', { required: true })} type="number" className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Lab?</label><select {...register('requires_lab')} className="input"><option value="false">No</option><option value="true">Yes</option></select></div>
            <button type="submit" className="btn btn-primary">Create</button>
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
            <div key={sub.id} className="card">
              <h3 className="text-xl font-bold">{sub.name}</h3>
              <p>Code: {sub.code}</p>
              <p className="text-sm text-gray-600">Dept: {departments.find(d => d.id === sub.department_id)?.name}</p>
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
