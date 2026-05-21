import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, Outlet } from 'react-router-dom';
const Dashboard = React.lazy(() => import('./components/Admin/Dashboard'));
const DepartmentManager = React.lazy(() => import('./components/Admin/DepartmentManager'));
const ClassManager = React.lazy(() => import('./components/Admin/ClassManager'));
const SubjectManager = React.lazy(() => import('./components/Admin/SubjectManager'));
const FacultyManager = React.lazy(() => import('./components/Admin/FacultyManager'));
const BatchManager = React.lazy(() => import('./components/Admin/BatchManager'));
const FacultyMapping = React.lazy(() => import('./components/Admin/FacultyMapping'));
const TimetableGenerator = React.lazy(() => import('./components/Timetable/TimetableGenerator'));
const TimetableView = React.lazy(() => import('./components/Timetable/TimetableView'));
const Settings = React.lazy(() => import('./components/Admin/Settings'));
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
        
        <Suspense fallback={
            <div className="flex flex-col items-center justify-center h-screen space-y-4 bg-slate-50">
                <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                <div className="text-xl font-medium text-slate-500">Loading Application...</div>
            </div>
        }>
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
        </Suspense>
      </Router>
    </ToastProvider>
  );
}

export default App;
