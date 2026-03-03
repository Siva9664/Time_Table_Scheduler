import React, { useState, useEffect } from 'react';
import { subjectAPI, facultyAPI, classAPI, departmentAPI, batchAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import { Edit, Trash2 } from 'lucide-react';
import ConfirmationModal from '../Layout/ConfirmationModal';

const FacultyMapping = () => {
    const [subjects, setSubjects] = useState([]);
    const [classes, setClasses] = useState([]);
    const [faculties, setFaculties] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [batches, setBatches] = useState([]);

    // Form Selection State
    const [selectedBatchId, setSelectedBatchId] = useState('');
    const [selectedDeptId, setSelectedDeptId] = useState('');
    const [selectedClassId, setSelectedClassId] = useState('');
    const [selectedSubjectId, setSelectedSubjectId] = useState('');
    const [selectedFacultyId, setSelectedFacultyId] = useState('');

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const { showToast } = useToast();

    // Modal State
    const [isUnassignModalOpen, setIsUnassignModalOpen] = useState(false);
    const [subjectToUnassign, setSubjectToUnassign] = useState(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [subRes, classRes, facRes, deptRes, batchRes] = await Promise.all([
                subjectAPI.getAll(),
                classAPI.getAll(),
                facultyAPI.getAll(),
                departmentAPI.getAll(),
                batchAPI.getAll()
            ]);
            setSubjects(subRes.data);
            setClasses(classRes.data);
            setFaculties(facRes.data);
            setDepartments(deptRes.data);
            setBatches(batchRes.data);
        } catch (err) {
            console.error(err);
            showToast('Failed to load data. Please ensure backend is running.', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleMap = async () => {
        if (!selectedSubjectId || !selectedFacultyId || !selectedClassId) {
            showToast("Please select Class, Subject and Faculty.", 'warning');
            return;
        }

        setSaving(true);
        try {
            await subjectAPI.update(selectedSubjectId, {
                class_id: parseInt(selectedClassId),
                faculty_id: parseInt(selectedFacultyId)
            });

            // Refresh data
            await loadData();

            // Reset form partly
            setSelectedSubjectId('');
            setSelectedFacultyId('');

            showToast('Mapped successfully!', 'success');
        } catch (err) {
            console.error(err);
            showToast('Failed to save mapping.', 'error');
        } finally {
            setSaving(false);
        }
    };

    const handleEditClick = (sub) => {
        // Pre-fill the form with this subject's details
        const cls = classes.find(c => c.id === sub.class_id);
        if (cls) {
            setSelectedBatchId(cls.batch_id || '');
            setSelectedDeptId(cls.department_id || '');
            setSelectedClassId(cls.id);
        }
        setSelectedSubjectId(sub.id);
        setSelectedFacultyId(sub.faculty_id || '');

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleUnassignClick = (id) => {
        setSubjectToUnassign(id);
        setIsUnassignModalOpen(true);
    };

    const confirmUnassign = async () => {
        if (!subjectToUnassign) return;
        try {
            await subjectAPI.update(subjectToUnassign, { faculty_id: null });
            loadData();
            showToast('Faculty unassigned!', 'success');
        } catch (error) {
            showToast('Failed to unassign faculty.', 'error');
        }
    };

    // --- Helper Functions ---
    const getDepartmentName = (deptId) => {
        const dept = departments.find(d => d.id === deptId);
        return dept ? dept.name : '-';
    };

    const getFacultyName = (facId) => {
        const fac = faculties.find(f => f.id === parseInt(facId));
        return fac ? fac.name : 'Unassigned';
    };

    const getClassName = (classId) => {
        const cls = classes.find(c => c.id === parseInt(classId));
        return cls ? `${cls.name} ${cls.section}` : 'Unassigned';
    };

    // --- Filtering Logic for Dropdowns ---

    // 1. Filter Classes based on Batch AND Department
    const availableClasses = classes.filter(c => {
        const matchBatch = !selectedBatchId || c.batch_id === parseInt(selectedBatchId);
        const matchDept = !selectedDeptId || c.department_id === parseInt(selectedDeptId);
        return matchBatch && matchDept;
    });

    // 2. Filter Subjects based on Class
    const availableSubjects = subjects.filter(s => {
        if (!selectedClassId) return false;
        const selectedClass = classes.find(c => c.id === parseInt(selectedClassId));
        if (!selectedClass) return false;

        return s.department_id === selectedClass.department_id &&
            (!s.batch_id || s.batch_id === selectedClass.batch_id);
    });

    // 3. Filter Faculties based on Dept
    const availableFaculties = faculties.filter(f => {
        // If Dept selected, filter by it
        if (selectedDeptId) return f.department_id === parseInt(selectedDeptId);
        // Fallback to Class/Subject dept logic if simplified
        if (selectedClassId) {
            const cls = classes.find(c => c.id === parseInt(selectedClassId));
            return cls ? f.department_id === cls.department_id : true;
        }
        return true;
    });


    // --- Filtering Logic for Table (Search) ---
    const filteredOverview = subjects.filter(sub => {
        const term = searchTerm.toLowerCase();
        const deptName = getDepartmentName(sub.department_id).toLowerCase();
        const facName = sub.faculty_id ? getFacultyName(sub.faculty_id).toLowerCase() : '';
        const clsName = sub.class_id ? getClassName(sub.class_id).toLowerCase() : '';

        return (
            sub.name.toLowerCase().includes(term) ||
            sub.code.toLowerCase().includes(term) ||
            deptName.includes(term) ||
            facName.includes(term) ||
            clsName.includes(term)
        );
    });

    if (loading) return <div className="p-8 text-center text-gray-500">Loading data...</div>;

    return (
        <div className="space-y-8">
            <ConfirmationModal
                isOpen={isUnassignModalOpen}
                onClose={() => setIsUnassignModalOpen(false)}
                onConfirm={confirmUnassign}
                title="Unassign Faculty"
                message="Are you sure you want to remove the assigned faculty from this subject?"
            />

            <h1 className="text-3xl font-bold text-slate-800">Faculty Mapping</h1>

            {/* Top Section: Mapping Form */}
            <div className="bg-white rounded-xl shadow-lg p-6 border border-slate-100">
                <div className="grid grid-cols-1 md:grid-cols-6 gap-4 items-end">

                    {/* Batch Select */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Batch</label>
                        <select
                            className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-slate-50"
                            value={selectedBatchId}
                            onChange={(e) => {
                                setSelectedBatchId(e.target.value);
                                setSelectedClassId('');
                            }}
                        >
                            <option value="">Select Batch</option>
                            {batches.map(b => (
                                <option key={b.id} value={b.id}>{b.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Department Select (Added) */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Department</label>
                        <select
                            className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-slate-50"
                            value={selectedDeptId}
                            onChange={(e) => {
                                setSelectedDeptId(e.target.value);
                                setSelectedClassId('');
                            }}
                        >
                            <option value="">Select Dept</option>
                            {departments.map(d => (
                                <option key={d.id} value={d.id}>{d.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Class Select */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Class</label>
                        <select
                            className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-slate-50"
                            value={selectedClassId}
                            onChange={(e) => {
                                setSelectedClassId(e.target.value);
                                setSelectedSubjectId('');
                            }}
                            // Enable if either Batch or Dept is selected (or both), or if just browsing
                            disabled={availableClasses.length === 0 && (selectedBatchId || selectedDeptId)}
                        >
                            <option value="">Select Class</option>
                            {availableClasses.map(c => (
                                <option key={c.id} value={c.id}>{c.name} {c.section}</option>
                            ))}
                        </select>
                    </div>

                    {/* Subject Select */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Subject</label>
                        <select
                            className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-slate-50"
                            value={selectedSubjectId}
                            onChange={(e) => setSelectedSubjectId(e.target.value)}
                            disabled={!selectedClassId}
                        >
                            <option value="">Select Subject</option>
                            {availableSubjects.map(s => (
                                <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
                            ))}
                        </select>
                    </div>

                    {/* Faculty Select */}
                    <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Faculty</label>
                        <select
                            className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-slate-50"
                            value={selectedFacultyId}
                            onChange={(e) => setSelectedFacultyId(e.target.value)}
                            disabled={!selectedClassId && !selectedDeptId}
                        >
                            <option value="">Select Faculty</option>
                            {availableFaculties.map(f => (
                                <option key={f.id} value={f.id}>{f.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* MAP Button */}
                    <div>
                        <button
                            onClick={handleMap}
                            disabled={saving}
                            className="w-full px-6 py-2 bg-slate-400 text-white font-bold rounded-lg hover:bg-slate-500 shadow-lg transition-all duration-200"
                            style={{ backgroundColor: '#94a3b8' }}
                        >
                            {saving ? '...' : 'MAP'}
                        </button>
                    </div>
                </div>
            </div>

            {/* Bottom Section: Overview Table */}
            <div className="bg-white rounded-xl shadow-lg border border-slate-100">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                    <h2 className="text-lg font-bold text-slate-700">Global Faculty Mapping Overview</h2>
                    <div className="relative w-64">
                        <input
                            type="text"
                            placeholder="Search overview..."
                            className="w-full pl-8 pr-4 py-1 rounded-full border border-slate-200 text-sm focus:outline-none focus:border-blue-400"
                            value={searchTerm}
                            onChange={e => setSearchTerm(e.target.value)}
                        />
                        <svg className="w-4 h-4 text-gray-400 absolute left-3 top-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead className="bg-slate-50/50">
                            <tr>
                                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Department</th>
                                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Class</th>
                                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Subject</th>
                                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Type</th>
                                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Assigned Faculty</th>
                                <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filteredOverview.map(sub => (
                                <tr key={sub.id} className="hover:bg-slate-50/50 transition-colors duration-150">
                                    <td className="px-6 py-4 text-sm font-medium text-slate-600">
                                        {getDepartmentName(sub.department_id)}
                                    </td>
                                    <td className="px-6 py-4 font-medium text-slate-700">
                                        {getClassName(sub.class_id)}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="font-semibold text-slate-800">{sub.name}</div>
                                        <div className="text-xs text-slate-400">{sub.code}</div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`px-3 py-1 text-xs font-bold rounded-full ${sub.requires_lab
                                            ? 'bg-purple-100 text-purple-600'
                                            : 'bg-blue-100 text-blue-600'
                                            }`}>
                                            {sub.requires_lab ? 'LAB' : 'THEORY'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        {sub.faculty_id ? (
                                            <span className="px-3 py-1 text-xs font-bold rounded-full bg-green-100 text-green-700 flex items-center w-fit gap-1">
                                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
                                                {getFacultyName(sub.faculty_id)}
                                            </span>
                                        ) : (
                                            <span className="text-sm text-slate-400 italic">Unassigned</span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 flex gap-2">
                                        <button
                                            onClick={() => handleEditClick(sub)}
                                            className="p-1.5 text-blue-500 hover:bg-blue-50 rounded-full transition-colors"
                                            title="Edit Assignment"
                                        >
                                            <Edit size={16} />
                                        </button>
                                        {sub.faculty_id && (
                                            <button
                                                onClick={() => handleUnassignClick(sub.id)}
                                                className="p-1.5 text-red-500 hover:bg-red-50 rounded-full transition-colors"
                                                title="Unassign Faculty"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                            {filteredOverview.length === 0 && (
                                <tr>
                                    <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                                        No mappings found.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default FacultyMapping;
