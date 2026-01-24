import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation, Outlet } from 'react-router-dom';
import Login from './components/Auth/Login';
import Dashboard from './components/Admin/Dashboard';
import DepartmentManager from './components/Admin/DepartmentManager';
import ClassManager from './components/Admin/ClassManager';
import SubjectManager from './components/Admin/SubjectManager';
import FacultyManager from './components/Admin/FacultyManager';
import RoomManager from './components/Admin/RoomManager';
import BatchManager from './components/Admin/BatchManager';
import FacultyMapping from './components/Admin/FacultyMapping';
import TimetableGenerator from './components/Timetable/TimetableGenerator';
import TimetableView from './components/Timetable/TimetableView';
import Settings from './components/Admin/Settings';
import Sidebar from './components/Layout/Sidebar';
import { isAuthenticated, removeToken } from './utils/auth';

import { ToastProvider } from './context/ToastContext';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(isAuthenticated());

  const handleLogin = () => setIsLoggedIn(true);
  const handleLogout = () => {
    removeToken();
    setIsLoggedIn(false);
  };

  const ProtectedRoute = ({ children }) => {
    return isLoggedIn ? children : <Navigate to="/login" />;
  };

  const MainLayout = () => (
    <div className="flex min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <Sidebar onLogout={handleLogout} />
      <div className="flex-1 ml-64 p-8 overflow-y-auto h-screen">
        <div className="max-w-6xl mx-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );


  return (
    <ToastProvider>
      <Router>
        <Routes>
          <Route path="/login" element={isLoggedIn ? <Navigate to="/" /> : <Login onLogin={handleLogin} />} />

          <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="departments" element={<DepartmentManager />} />
            <Route path="batches" element={<BatchManager />} />
            <Route path="classes" element={<ClassManager />} />
            <Route path="subjects" element={<SubjectManager />} />
            <Route path="faculty" element={<FacultyManager />} />
            <Route path="rooms" element={<RoomManager />} />
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
