import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { timetableAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';

// ── Small helper components ────────────────────────────────────────────────────

function DiagnosticPanel({ title, items, color, icon }) {
  if (!items || items.length === 0) return null;
  const styles = {
    amber:  { card: 'bg-amber-50 border-amber-300',  title: 'text-amber-800', item: 'text-amber-700', dot: 'bg-amber-400' },
    yellow: { card: 'bg-yellow-50 border-yellow-300', title: 'text-yellow-800', item: 'text-yellow-700', dot: 'bg-yellow-400' },
    blue:   { card: 'bg-blue-50 border-blue-300',    title: 'text-blue-800',   item: 'text-blue-700',  dot: 'bg-blue-400'   },
    orange: { card: 'bg-orange-50 border-orange-300', title: 'text-orange-800', item: 'text-orange-700', dot: 'bg-orange-400' },
    red:    { card: 'bg-red-50 border-red-300',       title: 'text-red-800',   item: 'text-red-700',   dot: 'bg-red-400'    },
  };
  const s = styles[color] || styles.blue;
  return (
    <div className={`rounded-xl border-2 p-4 ${s.card}`}>
      <h4 className={`font-semibold text-sm mb-2 flex items-center gap-2 ${s.title}`}>
        <span>{icon}</span>{title}
      </h4>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className={`text-sm flex items-start gap-2 ${s.item}`}>
            <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${s.dot}`} />
            {typeof item === 'object' ? (item.reason || JSON.stringify(item)) : item}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function TimetableGenerator() {
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const { register, handleSubmit } = useForm();
  const { showToast } = useToast();

  const onSubmit = async (data) => {
    setGenerating(true);
    setResult(null);
    try {
      const response = await timetableAPI.generate({
        name: data.name,
        academic_year: data.academic_year,
        semester: parseInt(data.semester),
        working_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        periods_per_day: 7,
        start_time: '09:00',
        end_time: '16:00',
        period_duration_mins: 60,
        break_duration_mins: 15,
        lunch_duration_mins: 60,
        break2_duration_mins: 15,
        constraints_text: data.constraints_text || null,
      });
      setResult(response.data);
      showToast('Timetable generated successfully!', 'success');
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to generate timetable', 'error');
    } finally {
      setGenerating(false);
    }
  };

  // Extract diagnostics from result
  const cu = result?.constraints_used || {};
  const parseDiag    = cu.parse_diagnostics || {};
  const corrections  = parseDiag.corrections   || [];
  const parseWarnings= parseDiag.warnings      || [];
  const unrecognized = parseDiag.unrecognized  || [];
  const autoAdj      = cu.auto_adjustments     || [];
  const constrWarn   = cu.constraint_warnings  || [];

  const hasDiagnostics = corrections.length || parseWarnings.length || unrecognized.length || autoAdj.length || constrWarn.length;

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-2 text-gray-900">Generate Timetable</h1>
      <p className="text-gray-500 mb-8 text-sm">
        The AI engine will auto-correct common errors and build an optimised schedule.
      </p>

      {/* ── Form ─────────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-5 text-gray-800">Schedule Configuration</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
              <input {...register('name', { required: true })} className="input w-full" placeholder="Fall 2024" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Academic Year *</label>
              <input {...register('academic_year', { required: true })} className="input w-full" placeholder="2024-2025" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Semester *</label>
              <input {...register('semester', { required: true })} type="number" min="1" max="12" className="input w-full" placeholder="1" />
            </div>
          </div>

          {/* AI Constraints */}
          <div className="border-t pt-5">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">🤖</span>
              <h3 className="text-base font-semibold text-indigo-700">AI Constraints</h3>
              <span className="text-xs bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full">Optional</span>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Type in plain English. The AI will parse and auto-correct names, typos, and common patterns.
            </p>
            <textarea
              {...register('constraints_text')}
              className="input w-full h-36 text-sm font-mono"
              placeholder={`Examples:\n• Dr. Shiva cannot teach on Fridays\n• All lab sessions must be consecutive\n• Mathematics should be in the morning\n• Don't schedule CSE-A in period 7 and 8\n• Prof. Meena is available only on Mon, Tue, Thu`}
            />
            {/* Hint chips */}
            <div className="flex flex-wrap gap-2 mt-2">
              {[
                'Faculty unavailability', 'Lab consecutive', 'Morning preference',
                'Subject max/day', 'Avoid period', 'Specific slot',
              ].map(hint => (
                <span key={hint} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">{hint}</span>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={generating}
            className="btn btn-primary w-full py-3 text-base font-semibold flex items-center justify-center gap-2"
          >
            {generating ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                Generating schedule…
              </>
            ) : '✨ Generate Timetable'}
          </button>
        </form>
      </div>

      {/* ── Success result ────────────────────────────────────────────────── */}
      {result && (
        <div className="space-y-4">
          {/* Status card */}
          <div className="bg-green-50 border-2 border-green-400 rounded-2xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white text-lg">✓</div>
              <div>
                <h2 className="text-lg font-bold text-green-800">Timetable Generated!</h2>
                <p className="text-sm text-green-600">ID: {result.id}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              {[
                { label: 'Status',   value: result.solver_status },
                { label: 'Solved in',value: `${parseFloat(result.solve_time_seconds).toFixed(1)}s` },
                { label: 'Year',     value: result.academic_year },
                { label: 'Semester', value: result.semester },
              ].map(({ label, value }) => (
                <div key={label} className="bg-white rounded-xl p-3 shadow-sm">
                  <div className="text-xs text-gray-500">{label}</div>
                  <div className="font-semibold text-gray-800 text-sm">{value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Diagnostics */}
          {hasDiagnostics && (
            <div className="bg-white border border-gray-200 rounded-2xl p-5 space-y-3">
              <h3 className="font-semibold text-gray-700 flex items-center gap-2">
                <span>🔍</span> Smart Scheduling Report
              </h3>

              <DiagnosticPanel
                title="Auto-corrected Names"
                items={corrections}
                color="amber"
                icon="✏️"
              />
              <DiagnosticPanel
                title="Workload Auto-adjustments"
                items={autoAdj}
                color="blue"
                icon="⚖️"
              />
              <DiagnosticPanel
                title="Constraint Warnings (skipped)"
                items={constrWarn}
                color="orange"
                icon="⚠️"
              />
              <DiagnosticPanel
                title="Partially Understood Constraints"
                items={parseWarnings}
                color="yellow"
                icon="💡"
              />
              <DiagnosticPanel
                title="Unrecognized Phrases"
                items={unrecognized}
                color="red"
                icon="❓"
              />
            </div>
          )}
        </div>
      )}

      {/* ── Tips ─────────────────────────────────────────────────────────── */}
      {!result && (
        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-5">
          <h3 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
            <span>💡</span> How it works
          </h3>
          <ul className="space-y-2 text-blue-700 text-sm">
            <li>📌 <strong>No hours_per_week?</strong> Automatically derived from subject credit score (3 credits = 3 hrs/week)</li>
            <li>📌 <strong>Schedule too full?</strong> Low-priority subjects are auto-reduced; labs and high-credit subjects are protected</li>
            <li>📌 <strong>Typo in a faculty name?</strong> Fuzzy matching will auto-correct it and tell you what changed</li>
            <li>📌 <strong>Bad constraint?</strong> It's skipped with a warning — the schedule still generates</li>
            <li>📌 All 8 constraint types are supported: availability, consecutive, max/day, preferred slot, avoid period, gap, and more</li>
          </ul>
        </div>
      )}
    </div>
  );
}
