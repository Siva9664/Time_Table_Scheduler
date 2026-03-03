import React, { useState, useEffect } from 'react';
import { timetableAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import ConfirmationModal from '../Layout/ConfirmationModal';

export default function TimetableView() {
  const [timetables, setTimetables] = useState([]);
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState('classes'); // 'classes', 'faculty', 'rooms'
  const { showToast } = useToast();

  // Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [timetableToDelete, setTimetableToDelete] = useState(null);

  useEffect(() => { loadTimetables(); }, []);

  const loadTimetables = async () => {
    try {
      const res = await timetableAPI.getAll();
      setTimetables(res.data);
    } catch (error) {
      console.error("Failed to load timetables");
      showToast("Failed to load timetables", "error");
    }
  };

  const viewTimetable = async (id) => {
    try {
      const res = await timetableAPI.getById(id);
      setSelected(res.data);
    } catch (error) {
      console.error("Failed to load details");
      showToast("Failed to load details", "error");
    }
  };

  const handleDelete = (e, id) => {
    e.stopPropagation();
    setTimetableToDelete(id);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!timetableToDelete) return;
    try {
      await timetableAPI.delete(timetableToDelete);
      setTimetables(timetables.filter(t => t.id !== timetableToDelete));
      if (selected?.id === timetableToDelete) setSelected(null);
      showToast("Timetable deleted!", "success");
    } catch (error) {
      showToast("Failed to delete timetable", "error");
    }
  };

  // --- DATA PIVOTING HELPERS ---

  const getFacultySchedule = (scheduleData) => {
    const facultyMap = {};
    if (!scheduleData) return {};

    Object.values(scheduleData).forEach(classData => {
      Object.entries(classData.timetable).forEach(([day, periods]) => {
        periods.forEach(slot => {
          if (slot.faculty && slot.faculty !== 'TBA') {
            if (!facultyMap[slot.faculty]) facultyMap[slot.faculty] = {};
            if (!facultyMap[slot.faculty][day]) facultyMap[slot.faculty][day] = [];

            facultyMap[slot.faculty][day].push({
              ...slot,
              class_name: classData.class_name,
              room: slot.room
            });
          }
        });
      });
    });
    return facultyMap;
  };

  const getRoomSchedule = (scheduleData) => {
    const roomMap = {};
    if (!scheduleData) return {};

    Object.values(scheduleData).forEach(classData => {
      Object.entries(classData.timetable).forEach(([day, periods]) => {
        periods.forEach(slot => {
          if (slot.room) {
            if (!roomMap[slot.room]) roomMap[slot.room] = {};
            if (!roomMap[slot.room][day]) roomMap[slot.room][day] = [];

            roomMap[slot.room][day].push({
              ...slot,
              class_name: classData.class_name,
              faculty: slot.faculty
            });
          }
        });
      });
    });
    return roomMap;
  };

  // --- RENDERERS ---

  const renderClassView = () => (
    <div className="space-y-8">
      {selected.schedule_data && Object.values(selected.schedule_data).map((classSchedule) => (
        <div key={classSchedule.class_id} className="card shadow-sm border border-gray-100">
          <div className="border-b pb-3 mb-4 flex justify-between items-end">
            <div>
              <h3 className="text-xl font-bold text-gray-800">{classSchedule.class_name}</h3>
              <p className="text-sm text-gray-500">{classSchedule.department} • {classSchedule.batch_name}</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse">
              <thead>
                <tr>
                  <th className="p-3 bg-gray-50 border w-24 text-left text-xs font-bold text-gray-500 uppercase">Day</th>
                  {classSchedule.timetable[Object.keys(classSchedule.timetable)[0]].map((slot, i) => (
                    <th key={i} className="p-3 bg-gray-50 border min-w-[140px] text-center">
                      <div className="text-xs font-bold text-gray-700 uppercase">Period {slot.period}</div>
                      <div className="text-[10px] text-gray-400 font-mono mt-1">{slot.time}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(classSchedule.timetable).map(([day, periods]) => (
                  <tr key={day}>
                    <td className="p-3 border font-semibold text-gray-700 bg-gray-50/30">{day}</td>
                    {periods.map((slot, idx) => (
                      <td key={idx} className="p-2 border align-top h-24">
                        {slot.subject ? (
                          <div className={`h-full p-2 rounded-md flex flex-col justify-between ${slot.is_lab ? 'bg-blue-50 border border-blue-100 text-blue-900' : 'bg-green-50 border border-green-100 text-green-900'}`}>
                            <div>
                              <div className="font-bold text-sm leading-tight">{slot.subject}</div>
                              <div className="text-xs opacity-75 mt-0.5">{slot.subject_code}</div>
                            </div>
                            <div className="mt-2 pt-2 border-t border-black/5 flex justify-between items-center">
                              <span className="text-xs font-medium">👤 {slot.faculty}</span>
                              <span className="text-xs bg-white/50 px-1.5 rounded">📍 {slot.room}</span>
                            </div>
                          </div>
                        ) : (
                          <div className="h-full flex items-center justify-center text-gray-300 text-xs italic">Free</div>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );

  const renderResourceView = (dataMap, type) => (
    <div className="space-y-8">
      {Object.entries(dataMap).sort().map(([name, schedule]) => (
        <div key={name} className="card shadow-sm border border-gray-100">
          <h3 className="text-xl font-bold text-gray-800 mb-4 border-b pb-2">
            {type === 'faculty' ? '👤' : '🚪'} {name}
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full border-collapse table-fixed">
              <thead>
                <tr>
                  <th className="p-2 bg-gray-50 border w-24">Day</th>
                  <th className="p-2 bg-gray-50 border text-left">Schedule</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(schedule).map(([day, slots]) => (
                  <tr key={day}>
                    <td className="p-3 border font-semibold text-gray-700 bg-gray-50/30 align-top">{day}</td>
                    <td className="p-2 border">
                      <div className="flex flex-wrap gap-2">
                        {slots.sort((a, b) => a.period - b.period).map((slot, idx) => (
                          <div key={idx} className="bg-gray-50 border rounded p-2 min-w-[180px]">
                            <div className="text-xs font-mono text-gray-500 mb-1">
                              {slot.time} (P{slot.period})
                            </div>
                            <div className="font-bold text-sm text-primary-700">
                              {slot.class_name}
                            </div>
                            <div className="text-xs text-gray-600">
                              {slot.subject}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {type === 'faculty' ? `📍 ${slot.room}` : `👤 ${slot.faculty}`}
                            </div>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="min-h-screen pb-12">
      <ConfirmationModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="Delete Timetable"
        message="Are you sure you want to delete this timetable? This action cannot be undone."
      />

      <h1 className="text-3xl font-bold text-gray-900 mb-8">Timetables Directory</h1>

      {/* List of Timetables */}
      {!selected && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {timetables.map(t => (
            <div
              key={t.id}
              onClick={() => viewTimetable(t.id)}
              className="card hover:shadow-lg transition-all cursor-pointer border-l-4 border-l-primary-500 group relative"
            >
              <button
                onClick={(e) => handleDelete(e, t.id)}
                className="absolute top-4 right-4 text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
              >
                <span className="text-xl">🗑️</span>
              </button>
              <h3 className="font-bold text-lg mb-1">{t.name}</h3>
              <p className="text-gray-600 mb-4">{t.academic_year} • Semester {t.semester}</p>
              <div className="flex justify-between items-center text-sm">
                <span className={`px-2 py-1 rounded-full ${t.solver_status === 'OPTIMAL' ? 'bg-green-100 text-green-700' :
                  t.solver_status === 'FEASIBLE' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                  }`}>
                  {t.solver_status}
                </span>
                <span className="text-gray-400">{(t.solve_time_seconds || 0)}s</span>
              </div>
            </div>
          ))}
          {timetables.length === 0 && (
            <div className="col-span-full text-center py-12 bg-white rounded-lg border border-dashed border-gray-300">
              <p className="text-gray-500 text-lg">No timetables generated yet.</p>
              <p className="text-gray-400 text-sm mt-2">Go to "Generate" page to create one.</p>
            </div>
          )}
        </div>
      )}

      {/* Selected Timetable View */}
      {selected && (
        <div>
          <button
            onClick={() => setSelected(null)}
            className="mb-6 text-gray-500 hover:text-primary-600 flex items-center gap-2 transition-colors"
          >
            ← Back to Directory
          </button>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{selected.name}</h2>
                <p className="text-gray-500 text-sm mt-1">Status: {selected.solver_status}</p>
              </div>

              {/* TABS */}
              <div className="flex bg-gray-200/50 p-1 rounded-lg">
                {['classes', 'faculty', 'rooms'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${activeTab === tab
                      ? 'bg-white text-primary-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                      }`}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)} View
                  </button>
                ))}
              </div>
            </div>

            <div className="p-6 bg-gray-50/30 min-h-[600px]">
              {activeTab === 'classes' && renderClassView()}
              {activeTab === 'faculty' && renderResourceView(getFacultySchedule(selected.schedule_data), 'faculty')}
              {activeTab === 'rooms' && renderResourceView(getRoomSchedule(selected.schedule_data), 'room')}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

