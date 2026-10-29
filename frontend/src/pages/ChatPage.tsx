import { ArrowUp, Bot, LoaderCircle, MessageCircle, ShieldCheck, UserRound } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { streamChat, type ChatResult } from "../lib/api";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: ChatResult;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || sending) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
    };
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setDraft("");
    setSending(true);
    setError("");
    try {
      const result = await streamChat(message, (token) => {
        setMessages((current) =>
          current.map((item) =>
            item.id === assistantId
              ? { ...item, content: item.content + token }
              : item,
          ),
        );
        requestAnimationFrame(() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }));
      });
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId
            ? { ...item, content: result.response || item.content, result }
            : item,
        ),
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The chat request failed");
      setMessages((current) => current.filter((item) => item.id !== assistantId));
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="content-page chat-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">PATIENT SUPPORT</p>
          <h1>Care assistant</h1>
          <p className="page-description">Ask about hospital policies or find an appointment.</p>
        </div>
        <div className="secure-badge"><ShieldCheck size={16} /> Private conversation</div>
      </header>
      <section className="chat-card">
        <div className="chat-card-heading">
          <div className="assistant-avatar"><Bot size={20} /></div>
          <div><strong>Doctorly assistant</strong><span>Here to help you navigate your care</span></div>
          <span className="status-dot" title="Available" />
        </div>
        <div className="chat-transcript" ref={scrollRef} aria-live="polite">
          {messages.length === 0 ? (
            <div className="chat-welcome">
              <div className="welcome-icon"><MessageCircle size={25} /></div>
              <h2>How can we help?</h2>
              <p>Ask a question about hospital information or explore available appointments.</p>
              <div className="suggestion-row">
                <span>What are the visiting hours?</span>
                <span>Help me find an appointment</span>
              </div>
            </div>
          ) : messages.map((message) => (
            <div className={`chat-message ${message.role}`} key={message.id}>
              <div className={message.role === "assistant" ? "message-avatar bot" : "message-avatar patient"}>
                {message.role === "assistant" ? <Bot size={16} /> : <UserRound size={16} />}
              </div>
              <div className="message-content">
                <span className="message-author">{message.role === "assistant" ? "Doctorly assistant" : "You"}</span>
                <p>{message.content || (sending && message.role === "assistant" ? <span className="typing"><i /><i /><i /></span> : "")}</p>
              </div>
            </div>
          ))}
          {sending && <div className="streaming-label"><LoaderCircle className="spin" size={14} /> Assistant is responding…</div>}
        </div>
        {error && <div className="alert alert-error chat-error" role="alert">{error}</div>}
        <form className="chat-composer" onSubmit={submit}>
          <input
            aria-label="Message"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Write your message…"
            maxLength={4000}
            disabled={sending}
          />
          <span className="character-count">{draft.length}/4000</span>
          <button className="send-button" type="submit" disabled={!draft.trim() || sending} aria-label="Send message">
            <ArrowUp size={19} />
          </button>
        </form>
        <p className="chat-disclaimer">For emergencies, contact emergency services immediately. This assistant does not provide medical advice.</p>
      </section>
    </section>
  );
}
