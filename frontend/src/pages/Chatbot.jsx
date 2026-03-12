import { useState, useRef, useEffect } from 'react'
import { FiSend, FiSquare, FiMessageCircle, FiUser, FiTrendingUp, FiAlertCircle } from 'react-icons/fi'
import { streamChatMessage } from '../services/chatService'
import './Chatbot.css'

/**
 * Render a message string that may contain **bold** markdown.
 * Splits on **...** patterns and returns an array of React nodes.
 */
function renderMarkdown(text) {
  if (!text) return null
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}

const WELCOME_MESSAGE = {
  id: 1,
  type: 'bot',
  content:
    "Hello! I'm MarketMind AI, your intelligent Indian stock market assistant. " +
    "I can help you with:\n\n" +
    "**• Stock Analysis** — Ask about any NSE/BSE listed stock\n" +
    "**• Stock Comparison** — Compare two stocks side by side\n" +
    "**• Portfolio Analysis** — Share your holdings for a full review\n" +
    "**• Investment Suggestions** — Get advice based on your age, goals, or budget\n" +
    "**• Finance Concepts** — PE ratio, book value, dividends, and more\n\n" +
    "How can I help you today?",
}

const Chatbot = () => {
  // Load messages from localStorage on mount, or use welcome message
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem('marketmind_chat_history')
      if (saved) {
        const parsed = JSON.parse(saved)
        return Array.isArray(parsed) && parsed.length > 0 ? parsed : [WELCOME_MESSAGE]
      }
    } catch (err) {
      console.error('Failed to load chat history:', err)
    }
    return [WELCOME_MESSAGE]
  })
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef(null)
  const abortControllerRef = useRef(null)
  const textareaRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Save messages to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('marketmind_chat_history', JSON.stringify(messages))
    } catch (err) {
      console.error('Failed to save chat history:', err)
    }
  }, [messages])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 120) + 'px'
    }
  }, [inputValue])

  // Cleanup on unmount — abort any active stream when navigating away
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  // Warn user before leaving page while streaming
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (isStreaming) {
        e.preventDefault()
        e.returnValue = 'Response is still generating. Are you sure you want to leave?'
        return e.returnValue
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isStreaming])

  const suggestedQuestions = [
    'What is PE ratio?',
    'Compare TCS and Infosys',
    'Analyze Reliance stock',
    'I have ₹10,000 to invest, I am 25 years old',
  ]

  const stopStreaming = () => {
    abortControllerRef.current?.abort()
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    const text = inputValue.trim()
    if (!text) return

    const userMsg = { id: Date.now(), type: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInputValue('')
    setIsTyping(true)
    setIsStreaming(true)

    const controller = new AbortController()
    abortControllerRef.current = controller
    const botMsgId = Date.now() + 1

    // Build conversation history (exclude welcome message, keep last 10 exchanges)
    const history = messages
      .filter(m => m.id !== WELCOME_MESSAGE.id && !m.isError)
      .slice(-10)
      .map(m => ({
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.content || ''
      }))

    await streamChatMessage(
      text,
      history,
      // onToken — append each new token to the bot message
      (token) => {
        setMessages(prev => {
          const existing = prev.find(m => m.id === botMsgId)
          if (existing) {
            return prev.map(m =>
              m.id === botMsgId ? { ...m, content: m.content + token } : m
            )
          }
          // First token: create the bot message and stop the typing indicator
          setIsTyping(false)
          return [...prev, { id: botMsgId, type: 'bot', content: token }]
        })
      },
      // onMeta — store intent badge once we know it
      (meta) => {
        setMessages(prev => {
          const existing = prev.find(m => m.id === botMsgId)
          if (existing) {
            return prev.map(m =>
              m.id === botMsgId ? { ...m, intent: meta.intent } : m
            )
          }
          return prev
        })
      },
      // onDone
      () => {
        setIsTyping(false)
        setIsStreaming(false)
      },
      // onError
      (err) => {
        setIsTyping(false)
        setIsStreaming(false)
        const errText =
          err.message.includes('Ollama') || err.message.includes('AI service')
            ? err.message
            : 'Something went wrong. Please try again.'
        setMessages(prev => {
          const existing = prev.find(m => m.id === botMsgId)
          if (existing) {
            return prev.map(m =>
              m.id === botMsgId ? { ...m, isError: true, content: errText } : m
            )
          }
          return [...prev, { id: botMsgId, type: 'bot', isError: true, content: errText }]
        })
      },
      controller.signal,
    )
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isStreaming && inputValue.trim()) {
        handleSendMessage(e)
      }
    }
  }

  const handleSuggestedQuestion = (question) => {
    setInputValue(question)
  }

  const clearChat = () => {
    if (window.confirm('Clear all chat history? This cannot be undone.')) {
      setMessages([WELCOME_MESSAGE])
      localStorage.removeItem('marketmind_chat_history')
    }
  }

  return (
    <div className="chatbot-page">
      <div className="chatbot-header">
        <div className="chatbot-title">
          <FiMessageCircle className="bot-icon" />
          <div>
            <h1>AI Investment Assistant</h1>
          </div>
        </div>
        <button 
          onClick={clearChat} 
          className="clear-chat-btn"
          disabled={isStreaming || messages.length <= 1}
          title="Clear chat history"
        >
          Clear Chat
        </button>
      </div>

      <div className="chatbot-container">
        <div className="messages-container">
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              <div className="message-avatar">
                {message.type === 'bot' ? (
                  message.isError ? <FiAlertCircle /> : <FiTrendingUp />
                ) : (
                  <FiUser />
                )}
              </div>
              <div className={`message-content${message.isError ? ' message-error' : ''}`}>
                <p style={{ whiteSpace: 'pre-line' }}>{renderMarkdown(message.content)}</p>
                {message.intent && message.intent !== 'general' && message.intent !== 'error' && (
                  <span className="intent-badge">{message.intent.replace('_', ' ')}</span>
                )}
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="message bot">
              <div className="message-avatar">
                <FiTrendingUp />
              </div>
              <div className="message-content typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="suggested-questions">
          {suggestedQuestions.map((question, index) => (
            <button
              key={index}
              className="suggestion-chip"
              onClick={() => handleSuggestedQuestion(question)}
              disabled={isTyping}
            >
              {question}
            </button>
          ))}
        </div>

        <form className="chat-input-form" onSubmit={handleSendMessage}>
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder="Ask about stocks, compare companies... (Shift+Enter for new line)"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
          />
          {isStreaming ? (
            <button type="button" className="stop-btn" onClick={stopStreaming} title="Stop response">
              <FiSquare />
            </button>
          ) : (
            <button type="submit" disabled={!inputValue.trim()}>
              <FiSend />
            </button>
          )}
        </form>
      </div>
    </div>
  )
}

export default Chatbot
