import React, { useState, useEffect } from 'react'
import axios from 'axios'

// API base URL
const API_BASE = 'http://localhost:8000'

// Chat Interface Component
const ChatInterface = ({ responseId, originalResponse }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = { role: 'user', content: inputMessage };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/thread/chat`, {
        message: inputMessage,
        response_id: responseId,
        conversation_history: messages,
        model: 'gpt-4o-mini'
      });

      const assistantMessage = { role: 'assistant', content: response.data.message };
      setMessages(prev => [...prev, assistantMessage]);
      
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="border-t border-gray-200 mt-4">
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full py-3 px-4 text-left text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 flex items-center justify-between"
      >
        <span className="flex items-center">
          💬 Ask follow-up questions about this response
        </span>
        <svg
          className={`w-4 h-4 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Chat Interface */}
      {isOpen && (
        <div className="p-4 bg-gray-50 border-t border-gray-200">
          {/* Messages */}
          <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
            {messages.length === 0 && (
              <p className="text-sm text-gray-500 italic">
                Start a conversation about this legal analysis...
              </p>
            )}
            
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-3 py-2 rounded-lg text-sm ${
                    msg.role === 'user'
                      ? 'bg-primary-600 text-white'
                      : 'bg-white text-gray-800 border border-gray-200'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white text-gray-800 border border-gray-200 px-3 py-2 rounded-lg text-sm">
                  <div className="flex items-center space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex space-x-2">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a follow-up question..."
              className="flex-1 p-2 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows="2"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={!inputMessage.trim() || isLoading}
              className={`px-4 py-2 rounded-lg font-medium ${
                inputMessage.trim() && !isLoading
                  ? 'bg-primary-600 hover:bg-primary-700 text-white'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

function App() {
  // State management
  const [surveys, setSurveys] = useState([])
  const [countries, setCountries] = useState([])
  const [models, setModels] = useState([])
  const [selectedSurvey, setSelectedSurvey] = useState('')
  const [selectedCountries, setSelectedCountries] = useState([])
  const [selectedCountry, setSelectedCountry] = useState('')
  const [selectedModel, setSelectedModel] = useState('gpt-5')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [analysisMode, setAnalysisMode] = useState('question') // 'question' or 'survey'

  // Load surveys, countries, and models on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [surveysRes, countriesRes, modelsRes] = await Promise.all([
          axios.get(`${API_BASE}/surveys`),
          axios.get(`${API_BASE}/countries`),
          axios.get(`${API_BASE}/models`)
        ])
        setSurveys(surveysRes.data)
        setCountries(countriesRes.data)
        setModels(modelsRes.data)
      } catch (err) {
        setError('Failed to load data. Make sure the backend is running.')
      }
    }
    loadData()
  }, [])

  // Handle analysis (both modes)
  const handleAnalyze = async () => {
    // Validation based on mode
    if (analysisMode === 'question') {
      if (!selectedSurvey || selectedCountries.length === 0) {
        setError('Please select a survey and at least one country.')
        return
      }
    } else {
      if (!selectedCountry) {
        setError('Please select a country for entire survey analysis.')
        return
      }
    }

    setLoading(true)
    setError('')
    setResults([])

    try {
      let response
      if (analysisMode === 'question') {
        // Original mode: one question across multiple countries
        response = await axios.post(`${API_BASE}/analyze`, {
          survey_id: selectedSurvey,
          countries: selectedCountries,
          model: selectedModel
        })
      } else {
        // New mode: all questions for one country
        response = await axios.post(`${API_BASE}/analyze-entire-survey`, {
          country: selectedCountry,
          model: selectedModel
        })
      }
      setResults(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Handle country selection
  const handleCountryToggle = (countryCode) => {
    setSelectedCountries(prev => 
      prev.includes(countryCode)
        ? prev.filter(c => c !== countryCode)
        : [...prev, countryCode]
    )
  }

  // Get selected survey details
  const selectedSurveyData = surveys.find(s => s.id === selectedSurvey)

  const canAnalyze = analysisMode === 'question' ? (selectedSurvey && selectedCountries.length > 0) : selectedCountry;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Legal AI Agent</h1>
          <p className="text-gray-600 mt-1">Analyze legal questions across different countries</p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Panel - All Controls in Single Card */}
          <div className="lg:col-span-1">
            <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 space-y-6">
              {/* Analysis Mode Toggle */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Analysis Mode</h2>
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="question"
                      checked={analysisMode === 'question'}
                      onChange={(e) => setAnalysisMode(e.target.value)}
                      className="text-primary-600 focus:ring-primary-500"
                    />
                    <span className="ml-2 text-gray-700 text-sm">Single Question → Multiple Countries</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      value="survey"
                      checked={analysisMode === 'survey'}
                      onChange={(e) => setAnalysisMode(e.target.value)}
                      className="text-primary-600 focus:ring-primary-500"
                    />
                    <span className="ml-2 text-gray-700 text-sm">Entire Survey → Single Country</span>
                  </label>
                </div>
              </div>

              {/* Divider */}
              <div className="border-t border-gray-200"></div>

              {/* Model Selection */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Select AI Model</h2>
                <select 
                  value={selectedModel} 
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  {models.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider}) - {model.cost} Cost
                    </option>
                  ))}
                </select>
                
                {selectedModel && models.find(m => m.id === selectedModel) && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-700">
                      <strong>Description:</strong> {models.find(m => m.id === selectedModel)?.description}
                    </p>
                  </div>
                )}
              </div>

              {/* Divider */}
              <div className="border-t border-gray-200"></div>

              {/* Survey Selection - Only show in question mode */}
              {analysisMode === 'question' && (
                <>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Survey Question</h2>
                    <select 
                      value={selectedSurvey} 
                      onChange={(e) => setSelectedSurvey(e.target.value)}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="">Choose a survey...</option>
                      {surveys.map(survey => (
                        <option key={survey.id} value={survey.id}>
                          {survey.question}
                        </option>
                      ))}
                    </select>
                    
                    {selectedSurvey && surveys.find(s => s.id === selectedSurvey) && (
                      <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                        <p className="text-sm text-gray-700">
                          <strong>Question:</strong> {surveys.find(s => s.id === selectedSurvey)?.question}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Divider */}
                  <div className="border-t border-gray-200"></div>
                </>
              )}

              {/* Country Selection */}
              <div>
                {analysisMode === 'question' ? (
                  <>
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Countries</h2>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {countries.map(country => (
                        <label key={country.code} className="flex items-center">
                          <input
                            type="checkbox"
                            checked={selectedCountries.includes(country.code)}
                            onChange={() => handleCountryToggle(country.code)}
                            className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="ml-3 text-gray-700">{country.name}</span>
                        </label>
                      ))}
                    </div>
                    
                    {selectedCountries.length > 0 && (
                      <div className="mt-4 p-3 bg-primary-50 rounded-lg">
                        <p className="text-sm text-primary-800">
                          {selectedCountries.length} countries selected
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Select Country</h2>
                    <select 
                      value={selectedCountry} 
                      onChange={(e) => setSelectedCountry(e.target.value)}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="">Choose a country...</option>
                      {countries.map(country => (
                        <option key={country.code} value={country.code}>
                          {country.name}
                        </option>
                      ))}
                    </select>
                    
                    {selectedCountry && (
                      <div className="mt-4 p-3 bg-primary-50 rounded-lg">
                        <p className="text-sm text-primary-800">
                          Will analyze all survey questions for {selectedCountry}
                        </p>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Divider */}
              <div className="border-t border-gray-200"></div>

              {/* Analyze Button */}
              <button
                onClick={handleAnalyze}
                disabled={loading || !canAnalyze}
                className={`w-full py-3 px-6 rounded-lg font-medium ${
                  canAnalyze && !loading
                    ? 'bg-primary-600 hover:bg-primary-700 text-white'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                {loading ? 'Analyzing...' : 'Start Analysis'}
              </button>
            </div>
          </div>

          {/* Right Panel - Results (NOW STARTS FROM TOP) */}
          <div className="lg:col-span-2">
            {loading && (
              <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200 text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">
                  {analysisMode === 'question' ? 'Analyzing legal question...' : 'Analyzing entire survey...'}
                </p>
              </div>
            )}

            {results.length > 0 && (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-semibold text-gray-900">Analysis Results</h2>
                  <span className="text-sm text-gray-500">
                    {results.length} result{results.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {results.map((result, index) => (
                  <div key={index} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {analysisMode === 'question' ? result.country : result.survey_id}
                        </h3>
                        {analysisMode === 'survey' && result.question && (
                          <p className="text-sm text-gray-600 mt-1">{result.question}</p>
                        )}
                      </div>
                      
                      {/* Badges container */}
                      <div className="flex gap-2">
                        {/* Cache indicator badge */}
                        {result.is_cached && (
                          <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                            🎯 Cached
                          </span>
                        )}
                        
                        {/* Confidence badge */}
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                          result.confidence_level === 'High' ? 'bg-green-100 text-green-800' :
                          result.confidence_level === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {result.confidence_level} Confidence
                        </span>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Answer</h4>
                        <p className="text-gray-700">{result.answer}</p>
                      </div>

                      <div>
                        <h4 className="font-medium text-gray-900 mb-2">Legal Basis</h4>
                        <p className="text-gray-700">{result.legal_basis}</p>
                      </div>

                      {result.additional_notes && (
                        <div>
                          <h4 className="font-medium text-gray-900 mb-2">Additional Notes</h4>
                          <p className="text-gray-700">{result.additional_notes}</p>
                        </div>
                      )}
                    </div>

                    {/* Chat Interface */}
                    <ChatInterface 
                      responseId={`${result.survey_id}|${result.country}|${selectedModel}`}
                      originalResponse={result}
                    />
                  </div>
                ))}
              </div>
            )}

            {results.length === 0 && !loading && (
              <div className="text-center py-12">
                <div className="text-gray-400 mb-4">
                  <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No results yet</h3>
                <p className="text-gray-500">Configure your analysis settings and click "Start Analysis" to begin.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App