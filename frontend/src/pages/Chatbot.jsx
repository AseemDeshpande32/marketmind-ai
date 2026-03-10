import { useState, useRef, useEffect } from 'react'
import { FiSend, FiMessageCircle, FiUser, FiTrendingUp, FiAlertCircle } from 'react-icons/fi'
import { sendChatMessage } from '../services/chatService'
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
    "Hello! I'm MarketMind AI, your intelligent Indian stock market assistant powered by Gemma. " +
    "I can help you with:\n\n" +
    "**• Stock Analysis** — Ask about any NSE/BSE listed stock\n" +
    "**• Stock Comparison** — Compare two stocks side by side\n" +
    "**• Portfolio Analysis** — Share your holdings for a full review\n" +
    "**• Finance Concepts** — PE ratio, book value, dividends, and more\n\n" +
    "How can I help you today?",
}

const Chatbot = () => {
  const [messages, setMessages] = useState([WELCOME_MESSAGE])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const suggestedQuestions = [
    'What is PE ratio?',
    'Compare TCS and Infosys',
    'Analyze Reliance stock',
    'My portfolio: TCS 5, Infosys 10, Wipro 8',
  ]

  const handleSendMessage = async (e) => {
    e.preventDefault()
    const text = inputValue.trim()
    if (!text) return

    const userMsg = { id: Date.now(), type: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInputValue('')
    setIsTyping(true)

    try {
      const result = await sendChatMessage(text)
      const botMsg = {
        id: Date.now() + 1,
        type: 'bot',
        content: result.response || 'No response received.',
        intent: result.intent,
      }
      setMessages(prev => [...prev, botMsg])
    } catch (err) {
      const errMsg = {
        id: Date.now() + 1,
        type: 'bot',
        isError: true,
        content:
          err.message.includes('Ollama') || err.message.includes('AI service')
            ? err.message
            : 'Something went wrong. Please try again.',
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setIsTyping(false)
    }
  }

  const handleSuggestedQuestion = (question) => {
    setInputValue(question)
  }

  return (
    <div className="chatbot-page">
      <div className="chatbot-header">
        <div className="chatbot-title">
          <FiMessageCircle className="bot-icon" />
          <div>
            <h1>AI Investment Assistant</h1>
            <p>Powered by Gemma · Live NSE/BSE data · FinBERT sentiment</p>
          </div>
        </div>
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
          <input
            type="text"
            placeholder="Ask about stocks, compare companies, or review your portfolio..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={isTyping}
          />
          <button type="submit" disabled={!inputValue.trim() || isTyping}>
            <FiSend />
          </button>
        </form>
      </div>
    </div>
  )
}

export default Chatbot
