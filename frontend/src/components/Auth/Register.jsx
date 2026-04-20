import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { authAPI } from '../../services/api';
import { setToken, setUser } from '../../utils/auth';
import { Link, useNavigate } from 'react-router-dom';

export default function Register({ onRegister }) {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onSubmit = async (data) => {
    setLoading(true);
    setError('');
    try {
      // 1. Register the new user
      await authAPI.register({
        username: data.username,
        email: data.email,
        full_name: data.full_name,
        password: data.password,
        role: "admin"
      });

      // 2. Automatically log them in after registration
      const loginResponse = await authAPI.login(data.email, data.password);
      setToken(loginResponse.data.access_token);
      
      const userResponse = await authAPI.getCurrentUser();
      setUser(userResponse.data);
      
      if (onRegister) {
        onRegister();
      } else {
        navigate('/');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-primary-900 to-blue-900 py-12 px-4">
      <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl p-8 w-full max-w-md">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-500 rounded-2xl mb-4 shadow-lg shadow-primary-500/30">
             <span className="text-3xl">✨</span>
          </div>
          <h1 className="text-3xl font-black text-white mb-2 tracking-tight">Join Us</h1>
          <p className="text-blue-200/70 font-medium">Create your scheduler account</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-blue-200 uppercase tracking-widest mb-1.5 ml-1">Username</label>
            <input 
              {...register('username', { required: 'Username is required' })} 
              type="text" 
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all duration-300" 
              placeholder="shiva_99" 
            />
            {errors.username && <p className="text-red-400 text-xs mt-1 ml-1">{errors.username.message}</p>}
          </div>

          <div>
            <label className="block text-xs font-bold text-blue-200 uppercase tracking-widest mb-1.5 ml-1">Full Name</label>
            <input 
              {...register('full_name', { required: 'Full name is required' })} 
              type="text" 
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all duration-300" 
              placeholder="Shiva Kumar" 
            />
            {errors.full_name && <p className="text-red-400 text-xs mt-1 ml-1">{errors.full_name.message}</p>}
          </div>

          <div>
            <label className="block text-xs font-bold text-blue-200 uppercase tracking-widest mb-1.5 ml-1">Email Address</label>
            <input 
              {...register('email', { 
                required: 'Email is required',
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: 'Invalid email address'
                }
              })} 
              type="email" 
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all duration-300" 
              placeholder="shiva@institution.com" 
            />
            {errors.email && <p className="text-red-400 text-xs mt-1 ml-1">{errors.email.message}</p>}
          </div>

          <div className="hidden">
            <input 
              {...register('role')} 
              type="hidden" 
              value="admin"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-blue-200 uppercase tracking-widest mb-1.5 ml-1">Password</label>
            <input 
              {...register('password', { 
                required: 'Password is required',
                minLength: {
                  value: 6,
                  message: 'Password must be at least 6 characters'
                }
              })} 
              type="password" 
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all duration-300" 
              placeholder="••••••••" 
            />
            {errors.password && <p className="text-red-400 text-xs mt-1 ml-1">{errors.password.message}</p>}
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-xl text-sm font-medium">
              {error}
            </div>
          )}
          
          <button 
            type="submit" 
            disabled={loading} 
            className="w-full bg-primary-500 hover:bg-primary-600 disabled:opacity-50 text-white font-bold py-3.5 rounded-xl text-md transition-all duration-300 transform hover:scale-[1.02] active:scale-[0.98] shadow-xl shadow-primary-500/20 mt-4"
          >
            {loading ? (
                 <div className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Creating Account...
                </div>
            ) : 'Create Account'}
          </button>
        </form>

        <div className="mt-8 text-center pt-8 border-t border-white/5">
          <p className="text-sm text-blue-200/50">
            Already have an account?{' '}
            <Link to="/login" className="font-bold text-primary-400 hover:text-primary-300 transition-colors">
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
