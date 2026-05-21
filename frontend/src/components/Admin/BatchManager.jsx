import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { batchAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import { useFormCache } from '../../hooks/useFormCache';
import ConfirmationModal from '../Layout/ConfirmationModal';
import { Edit, Trash2, Plus } from 'lucide-react';

export default function BatchManager() {
    const [batches, setBatches] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [editData, setEditData] = useState(null);
    const { register, handleSubmit, reset, setValue, watch } = useForm();
    const { showToast } = useToast();

    // Modal State
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [batchToDelete, setBatchToDelete] = useState(null);

    // Watch all form fields for caching
    const formValues = watch();

    // Use form cache hook
    const { clearCache } = useFormCache('batchFormCache', formValues, setValue, showForm, !!editData);

    const loadBatches = async () => {
        try {
            const res = await batchAPI.getAll();
            setBatches(res.data);
        } catch (error) {
            console.error("Failed to load batches", error);
            showToast("Failed to load batches", "error");
        }
    };

    useEffect(() => {
        loadBatches();
    }, []);

    const handleEdit = (batch) => {
        setEditData(batch);
        setValue('name', batch.name);
        setValue('period_duration', batch.period_duration);
        setValue('start_time', batch.start_time);
        setValue('end_time', batch.end_time);

        if (batch.lunch_break) {
            setValue('lunch_start', batch.lunch_break.start);
            setValue('lunch_end', batch.lunch_break.end);
        } else {
            setValue('lunch_start', '');
            setValue('lunch_end', '');
        }

        if (batch.break_times) {
            const text = batch.break_times.map(b => `${b.start}-${b.end}`).join('\n');
            setValue('breaks_text', text);
        } else {
            setValue('breaks_text', '');
        }

        setShowForm(true);
    };

    const onSubmit = async (data) => {
        try {
            // Parse breaks from textarea (line separated HH:MM-HH:MM)
            const breaks = data.breaks_text.split('\n').filter(line => line.includes('-')).map(line => {
                const [start, end] = line.split('-').map(s => s.trim());
                return { start, end };
            });

            const payload = {
                name: data.name,
                start_time: data.start_time,
                end_time: data.end_time,
                period_duration: parseInt(data.period_duration),
                break_times: breaks,
                lunch_break: data.lunch_start && data.lunch_end ? { start: data.lunch_start, end: data.lunch_end } : {}
            };

            if (editData) {
                await batchAPI.update(editData.id, payload);
                showToast("Batch updated successfully!", "success");
            } else {
                await batchAPI.create(payload);
                showToast("Batch created successfully!", "success");
            }

            reset();
            setEditData(null);
            setShowForm(false);
            clearCache();
            loadBatches();
        } catch (error) {
            showToast("Failed to save batch: " + error.message, "error");
        }
    };

    const confirmDelete = async () => {
        if (!batchToDelete) return;
        try {
            await batchAPI.delete(batchToDelete);
            loadBatches();
            showToast("Batch deleted!", "success");
        } catch (error) {
            showToast("Failed to delete batch", "error");
        }
    };

    const handleDeleteClick = (id) => {
        setBatchToDelete(id);
        setIsDeleteModalOpen(true);
    };

    return (
        <div>
            <ConfirmationModal
                isOpen={isDeleteModalOpen}
                onClose={() => setIsDeleteModalOpen(false)}
                onConfirm={confirmDelete}
                title="Delete Batch"
                message="Are you sure you want to delete this batch configuration?"
            />

            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold">Batch Configurations</h1>
                <button
                    onClick={() => {
                        setEditData(null);
                        setShowForm(!showForm);
                    }}
                    className="btn btn-primary flex items-center gap-2"
                >
                    {showForm ? 'Cancel' : <><Plus size={20} /> Add Batch</>}
                </button>
            </div>

            {showForm && (
                <div className="card mb-6 bg-white p-6 rounded-lg shadow-sm border border-gray-100">
                    <h2 className="text-xl font-bold mb-4">{editData ? 'Edit Batch Configuration' : 'Add New Batch Configuration'}</h2>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div><label className="block text-sm font-medium mb-1">Batch Name *</label><input {...register('name', { required: true })} className="input w-full border rounded p-2" placeholder="e.g. 1st Year Main block" /></div>
                            <div><label className="block text-sm font-medium mb-1">Period Duration (mins) *</label><input {...register('period_duration', { required: true })} type="number" defaultValue="60" className="input w-full border rounded p-2" /></div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div><label className="block text-sm font-medium mb-1">College Start Time *</label><input {...register('start_time', { required: true })} type="time" defaultValue="09:00" className="input w-full border rounded p-2" /></div>
                            <div><label className="block text-sm font-medium mb-1">College End Time *</label><input {...register('end_time', { required: true })} type="time" defaultValue="16:00" className="input w-full border rounded p-2" /></div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div><label className="block text-sm font-medium mb-1">Lunch Start</label><input {...register('lunch_start')} type="time" className="input w-full border rounded p-2" /></div>
                            <div><label className="block text-sm font-medium mb-1">Lunch End</label><input {...register('lunch_end')} type="time" className="input w-full border rounded p-2" /></div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-1">Breaks (One per line: HH:MM-HH:MM)</label>
                            <textarea {...register('breaks_text')} className="input w-full border rounded p-2 h-24 font-mono text-sm" placeholder="10:30-10:45&#10;15:00-15:15"></textarea>
                        </div>

                        <div className="flex justify-end gap-2">
                            <button
                                type="button"
                                onClick={() => {
                                    setShowForm(false);
                                    setEditData(null);
                                    reset();
                                }}
                                className="btn btn-secondary"
                            >
                                Cancel
                            </button>
                            <button type="submit" className="btn btn-primary py-2 bg-blue-600 text-white rounded hover:bg-blue-700">{editData ? 'Update Configuration' : 'Create Configuration'}</button>
                        </div>
                    </form>
                </div>
            )}

            {batches.length === 0 ? (
                <div className="card text-center py-12">
                    <p className="text-xl text-gray-600">No batches configured.</p>
                    <p className="text-gray-500 mt-2">Create one to define timings for student groups.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {batches.map(b => (
                        <div key={b.id} className="card relative group hover:shadow-lg transition-shadow">
                            <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                    onClick={() => handleEdit(b)}
                                    className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-full transition-colors"
                                    title="Edit Batch"
                                >
                                    <Edit size={18} />
                                </button>
                                <button onClick={() => handleDeleteClick(b.id)} className="p-1.5 text-red-600 hover:bg-red-50 rounded-full transition-colors" title="Delete Batch">
                                    <Trash2 size={18} />
                                </button>
                            </div>

                            <h3 className="font-bold text-lg mb-2">{b.name}</h3>
                            <div className="text-sm text-gray-600 space-y-1">
                                <p>🕒 {b.start_time} - {b.end_time}</p>
                                <p>⏱️ {b.period_duration} mins/period</p>
                                {b.lunch_break && b.lunch_break.start && (
                                    <p>🍱 Lunch: {b.lunch_break.start} - {b.lunch_break.end}</p>
                                )}
                                {b.break_times && b.break_times.length > 0 && (
                                    <div className="mt-2 text-xs bg-gray-50 p-2 rounded">
                                        <strong>Breaks:</strong>
                                        {b.break_times.map((br, idx) => (
                                            <div key={idx}>{br.start} - {br.end}</div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}