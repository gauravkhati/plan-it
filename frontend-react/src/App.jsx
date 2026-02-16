import { useState, useEffect, useCallback } from 'react';
import ChatPanel from './ChatPanel';
import PlanPanel from './PlanPanel';
import AuthScreen from './AuthScreen';
import SessionSidebar from './SessionSidebar';
import {
  createSession, sendMessage, getPlanVersions, getSession, getHistory,
  login, register, setToken, getToken, clearAuth, listSessions,
} from './api';

export default function App() {
  // Auth state
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('planit_user')); } catch { return null; }
  });
  const isLoggedIn = !!user && !!getToken();

  // Session / plan state
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [pendingPlan, setPendingPlan] = useState(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [planSummary, setPlanSummary] = useState(null);
  const [changeSummary, setChangeSummary] = useState(null);
  const [conversationSummary, setConversationSummary] = useState(null);
  const [planVersions, setPlanVersions] = useState([]);
  const [turnCount, setTurnCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [updatedStepIds, setUpdatedStepIds] = useState(new Set());

  // ── Auth handlers ───────────────────────────────────────────────

  const handleAuth = async (mode, email, password, displayName) => {
    const fn = mode === 'login' ? login : register;
    const data = mode === 'login' ? await fn(email, password) : await fn(email, password, displayName);
    setToken(data.token);
    const userData = { user_id: data.user_id, email: data.email, display_name: data.display_name };
    localStorage.setItem('planit_user', JSON.stringify(userData));
    setUser(userData);
  };

  const handleLogout = () => {
    clearAuth();
    setUser(null);
    resetSession();
  };

  // ── Session management ──────────────────────────────────────────

  const resetSession = () => {
    setSessionId(null);
    setMessages([]);
    setCurrentPlan(null);
    setPendingPlan(null);
    setAwaitingConfirmation(false);
    setPlanSummary(null);
    setChangeSummary(null);
    setConversationSummary(null);
    setPlanVersions([]);
    setTurnCount(0);
    setUpdatedStepIds(new Set());
  };

  const initSession = async () => {
    try {
      const data = await createSession();
      resetSession();
      setSessionId(data.session_id);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const loadSession = async (sid) => {
    try {
      resetSession();
      setSessionId(sid);
      // Load session data
      const [sessionData, history] = await Promise.all([
        getSession(sid),
        getHistory(sid),
      ]);
      setMessages(history.map(m => ({ role: m.role, content: m.content })));
      setTurnCount(sessionData.turn_count || 0);
      if (sessionData.current_plan) setCurrentPlan(sessionData.current_plan);
      if (sessionData.conversation_summary) setConversationSummary(sessionData.conversation_summary);
      if (sessionData.plan_versions?.length) setPlanVersions(sessionData.plan_versions);
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  // Create first session when user logs in if no session active
  useEffect(() => {
    if (isLoggedIn && !sessionId) {
      // Check if user has existing sessions
      listSessions().then(sessions => {
        if (sessions.length > 0) {
          loadSession(sessions[0].session_id);
        } else {
          initSession();
        }
      }).catch(() => initSession());
    }
  }, [isLoggedIn]);

  // ── Chat handler ────────────────────────────────────────────────

  const handleSend = useCallback(
    async (text) => {
      if (!sessionId || !text.trim() || isLoading) return;

      setMessages((prev) => [...prev, { role: 'user', content: text }]);
      setIsLoading(true);

      try {
        const data = await sendMessage(sessionId, text);

        setMessages((prev) => [...prev, { role: 'assistant', content: data.response }]);
        setTurnCount(data.turn_count || 0);

        if (data.plan) {
          if (data.action === 'PROPOSE') {
            setPendingPlan(data.plan);
            setAwaitingConfirmation(true);
            setUpdatedStepIds(new Set());
          } else if (data.action === 'CREATE') {
            setCurrentPlan(data.plan);
            setPendingPlan(null);
            setAwaitingConfirmation(false);
            setUpdatedStepIds(new Set());
          } else if (data.action === 'UPDATE') {
            setCurrentPlan((prev) => {
              const changed = new Set();
              const oldMap = new Map();
              prev?.steps?.forEach(s => oldMap.set(s.id, s));
              data.plan.steps?.forEach(s => {
                const old = oldMap.get(s.id);
                if (!old) {
                  changed.add(s.id);
                } else if (
                  old.title !== s.title ||
                  old.description !== s.description ||
                  old.status !== s.status
                ) {
                  changed.add(s.id);
                }
              });
              setUpdatedStepIds(changed);
              return data.plan;
            });
          }
        } else {
          setUpdatedStepIds(new Set());
        }

        setAwaitingConfirmation(data.awaiting_confirmation ?? false);

        if (data.plan_summary) setPlanSummary(data.plan_summary);
        if (data.conversation_summary) setConversationSummary(data.conversation_summary);
        if (data.change_summary) setChangeSummary(data.change_summary);

        if (data.plan_version) {
          try {
            const versions = await getPlanVersions(sessionId);
            setPlanVersions(versions);
          } catch {}
        }
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
        ]);
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, isLoading]
  );

  const handleApprove = () => handleSend('Yes, go ahead and finalize this plan.');
  const handleReject = () => handleSend("I'd like to make some changes to this plan.");

  // ── Not logged in ───────────────────────────────────────────────

  if (!isLoggedIn) {
    return <AuthScreen onAuth={handleAuth} />;
  }

  // ── Main app ────────────────────────────────────────────────────

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">📋</span>
          <span className="logo-text">Plan-It</span>
        </div>
        <span className="tagline">AI-Powered Planning Assistant</span>
        <div className="header-user">
          <span className="header-email">{user?.display_name || user?.email}</span>
        </div>
      </header>

      <div className="app-body">
        <SessionSidebar
          user={user}
          activeSessionId={sessionId}
          onSelectSession={loadSession}
          onNewSession={initSession}
          onLogout={handleLogout}
        />

        <main className="app-main">
          <ChatPanel
            messages={messages}
            onSend={handleSend}
            isLoading={isLoading}
          />
          <PlanPanel
            currentPlan={currentPlan}
            pendingPlan={pendingPlan}
            awaitingConfirmation={awaitingConfirmation}
            planSummary={planSummary}
            changeSummary={changeSummary}
            conversationSummary={conversationSummary}
            planVersions={planVersions}
            turnCount={turnCount}
            sessionId={sessionId}
            updatedStepIds={updatedStepIds}
            onApprove={handleApprove}
            onReject={handleReject}
            onNewSession={initSession}
          />
        </main>
      </div>
    </div>
  );
}
