"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Send, Loader2, User as UserIcon } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { ChatMessage, ChatSession } from "@/lib/types";
import { Button, Card, Input } from "@/components/ui/primitives";
import { PageHeader } from "@/components/ui/shared";

export default function AssistantPage() {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const content = input.trim();
    if (!content || sending) return;
    setInput("");
    setMessages((m) => [...m, { id: Date.now(), role: "user", content, created_at: new Date().toISOString() }]);
    setSending(true);
    try {
      const session = await apiFetch<ChatSession>("/chat/message", {
        method: "POST",
        body: { content, session_id: sessionId },
      });
      setSessionId(session.id);
      setMessages(session.messages ?? []);
    } catch {
      setMessages((m) => [
        ...m,
        { id: Date.now() + 1, role: "assistant", content: "Sorry, I couldn't reach the assistant service.", created_at: new Date().toISOString() },
      ]);
    } finally {
      setSending(false);
    }
  }

  const suggestions = [
    "Summarize the latest critical findings",
    "How do I exploit Drupalgeddon2 safely?",
    "Draft remediation steps for exposed installers",
  ];

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col">
      <PageHeader title="AI Assistant" description="Ask about findings, exploitation techniques and remediation." />

      <Card className="flex min-h-0 flex-1 flex-col">
        <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <Bot className="h-7 w-7" />
              </div>
              <p className="font-medium">How can I help with your assessment?</p>
              <p className="mt-1 text-sm text-muted-foreground">Grounded by the Pentest RAG when available.</p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => setInput(s)}
                    className="rounded-full border px-3 py-1.5 text-xs hover:bg-accent"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${m.role === "user" ? "bg-secondary" : "bg-primary text-primary-foreground"}`}>
                  {m.role === "user" ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>
                <div className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm ${m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                  {m.content}
                </div>
              </div>
            ))
          )}
          {sending && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <Bot className="h-4 w-4" />
              </div>
              <div className="rounded-2xl bg-muted px-4 py-3"><Loader2 className="h-4 w-4 animate-spin" /></div>
            </div>
          )}
        </div>

        <form onSubmit={send} className="flex items-center gap-2 border-t p-3">
          <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask the assistant…" className="flex-1" />
          <Button type="submit" size="icon" disabled={sending || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </Card>
    </div>
  );
}
