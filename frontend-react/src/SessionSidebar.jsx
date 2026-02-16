import { useState, useEffect } from 'react';
import { Plus, FileText, ChevronRight, LogOut, MessageSquare } from 'lucide-react';
import { listSessions } from './api';

export default function SessionSidebar({ user, activeSessionId, onSelectSession, onNewSession, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  // Refresh when active session changes (plan may have been created)
  useEffect(() => { if (activeSessionId) refresh(); }, [activeSessionId]);

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-user">
          <div className="sidebar-avatar">{(user?.email?.[0] || '?').toUpperCase()}</div>
          <div className="sidebar-user-info">
            <span className="sidebar-name">{user?.display_name || user?.email}</span>
          </div>
        </div>
        <button className="sidebar-logout" onClick={onLogout} title="Sign out">
          <LogOut size={15} />
        </button>
      </div>

      <button className="sidebar-new" onClick={async () => { await onNewSession(); refresh(); }}>
        <Plus size={15} /> New Plan
      </button>

      <div className="sidebar-list">
        {loading && <p className="sidebar-empty">Loading…</p>}
        {!loading && sessions.length === 0 && (
          <p className="sidebar-empty">No plans yet. Create one!</p>
        )}
        {sessions.map((s) => (
          <button
            key={s.session_id}
            className={`sidebar-item ${s.session_id === activeSessionId ? 'active' : ''}`}
            onClick={() => onSelectSession(s.session_id)}
          >
            <FileText size={14} />
            <div className="sidebar-item-info">
              <span className="sidebar-item-name">{s.plan_name || 'Untitled Plan'}</span>
              <span className="sidebar-item-meta">
                {s.turn_count} turn{s.turn_count !== 1 ? 's' : ''}
                {s.has_plan ? ' · Has plan' : ''}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
