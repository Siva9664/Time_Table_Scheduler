import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation, Outlet } from 'react-router-dom';
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
import { isAuthenticated, removeToken, isAdmin } from './utils/auth';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import { ToastProvider } from './context/ToastContext';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(isAuthenticated());

  const handleLogout = () => {
    removeToken();
    setIsLoggedIn(false);
  };

  const ProtectedRoute = ({ children }) => {
    if (!isLoggedIn) {
      return <Navigate to="/login" replace />;
    }
    return children;
  };

  const AdminRoute = ({ children }) => {
    if (!isLoggedIn) return <Navigate to="/login" replace />;
    if (!isAdmin()) return <Navigate to="/" replace />;
    return children;
  };

  const MainLayout = () => {
    const location = useLocation();

    return (
      <div className="flex h-screen overflow-hidden bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <Sidebar onLogout={handleLogout} />
        <div className="flex-1 main-content p-8 overflow-y-auto h-full relative">
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
          <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="departments" element={<AdminRoute><DepartmentManager /></AdminRoute>} />
            <Route path="batches" element={<AdminRoute><BatchManager /></AdminRoute>} />
            <Route path="classes" element={<AdminRoute><ClassManager /></AdminRoute>} />
            <Route path="subjects" element={<AdminRoute><SubjectManager /></AdminRoute>} />
            <Route path="faculty" element={<AdminRoute><FacultyManager /></AdminRoute>} />
            <Route path="rooms" element={<AdminRoute><RoomManager /></AdminRoute>} />
            <Route path="mapping" element={<AdminRoute><FacultyMapping /></AdminRoute>} />
            <Route path="generate" element={<AdminRoute><TimetableGenerator /></AdminRoute>} />
            <Route path="view" element={<TimetableView />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="/login" element={<Login onLogin={() => setIsLoggedIn(true)} />} />
          <Route path="/register" element={<Register onRegister={() => setIsLoggedIn(true)} />} />
        </Routes>
      </Router>
    </ToastProvider>
  );
}

export default App;
