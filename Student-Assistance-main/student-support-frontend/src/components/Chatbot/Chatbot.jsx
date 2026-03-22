import React, { useState, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";
import "./chatbot.css";
import Sidebar from "../Layout/Sidebar";
import {
  getApiErrorMessage,
  getGeneratedFaqs,
  sendMessage,
  sendVoiceMessage,
} from "../../services/api";

const CHAT_SESSIONS_KEY = "chatSessions";
const ACTIVE_CHAT_KEY = "activeChatId";

const makeSession = (title = "New Chat") => ({
  id: `chat_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
  title,
  messages: [],
  updatedAt: Date.now(),
});

function Chatbot() {
  const navigate = useNavigate();

  const [message, setMessage] = useState("");
  const [typing, setTyping] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [faqEnabled, setFaqEnabled] = useState(false);
  const [faqAnimating, setFaqAnimating] = useState(false);
  const [moduleLoading, setModuleLoading] = useState(false);
  const [moduleResult, setModuleResult] = useState(null);
  const [chatSessions, setChatSessions] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [faqSuggestions, setFaqSuggestions] = useState([]);
  const [faqLoading, setFaqLoading] = useState(false);
  const [faqError, setFaqError] = useState("");
  const [voiceLanguage, setVoiceLanguage] = useState("en");

  const chatEndRef = useRef(null);

  const { transcript, listening, resetTranscript, browserSupportsSpeechRecognition } = useSpeechRecognition();
  const fallbackSuggestions = ["hostel facilities", "college timings", "library timings", "exam rules"];
  const voiceLanguageOptions = [
    { code: "en", label: "English", locale: "en-US" },
    { code: "hi", label: "Hindi", locale: "hi-IN" },
    { code: "te", label: "Telugu", locale: "te-IN" },
    { code: "ta", label: "Tamil", locale: "ta-IN" },
    { code: "kn", label: "Kannada", locale: "kn-IN" },
  ];

  const activeSession = useMemo(
    () => chatSessions.find((s) => s.id === activeChatId) || null,
    [chatSessions, activeChatId]
  );
  const messages = useMemo(() => activeSession?.messages || [], [activeSession]);

  useEffect(() => {
    try {
      const savedSessions = JSON.parse(localStorage.getItem(CHAT_SESSIONS_KEY) || "[]");
      const savedActiveId = localStorage.getItem(ACTIVE_CHAT_KEY);
      const oldSingleChat = JSON.parse(localStorage.getItem("chatHistory") || "[]");

      let sessions = Array.isArray(savedSessions) ? savedSessions : [];
      if (sessions.length === 0 && Array.isArray(oldSingleChat) && oldSingleChat.length > 0) {
        sessions = [{ ...makeSession("Previous Chat"), messages: oldSingleChat }];
      }

      setChatSessions(sessions);
      if (sessions.length > 0) {
        const hasSavedActive = sessions.some((s) => s.id === savedActiveId);
        setActiveChatId(hasSavedActive ? savedActiveId : sessions[0].id);
      }
    } catch {
      setChatSessions([]);
      setActiveChatId(null);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(CHAT_SESSIONS_KEY, JSON.stringify(chatSessions));
    if (activeChatId) {
      localStorage.setItem(ACTIVE_CHAT_KEY, activeChatId);
    } else {
      localStorage.removeItem(ACTIVE_CHAT_KEY);
    }
  }, [chatSessions, activeChatId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  useEffect(() => {
    if (!listening && transcript && faqEnabled) {
      setMessage(transcript);
      handleVoiceSend(transcript);
      resetTranscript();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listening, transcript, faqEnabled]);

  useEffect(() => {
    if (!faqEnabled) return;
    if (faqSuggestions.length > 0) return;
    loadGeneratedFaqs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [faqEnabled]);

  const upsertSession = (sessionId, updater) => {
    setChatSessions((prev) =>
      prev.map((session) => {
        if (session.id !== sessionId) return session;
        return updater(session);
      })
    );
  };

  const appendMessageToSession = (sessionId, msg) => {
    upsertSession(sessionId, (session) => {
      const nextMessages = [...(session.messages || []), msg];
      const nextTitle =
        session.title === "New Chat" && msg.sender === "user"
          ? (msg.text || "New Chat").slice(0, 40)
          : session.title;
      return {
        ...session,
        title: nextTitle || "New Chat",
        messages: nextMessages,
        updatedAt: Date.now(),
      };
    });
  };

  const ensureActiveSession = () => {
    if (activeChatId) return activeChatId;
    const created = makeSession();
    setChatSessions((prev) => [created, ...prev]);
    setActiveChatId(created.id);
    return created.id;
  };

  const startListening = () => {
    window.speechSynthesis.cancel();
    if (!faqEnabled) return;

    if (!browserSupportsSpeechRecognition) {
      alert("Speech recognition not supported in this browser");
      return;
    }

    setVoiceMode(true);
    const selectedLocale =
      voiceLanguageOptions.find((opt) => opt.code === voiceLanguage)?.locale || "en-US";
    SpeechRecognition.startListening({ continuous: false, language: selectedLocale });
  };

  const speak = (text) => {
    if (!("speechSynthesis" in window)) return;
    const speech = new SpeechSynthesisUtterance(text);
    speech.lang = voiceLanguageOptions.find((opt) => opt.code === voiceLanguage)?.locale || "en-US";
    speech.rate = 0.95;
    speech.pitch = 1.1;
    window.speechSynthesis.speak(speech);
  };

  const loadGeneratedFaqs = async () => {
    try {
      setFaqLoading(true);
      setFaqError("");
      const res = await getGeneratedFaqs(8);
      const rows = res.data?.items || [];
      setFaqSuggestions(rows);
    } catch {
      setFaqError("Could not load generated FAQs. Showing starter prompts.");
      setFaqSuggestions([]);
    } finally {
      setFaqLoading(false);
    }
  };

  const handleSend = async (text = message) => {
    if (!faqEnabled) return;
    if (text.trim() === "") return;

    window.speechSynthesis.cancel();

    const sessionId = ensureActiveSession();
    const userMessage = {
      text,
      sender: "user",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    appendMessageToSession(sessionId, userMessage);
    setTyping(true);
    setMessage("");

    try {
      const storedUser = JSON.parse(localStorage.getItem("loggedInUser") || "null");
      const userIdentifier = storedUser?.email || storedUser?.registration_number || "guest";
      const res = await sendMessage(text, userIdentifier);

      const botMessage = {
        text: res.data.response,
        sender: "bot",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      appendMessageToSession(sessionId, botMessage);

      if (voiceMode) {
        speak(res.data.response);
        setVoiceMode(false);
      }
    } catch (error) {
      appendMessageToSession(sessionId, {
        text: getApiErrorMessage(error, "Server error. Please try again."),
        sender: "bot",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      });
    }

    setTyping(false);
  };

  const handleVoiceSend = async (text) => {
    if (!faqEnabled) return;
    if (!text || text.trim() === "") return;

    window.speechSynthesis.cancel();

    const sessionId = ensureActiveSession();
    const userMessage = {
      text,
      sender: "user",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    appendMessageToSession(sessionId, userMessage);
    setTyping(true);
    setMessage("");

    try {
      const storedUser = JSON.parse(localStorage.getItem("loggedInUser") || "null");
      const userIdentifier = storedUser?.email || storedUser?.registration_number || "voice_user";
      const res = await sendVoiceMessage(text, userIdentifier);
      const responseText = res.data?.response || "I could not process that voice input.";
      const ttsText = res.data?.voice?.tts_text || responseText;

      appendMessageToSession(sessionId, {
        text: responseText,
        sender: "bot",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      });

      speak(ttsText);
    } catch (error) {
      appendMessageToSession(sessionId, {
        text: getApiErrorMessage(error, "Voice processing failed. Please type your question once."),
        sender: "bot",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      });
    }

    setTyping(false);
    setVoiceMode(false);
  };

  const handleNewChat = () => {
    const created = makeSession();
    setChatSessions((prev) => [created, ...prev]);
    setActiveChatId(created.id);
    if (!faqEnabled) {
      setFaqAnimating(true);
      setFaqEnabled(true);
      window.setTimeout(() => setFaqAnimating(false), 480);
    }
  };

  const handleSelectChat = (chatId) => {
    setActiveChatId(chatId);
  };

  const handleDeleteChat = (chatId) => {
    setChatSessions((prev) => {
      const next = prev.filter((s) => s.id !== chatId);
      if (activeChatId === chatId) {
        setActiveChatId(next[0]?.id || null);
      }
      return next;
    });
  };

  const toggleFaqAssistant = () => {
    setFaqAnimating(true);
    setFaqEnabled((prev) => !prev);
    window.setTimeout(() => setFaqAnimating(false), 480);
  };

  const handleFunctionalModuleClick = () => {
    if (faqEnabled) {
      setFaqAnimating(true);
      setFaqEnabled(false);
      window.setTimeout(() => setFaqAnimating(false), 480);
    }
  };

  return (
    <div className="chat-layout">
      <Sidebar
        newChat={handleNewChat}
        onClose={() => navigate("/")}
        onFunctionalModuleClick={handleFunctionalModuleClick}
        onModuleResult={setModuleResult}
        onModuleLoading={setModuleLoading}
        faqEnabled={faqEnabled}
        chatSessions={chatSessions}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
      />

      <div className={`chat-container ${faqAnimating ? "assistant-animating" : ""}`}>
        <div className="chat-header">
          <div className="chat-title">Student Assistant</div>
        </div>

        <div className="chat-body">
          {!faqEnabled && (
            <section className="functional-workspace">
              <div className="functional-head">
                <h2>Functional Module Response</h2>
                <p>Structured, professional answers are shown here.</p>
              </div>

              {moduleLoading && <p className="workspace-note">Loading module data...</p>}

              {!moduleLoading && !moduleResult && (
                <div className="functional-card">
                  <h3>Ready</h3>
                  <p>Select any functional module item from the left sidebar.</p>
                </div>
              )}

              {!moduleLoading && moduleResult && (
                <div className="functional-card">
                  <h3>{moduleResult.title}</h3>
                  {moduleResult.lines.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              )}
            </section>
          )}

          {faqEnabled && messages.length === 0 && (
            <>
              <h2>FAQ Assistant</h2>
              <p>Ask by text or voice. FAQs are generated from your AI knowledge base.</p>
              {faqLoading && <p className="workspace-note">Loading AI-generated FAQs...</p>}
              {!!faqError && <p className="workspace-note">{faqError}</p>}
              <div className="suggestions">
                {(faqSuggestions.length > 0
                  ? faqSuggestions.map((item) => ({
                      key: `${item.question}_${item.source || "faq"}`,
                      question: item.question,
                      meta: item.category || item.source || "generated",
                    }))
                  : fallbackSuggestions.map((item) => ({
                      key: item,
                      question: item,
                      meta: "starter",
                    }))
                ).map((item) => (
                  <div key={item.key} className="suggestion-card" onClick={() => handleSend(item.question)}>
                    <div className="suggestion-question">{item.question}</div>
                    <div className="suggestion-meta">{item.meta}</div>
                  </div>
                ))}
              </div>
              <button className="faq-refresh" onClick={loadGeneratedFaqs} type="button" disabled={faqLoading}>
                {faqLoading ? "Refreshing..." : "Refresh FAQs"}
              </button>
            </>
          )}

          {faqEnabled &&
            messages.map((msg, index) => (
              <div key={`${msg.time}_${index}`} className={`chat-message ${msg.sender}`}>
                <div className="message-text" dangerouslySetInnerHTML={{ __html: msg.text }}></div>
                <div className="message-time">{msg.time}</div>
              </div>
            ))}

          {faqEnabled && typing && (
            <div className="chat-message bot typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
          )}

          <div ref={chatEndRef}></div>
        </div>

        {faqEnabled && (
          <div className="chat-input">
            <select
              className="voice-lang"
              value={voiceLanguage}
              onChange={(e) => setVoiceLanguage(e.target.value)}
              aria-label="Voice language"
            >
              {voiceLanguageOptions.map((opt) => (
                <option key={opt.code} value={opt.code}>
                  {opt.label}
                </option>
              ))}
            </select>

            <button className={`mic ${listening ? "listening" : ""}`} onClick={startListening}>
              {listening ? "Listening..." : "Voice"}
            </button>

            <input
              type="text"
              placeholder="Ask FAQ..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
            />

            <button className="send" onClick={() => handleSend()}>
              Send
            </button>
          </div>
        )}

        <button
          className={`faq-toggle ${faqEnabled ? "active" : ""}`}
          onClick={toggleFaqAssistant}
          type="button"
          style={{ position: "fixed", top: "18px", right: "22px", bottom: "auto", left: "auto" }}
        >
          <span className="assistant-dot" aria-hidden="true">
            <span className="assistant-glyph">*</span>
          </span>
          <span className="assistant-label">Student Assistance</span>
        </button>
      </div>
    </div>
  );
}

export default Chatbot;
