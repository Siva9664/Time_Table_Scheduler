import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { batchAPI } from '../../services/api';

export default function BatchManager() {
    const [batches, setBatches] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const { register, handleSubmit, reset, setValue } = useForm();

    useEffect(() => { loadBatches(); }, []);

    const loadBatches = async () => {
        try {
            const res = await batchAPI.getAll();
            setBatches(res.data);
        } catch (error) {
            console.error("Failed to load batches", error);
        }
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

            await batchAPI.create(payload);
            reset();
            setShowForm(false);
            loadBatches();
        } catch (error) {
            alert("Failed to create batch: " + error.message);
        }
    };

    const handleDelete = async (id) => {
        if (window.confirm("Delete this batch?")) {
            await batchAPI.delete(id);
            loadBatches();
        }
    };

    return (
        <div>
            <div className="flex justify-between mb-6">
                <h1 className="text-3xl font-bold">Batch Configurations</h1>
                <button onClick={() => setShowForm(!showForm)} className="btn btn-primary">{showForm ? 'Cancel' : '+ Add Batch'}</button>
            </div>

            {showForm && (
                <div className="card mb-6 bg-white p-6 rounded-lg shadow-sm border border-gray-100">
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

                        <button type="submit" className="btn btn-primary w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Create Configuration</button>
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
                        <div key={b.id} className="card relative group">
                            <button onClick={() => handleDelete(b.id)} className="absolute top-2 right-2 text-red-500 opacity-0 group-hover:opacity-100 transition-opacity">Delete</button>
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
