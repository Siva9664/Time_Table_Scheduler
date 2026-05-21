import React, { useState, useEffect } from 'react';
import { subjectAPI, facultyAPI, classAPI, departmentAPI, batchAPI } from '../../services/api';
import { useToast } from '../../context/ToastContext';
import { Edit, Trash2 } from 'lucide-react';
import ConfirmationModal from '../Layout/ConfirmationModal';
import CsvUploader from '../Layout/CsvUploader';
import Select from 'react-select';

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
        // Restore cached selections on mount
        const cachedSelections = localStorage.getItem('facultyMappingCache');
        if (cachedSelections) {
            const cached = JSON.parse(cachedSelections);
            if (cached.selectedBatchId) setSelectedBatchId(cached.selectedBatchId);
            if (cached.selectedDeptId) setSelectedDeptId(cached.selectedDeptId);
            if (cached.selectedClassId) setSelectedClassId(cached.selectedClassId);
            if (cached.selectedSubjectId) setSelectedSubjectId(cached.selectedSubjectId);
            if (cached.selectedFacultyId) setSelectedFacultyId(cached.selectedFacultyId);
        }
    }, []);

    // Cache selections whenever they change
    useEffect(() => {
        const selectionsToCache = {
            selectedBatchId,
            selectedDeptId,
            selectedClassId,
            selectedSubjectId,
            selectedFacultyId
        };
        localStorage.setItem('facultyMappingCache', JSON.stringify(selectionsToCache));
    }, [selectedBatchId, selectedDeptId, selectedClassId, selectedSubjectId, selectedFacultyId]);

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
                class_id: selectedClassId,
                faculty_id: selectedFacultyId
            });

            // Optimistically update local state instead of doing a full slow re-fetch
            setSubjects(prev => prev.map(s => 
                s.id === selectedSubjectId ? { ...s, class_id: selectedClassId, faculty_id: selectedFacultyId } : s
            ));

            // Reset form partly (keep faculty selected)
            setSelectedSubjectId('');

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
        setTimeout(() => {
            document.querySelector('.main-content')?.scrollTo({ top: 0, behavior: 'smooth' });
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }, 50);
    };

    const handleUnassignClick = (id) => {
        setSubjectToUnassign(id);
        setIsUnassignModalOpen(true);
    };

    const confirmUnassign = async () => {
        if (!subjectToUnassign) return;
        try {
            await subjectAPI.update(subjectToUnassign, { faculty_id: null });
            // Optimistically update local state instead of doing a full slow re-fetch
            setSubjects(prev => prev.map(s => 
                s.id === subjectToUnassign ? { ...s, faculty_id: null } : s
            ));
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
        const fac = faculties.find(f => f.id === facId);
        return fac ? fac.name : 'Unassigned';
    };

    const getClassName = (classId) => {
        const cls = classes.find(c => c.id === classId);
        return cls ? `${cls.name} ${cls.section}` : 'Unassigned';
    };

    // --- Filtering Logic for Dropdowns ---

    // 1. Filter Classes based on Batch AND Department
    const availableClasses = classes.filter(c => {
        const matchBatch = !selectedBatchId || c.batch_id === selectedBatchId;
        const matchDept = !selectedDeptId || c.department_id === selectedDeptId;
        return matchBatch && matchDept;
    });

    // 2. Filter Subjects based on Class
    const availableSubjects = subjects.filter(s => {
        if (!selectedClassId) return false;
        const selectedClass = classes.find(c => c.id === selectedClassId);
        if (!selectedClass) return false;

        const subjectDeptIds = s.department_ids && s.department_ids.length > 0
            ? s.department_ids
            : s.department_id ? [s.department_id] : [];

        return subjectDeptIds.includes(selectedClass.department_id) &&
            (!s.batch_id || s.batch_id === selectedClass.batch_id);
    });

    // 3. ALL faculty are available cross-department — a faculty can teach
    //    subjects in any department. Sort by name for easy lookup.
    const availableFaculties = [...faculties].sort((a, b) =>
        (a.name || '').localeCompare(b.name || '')
    );


    // --- Filtering Logic for Table (Search) ---
    const getSubjectDepartmentNames = (sub) => {
        const ids = sub.department_ids && sub.department_ids.length > 0
            ? sub.department_ids
            : sub.department_id ? [sub.department_id] : [];
        return ids.map(getDepartmentName).filter(Boolean).join(', ');
    };

    const filteredOverview = subjects.filter(sub => {
        const term = searchTerm.toLowerCase();
        const deptName = getSubjectDepartmentNames(sub).toLowerCase();
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
                <div className="flex flex-wrap items-end gap-4">

                    {/* Batch Select */}
                    <div className="flex-1 min-w-[120px]">
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
                    <div className="flex-1 min-w-[120px]">
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
                    <div className="flex-1 min-w-[140px]">
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
                    <div className="flex-1 min-w-[160px]">
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

                    {/* Faculty Select — shows ALL faculty across all departments */}
                    <div className="flex-[2] min-w-[200px]">
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">
                            Faculty <span className="text-blue-400 normal-case font-normal">(any dept)</span>
                        </label>
                        <Select
                            options={availableFaculties.map(f => ({
                                value: f.id,
                                label: `${f.name}${f.department_id ? ` (${getDepartmentName(f.department_id)})` : ''}`
                            }))}
                            value={
                                selectedFacultyId 
                                ? { 
                                    value: selectedFacultyId, 
                                    label: (() => {
                                        const f = availableFaculties.find(fac => fac.id === selectedFacultyId);
                                        return f ? `${f.name}${f.department_id ? ` (${getDepartmentName(f.department_id)})` : ''}` : '';
                                    })()
                                  } 
                                : null
                            }
                            onChange={(option) => setSelectedFacultyId(option ? option.value : '')}
                            isClearable
                            placeholder="Search..."
                            styles={{
                                control: (base) => ({
                                    ...base,
                                    minHeight: '40px',
                                    borderRadius: '0.5rem',
                                    borderColor: '#e2e8f0',
                                    backgroundColor: '#f8fafc',
                                    boxShadow: 'none',
                                    '&:hover': { borderColor: '#cbd5e1' }
                                }),
                                menu: (base) => ({ ...base, zIndex: 50 })
                            }}
                        />
                    </div>

                    {/* MAP Button */}
                    <div className="w-full sm:w-auto">
                        <button
                            onClick={handleMap}
                            disabled={saving}
                            className="w-full px-2 py-2 bg-slate-400 text-white font-bold rounded-lg hover:bg-slate-500 shadow-lg transition-all duration-200"
                            style={{ backgroundColor: '#94a3b8', height: '40px' }}
                        >
                            {saving ? '...' : 'MAP'}
                        </button>
                    </div>

                    {/* CSV Upload Button */}
                    <div className="w-full sm:w-auto">
                        <CsvUploader
                            type="mappings"
                            onSuccess={loadData}
                            className="w-full px-4 py-2 bg-slate-400 text-white font-bold rounded-lg hover:bg-slate-500 shadow-lg transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer"
                            style={{ backgroundColor: '#94a3b8', height: '40px' }}
                        />
                    </div>
                </div>
                
                {/* CSV Format Helper Hint */}
                <div className="mt-3 text-xs text-slate-400 text-right">
                    CSV format: <code className="bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">subject_code, class_name, class_section, faculty_email</code>
                </div>
            </div>

            {/* Bottom Section: Overview Table */}
            <div className="bg-white rounded-xl shadow-lg border border-slate-100">
                <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <h2 className="text-lg font-bold text-slate-700">Global Faculty Mapping Overview</h2>

                    {/* Search */}
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
                                        {getSubjectDepartmentNames(sub) || '-'}
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
