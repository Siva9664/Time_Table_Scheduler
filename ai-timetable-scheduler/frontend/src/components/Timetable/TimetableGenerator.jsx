import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { timetableAPI, departmentAPI, batchAPI, classAPI, facultyAPI, subjectAPI } from '../../services/api';

export default function TimetableGenerator() {
  const [departments, setDepartments] = useState([]);
  const [batches, setBatches] = useState([]);
  const [classes, setClasses] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [mapping, setMapping] = useState({});
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const { register, handleSubmit, watch, setValue } = useForm();

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

  useEffect(() => {
    if (startTime && endTime && periodDuration) {
      calculatePeriods();
    }
  }, [startTime, endTime, periodDuration, breakAfter, breakDuration, lunchAfter, lunchDuration, break2After, break2Duration]);

  // No-op for removed complexity
  const calculatePeriods = () => { };

  useEffect(() => { loadAllData(); }, []);

  const loadAllData = async () => {
    const dRes = await departmentAPI.getAll(); setDepartments(dRes.data);
    const bRes = await batchAPI.getAll().catch(() => ({ data: [] })); setBatches(bRes.data);
    const cRes = await classAPI.getAll().catch(() => ({ data: [] })); setClasses(cRes.data);
    const fRes = await facultyAPI.getAll().catch(() => ({ data: [] })); setFaculty(fRes.data);
    const sRes = await subjectAPI.getAll().catch(() => ({ data: [] })); setSubjects(sRes.data);
  };

  const handleMappingChange = (subId, field, value) => {
    setMapping(prev => ({
      ...prev,
      [subId]: { ...(prev[subId] || {}), [field]: value }
    }));
  };

  const filteredSubjects = subjects;

  const onSubmit = async (data) => {
    setGenerating(true);
    setResult(null);
    try {
      // 1. Update mappings
      const updates = [];
      for (const [subId, mapData] of Object.entries(mapping)) {
        if (mapData && (mapData.faculty_id || mapData.class_id)) {
          const payload = {};
          if (mapData.faculty_id) payload.faculty_id = parseInt(mapData.faculty_id);
          if (mapData.class_id) payload.class_id = parseInt(mapData.class_id);
          updates.push(subjectAPI.update(subId, payload));
        }
      }
      await Promise.all(updates);

      // 2. Generate
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
        faculty_ids: data.faculty_ids && data.faculty_ids.length > 0 ? data.faculty_ids.map(Number) : null, // Optional if we use mapping
        constraints_text: data.constraints_text
      });
      setResult(response.data);
      alert('Timetable generated successfully!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to generate timetable');
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
          {/* Simplified Configuration - Hidden Inputs */}
          {/* Defaults: 7 periods, 9-4, 1h periods */}





          <div className="border-t pt-4 mt-4">
            <h3 className="text-lg font-medium mb-3">🧑‍🏫 Faculty-Subject Mapping</h3>
            <p className="text-sm text-gray-500 mb-2">Assign Faculty to Subjects for the selected Scope.</p>
            <div className="bg-gray-50 p-4 rounded max-h-96 overflow-y-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b">
                    <th className="p-2">Subject</th>
                    <th className="p-2">Code</th>
                    <th className="p-2">Class</th>
                    <th className="p-2">Faculty</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSubjects.map(sub => (
                    <tr key={sub.id} className="border-b">
                      <td className="p-2">{sub.name}</td>
                      <td className="p-2">{sub.code}</td>
                      <td className="p-2">
                        <select
                          className="input py-1"
                          value={mapping[sub.id]?.class_id || sub.class_id || ""}
                          onChange={e => handleMappingChange(sub.id, 'class_id', e.target.value)}
                        >
                          <option value="">-- Select Class --</option>
                          {classes
                            .filter(c => c.department_id === sub.department_id && c.batch_id === sub.batch_id)
                            .map(c => (
                              <option key={c.id} value={c.id}>{c.name} {c.section}</option>
                            ))}
                        </select>
                      </td>
                      <td className="p-2">
                        <select
                          className="input py-1"
                          value={mapping[sub.id]?.faculty_id || sub.faculty_id || ""}
                          onChange={e => handleMappingChange(sub.id, 'faculty_id', e.target.value)}
                        >
                          <option value="">-- Select Faculty --</option>
                          {faculty
                            .filter(f => f.department_id === sub.department_id)
                            .map(f => (
                              <option key={f.id} value={f.id}>{f.name}</option>
                            ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                  {filteredSubjects.length === 0 && (
                    <tr><td colSpan="4" className="p-4 text-center text-red-500 font-bold">No subjects found. Please create subjects in the Admin Dashboard first.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

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
