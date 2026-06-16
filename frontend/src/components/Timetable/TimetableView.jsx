import React, { useState, useEffect } from 'react';
import { timetableAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import ConfirmationModal from '../Layout/ConfirmationModal';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';

export default function TimetableView() {
  const [timetables, setTimetables] = useState([]);
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState('classes');
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

  // --- DOWNLOAD HANDLER ---
  const handleDownload = async () => {
    console.log("handleDownload started!");
    console.log("Selected timetable data:", selected);
    if (!selected) {
      console.log("selected is null or undefined!");
      return;
    }

    showToast("Generating PDF... Please wait.", "info");

    const pdf = new jsPDF('landscape', 'pt', 'a4');
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 20;
    const availableWidth = pageWidth - (margin * 2);

    // Create a hidden container in the DOM
    const wrapper = document.createElement('div');
    wrapper.style.position = 'absolute';
    wrapper.style.left = '-9999px';
    wrapper.style.top = '0';
    wrapper.style.width = '1200px';
    wrapper.style.display = 'inline-block';
    wrapper.style.padding = '20px';
    wrapper.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    wrapper.style.color = '#111827';
    wrapper.style.background = '#ffffff';
    document.body.appendChild(wrapper);

    try {
      const pagesHTML = [];

      // 1. Build Class Pages
      if (selected.schedule_data) {
        Object.values(selected.schedule_data).forEach(cs => {
          const firstDay = Object.keys(cs.timetable)[0];
          const headers = cs.timetable[firstDay].map(slot => {
            const isBreak = slot.slot_type === 'break';
            const label = isBreak ? (slot.label || 'Break') : `Period ${slot.period}`;
            return `<th style="padding:8px 12px;background:${isBreak ? '#fff7ed' : '#f3f4f6'};border:1px solid #d1d5db;min-width:${isBreak ? '110px' : '130px'};text-align:center;font-size:11px;">
              <div style="font-weight:700;text-transform:uppercase;color:${isBreak ? '#9a3412' : '#374151'};">${label}</div>
              <div style="color:#9ca3af;font-family:monospace;font-size:10px;margin-top:2px;">${slot.time}</div>
            </th>`;
          }).join('');

          const rows = Object.entries(cs.timetable).map(([day, periods]) => {
            const cells = periods.map(slot => {
              if (slot.slot_type === 'break') {
                return `<td style="padding:8px;border:1px solid #d1d5db;text-align:center;background:#fffbeb;color:#92400e;font-size:12px;font-weight:700;text-transform:uppercase;">${slot.label || 'Break'}</td>`;
              }
              if (!slot.subject) return `<td style="padding:8px;border:1px solid #d1d5db;text-align:center;color:#d1d5db;font-size:11px;font-style:italic;">Free</td>`;
              const bg = slot.is_lab ? '#eff6ff' : '#f0fdf4';
              const border = slot.is_lab ? '#bfdbfe' : '#bbf7d0';
              const color = slot.is_lab ? '#1e3a8a' : '#14532d';
              const customMarker = slot.is_custom ? '<span style="float:right;font-size:11px;" title="User Constraint">📌</span>' : '';
              return `<td style="padding:6px;border:1px solid #d1d5db;vertical-align:top;">
                <div style="background:${bg};border:1px solid ${border};color:${color};border-radius:6px;padding:6px;height:100%;min-height:80px;">
                  <div style="font-weight:700;font-size:12px;">${customMarker}${slot.subject}</div>
                  <div style="font-size:10px;opacity:0.7;margin-top:2px;">${slot.subject_code || ''}</div>
                  <div style="font-size:11px;margin-top:6px;padding-top:4px;border-top:1px solid rgba(0,0,0,0.08);"><span style="opacity:0.8;">Faculty:</span> ${slot.faculty}</div>
                  ${slot.room ? `<div style="font-size:10px;margin-top:3px;opacity:0.8;"><span>Room:</span> ${slot.room}${slot.room_changed ? ' *' : ''}</div>` : ''}
                </div>
              </td>`;
            }).join('');
            return `<tr>
              <td style="padding:10px 14px;border:1px solid #d1d5db;font-weight:600;color:#374151;background:#f9fafb;white-space:nowrap;">${day}</td>
              ${cells}
            </tr>`;
          }).join('');

          pagesHTML.push(`
            <div>
              <div style="margin-bottom:20px;">
                <h1 style="font-size:22px;font-weight:800;margin-bottom:4px;color:#111827;">${selected.name} <span style="font-size:14px;font-weight:400;color:#6b7280;margin-left:12px;">(Class View)</span></h1>
                <h3 style="font-size:17px;font-weight:700;color:#111827;margin-bottom:4px;">${cs.class_name}</h3>
                <p style="font-size:13px;color:#6b7280;">${cs.department} • ${cs.batch_name}</p>
              </div>
              <table style="border-collapse:collapse;width:100%;">
                <thead><tr>
                  <th style="padding:8px 14px;background:#f3f4f6;border:1px solid #d1d5db;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;color:#6b7280;">Day</th>
                  ${headers}
                </tr></thead>
                <tbody>${rows}</tbody>
              </table>
            </div>
          `);
        });
      }

      // 2. Build Faculty Pages
      const facData = getFacultySchedule(selected.schedule_data);
      if (facData && selected.schedule_data) {
        const firstClassKey = Object.keys(selected.schedule_data)[0];
        if (firstClassKey) {
          const masterTimetable = selected.schedule_data[firstClassKey].timetable;
          const days = Object.keys(masterTimetable);
          const masterSlotsTemplate = masterTimetable[days[0]];

          const headers = masterSlotsTemplate.map(slot => {
            const isBreak = slot.slot_type === 'break';
            const label = isBreak ? (slot.label || 'Break') : `Period ${slot.period}`;
            return `<th style="padding:8px 12px;background:${isBreak ? '#fff7ed' : '#f3f4f6'};border:1px solid #d1d5db;min-width:${isBreak ? '110px' : '130px'};text-align:center;font-size:11px;">
              <div style="font-weight:700;text-transform:uppercase;color:${isBreak ? '#9a3412' : '#374151'};">${label}</div>
              <div style="color:#9ca3af;font-family:monospace;font-size:10px;margin-top:2px;">${slot.time}</div>
            </th>`;
          }).join('');

          Object.entries(facData).sort().forEach(([facultyName, schedule]) => {
            const rows = days.map(day => {
              const facultyDaySlots = schedule[day] || [];
              const cells = masterSlotsTemplate.map(slot => {
                if (slot.slot_type === 'break') {
                  return `<td style="padding:8px;border:1px solid #d1d5db;text-align:center;background:#fffbeb;color:#92400e;font-size:12px;font-weight:700;text-transform:uppercase;">${slot.label || 'Break'}</td>`;
                }
                const assignedSlot = facultyDaySlots.find(s => s.period === slot.period);
                if (!assignedSlot) {
                  return `<td style="padding:8px;border:1px solid #d1d5db;text-align:center;color:#d1d5db;font-size:11px;font-style:italic;">Free</td>`;
                }
                return `<td style="padding:6px;border:1px solid #d1d5db;vertical-align:top;">
                  <div style="background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a8a;border-radius:6px;padding:6px;height:100%;min-height:80px;">
                    <div style="font-weight:700;font-size:12px;">${assignedSlot.class_name}</div>
                    <div style="font-size:11px;margin-top:6px;padding-top:4px;border-top:1px solid rgba(0,0,0,0.08);"><span style="opacity:0.8;">Subject:</span> ${assignedSlot.subject}</div>
                    <div style="font-size:10px;opacity:0.7;margin-top:2px;">${assignedSlot.subject_code || ''}</div>
                    ${assignedSlot.room ? `<div style="font-size:10px;opacity:0.75;margin-top:3px;">Room: ${assignedSlot.room}${assignedSlot.room_changed ? ' *' : ''}</div>` : ''}
                  </div>
                </td>`;
              }).join('');

              return `<tr>
                <td style="padding:10px 14px;border:1px solid #d1d5db;font-weight:600;color:#374151;background:#f9fafb;white-space:nowrap;">${day}</td>
                ${cells}
              </tr>`;
            }).join('');

            pagesHTML.push(`
              <div>
                <div style="margin-bottom:20px;">
                  <h1 style="font-size:22px;font-weight:800;margin-bottom:4px;color:#111827;">${selected.name} <span style="font-size:14px;font-weight:400;color:#6b7280;margin-left:12px;">(Faculty View)</span></h1>
                  <h3 style="font-size:18px;font-weight:700;color:#111827;margin-bottom:4px;">${facultyName}</h3>
                </div>
                <table style="border-collapse:collapse;width:100%;">
                  <thead><tr>
                    <th style="padding:8px 14px;background:#f3f4f6;border:1px solid #d1d5db;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;color:#6b7280;">Day</th>
                    ${headers}
                  </tr></thead>
                  <tbody>${rows}</tbody>
                </table>
              </div>
            `);
          });
        }
      }

      // 3. Render each page sequentially
      console.log("Total pages to render:", pagesHTML.length);
      for (let i = 0; i < pagesHTML.length; i++) {
        console.log(`Rendering page ${i + 1}/${pagesHTML.length}...`);
        wrapper.innerHTML = pagesHTML[i];
        
        const canvas = await html2canvas(wrapper, { 
          scale: 2, 
          useCORS: true,
          logging: false,
          windowWidth: wrapper.scrollWidth,
          width: wrapper.scrollWidth
        });
        console.log(`Finished canvas for page ${i + 1}/${pagesHTML.length}. Converting to image...`);
        
        const imgData = canvas.toDataURL('image/jpeg', 0.98);
        const imgWidth = availableWidth;
        const imgHeight = (canvas.height * availableWidth) / canvas.width;

        if (i > 0) pdf.addPage();
        pdf.addImage(imgData, 'JPEG', margin, margin, imgWidth, imgHeight);
        console.log(`Page ${i + 1}/${pagesHTML.length} successfully added to PDF.`);
      }
      console.log("Saving PDF...");

      pdf.save(`${selected.name.replace(/[^a-z0-9]/gi, '_')} - Full Schedule.pdf`);
      showToast("PDF downloaded successfully!", "success");

    } catch (err) {
      console.error("PDF generation failed", err);
      showToast("Failed to generate PDF", "error");
    } finally {
      document.body.removeChild(wrapper);
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
              class_name: classData.class_name
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
              class_name: classData.class_name
            });
          }
        });
      });
    });
    return roomMap;
  };


  // --- RENDERERS ---

  const getSlotLabel = (slot) => (
    slot.slot_type === 'break' ? (slot.label || 'Break') : `Period ${slot.period}`
  );

  const renderClassView = () => (
    <div className="space-y-8">
      {selected.schedule_data && Object.values(selected.schedule_data).map((classSchedule) => (
        <div key={classSchedule.class_id} className="card shadow-sm border border-gray-100">
          <div className="border-b pb-3 mb-4 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-2">
            <div>
              <h3 className="text-xl font-bold text-gray-800">{classSchedule.class_name}</h3>
              <p className="text-sm text-gray-500">{classSchedule.department} • {classSchedule.batch_name}{classSchedule.default_room ? ` • ${classSchedule.default_room}` : ''}</p>
            </div>
          </div>
          {/* Scrollable table container */}
          <div className="visible-scrollbar" style={{ overflowX: 'auto', overflowY: 'auto', maxHeight: '420px', border: '1px solid #e5e7eb', borderRadius: '6px' }}>
            <table style={{ minWidth: '750px', borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr>
                  <th style={{ position: 'sticky', top: 0, left: 0, zIndex: 4, background: '#f9fafb', padding: '10px 14px', border: '1px solid #e5e7eb', textAlign: 'left', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#6b7280', minWidth: '90px' }}>Day</th>
                  {classSchedule.timetable[Object.keys(classSchedule.timetable)[0]].map((slot, i) => (
                    <th key={i} style={{ position: 'sticky', top: 0, zIndex: 3, background: slot.slot_type === 'break' ? '#fff7ed' : '#f9fafb', padding: '10px 12px', border: '1px solid #e5e7eb', minWidth: slot.slot_type === 'break' ? '115px' : '145px', textAlign: 'center' }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: slot.slot_type === 'break' ? '#9a3412' : '#374151' }}>{getSlotLabel(slot)}</div>
                      <div style={{ fontSize: '10px', color: '#9ca3af', fontFamily: 'monospace', marginTop: '2px' }}>{slot.time}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(classSchedule.timetable).map(([day, periods]) => (
                  <tr key={day}>
                    <td style={{ position: 'sticky', left: 0, zIndex: 1, background: 'rgba(249,250,251,0.97)', padding: '10px 14px', border: '1px solid #e5e7eb', fontWeight: 600, color: '#374151', whiteSpace: 'nowrap' }}>{day}</td>
                    {periods.map((slot, idx) => (
                      <td key={idx} style={{ padding: '6px', border: '1px solid #e5e7eb', verticalAlign: 'top', height: '100px' }}>
                        {slot.slot_type === 'break' ? (
                          <div style={{ height: '100%', minHeight: '72px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e', fontWeight: 700, fontSize: '12px', textTransform: 'uppercase' }}>
                            {slot.label || 'Break'}
                          </div>
                        ) : slot.subject ? (
                          <div style={{ height: '100%', padding: '8px', borderRadius: '6px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', background: slot.is_lab ? '#eff6ff' : '#f0fdf4', border: `1px solid ${slot.is_lab ? '#bfdbfe' : '#bbf7d0'}`, color: slot.is_lab ? '#1e3a8a' : '#14532d' }}>
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '4px' }}>
                                <div style={{ fontWeight: 700, fontSize: '13px', lineHeight: 1.3 }}>{slot.subject}</div>
                                {slot.is_custom && (
                                  <span title="User Constraint" style={{ fontSize: '12px', flexShrink: 0 }}>📌</span>
                                )}
                              </div>
                              <div style={{ fontSize: '11px', opacity: 0.7, marginTop: '2px' }}>{slot.subject_code}</div>
                            </div>
                            <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(0,0,0,0.07)', fontSize: '11px', fontWeight: 500 }}>
                              <div>Faculty: {slot.faculty}</div>
                              {slot.room && (
                                <div className={slot.room_changed ? 'text-amber-700 font-semibold' : ''}>
                                  Room: {slot.room}{slot.room_changed ? ' (changed)' : ''}
                                </div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#d1d5db', fontSize: '11px', fontStyle: 'italic' }}>Free</div>
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
            {type === 'faculty' ? 'Faculty' : 'Room'}: {name}
          </h3>
          <div className="visible-scrollbar" style={{ overflowX: 'auto', overflowY: 'auto', maxHeight: '420px', border: '1px solid #e5e7eb', borderRadius: '6px' }}>
            <table style={{ minWidth: '600px', borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr>
                  <th style={{ position: 'sticky', top: 0, left: 0, zIndex: 4, background: '#f9fafb', padding: '10px 14px', border: '1px solid #e5e7eb', minWidth: '90px' }}>Day</th>
                  <th style={{ position: 'sticky', top: 0, zIndex: 3, background: '#f9fafb', padding: '10px 14px', border: '1px solid #e5e7eb', textAlign: 'left' }}>Schedule</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(schedule).map(([day, slots]) => (
                  <tr key={day}>
                    <td style={{ position: 'sticky', left: 0, zIndex: 1, background: 'rgba(249,250,251,0.97)', padding: '10px 14px', border: '1px solid #e5e7eb', fontWeight: 600, color: '#374151', verticalAlign: 'top', whiteSpace: 'nowrap' }}>{day}</td>
                    <td style={{ padding: '8px', border: '1px solid #e5e7eb' }}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {slots.sort((a, b) => a.period - b.period).map((slot, idx) => (
                          <div key={idx} style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '6px', padding: '8px', minWidth: '180px' }}>
                            <div style={{ fontSize: '11px', fontFamily: 'monospace', color: '#9ca3af', marginBottom: '4px' }}>
                              {slot.time} (P{slot.period})
                            </div>
                            <div style={{ fontWeight: 700, fontSize: '13px', color: '#2563eb' }}>
                              {slot.class_name}
                            </div>
                            <div style={{ fontSize: '12px', color: '#4b5563' }}>
                              {slot.subject}
                            </div>
                            <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                              {type === 'faculty' ? `Room: ${slot.room || '-'}` : `Faculty: ${slot.faculty || '-'}`}
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
              <div className="flex items-center text-sm">
                <span className={`px-2 py-1 rounded-full ${t.solver_status === 'OPTIMAL' ? 'bg-green-100 text-green-700' :
                  t.solver_status === 'FEASIBLE' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
                  }`}>
                  {t.solver_status}
                </span>
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

          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            {/* Header bar */}
            <div className="p-6 border-b border-gray-100 bg-gray-50/50 flex justify-between items-center flex-wrap gap-3">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{selected.name}</h2>
                <p className="text-gray-500 text-sm mt-1">Status: {selected.solver_status}</p>
              </div>

              {/* TABS + DOWNLOAD */}
              <div className="flex items-center gap-3">
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

                {/* Download Button */}
                <button
                  onClick={handleDownload}
                  title="Download Timetable as PDF"
                  style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    padding: '8px 16px', borderRadius: '8px',
                    background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                    color: '#fff', fontWeight: 600, fontSize: '14px',
                    border: 'none', cursor: 'pointer', boxShadow: '0 1px 4px rgba(37,99,235,0.3)',
                    transition: 'opacity 0.15s'
                  }}
                  onMouseOver={e => e.currentTarget.style.opacity = '0.88'}
                  onMouseOut={e => e.currentTarget.style.opacity = '1'}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  Download PDF
                </button>
              </div>
            </div>

            {/* Scrollable content area */}
            <div className="visible-scrollbar" style={{ overflowY: 'auto', overflowX: 'auto', maxHeight: 'calc(100vh - 260px)', minHeight: '400px', padding: '24px', background: 'rgba(249,250,251,0.3)' }}>
              {activeTab === 'classes' && renderClassView()}
              {activeTab === 'faculty' && renderResourceView(getFacultySchedule(selected.schedule_data), 'faculty')}
              {activeTab === 'rooms' && renderResourceView(getRoomSchedule(selected.schedule_data), 'rooms')}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
