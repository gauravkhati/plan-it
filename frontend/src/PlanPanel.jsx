import { useState, useRef } from 'react';
import {
  CheckCircle2,
  Circle,
  Clock,
  ChevronDown,
  ChevronRight,
  FileText,
  History,
  MessageSquareText,
  Sparkles,
  ArrowRightCircle,
  XCircle,
  Info,
} from 'lucide-react';

const STATUS = {
  pending:       { icon: Circle,       color: '#94a3b8', label: 'Pending' },
  'in-progress': { icon: Clock,        color: '#f59e0b', label: 'In Progress' },
  completed:     { icon: CheckCircle2,  color: '#10b981', label: 'Completed' },
};

/* ── Step row ─────────────────────────────────────────────────────── */
function StepRow({ step, num, highlighted }) {
  const [open, setOpen] = useState(false);
  const s = STATUS[step.status] || STATUS.pending;
  const Icon = s.icon;

  return (
    <li className={`pp-step ${step.status}${highlighted ? ' pp-step-updated' : ''}`}>
      <button className="pp-step-row" onClick={() => setOpen(!open)}>
        <Icon size={15} color={s.color} />
        <span className="pp-step-num">{num}</span>
        <span className="pp-step-title">{step.title}</span>
        {highlighted && (
          <span className="pp-step-updated-tag">Updated</span>
        )}
        <span className="pp-step-badge" style={{ background: s.color + '1a', color: s.color }}>
          {s.label}
        </span>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
      </button>
      {open && <p className="pp-step-desc">{step.description}</p>}
    </li>
  );
}

/* ── Compact plan renderer ────────────────────────────────────────── */
function PlanBlock({ plan, updatedStepIds }) {
  if (!plan) return null;
  const done  = plan.steps?.filter(s => s.status === 'completed').length || 0;
  const total = plan.steps?.length || 0;
  const pct   = total ? Math.round((done / total) * 100) : 0;

  return (
    <div className="pp-plan">
      <h4 className="pp-plan-title">{plan.title}</h4>
      {plan.overview && <p className="pp-plan-overview">{plan.overview}</p>}

      {total > 0 && (
        <div className="pp-progress">
          <div className="pp-progress-track">
            <div className="pp-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="pp-progress-label">{done}/{total} done ({pct}%)</span>
        </div>
      )}

      <ul className="pp-steps">
        {plan.steps?.map((step, i) => (
          <StepRow
            key={step.id}
            step={step}
            num={i + 1}
            highlighted={updatedStepIds?.has(step.id)}
          />
        ))}
      </ul>
    </div>
  );
}

/* ── Version history item with inline accordion ────────────────────── */
function VersionItem({ version, isLatest }) {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <div className="pp-timeline-item">
      <div className="pp-timeline-marker">
        <div className={`pp-timeline-dot ${isLatest ? 'latest' : ''}`}>
          {isLatest ? <Sparkles size={12} /> : <History size={12} />}
        </div>
        <div className="pp-timeline-line" />
      </div>
      
      <div className="pp-timeline-content">
        <button 
          className="pp-ver-header"
          onClick={() => setExpanded(!expanded)}
          type="button"
        >
          <div className="pp-ver-header-left">
            <span className="pp-ver-badge">v{version.version}</span>
            <span className="pp-ver-summary">{version.change_summary}</span>
          </div>
          <div className="pp-ver-header-right">
            {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </div>
        </button>
        
        {expanded && (
          <div className="pp-ver-details">
            <PlanBlock plan={version.plan} />
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Version history (timeline style) ───────────────────────────────── */
function Versions({ versions }) {
  const [show, setShow] = useState(false);
  
  // If no versions, don't render anything
  if (!versions || versions.length === 0) return null;

  return (
    <div className="pp-card">
      <button 
        className="pp-card-hdr pp-card-hdr-clickable" 
        onClick={() => setShow(!show)}
        type="button"
      >
        <History size={14} />
        <span>Version History ({versions.length})</span>
        <div style={{ marginLeft: 'auto' }}>
          {show ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {show && (
        <div className="pp-timeline">
          {[...versions].reverse().map((v, idx) => (
            <VersionItem 
              key={v.version} 
              version={v} 
              isLatest={idx === 0}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Main panel ───────────────────────────────────────────────────── */
export default function PlanPanel({
  currentPlan, pendingPlan, awaitingConfirmation,
  planSummary, changeSummary, conversationSummary,
  planVersions, turnCount, sessionId, updatedStepIds,
  onApprove, onReject, onNewSession,
}) {
  return (
    <div className="pp">
      {/* fixed header */}
      <div className="pp-header">
        <FileText size={18} />
        <span>Plan Dashboard</span>
      </div>

      {/* scrollable body — uses absolute positioning for reliable scroll */}
      <div className="pp-scroll-wrapper">
        <div className="pp-body">

          {/* proposed plan */}
          {awaitingConfirmation && pendingPlan && (
            <div className="pp-card pp-proposed">
              <div className="pp-proposed-banner">
                <Sparkles size={14} /> Proposed — Awaiting Confirmation
              </div>
              {planSummary && (
                <div className="pp-note pp-note-blue">
                  <Info size={13} /> {planSummary}
                </div>
              )}
              <PlanBlock plan={pendingPlan} />
              <div className="pp-actions">
                <button className="btn btn-primary" onClick={onApprove}>
                  <CheckCircle2 size={14} /> Approve
                </button>
                <button className="btn btn-secondary" onClick={onReject}>
                  <XCircle size={14} /> Revise
                </button>
              </div>
            </div>
          )}

          {/* current plan */}
          <div className="pp-card">
            <div className="pp-card-hdr">
              <ArrowRightCircle size={14} /> Current Plan
            </div>

            {currentPlan ? (
              <>
                {planSummary && !awaitingConfirmation && (
                  <div className="pp-note pp-note-blue"><Info size={13} /> {planSummary}</div>
                )}
                {changeSummary && !awaitingConfirmation && (
                  <div className="pp-note pp-note-green"><Sparkles size={13} /> {changeSummary}</div>
                )}
                <PlanBlock plan={currentPlan} updatedStepIds={updatedStepIds} />
              </>
            ) : (
              <div className="pp-empty">
                <FileText size={28} strokeWidth={1.2} />
                <p>No plan yet — start chatting!</p>
              </div>
            )}
          </div>

          {/* versions */}
          <Versions versions={planVersions} />

          {/* conversation summary */}
          {conversationSummary && (
            <div className="pp-card">
              <div className="pp-card-hdr">
                <MessageSquareText size={14} /> Conversation Summary
              </div>
              <p className="pp-conv-summary">{conversationSummary}</p>
            </div>
          )}

          {/* footer */}
          <div className="pp-footer">
            {/* <span className="pp-meta">Turn {turnCount} · {sessionId?.slice(0, 8)}…</span> */}
            {/* <button className="btn btn-ghost" onClick={onNewSession}>New Session</button> */}
          </div>
        </div>
      </div>
    </div>
  );
}
