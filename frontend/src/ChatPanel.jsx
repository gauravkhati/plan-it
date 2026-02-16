import { useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function ChatPanel({ messages, onSend, isLoading, onAutoMessage }) {
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const val = inputRef.current.value.trim();
    if (!val || isLoading) return;
    onSend(val);
    inputRef.current.value = '';
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <Bot size={20} />
        <span>Chat with Plan-It</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-icon">📋</div>
            <h3>Welcome to Plan-It!</h3>
            <p>Describe what you'd like to plan, and I'll help you create a structured plan step by step.</p>
            <div className="chat-suggestions">
              {[
                'Plan a product launch',
                'Help me organize a wedding',
                'Create a study schedule',
                'Plan a software project',
              ].map((s) => (
                <button key={s} className="suggestion-chip" onClick={() => onSend(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            <div className="bubble-avatar">
              {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className="bubble-content">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="chat-bubble assistant">
            <div className="bubble-avatar">
              <Bot size={16} />
            </div>
            <div className="bubble-content typing">
              <Loader2 size={16} className="spin" />
              <span>Thinking…</span>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          placeholder="Describe your plan or ask a question…"
          disabled={isLoading}
          autoFocus
        />
        <button type="submit" disabled={isLoading} className="send-btn">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
