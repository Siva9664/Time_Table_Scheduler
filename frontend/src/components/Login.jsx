import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import { setToken, setUser, firebaseEmailLogin } from '../utils/auth';
import { useToast } from '../context/ToastContext';
import {
  Calendar,
  Lock,
  User,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  GraduationCap,
  Clock,
  Cpu,
  BookOpen,
  Network
} from 'lucide-react';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();
  const { showToast } = useToast();

  const cardRef = useRef(null);
  const [tiltStyle, setTiltStyle] = useState({});

  // 3D Parallax Tilt Effect on Mouse Move
  const handleMouseMove = (e) => {
    if (!cardRef.current) return;
    const card = cardRef.current;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;

    // Constrain rotation to maximum of 4 degrees for subtle premium feel
    const rotateX = -(y / (rect.height / 2)) * 4;
    const rotateY = (x / (rect.width / 2)) * 4;

    setTiltStyle({
      transform: `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`,
      transition: 'transform 0.08s ease-out, box-shadow 0.3s ease'
    });
  };

  const handleMouseLeave = () => {
    setTiltStyle({
      transform: 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)',
      transition: 'transform 0.6s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease'
    });
  };

  const handleLogin = async (e) => {
    if (e) e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMsg('Please enter both username and password.');
      return;
    }

    setErrorMsg('');
    setIsLoading(true);

    try {
      // 1. Try Firebase Authentication first
      const firebaseUser = await firebaseEmailLogin(username.trim(), password.trim());
      const isAdminUser = firebaseUser.email?.toLowerCase().includes('admin');
      
      setUser({
        uid: firebaseUser.uid,
        username: firebaseUser.displayName || firebaseUser.email.split('@')[0],
        full_name: firebaseUser.displayName || firebaseUser.email.split('@')[0],
        email: firebaseUser.email,
        role: isAdminUser ? 'admin' : 'faculty',
        is_admin: isAdminUser,
      });

      showToast('Successfully logged in!', 'success');
      navigate('/');
      return;
    } catch (firebaseErr) {
      console.warn('Firebase auth failed, trying backend API...', firebaseErr.message);
    }

    try {
      // 2. Fallback: Try backend API login
      const response = await authAPI.login(username, password);
      const data = response.data;
      if (data && data.access_token) {
        setToken(data.access_token);

        try {
          const userRes = await authAPI.getCurrentUser();
          setUser(userRes.data);
        } catch (profileErr) {
          setUser({
            username: username,
            full_name: username.charAt(0).toUpperCase() + username.slice(1),
            role: username.toLowerCase().includes('admin') ? 'admin' : 'faculty',
            is_admin: username.toLowerCase().includes('admin')
          });
        }

        showToast('Successfully logged in!', 'success');
        navigate('/');
        return;
      }
    } catch (apiErr) {
      console.warn('Backend API auth failed, trying demo credentials...', apiErr.message);
    }

    // 3. Fallback: Mock demo credentials
    const normalizedUser = username.trim().toLowerCase();
    const normalizedPass = password.trim();

    if (normalizedUser === 'admin' && normalizedPass === 'admin123') {
      setToken('mock-admin-token-12345');
      setUser({
        username: 'admin',
        full_name: 'Administrator',
        role: 'admin',
        is_admin: true,
        tenant_db_name: 'timetable_scheduler'
      });
      showToast('Demo Admin Logged In', 'success');
      navigate('/');
    } else if (normalizedUser === 'faculty' && normalizedPass === 'faculty123') {
      setToken('mock-faculty-token-54321');
      setUser({
        username: 'faculty',
        full_name: 'Dr. Jane Smith (Faculty)',
        role: 'faculty',
        is_admin: false,
        tenant_db_name: 'timetable_scheduler'
      });
      showToast('Demo Faculty Logged In', 'success');
      navigate('/');
    } else {
      setErrorMsg('Invalid credentials. Check your email/password or use demo access below.');
    }

    setIsLoading(false);
  };

  const handleDemoFill = (role) => {
    setErrorMsg('');
    if (role === 'admin') {
      setUsername('admin');
      setPassword('admin123');
    } else {
      setUsername('faculty');
      setPassword('faculty123');
    }
  };

  // Automatically submit after filling demo credentials for super smooth interaction
  useEffect(() => {
    if ((username === 'admin' && password === 'admin123') || (username === 'faculty' && password === 'faculty123')) {
      const timer = setTimeout(() => {
        handleLogin();
      }, 400);
      return () => clearTimeout(timer);
    }
  }, [username, password]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 md:p-8 relative overflow-hidden select-none bg-bg-primary font-sans">
      
      {/* BACKGROUND DECORATIONS */}
      {/* Soft mesh background */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(247,249,252,0.85),rgba(247,249,252,0.85)),radial-gradient(at_top_left,rgba(79,124,255,0.09),transparent_60%),radial-gradient(at_bottom_right,rgba(108,92,255,0.06),transparent_60%)] pointer-events-none" />

      {/* Very soft blue radial gradients and moving blobs */}
      <div className="absolute top-[-15%] left-[-10%] w-[50vw] h-[50vw] max-w-[600px] max-h-[600px] rounded-full bg-accent-blue/8 blur-[100px] pointer-events-none animate-blob-drift" />
      <div className="absolute bottom-[-15%] right-[-10%] w-[55vw] h-[55vw] max-w-[700px] max-h-[700px] rounded-full bg-grad-end/6 blur-[120px] pointer-events-none animate-blob-drift-reverse" />
      
      {/* Floating glass shapes */}
      <div className="absolute top-[18%] right-[12%] w-[220px] h-[110px] rounded-full bg-white/10 border border-white/20 backdrop-blur-[10px] animate-float-slow pointer-events-none select-none hidden lg:block opacity-40 shadow-[0_10px_30px_rgba(0,0,0,0.01)]" />
      <div className="absolute bottom-[22%] left-[10%] w-[130px] h-[130px] rounded-[38px] bg-white/8 border border-white/15 backdrop-blur-[8px] animate-float-slower rotate-[15deg] pointer-events-none select-none hidden lg:block opacity-35 shadow-[0_10px_30px_rgba(0,0,0,0.01)]" />
      
      {/* Tiny glowing particles */}
      <div className="absolute top-[30%] left-[25%] w-2 h-2 rounded-full bg-accent-blue/30 blur-[1px] animate-float-slow" style={{ animationDelay: '1s' }} />
      <div className="absolute top-[75%] left-[40%] w-1.5 h-1.5 rounded-full bg-grad-end/25 blur-[1px] animate-float-slower" style={{ animationDelay: '3s' }} />
      <div className="absolute top-[20%] right-[35%] w-2.5 h-2.5 rounded-full bg-accent-blue/20 blur-[1.5px] animate-float-slow" style={{ animationDelay: '0.5s' }} />
      <div className="absolute bottom-[35%] right-[22%] w-1.5 h-1.5 rounded-full bg-grad-end/30 blur-[0.8px] animate-float-slower" style={{ animationDelay: '2.2s' }} />

      {/* Subtle floating academic decoration icons */}
      <div className="absolute top-[12%] left-[15%] text-accent-blue/15 animate-float-slow pointer-events-none select-none" style={{ animationDelay: '0s' }}>
        <GraduationCap size={44} strokeWidth={1.2} />
      </div>
      <div className="absolute top-[15%] right-[20%] text-grad-end/15 animate-float-slower pointer-events-none select-none" style={{ animationDelay: '1.5s' }}>
        <Clock size={36} strokeWidth={1.2} />
      </div>
      <div className="absolute bottom-[28%] left-[18%] text-accent-blue/15 animate-float-slower pointer-events-none select-none" style={{ animationDelay: '2.5s' }}>
        <Cpu size={40} strokeWidth={1.2} />
      </div>
      <div className="absolute bottom-[16%] right-[15%] text-grad-end/15 animate-float-slow pointer-events-none select-none" style={{ animationDelay: '0.8s' }}>
        <BookOpen size={42} strokeWidth={1.2} />
      </div>
      <div className="absolute top-[48%] left-[6%] text-accent-blue/10 animate-float-slower pointer-events-none select-none" style={{ animationDelay: '3.2s' }}>
        <Calendar size={38} strokeWidth={1.2} />
      </div>
      <div className="absolute top-[55%] right-[8%] text-grad-end/10 animate-float-slow pointer-events-none select-none" style={{ animationDelay: '2s' }}>
        <Network size={40} strokeWidth={1.2} />
      </div>

      {/* LOGIN CARD WRAPPER */}
      <div 
        ref={cardRef}
        style={tiltStyle}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="relative w-full max-w-[480px] bg-white/78 backdrop-blur-[30px] rounded-[28px] border border-white/60 p-8 md:p-12 shadow-premium hover:shadow-premium-hover transition-all duration-300 z-10 animate-fade-in-up"
      >
        
        {/* LOGO & BRAND HEADER */}
        <div className="text-center mb-10 flex flex-col items-center select-none">
          <div className="relative mb-5 flex items-center justify-center">
            {/* Soft glow behind the logo */}
            <div className="absolute -inset-4 bg-accent-blue/20 rounded-full blur-xl animate-pulse" />
            {/* Logo container */}
            <div className="relative w-[72px] h-[72px] bg-gradient-to-tr from-accent-blue to-grad-end rounded-2xl flex items-center justify-center shadow-lg shadow-accent-blue/20 text-white animate-float-slow">
              <Calendar size={34} className="text-white" strokeWidth={2.2} />
            </div>
          </div>
          <h2 className="text-[34px] font-extrabold text-text-primary tracking-tight leading-none font-sans">
            AI Timetable Scheduler
          </h2>
          <p className="text-[14px] font-medium text-text-secondary mt-2.5 max-w-[300px] leading-relaxed">
            Generate Academic Schedules using Artificial Intelligence
          </p>
        </div>

        {/* ERROR DISPLAY */}
        {errorMsg && (
          <div className="mb-6 p-4 bg-red-50/60 backdrop-blur-md border border-red-200/40 rounded-2xl text-[13px] font-semibold text-red-600 flex items-start gap-3 animate-headshake">
            <AlertCircle size={18} className="shrink-0 text-red-500 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* FORM */}
        <form onSubmit={handleLogin} className="space-y-5">
          
          {/* USERNAME INPUT */}
          <div className="relative flex items-center h-[58px] bg-[#F8FAFC] border border-transparent rounded-[16px] hover:border-accent-blue/30 focus-within:border-accent-blue focus-within:ring-[3px] focus-within:ring-accent-blue/15 transition-all duration-300">
            <span className="absolute left-4 text-text-secondary/50 transition-colors pointer-events-none">
              <User size={18} />
            </span>
            <input
              id="username"
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder=" "
              className="peer w-full h-full pl-12 pr-4 pt-4 bg-transparent outline-none text-[15px] font-semibold text-text-primary"
            />
            <label
              htmlFor="username"
              className="absolute left-12 top-1/2 -translate-y-1/2 text-[14px] font-semibold text-text-secondary/50 pointer-events-none transition-all duration-200 peer-focus:text-[10px] peer-focus:translate-y-[-16px] peer-focus:text-accent-blue peer-[:not(:placeholder-shown)]:text-[10px] peer-[:not(:placeholder-shown)]:translate-y-[-16px]"
            >
              Username or Email
            </label>
          </div>

          {/* PASSWORD INPUT */}
          <div className="relative flex items-center h-[58px] bg-[#F8FAFC] border border-transparent rounded-[16px] hover:border-accent-blue/30 focus-within:border-accent-blue focus-within:ring-[3px] focus-within:ring-accent-blue/15 transition-all duration-300">
            <span className="absolute left-4 text-text-secondary/50 transition-colors pointer-events-none">
              <Lock size={18} />
            </span>
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder=" "
              className="peer w-full h-full pl-12 pr-14 pt-4 bg-transparent outline-none text-[15px] font-semibold text-text-primary"
            />
            <label
              htmlFor="password"
              className="absolute left-12 top-1/2 -translate-y-1/2 text-[14px] font-semibold text-text-secondary/50 pointer-events-none transition-all duration-200 peer-focus:text-[10px] peer-focus:translate-y-[-16px] peer-focus:text-accent-blue peer-[:not(:placeholder-shown)]:text-[10px] peer-[:not(:placeholder-shown)]:translate-y-[-16px]"
            >
              Password
            </label>
            {/* Eye Toggle Container */}
            <div className="absolute right-3.5 flex items-center justify-center">
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="p-1.5 bg-slate-200/40 hover:bg-slate-200/70 rounded-full text-text-secondary hover:text-text-primary transition-all duration-200 cursor-pointer"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {/* REMEMBER & FORGOT */}
          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              className="text-[13px] ml-66 font-bold text-black hover:text-grad-end transition-colors cursor-pointer"
            >
              Forgot password?
            </button>
          </div>

          {/* SIGN IN BUTTON */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-[58px] relative group flex items-center justify-center bg-gradient-to-r from-accent-blue to-grad-end text-white font-bold rounded-[16px] text-[15px] transition-all duration-300 shadow-premium-glow hover:shadow-[0_15px_35px_rgba(79,124,255,0.35)] hover:-translate-y-0.5 active:scale-[0.98] disabled:opacity-75 disabled:pointer-events-none cursor-pointer"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <span className="flex items-center justify-center gap-2 tracking-wide">
                Sign In 
                <ArrowRight size={18} className="group-hover:translate-x-1.5 transition-transform duration-300" />
              </span>
            )}
          </button>
        </form>

        {/* QUICK LOGIN ROLE CARDS */}
        <div className="space-y-4 pt-8 border-t border-premium-border mt-8">
          <div className="flex items-center justify-center gap-1.5 text-[11px] font-bold text-text-secondary/70 tracking-widest uppercase">
            <Sparkles size={14} className="text-yellow-500" />
            <span>Quick Demo Access</span>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <button
              type="button"
              onClick={() => handleDemoFill('admin')}
              className="group flex flex-col items-start p-4 rounded-2xl border border-premium-border bg-slate-50/40 hover:bg-white hover:border-accent-blue/40 hover:shadow-premium transition-all duration-300 text-left relative overflow-hidden cursor-pointer"
            >
              <div className="absolute top-0 right-0 w-[40px] h-[40px] bg-accent-blue/5 rounded-bl-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
              <div className="flex items-center gap-2 mb-2 w-full">
                <div className="p-1.5 bg-accent-blue/10 rounded-lg text-accent-blue group-hover:scale-110 transition-transform duration-300">
                  <ShieldCheck size={16} />
                </div>
                <span className="text-[13px] font-extrabold text-text-primary">Admin</span>
                <span className="text-[9px] font-bold bg-accent-blue/10 text-accent-blue px-1.5 py-0.5 rounded-full ml-auto">
                  Demo
                </span>
              </div>
              <p className="text-[11px] text-text-secondary font-medium leading-relaxed">
                Full configuration and scheduling access.
              </p>
            </button>
            
            <button
              type="button"
              onClick={() => handleDemoFill('faculty')}
              className="group flex flex-col items-start p-4 rounded-2xl border border-premium-border bg-slate-50/40 hover:bg-white hover:border-grad-end/40 hover:shadow-premium transition-all duration-300 text-left relative overflow-hidden cursor-pointer"
            >
              <div className="absolute top-0 right-0 w-[40px] h-[40px] bg-grad-end/5 rounded-bl-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
              <div className="flex items-center gap-2 mb-2 w-full">
                <div className="p-1.5 bg-grad-end/10 rounded-lg text-grad-end group-hover:scale-110 transition-transform duration-300">
                  <GraduationCap size={16} />
                </div>
                <span className="text-[13px] font-extrabold text-text-primary">Faculty</span>
                <span className="text-[9px] font-bold bg-grad-end/10 text-grad-end px-1.5 py-0.5 rounded-full ml-auto">
                  Demo
                </span>
              </div>
              <p className="text-[11px] text-text-secondary font-medium leading-relaxed">
                View schedules and manage faculty slots.
              </p>
            </button>
          </div>
        </div>
      </div>

      {/* FOOTER */}
      <div className="w-full max-w-[480px] flex items-center justify-between mt-6 text-[11px] font-bold text-text-secondary/50 px-4 select-none z-10">
        <span>© 2026 AI Timetable Scheduler</span>
        <div className="flex items-center gap-3">
          <a href="#" className="hover:text-text-primary transition-colors">Privacy Policy</a>
          <span className="w-1 h-1 bg-slate-300 rounded-full" />
          <a href="#" className="hover:text-text-primary transition-colors">Terms</a>
        </div>
      </div>

    </div>
  );
}
