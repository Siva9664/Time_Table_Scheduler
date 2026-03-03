import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { departmentAPI, classAPI, facultyAPI, roomAPI, timetableAPI } from '../../services/api';
import {
  Users,
  BookOpen,
  GraduationCap,
  DoorOpen,
  Calendar,
  Plus,
  LayoutDashboard,
  Clock,
  ChevronRight
} from 'lucide-react';

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

  const StatCard = ({ title, value, color, path }) => (
    <div
      onClick={() => handleStatClick(path)}
      className={`relative overflow-hidden rounded-2xl p-8 text-white cursor-pointer transform hover:scale-[1.02] transition-all duration-300 shadow-lg ${color}`}
    >
      {/* Background pattern blobs */}
      <div className="absolute -right-6 -top-6 w-32 h-32 bg-white/10 rounded-full blur-2xl" />
      <div className="absolute right-10 bottom-2 w-16 h-16 bg-black/5 rounded-full blur-xl" />

      <div className="relative flex flex-col items-center justify-center text-center">
        <p className="text-6xl font-black mb-2 tracking-tight">{value}</p>
        <p className="text-xs font-bold uppercase tracking-[0.2em] opacity-90">{title}</p>
      </div>
    </div>
  );

  const ActionButton = ({ icon: Icon, label, color, onClick }) => (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-sm transition-all duration-200 shadow-md hover:shadow-lg active:scale-95 ${color} text-white`}
    >
      <Icon size={18} />
      {label}
    </button>
  );

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-full space-y-4">
      <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
      <div className="text-xl font-medium text-gray-500">Wait a moment...</div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto space-y-10">
      <header>
        <h1 className="text-4xl font-black text-slate-800 tracking-tight uppercase">Dashboard</h1>
        <div className="h-1.5 w-20 bg-primary-500 rounded-full mt-2"></div>
      </header>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Total Departments" value={stats.departments} color="bg-[#434d5b]" path="/departments" />
        <StatCard title="Static Classes" value={stats.classes} color="bg-[#3b82f6]" path="/classes" />
        <StatCard title="Total Faculty" value={stats.faculty} color="bg-[#22c55e]" path="/faculty" />
        <StatCard title="Rooms Available" value={stats.rooms} color="bg-[#f59e0b]" path="/rooms" />
      </div>

      {/* Quick Actions Row */}
      <div className="bg-white rounded-3xl p-8 shadow-xl border border-slate-100">
        <h2 className="text-xl font-extrabold text-slate-700 mb-6 flex items-center gap-2">
          <LayoutDashboard size={24} className="text-primary-500" />
          Quick Actions
        </h2>
        <div className="flex flex-wrap gap-4">
          <ActionButton icon={BookOpen} label="Manage Subjects" color="bg-slate-700" onClick={() => navigate('/subjects')} />
          <ActionButton icon={Users} label="Faculty Mapping" color="bg-blue-600" onClick={() => navigate('/mapping')} />
          <ActionButton icon={Calendar} label="View Timetables" color="bg-orange-500" onClick={() => navigate('/view')} />
          <ActionButton icon={Plus} label="Generate New" color="bg-slate-600" onClick={() => navigate('/generate')} />
        </div>
      </div>

      {/* Recent Activity Section */}
      <div className="bg-white rounded-3xl p-8 shadow-xl border border-slate-100">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-extrabold text-slate-700 flex items-center gap-2">
            <Clock size={24} className="text-primary-500" />
            Recent Activity
          </h2>
          <button className="text-primary-600 font-bold text-sm hover:underline flex items-center gap-1">
            View All <ChevronRight size={16} />
          </button>
        </div>

        <div className="space-y-4">
          {[
            { action: "Generated timetable for Spring 2024", time: "2 hours ago", type: "system" },
            { action: "Added 5 new faculty members to CSE Dept", time: "5 hours ago", type: "modify" },
            { action: "Updated room capacity for Lab 102", time: "1 day ago", type: "modify" }
          ].map((item, idx) => (
            <div key={idx} className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 border border-slate-100 hover:bg-slate-100 transition-colors cursor-default">
              <div className="flex items-center gap-4">
                <div className={`w-2 h-2 rounded-full ${item.type === 'system' ? 'bg-blue-500' : 'bg-green-500'}`} />
                <div>
                  <p className="font-bold text-slate-700 text-sm">{item.action}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{item.time}</p>
                </div>
              </div>
              <ChevronRight size={18} className="text-slate-300" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
