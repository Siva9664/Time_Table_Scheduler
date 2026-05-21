import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, Outlet } from 'react-router-dom';
import Dashboard from './components/Admin/Dashboard';
import DepartmentManager from './components/Admin/DepartmentManager';
import ClassManager from './components/Admin/ClassManager';
import SubjectManager from './components/Admin/SubjectManager';
import FacultyManager from './components/Admin/FacultyManager';
import BatchManager from './components/Admin/BatchManager';
import FacultyMapping from './components/Admin/FacultyMapping';
import TimetableGenerator from './components/Timetable/TimetableGenerator';
import TimetableView from './components/Timetable/TimetableView';
import Settings from './components/Admin/Settings';
import Sidebar from './components/Layout/Sidebar';
import { ToastProvider } from './context/ToastContext';

function App() {
  const MainLayout = () => {
    const location = useLocation();

    return (
      <div className="flex h-screen overflow-hidden bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <Sidebar />
        <div className="flex-1 main-content p-4 sm:p-6 md:p-8 overflow-y-auto h-full relative">
          <div key={location.pathname} className="max-w-6xl mx-auto animate-page">
            <Outlet />
          </div>
        </div>
      </div>
    );
  };

  return (
    <ToastProvider>
      <Router>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="departments" element={<DepartmentManager />} />
            <Route path="batches" element={<BatchManager />} />
            <Route path="classes" element={<ClassManager />} />
            <Route path="subjects" element={<SubjectManager />} />
            <Route path="faculty" element={<FacultyManager />} />
            <Route path="mapping" element={<FacultyMapping />} />
            <Route path="generate" element={<TimetableGenerator />} />
            <Route path="view" element={<TimetableView />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </Router>
    </ToastProvider>
  );
}

export default App;
