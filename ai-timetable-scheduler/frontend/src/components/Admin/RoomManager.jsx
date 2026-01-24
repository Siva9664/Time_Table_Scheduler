import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { roomAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';

export default function RoomManager() {
  const [rooms, setRooms] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const { register, handleSubmit, reset } = useForm();
  const { showToast } = useToast();

  useEffect(() => { loadRooms(); }, []);

  const loadRooms = async () => {
    try {
      const res = await roomAPI.getAll();
      setRooms(res.data);
    } catch (error) {
      console.error('Failed to load rooms', error);
      showToast('Failed to load rooms', 'error');
    }
  };

  const onSubmit = async (data) => {
    try {
      await roomAPI.create({ ...data, capacity: parseInt(data.capacity), has_projector: data.has_projector === 'true', has_computers: data.has_computers === 'true' });
      reset();
      setShowForm(false);
      loadRooms();
      showToast('Room created!', 'success');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to create room', 'error');
    }
  };

  return (
    <div>
      <div className="flex justify-between mb-6">
        <h1 className="text-3xl font-bold">Rooms</h1>
        <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">{showForm ? 'Cancel' : '+ Add'}</button>
      </div>
      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-2">Name *</label><input {...register('name', { required: true })} className="input" placeholder="Room 101" /></div>
            <div><label className="block text-sm font-medium mb-2">Type *</label><select {...register('room_type', { required: true })} className="input"><option value="">Select</option><option value="classroom">Classroom</option><option value="lab">Lab</option><option value="auditorium">Auditorium</option></select></div>
            <div><label className="block text-sm font-medium mb-2">Capacity *</label><input {...register('capacity', { required: true })} type="number" className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Projector?</label><select {...register('has_projector')} className="input"><option value="false">No</option><option value="true">Yes</option></select></div>
            <div><label className="block text-sm font-medium mb-2">Computers?</label><select {...register('has_computers')} className="input"><option value="false">No</option><option value="true">Yes</option></select></div>
            <button type="submit" className="btn btn-primary">Add</button>
          </form>
        </div>
      )}
      {rooms.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-xl text-gray-600">There are no rooms.</p>
          <p className="text-gray-500 mt-2">Kindly add it.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {rooms.map(r => (
            <div key={r.id} className="card">
              <h3 className="text-xl font-bold">{r.name}</h3>
              <p>Type: {r.room_type}</p>
              <p>Capacity: {r.capacity}</p>
              <p>Projector: {r.has_projector ? '✓' : '✗'}</p>
              <p>Computers: {r.has_computers ? '✓' : '✗'}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
