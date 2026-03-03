import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { roomAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import ConfirmationModal from '../Layout/ConfirmationModal';
import { Edit, Trash2, Plus } from 'lucide-react';

export default function RoomManager() {
  const [rooms, setRooms] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editData, setEditData] = useState(null);
  const { register, handleSubmit, reset, setValue } = useForm();
  const { showToast } = useToast();

  // Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [roomToDelete, setRoomToDelete] = useState(null);

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

  const handleEdit = (room) => {
    setEditData(room);
    setValue('name', room.name);
    setValue('room_type', room.room_type);
    setValue('capacity', room.capacity);
    setValue('has_projector', room.has_projector ? 'true' : 'false');
    setValue('has_computers', room.has_computers ? 'true' : 'false');
    setShowForm(true);
  };

  const onSubmit = async (data) => {
    try {
      const payload = {
        ...data,
        capacity: parseInt(data.capacity),
        has_projector: data.has_projector === 'true',
        has_computers: data.has_computers === 'true'
      };

      if (editData) {
        await roomAPI.update(editData.id, payload);
        showToast('Room updated!', 'success');
      } else {
        await roomAPI.create(payload);
        showToast('Room created!', 'success');
      }

      reset();
      setEditData(null);
      setShowForm(false);
      loadRooms();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to save room', 'error');
    }
  };

  const confirmDelete = async () => {
    if (!roomToDelete) return;
    try {
      await roomAPI.delete(roomToDelete);
      loadRooms();
      showToast('Room deleted!', 'success');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to delete room', 'error');
    }
  };

  const handleDeleteClick = (id) => {
    setRoomToDelete(id);
    setIsDeleteModalOpen(true);
  };

  return (
    <div>
      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="Delete Room"
        message="Are you sure you want to delete this room?"
      />

      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Rooms</h1>
        <button
          onClick={() => {
            setEditData(null);
            reset();
            setShowForm(!showForm);
          }}
          className="btn btn-primary flex items-center gap-2"
        >
          {showForm ? 'Cancel' : <><Plus size={20} /> Add Room</>}
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h2 className="text-xl font-bold mb-4">{editData ? 'Edit Room' : 'Add New Room'}</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div><label className="block text-sm font-medium mb-2">Name *</label><input {...register('name', { required: true })} className="input" placeholder="Room 101" /></div>
            <div><label className="block text-sm font-medium mb-2">Type *</label><select {...register('room_type', { required: true })} className="input"><option value="">Select</option><option value="classroom">Classroom</option><option value="lab">Lab</option><option value="auditorium">Auditorium</option></select></div>
            <div><label className="block text-sm font-medium mb-2">Capacity *</label><input {...register('capacity', { required: true })} type="number" className="input" /></div>
            <div><label className="block text-sm font-medium mb-2">Projector?</label><select {...register('has_projector')} className="input"><option value="false">No</option><option value="true">Yes</option></select></div>
            <div><label className="block text-sm font-medium mb-2">Computers?</label><select {...register('has_computers')} className="input"><option value="false">No</option><option value="true">Yes</option></select></div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowForm(false)} className="btn btn-secondary">Cancel</button>
              <button type="submit" className="btn btn-primary">{editData ? 'Update' : 'Add'}</button>
            </div>
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
            <div key={r.id} className="card relative group hover:shadow-lg transition-shadow">
              <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleEdit(r)}
                  className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-full transition-colors"
                  title="Edit Room"
                >
                  <Edit size={18} />
                </button>
                <button
                  onClick={() => handleDeleteClick(r.id)}
                  className="p-1.5 text-red-600 hover:bg-red-50 rounded-full transition-colors"
                  title="Delete Room"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <h3 className="text-xl font-bold pr-16">{r.name}</h3>
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
