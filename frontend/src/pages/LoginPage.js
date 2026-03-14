import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 text-white flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-20 left-20 w-72 h-72 border border-slate-400 rounded-full" />
          <div className="absolute bottom-32 right-16 w-96 h-96 border border-slate-400 rounded-full" />
          <div className="absolute top-1/2 left-1/3 w-48 h-48 border border-slate-400 rounded-full" />
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center">
              <span className="text-white font-heading font-bold">B2T</span>
            </div>
            <span className="font-heading font-bold text-2xl">Bank2Tally</span>
          </div>
        </div>
        <div className="relative z-10 space-y-6">
          <h1 className="font-heading text-4xl font-bold leading-tight">
            Bank Statements to<br />
            <span className="text-accent">Tally Entries</span><br />
            in Minutes.
          </h1>
          <p className="text-slate-400 text-lg max-w-md leading-relaxed">
            Upload any bank statement. Auto-detect format. Map ledgers intelligently. Export ready-to-import Tally XML.
          </p>
          <div className="flex gap-8 pt-4">
            <div>
              <p className="font-heading text-3xl font-bold text-accent">5+</p>
              <p className="text-slate-500 text-sm">Bank Formats</p>
            </div>
            <div>
              <p className="font-heading text-3xl font-bold text-accent">Auto</p>
              <p className="text-slate-500 text-sm">Ledger Mapping</p>
            </div>
            <div>
              <p className="font-heading text-3xl font-bold text-accent">XML</p>
              <p className="text-slate-500 text-sm">Tally Export</p>
            </div>
          </div>
        </div>
        <p className="text-slate-600 text-sm relative z-10">Built for Chartered Accountants & Accounting Firms</p>
      </div>

      {/* Right panel - form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md animate-fade-in">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center">
              <span className="text-white font-heading font-bold">B2T</span>
            </div>
            <span className="font-heading font-bold text-2xl text-slate-900">Bank2Tally</span>
          </div>
          <h2 className="font-heading text-2xl font-bold text-slate-900 mb-1">Welcome back</h2>
          <p className="text-slate-500 mb-8">Sign in to your account to continue</p>

          {error && (
            <div data-testid="login-error" className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
              <input
                data-testid="login-email-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full h-11 px-4 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-all"
                placeholder="you@company.com"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Password</label>
              <input
                data-testid="login-password-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full h-11 px-4 rounded-lg border border-slate-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-all"
                placeholder="Enter your password"
                required
              />
            </div>
            <button
              data-testid="login-submit-btn"
              type="submit"
              disabled={loading}
              className="w-full h-11 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          <p className="text-center text-sm text-slate-500 mt-6">
            Don't have an account?{' '}
            <Link to="/register" data-testid="register-link" className="text-accent font-medium hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
