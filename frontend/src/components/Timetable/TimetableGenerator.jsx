import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { timetableAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';

export default function TimetableGenerator() {
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const { register, handleSubmit, watch } = useForm();
  const { showToast } = useToast();

  // Watch fields for auto-calculation
  const startTime = watch('start_time');
  const endTime = watch('end_time');
  const periodDuration = watch('period_duration_mins');
  const breakAfter = watch('break_after_period');
  const breakDuration = watch('break_duration_mins');
  const lunchAfter = watch('lunch_after_period');
  const lunchDuration = watch('lunch_duration_mins');
  const break2After = watch('break2_after_period');
  const break2Duration = watch('break2_duration_mins');

  // Logic for calculating periods (minimized from original)
  useEffect(() => {
    if (startTime && endTime && periodDuration) {
      // calculate periods logic
    }
  }, [startTime, endTime, periodDuration, breakAfter, breakDuration, lunchAfter, lunchDuration, break2After, break2Duration]);

  const onSubmit = async (data) => {
    setGenerating(true);
    setResult(null);
    try {
      // Generate
      const response = await timetableAPI.generate({
        name: data.name,
        academic_year: data.academic_year,
        semester: parseInt(data.semester),
        working_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        periods_per_day: 7, // Fixed default
        start_time: "09:00", // Fixed default
        end_time: "16:00", // Fixed default
        period_duration_mins: 60, // Fixed default
        break_duration_mins: 15,
        lunch_duration_mins: 60,
        break2_duration_mins: 15,
        department_ids: data.department_ids && data.department_ids.length > 0 ? data.department_ids.map(Number) : null,
        batch_ids: data.batch_ids && data.batch_ids.length > 0 ? data.batch_ids.map(Number) : null,
        class_ids: data.class_ids && data.class_ids.length > 0 ? data.class_ids.map(Number) : null,
        faculty_ids: data.faculty_ids && data.faculty_ids.length > 0 ? data.faculty_ids.map(Number) : null,
        constraints_text: data.constraints_text
      });
      setResult(response.data);
      showToast('Timetable generated successfully!', 'success');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to generate timetable', 'error');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Generate Timetable</h1>
      <div className="card mb-6">
        <h2 className="text-xl font-semibold mb-4">Configuration</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div><label className="block text-sm font-medium mb-2">Name *</label><input {...register('name', { required: true })} className="input" placeholder="Fall 2024" /></div>
          <div><label className="block text-sm font-medium mb-2">Academic Year *</label><input {...register('academic_year', { required: true })} className="input" placeholder="2024-2025" /></div>
          <div><label className="block text-sm font-medium mb-2">Semester *</label><input {...register('semester', { required: true })} type="number" className="input" /></div>

          <div className="border-t pt-4 mt-4">
            <h3 className="text-lg font-medium mb-3 text-indigo-700">🤖 AI Constraints</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Natural Language Constraints</label>
              <textarea
                {...register('constraints_text')}
                className="input h-32"
                placeholder="e.g., Faculty Shiva available only on Mon/Tue. Labs must be consecutive."
              ></textarea>
            </div>
          </div>

          <button type="submit" disabled={generating} className="btn btn-primary w-full py-3 text-lg">
            {generating ? '🔄 Generating...' : '✨ Generate Timetable'}
          </button>
        </form>
      </div>
      {result && (
        <div className="card bg-green-50 border-2 border-green-500">
          <h2 className="text-xl font-bold text-green-800 mb-4">✓ Success!</h2>
          <p><strong>Status:</strong> {result.solver_status}</p>
          <p><strong>Time:</strong> {result.solve_time_seconds}s</p>
          <p><strong>Year:</strong> {result.academic_year}</p>
          <p><strong>Semester:</strong> {result.semester}</p>
          <p className="text-sm text-gray-600 mt-4">Timetable ID: {result.id}</p>
        </div>
      )}
      <div className="card bg-blue-50 mt-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">💡 Tips</h3>
        <ul className="list-disc list-inside space-y-2 text-blue-800 text-sm">
          <li>Ensure all departments have classes, subjects, faculty</li>
          <li>Configure rooms with proper capacity</li>
          <li>Solver finds optimal schedule within constraints</li>
          <li>Generation may take 1-5 minutes</li>
        </ul>
      </div>
    </div>
  );
}
