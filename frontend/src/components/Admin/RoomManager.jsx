import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { DoorOpen, Edit, Plus, Trash2 } from 'lucide-react';
import { departmentAPI, roomAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import ConfirmationModal from '../Layout/ConfirmationModal';
import CsvUploader from '../Layout/CsvUploader';

export default function RoomManager() {
  const [rooms, setRooms] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editData, setEditData] = useState(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [roomToDelete, setRoomToDelete] = useState(null);
  const { register, handleSubmit, reset, setValue } = useForm();
  const { showToast } = useToast();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [roomRes, deptRes] = await Promise.all([
        roomAPI.getAll().catch(() => ({ data: [] })),
        departmentAPI.getAll().catch(() => ({ data: [] })),
      ]);
      setRooms(roomRes.data || []);
      setDepartments(deptRes.data || []);
    } catch (error) {
      showToast('Failed to load rooms', 'error');
    }
  };

  const getDepartmentName = (deptId) => departments.find(d => d.id === deptId)?.name || 'Shared';

  const handleEdit = (room) => {
    setEditData(room);
    setValue('name', room.name || '');
    setValue('code', room.code || '');
    setValue('capacity', room.capacity || '');
    setValue('room_type', room.room_type || 'lecture');
    setValue('department_id', room.department_id || '');
    setShowForm(true);
    setTimeout(() => {
      document.querySelector('.main-content')?.scrollTo({ top: 0, behavior: 'smooth' });
    }, 50);
  };

  const onSubmit = async (data) => {
    try {
      const payload = {
        ...data,
        capacity: data.capacity === '' ? null : parseInt(data.capacity),
        department_id: data.department_id || null,
        room_type: data.room_type || 'lecture',
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
      loadData();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to save room', 'error');
    }
  };

  const confirmDelete = async () => {
    if (!roomToDelete) return;
    try {
      await roomAPI.delete(roomToDelete);
      showToast('Room deleted!', 'success');
      loadData();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to delete room', 'error');
    }
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

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <h1 className="text-3xl font-bold">Rooms</h1>
        <div className="flex gap-2">
          <CsvUploader type="rooms" onSuccess={loadData} />
          <button
            onClick={() => {
              setEditData(null);
              reset({ room_type: 'lecture' });
              setShowForm(!showForm);
            }}
            className="btn btn-primary flex items-center gap-2"
          >
            {showForm ? 'Cancel' : <><Plus size={20} /> Add Room</>}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h2 className="text-xl font-bold mb-4">{editData ? 'Edit Room' : 'Add New Room'}</h2>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Name *</label>
                <input {...register('name', { required: true })} className="input" placeholder="Room 204" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Code</label>
                <input {...register('code')} className="input" placeholder="R204" />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Type</label>
                <select {...register('room_type')} className="input" defaultValue="lecture">
                  <option value="lecture">Lecture</option>
                  <option value="lab">Lab</option>
                  <option value="seminar">Seminar</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Capacity</label>
                <input {...register('capacity')} type="number" min="0" className="input" placeholder="60" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Department</label>
                <select {...register('department_id')} className="input">
                  <option value="">Shared</option>
                  {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => { setShowForm(false); setEditData(null); reset(); }} className="btn btn-secondary">Cancel</button>
              <button type="submit" className="btn btn-primary">{editData ? 'Update' : 'Create'}</button>
            </div>
          </form>
        </div>
      )}

      {rooms.length === 0 ? (
        <div className="card text-center py-12">
          <DoorOpen size={36} className="mx-auto text-slate-300 mb-3" />
          <p className="text-xl text-gray-600">There are no rooms.</p>
          <p className="text-gray-500 mt-2">Add classrooms and labs before generating room-aware timetables.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rooms.map(room => (
            <div key={room.id} className="card relative group hover:shadow-lg transition-shadow">
              <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => handleEdit(room)} className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-full transition-colors" title="Edit Room">
                  <Edit size={18} />
                </button>
                <button onClick={() => { setRoomToDelete(room.id); setIsDeleteModalOpen(true); }} className="p-1.5 text-red-600 hover:bg-red-50 rounded-full transition-colors" title="Delete Room">
                  <Trash2 size={18} />
                </button>
              </div>
              <h3 className="text-xl font-bold pr-16">{room.name}</h3>
              <div className="mt-2 space-y-1 text-sm text-gray-600">
                <p>Code: <span className="font-medium text-gray-800">{room.code || '-'}</span></p>
                <p>Type: <span className="font-medium text-gray-800 capitalize">{room.room_type || 'lecture'}</span></p>
                <p>Capacity: <span className="font-medium text-gray-800">{room.capacity ?? '-'}</span></p>
                <p>Department: <span className="font-medium text-gray-800">{getDepartmentName(room.department_id)}</span></p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
