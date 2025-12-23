import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { departmentAPI, classAPI, facultyAPI, roomAPI, timetableAPI } from '../../services/api';


export default function Dashboard() {
  const [stats, setStats] = useState({ departments: 0, classes: 0, faculty: 0, rooms: 0, timetables: 0 });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();



  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const results = await Promise.allSettled([
        departmentAPI.getAll(), classAPI.getAll(), facultyAPI.getAll(), roomAPI.getAll(), timetableAPI.getAll()
      ]);

      const [dRes, cRes, fRes, rRes, tRes] = results;

      if (dRes.status === 'rejected') console.error("Depts failed", dRes.reason);
      if (cRes.status === 'rejected') console.error("Classes failed", cRes.reason);
      if (fRes.status === 'rejected') console.error("Faculty failed", fRes.reason);
      if (rRes.status === 'rejected') console.error("Rooms failed", rRes.reason);
      if (tRes.status === 'rejected') console.error("Timetables failed", tRes.reason);

      setStats({
        departments: dRes.status === 'fulfilled' ? dRes.value.data.length : 0,
        classes: cRes.status === 'fulfilled' ? cRes.value.data.length : 0,
        faculty: fRes.status === 'fulfilled' ? fRes.value.data.length : 0,
        rooms: rRes.status === 'fulfilled' ? rRes.value.data.length : 0,
        timetables: tRes.status === 'fulfilled' ? tRes.value.data.length : 0
      });
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStatClick = (path) => {
    navigate(path);
  };

  const StatCard = ({ title, value, color, icon, path }) => (
    <div
      onClick={() => handleStatClick(path)}
      className={`card bg-gradient-to-br ${color} text-white cursor-pointer transform hover:scale-105 transition-all duration-200 shadow-lg`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm opacity-90">{title}</p>
          <p className="text-4xl font-bold mt-2">{value}</p>
        </div>
        <div className="text-5xl opacity-50">{icon}</div>
      </div>
    </div>
  );

  if (loading) return <div className="flex items-center justify-center h-64"><div className="text-xl text-gray-600">Loading...</div></div>;

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <StatCard title="Departments" value={stats.departments} color="from-blue-500 to-blue-600" icon="🏢" path="/departments" />
        <StatCard title="Classes" value={stats.classes} color="from-green-500 to-green-600" icon="📚" path="/classes" />
        <StatCard title="Faculty" value={stats.faculty} color="from-purple-500 to-purple-600" icon="👨‍🏫" path="/faculty" />
        <StatCard title="Rooms" value={stats.rooms} color="from-orange-500 to-orange-600" icon="🚪" path="/rooms" />
        <StatCard title="Timetables" value={stats.timetables} color="from-pink-500 to-pink-600" icon="📅" path="/view" />
        <div
          onClick={() => navigate('/generate')}
          className="card bg-gradient-to-br from-teal-500 to-teal-600 text-white cursor-pointer transform hover:scale-105 transition-all duration-200 shadow-lg"
        >
          <div className="text-center">
            <p className="text-xl font-semibold mb-2">Ready to Generate</p>
            <p className="text-4xl">✨</p>
            <p className="text-sm opacity-90 mt-2">Click Generate</p>
          </div>
        </div>
      </div>
      <div className="card">
        <h2 className="text-2xl font-bold mb-4">Quick Start</h2>
        <ol className="list-decimal list-inside space-y-3 text-gray-700">
          <li onClick={() => navigate('/departments')} className="cursor-pointer hover:text-blue-600 hover:underline">Add Departments</li>
          <li onClick={() => navigate('/classes')} className="cursor-pointer hover:text-blue-600 hover:underline">Create Classes</li>
          <li onClick={() => navigate('/subjects')} className="cursor-pointer hover:text-blue-600 hover:underline">Define Subjects</li>
          <li onClick={() => navigate('/faculty')} className="cursor-pointer hover:text-blue-600 hover:underline">Add Faculty</li>
          <li onClick={() => navigate('/rooms')} className="cursor-pointer hover:text-blue-600 hover:underline">Configure Rooms</li>
          <li onClick={() => navigate('/generate')} className="cursor-pointer hover:text-blue-600 hover:underline">Generate Timetable</li>
        </ol>
      </div>
    </div>
  );
}
