import { useState } from 'react';
import { LogIn, UserPlus, Mail, Lock, User, AlertCircle } from 'lucide-react';

export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.');
      return;
    }
    setLoading(true);
    try {
      await onAuth(mode, email.trim(), password, displayName.trim() || undefined);
    } catch (err) {
      setError(err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-backdrop">
      <div className="auth-card">
        <div className="auth-logo">
          <span className="logo-icon">📋</span>
          <span className="logo-text">Plan-It</span>
        </div>
        <p className="auth-tagline">AI-Powered Planning Assistant</p>

        <div className="auth-tabs">
          <button
            className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); setError(''); }}
          >
            <LogIn size={14} /> Sign In
          </button>
          <button
            className={`auth-tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); setError(''); }}
          >
            <UserPlus size={14} /> Sign Up
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="auth-field">
              <User size={15} className="auth-field-icon" />
              <input
                type="text"
                placeholder="Display Name (optional)"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="auth-input"
              />
            </div>
          )}
          <div className="auth-field">
            <Mail size={15} className="auth-field-icon" />
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="auth-input"
              required
              autoFocus
            />
          </div>
          <div className="auth-field">
            <Lock size={15} className="auth-field-icon" />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="auth-input"
              required
              minLength={6}
            />
          </div>

          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px', fontStyle: 'italic', textAlign: 'center' }}>
            Note: The server may take ~1 minute to wake up (cold start).
          </div>

          {error && (
            <div className="auth-error">
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}
