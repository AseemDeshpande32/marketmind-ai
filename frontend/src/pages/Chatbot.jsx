import { useState, useRef, useEffect } from 'react'
import { FiSend, FiMessageCircle, FiUser, FiTrendingUp } from 'react-icons/fi'
import './Chatbot.css'

const Chatbot = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: "Hello! I'm MarketMind AI, your intelligent investment assistant. How can I help you today? You can ask me about stocks, market trends, investment strategies, or financial concepts."
    }
  ])
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
    "What is P/E ratio?",
    "Analyze AAPL stock",
    "Best investment strategies for beginners",
    "How does inflation affect stocks?"
  ]

  const getBotResponse = (userMessage) => {
    // Mock responses - replace with actual AI integration
    const lowerMessage = userMessage.toLowerCase()
    
    if (lowerMessage.includes('p/e') || lowerMessage.includes('pe ratio')) {
      return "The P/E (Price-to-Earnings) ratio is a valuation metric that compares a company's stock price to its earnings per share. A higher P/E suggests investors expect higher growth, while a lower P/E might indicate an undervalued stock or lower growth expectations. The average P/E for S&P 500 companies is around 20-25."
    }
    
    if (lowerMessage.includes('aapl') || lowerMessage.includes('apple')) {
      return "Apple Inc. (AAPL) is currently trading at $178.52, up 1.39% today. Key highlights:\n\n• Market Cap: $2.78T\n• P/E Ratio: 28.45\n• Dividend Yield: 0.54%\n\nApple continues to show strong performance in its services segment, with growing revenue from App Store, iCloud, and Apple Music. The company's focus on AI integration in upcoming products could be a significant growth driver."
    }
    
    if (lowerMessage.includes('beginner') || lowerMessage.includes('start investing')) {
      return "Great question! Here are some investment strategies for beginners:\n\n1. **Start with Index Funds**: Low-cost ETFs like VOO or VTI provide instant diversification.\n\n2. **Dollar-Cost Averaging**: Invest fixed amounts regularly to reduce timing risk.\n\n3. **Emergency Fund First**: Have 3-6 months of expenses saved before investing.\n\n4. **Diversify**: Spread investments across different sectors and asset classes.\n\n5. **Think Long-Term**: Focus on your investment horizon, not daily fluctuations.\n\nWould you like me to explain any of these in more detail?"
    }
    
    if (lowerMessage.includes('inflation')) {
      return "Inflation affects stocks in several ways:\n\n**Negative Effects:**\n• Reduces purchasing power and consumer spending\n• Can lead to higher interest rates\n• Increases operating costs for companies\n\n**Positive Effects:**\n• Companies can raise prices, potentially increasing revenue\n• Hard assets and commodities often perform well\n• Real estate stocks may benefit\n\n**Inflation-Resistant Sectors:**\n• Energy, utilities, and consumer staples often outperform during high inflation periods."
    }
    
    return "That's an interesting question! While I don't have real-time data access in this demo, in a production environment, I would analyze market data, news sentiment, and financial metrics to provide you with detailed insights. Is there something specific about the stock market or investing I can help explain?"
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!inputValue.trim()) return

    const userMessage = {
      id: messages.length + 1,
      type: 'user',
      content: inputValue
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsTyping(true)

    // Simulate AI response delay
    setTimeout(() => {
      const botResponse = {
        id: messages.length + 2,
        type: 'bot',
        content: getBotResponse(inputValue)
      }
      setMessages(prev => [...prev, botResponse])
      setIsTyping(false)
    }, 1000 + Math.random() * 1000)
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
            <p>Ask me anything about stocks, markets, and investing</p>
          </div>
        </div>
      </div>

      <div className="chatbot-container">
        <div className="messages-container">
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              <div className="message-avatar">
                {message.type === 'bot' ? <FiTrendingUp /> : <FiUser />}
              </div>
              <div className="message-content">
                <p style={{ whiteSpace: 'pre-line' }}>{message.content}</p>
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
            >
              {question}
            </button>
          ))}
        </div>

        <form className="chat-input-form" onSubmit={handleSendMessage}>
          <input
            type="text"
            placeholder="Ask about stocks, markets, or investment strategies..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
          />
          <button type="submit" disabled={!inputValue.trim()}>
            <FiSend />
          </button>
        </form>
      </div>
    </div>
  )
}

export default Chatbot
