import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { authAPI } from '../../services/api';
import { setToken, setUser } from '../../utils/auth';

export default function Login({ onLogin }) {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [loginRole, setLoginRole] = useState('faculty');

  const onSubmit = async (data) => {
    setLoading(true);
    setError('');
    try {
      const response = await authAPI.login(data.email, data.password);
      setToken(response.data.access_token);
      
      // Fetch current user info
      const userResponse = await authAPI.getCurrentUser();
      const user = userResponse.data;
      setUser(user);
      
      // Verification: if they selected 'admin' but are 'faculty', or vice versa?
      // Actually, let's just use what's in the DB.
      
      onLogin();
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-primary-900 to-blue-900">
      <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-500 rounded-2xl mb-4 shadow-lg shadow-primary-500/30">
             <span className="text-3xl">📅</span>
          </div>
          <h1 className="text-3xl font-black text-white mb-2 tracking-tight">Time Table Pro</h1>
          <p className="text-blue-200/70 font-medium">Smart Scheduling & Management</p>
        </div>

        <div className="flex bg-white/5 p-1 rounded-xl mb-8">
            <button 
                onClick={() => setLoginRole('faculty')}
                className={`flex-1 py-2.5 rounded-lg text-sm font-bold transition-all duration-300 ${loginRole === 'faculty' ? 'bg-white text-primary-900 shadow-lg' : 'text-white/60 hover:text-white'}`}
            >
                Faculty Login
            </button>
            <button 
                onClick={() => setLoginRole('admin')}
                className={`flex-1 py-2.5 rounded-lg text-sm font-bold transition-all duration-300 ${loginRole === 'admin' ? 'bg-primary-500 text-white shadow-lg shadow-primary-500/30' : 'text-white/60 hover:text-white'}`}
            >
                Admin Login
            </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div>
            <label className="block text-xs font-bold text-blue-200 uppercase tracking-widest mb-2 ml-1">Email Address</label>
            <input 
              {...register('email', { required: 'Email is required' })} 
              type="email" 
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all duration-300" 
              placeholder="name@institution.com" 
            />
            {errors.email && <p className="text-red-400 text-xs mt-1 ml-1">{errors.email.message}</p>}
          </div>
          
          <div>
            <label className="block text-xs font-bold text-blue-200 uppercase tracking-widest mb-2 ml-1">Password</label>
            <input 
              {...register('password', { required: 'Password is required' })} 
              type="password" 
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all duration-300" 
              placeholder="••••••••" 
            />
            {errors.password && <p className="text-red-400 text-xs mt-1 ml-1">{errors.password.message}</p>}
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-xl text-sm font-medium animate-pulse">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={loading} 
            className="w-full bg-primary-500 hover:bg-primary-600 disabled:opacity-50 text-white font-bold py-3.5 rounded-xl text-md transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] shadow-xl shadow-primary-500/20"
          >
            {loading ? (
                <div className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Signing in...
                </div>
            ) : 'Sign In'}
          </button>
        </form>

        <div className="mt-8 text-center pt-8 border-t border-white/5">
          <p className="text-sm text-blue-200/50">
            Don't have an account?{' '}
            <Link to="/register" className="font-bold text-primary-400 hover:text-primary-300 transition-colors">
              Create Account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
