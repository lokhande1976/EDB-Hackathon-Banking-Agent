import { useState, useRef, useEffect, useCallback } from 'react';
import { createSession, streamMessage, generateId } from './api/adkClient';
import './App.css';

function LloydsLogo({ size = 'md' }) {
  return (
    <div className={`lloyds-badge lloyds-badge--${size}`}>
      <div className="lloyds-badge-text">
        <span className="lloyds-badge-title">LLOYDS</span>
        <span className="lloyds-badge-sub">BANKING GROUP</span>
      </div>
    </div>
  );
}

const QUICK_ACTIONS = [
  { icon: '💰', label: 'Savings accounts', query: "Which Lloyds savings account would suit me best?" },
  { icon: '📊', label: 'Spending review', query: 'Can you review my recent spending and suggest ways to save?' },
  { icon: '💚', label: 'Wellbeing check', query: 'Can you give me a full financial wellbeing assessment?' },
  { icon: '🏠', label: 'First home', query: "I'm looking to buy my first home. What Lloyds mortgage options are available?" },
  { icon: '📈', label: 'Investments', query: 'What investment products does Lloyds offer?' },
  { icon: '💳', label: 'Credit cards', query: 'Which Lloyds credit card is best for me?' },
];

const PRODUCT_DB = {
  'Club Lloyds Monthly Saver': { rate: '6.25% AER', access: 'Monthly deposits', fee: 'No fee', color: '#006A4D' },
  'Monthly Saver':             { rate: '5.25% AER', access: 'Monthly deposits', fee: 'No fee', color: '#009660' },
  'Easy Saver':                { rate: '1.40% AER', access: 'Instant access',   fee: 'No fee', color: '#4CAF74' },
  'Cash ISA':                  { rate: '3.20% AER', access: 'Instant access',   fee: 'No fee', color: '#10B981' },
  'Fixed Rate Saver 1 Year':   { rate: '4.65% AER', access: 'Fixed 1 year',     fee: 'No fee', color: '#F59E0B' },
  'Fixed Rate Saver 2 Year':   { rate: '4.60% AER', access: 'Fixed 2 years',    fee: 'No fee', color: '#EF4444' },
  'Club Lloyds Account':       { rate: 'Lifestyle rewards', access: 'Current account', fee: '£3/mo (waivable)', color: '#006A4D' },
  'Classic Account':           { rate: 'Free banking',      access: 'Current account', fee: 'No fee',           color: '#009660' },
  'Silver Account':            { rate: 'Travel insurance',  access: 'Current account', fee: '£9.50/mo',         color: '#7BA3CC' },
  'Gold Account':              { rate: 'Travel + phone',    access: 'Current account', fee: '£12.50/mo',        color: '#F59E0B' },
  'Cashback Credit Card':      { rate: '0.25% cashback',   access: 'Credit card', fee: 'No fee',   color: '#006A4D' },
  'Balance Transfer Card':     { rate: '0% for 20 months', access: 'Credit card', fee: 'No fee',   color: '#4CAF74' },
  'Personal Loan':             { rate: '6.9% APR',         access: 'Loan',        fee: 'No fee',   color: '#009660' },
  'Stocks and Shares ISA':     { rate: 'Tax-free growth',  access: 'Investment',  fee: 'From £40/yr', color: '#10B981' },
  'First Time Buyer Mortgage': { rate: '4.89% fixed',      access: 'Mortgage',    fee: 'No product fee option', color: '#006A4D' },
};

function parseInsights(text) {
  const insights = {};
  const scoreMatch = text.match(/\b(\d{1,3})\/100\b/);
  if (scoreMatch) insights.wellbeingScore = parseInt(scoreMatch[1]);
  const ratingMatch = text.match(/\b(Excellent|Good|Fair|Poor|Strong|Moderate|Developing)\b/i);
  if (ratingMatch) insights.wellbeingRating = ratingMatch[1];
  const products = [];
  for (const [name, data] of Object.entries(PRODUCT_DB)) {
    if (text.includes(name)) products.push({ name, ...data });
  }
  if (products.length) insights.products = products.slice(0, 3);
  return insights;
}

export default function App() {
  const [userId]    = useState(() => `user_${generateId()}`);
  const [sessionId, setSessionId] = useState(null);
  const [messages,  setMessages]  = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [input,     setInput]     = useState('');
  const [insights,  setInsights]  = useState({});
  const [error,     setError]     = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);
  const fullTextRef    = useRef('');

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  const resetSession = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setInsights({});
    setError(null);
    fullTextRef.current = '';
  }, []);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || streaming) return;

    setError(null);
    setStreaming(true);
    setInput('');
    fullTextRef.current = '';

    setMessages((prev) => [...prev, { id: generateId(), role: 'user', content: text }]);

    try {
      let sid = sessionId;
      if (!sid) {
        const session = await createSession(userId);
        sid = session.id;
        setSessionId(sid);
      }

      const botMsgId = generateId();
      let botBuffer = '';
      let botCreated = false;

      for await (const event of streamMessage(userId, sid, text)) {
        const parts = event.content?.parts ?? [];
        for (const part of parts) {
          if (!part.text) continue;
          botBuffer += part.text;
          fullTextRef.current += part.text;
          if (!botCreated) {
            botCreated = true;
            setMessages((prev) => [...prev, { id: botMsgId, role: 'bot', content: botBuffer }]);
          } else {
            setMessages((prev) =>
              prev.map((m) => m.id === botMsgId ? { ...m, content: botBuffer } : m)
            );
          }
        }
      }

      const parsed = parseInsights(fullTextRef.current);
      if (Object.keys(parsed).length) setInsights(parsed);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [...prev, { id: generateId(), role: 'error', content: err.message }]);
    } finally {
      setStreaming(false);
    }
  }, [sessionId, userId, streaming]);

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="app">
      <div className="bg-grid" aria-hidden="true" />
      <div className="bg-glow bg-glow-1" aria-hidden="true" />
      <div className="bg-glow bg-glow-2" aria-hidden="true" />

      {/* ── Header ── */}
      <header className="header">
        <div className="header-brand">
          <LloydsLogo size="sm" />
          <div className="brand-divider" />
          <div className="brand-sub">AI Assistant</div>
        </div>

        <div className="header-right">
          <div className={`status-pill ${streaming ? 'status-busy' : 'status-on'}`}>
            <span className="status-dot" />
            <span>{streaming ? 'Thinking…' : 'Online'}</span>
          </div>
          {hasMessages && (
            <button className="btn-new-chat" onClick={resetSession}>+ New chat</button>
          )}
        </div>
      </header>

      {/* ── Chat area ── */}
      <div className="chat-area">
        {!hasMessages ? (
          <Welcome />
        ) : (
          <div className="chat-scroll">
            <div className="chat-feed">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} msg={msg} />
              ))}

              {/* Inline insights after conversation */}
              {!streaming && Object.keys(insights).length > 0 && (
                <div className="insights-row">
                  {insights.wellbeingScore != null && (
                    <WellbeingGauge score={insights.wellbeingScore} rating={insights.wellbeingRating} />
                  )}
                  {insights.products?.map((p) => (
                    <ProductCard key={p.name} product={p} />
                  ))}
                </div>
              )}

              {streaming && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom bar ── */}
      <div className="bottom-bar">
        {!hasMessages && (
          <div className="quick-chips">
            {QUICK_ACTIONS.map((a) => (
              <button
                key={a.label}
                className="qa-chip"
                onClick={() => sendMessage(a.query)}
                disabled={streaming}
              >
                <span className="qa-icon">{a.icon}</span>
                <span>{a.label}</span>
              </button>
            ))}
          </div>
        )}

        <form className="input-form" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about savings, products, spending or your financial health…"
            disabled={streaming}
            autoFocus
          />
          <button
            type="submit"
            className={`send-btn${streaming ? ' send-btn--busy' : ''}`}
            disabled={streaming || !input.trim()}
            aria-label="Send"
          >
            {streaming ? (
              <span className="spinner" />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </button>
        </form>
        <p className="input-hint">Lloyds Bank AI · Powered by Google Gemini · For guidance only — not financial advice</p>
      </div>
    </div>
  );
}

/* ── Sub-components ─────────────────────────────── */

function Welcome() {
  return (
    <div className="welcome">
      <div className="welcome-logo-wrap">
        <LloydsLogo size="lg" />
      </div>
      <h1 className="welcome-title">Hi, I'm your Lloyds Bank<br />AI assistant</h1>
      <p className="welcome-sub">
        I can help you find the right savings account, review your spending,<br />
        check your financial health, and explore Lloyds products.
      </p>
      <div className="welcome-note">
        <span className="welcome-note-dot" />
        Ready to help · Just type or choose a topic below
      </div>
    </div>
  );
}

function ChatMessage({ msg }) {
  if (msg.role === 'error') {
    return (
      <div className="msg msg--error">
        <div className="msg-bubble msg-bubble--error">⚠ {msg.content}</div>
      </div>
    );
  }
  if (msg.role === 'user') {
    return (
      <div className="msg msg--user">
        <div className="msg-bubble msg-bubble--user">{msg.content}</div>
      </div>
    );
  }
  return (
    <div className="msg msg--bot">
      <div className="bot-avatar-sm">
        <img src="/lloyds-horse.svg" alt="" className="bot-horse-img" />
      </div>
      <div className="bot-body">
        <div className="bot-name">Lloyds</div>
        <div className="msg-bubble msg-bubble--bot">
          <RichText text={msg.content} />
        </div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="msg msg--bot">
      <div className="bot-avatar-sm">
        <img src="/lloyds-horse.svg" alt="" className="bot-horse-img" />
      </div>
      <div className="bot-body">
        <div className="bot-name">Lloyds</div>
        <div className="typing-bubble">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}

function RichText({ text }) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let listItems = [];

  const flushList = () => {
    if (listItems.length) {
      elements.push(<ul key={`ul-${elements.length}`}>{listItems}</ul>);
      listItems = [];
    }
  };

  lines.forEach((line, i) => {
    if (/^\*\*(.*)\*\*$/.test(line)) {
      flushList();
      elements.push(<p key={i} className="rt-heading">{line.replace(/\*\*/g, '')}</p>);
    } else if (line.startsWith('- ') || line.startsWith('• ')) {
      listItems.push(<li key={i}>{inlineMarkdown(line.slice(2))}</li>);
    } else if (/^\d+\./.test(line)) {
      flushList();
      elements.push(<p key={i} className="rt-numbered">{inlineMarkdown(line)}</p>);
    } else if (line.trim() === '') {
      flushList();
      elements.push(<br key={i} />);
    } else {
      flushList();
      elements.push(<p key={i}>{inlineMarkdown(line)}</p>);
    }
  });
  flushList();
  return <div className="rich-text">{elements}</div>;
}

function inlineMarkdown(text) {
  const parts = text.split(/(\*\*.*?\*\*|\[.*?\]\(.*?\))/g);
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) return <strong key={i}>{p.slice(2, -2)}</strong>;
    const link = p.match(/^\[(.*?)\]\((.*?)\)$/);
    if (link) return <a key={i} href={link[2]} target="_blank" rel="noopener noreferrer" className="inline-link">{link[1]}</a>;
    return p;
  });
}

function WellbeingGauge({ score, rating }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = score >= 70 ? '#10B981' : score >= 50 ? '#F59E0B' : '#EF4444';
  return (
    <div className="card-gauge">
      <div className="card-gauge-label">Financial Wellbeing</div>
      <div className="card-gauge-body">
        <svg width="72" height="72" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
          <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${fill} ${circ}`}
            transform="rotate(-90 40 40)"
            style={{ transition: 'stroke-dasharray 1s ease' }} />
        </svg>
        <div className="card-gauge-score" style={{ color }}>
          <span className="card-gauge-num">{score}</span>
          <span className="card-gauge-denom">/100</span>
        </div>
      </div>
      {rating && <div className="card-gauge-rating" style={{ color }}>{rating}</div>}
    </div>
  );
}

function ProductCard({ product }) {
  return (
    <div className="card-product" style={{ '--pc': product.color }}>
      <div className="card-product-name">{product.name}</div>
      <div className="card-product-rate">{product.rate}</div>
      <div className="card-product-tags">
        <span className="ptag">{product.access}</span>
        <span className="ptag ptag--green">{product.fee}</span>
      </div>
    </div>
  );
}
