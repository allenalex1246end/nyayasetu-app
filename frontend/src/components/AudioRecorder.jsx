import React, { useState, useRef } from 'react'

export default function AudioRecorder({ onTranscribed, disabled = false }) {
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [language, setLanguage] = useState('en') // 'en' for English, 'ml' for Malayalam
  const [useWebSpeech, setUseWebSpeech] = useState(false) // Toggle between Whisper and Web Speech
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const timerRef = useRef(null)
  const recognitionRef = useRef(null)

  // Initialize Web Speech Recognition
  const createWebSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return null
    
    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.language = language === 'ml' ? 'ml-IN' : 'en-US'
    return recognition
  }

  const startRecordingWebSpeech = async () => {
    try {
      const recognition = createWebSpeechRecognition()
      if (!recognition) {
        onTranscribed({ error: 'Web Speech API not supported in your browser' })
        return
      }

      recognitionRef.current = recognition
      let transcript = ''

      recognition.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript
        }
      }

      recognition.onend = async () => {
        if (transcript.trim()) {
          let finalText = transcript.trim()
          
          // If Malayalam, translate to English
          if (language === 'ml') {
            try {
              const token = localStorage.getItem('authToken') || 'demo-token-nyayasetu-2026'
              const response = await fetch('http://localhost:8000/api/translate-from-malayalam', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ text: transcript })
              })
              const result = await response.json()
              if (result.success && result.data?.english) {
                finalText = result.data.english
              }
            } catch (err) {
              console.error('Translation error:', err)
            }
          }
          
          onTranscribed({ text: finalText })
        }
        setIsRecording(false)
        setIsTranscribing(false)
      }

      recognition.onerror = (event) => {
        onTranscribed({ error: `Speech recognition error: ${event.error}` })
        setIsRecording(false)
        setIsTranscribing(false)
      }

      recognition.start()
      setIsRecording(true)
      setIsTranscribing(true)
      setRecordingTime(0)

      timerRef.current = setInterval(() => {
        setRecordingTime(t => {
          if (t >= 300) {
            recognition.stop()
            return 300
          }
          return t + 1
        })
      }, 1000)
    } catch (err) {
      onTranscribed({ error: `Microphone error: ${err.message}` })
    }
  }

  const stopRecordingWebSpeech = () => {
    if (recognitionRef.current && isRecording) {
      recognitionRef.current.stop()
    }
  }

  const startRecording = async () => {
    if (useWebSpeech) {
      return startRecordingWebSpeech()
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      
      audioChunksRef.current = []
      mediaRecorder.ondataavailable = (e) => {
        audioChunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await transcribeAudio(audioBlob)
        
        // Stop stream
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(t => {
          if (t >= 300) { // 5 minute limit
            stopRecording()
            return 300
          }
          return t + 1
        })
      }, 1000)
    } catch (err) {
      console.error('Microphone access error:', err)
      onTranscribed({ error: 'Microphone access denied. Please check permissions.' })
    }
  }

  const stopRecording = () => {
    if (useWebSpeech) {
      return stopRecordingWebSpeech()
    }

    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }

  const transcribeAudio = async (audioBlob) => {
    setIsTranscribing(true)
    try {
      const formData = new FormData()
      formData.append('file', audioBlob, 'audio.webm')
      
      const token = localStorage.getItem('authToken') || 'demo-token-nyayasetu-2026'
      const response = await fetch('http://localhost:8000/api/audio/transcribe', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      const result = await response.json()
      
      // If Whisper fails, suggest Web Speech API
      if (!result.success || !result.data?.text) {
        console.log('Whisper API failed - switch to Web Speech API for better results')
        const hasWebSpeech = window.SpeechRecognition || window.webkitSpeechRecognition
        const suggestion = hasWebSpeech 
          ? 'Click the gear icon to enable Web Speech mode' 
          : 'Your browser does not support Web Speech API'
        onTranscribed({ error: `Whisper error. ${suggestion}` })
        return
      }
      
      let finalText = result.data.text
      
      // If Malayalam is selected, translate to English
      if (language === 'ml') {
        try {
          const translateResponse = await fetch('http://localhost:8000/api/translate-from-malayalam', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ text: result.data.text })
          })
          const translateResult = await translateResponse.json()
          if (translateResult.success && translateResult.data?.english) {
            finalText = translateResult.data.english
          }
        } catch (err) {
          console.error('Translation error:', err)
        }
      }
      
      onTranscribed({ text: finalText })
    } catch (err) {
      console.error('Transcription error:', err)
      onTranscribed({ error: 'Failed to transcribe. Try Web Speech API mode.' })
    } finally {
      setIsTranscribing(false)
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Control Bar: Language Selector + Settings */}
      <div className="flex gap-2 items-center">
        {/* Language Selector */}
        <div className="flex gap-1 bg-gray-100 rounded p-1">
          <button
            type="button"
            onClick={() => setLanguage('en')}
            disabled={disabled || isRecording || isTranscribing}
            className={`px-2 py-1 rounded text-xs font-medium transition ${
              language === 'en'
                ? 'bg-accent text-white'
                : 'bg-transparent text-gray-700 hover:bg-gray-200'
            }`}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => setLanguage('ml')}
            disabled={disabled || isRecording || isTranscribing}
            className={`px-2 py-1 rounded text-xs font-medium transition ${
              language === 'ml'
                ? 'bg-accent text-white'
                : 'bg-transparent text-gray-700 hover:bg-gray-200'
            }`}
          >
            ML
          </button>
        </div>
        
        {/* Web Speech Toggle */}
        <button
          type="button"
          onClick={() => setUseWebSpeech(!useWebSpeech)}
          disabled={disabled || isRecording || isTranscribing}
          title={useWebSpeech ? 'Using Web Speech API' : 'Using Whisper API'}
          className={`p-2 rounded transition ${
            useWebSpeech
              ? 'bg-green-100 text-green-700 hover:bg-green-200'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm1-13h-2v6l5.25 3.15.75-1.23-4-2.42z" />
          </svg>
        </button>
      </div>

      {/* Mode Indicator */}
      <p className="text-xs text-gray-500">
        {useWebSpeech ? '🌐 Web Speech Mode' : '🎙️ Whisper API Mode'}
      </p>

      {/* Microphone Button */}
      <button
        type="button"
        onClick={isRecording ? stopRecording : startRecording}
        disabled={disabled || isTranscribing}
        className={`relative flex h-16 w-16 items-center justify-center rounded-full shadow-lg transition-all focus:outline-none focus:ring-4 focus:ring-offset-2 ${
          isRecording
            ? 'bg-critical text-white focus:ring-critical/50 animate-pulse'
            : isTranscribing
            ? 'bg-gray-400 text-white focus:ring-gray-400/50 cursor-wait'
            : 'bg-accent text-white hover:bg-accent/90 hover:scale-105 focus:ring-accent/50'
        }`}
        title={isRecording ? 'Stop recording' : isTranscribing ? 'Transcribing...' : 'Record audio'}
      >
        {isTranscribing ? (
          <svg className="h-6 w-6 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        ) : (
          <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
          </svg>
        )}
      </button>

      {isRecording && (
        <div className="text-center">
          <p className="text-sm font-semibold text-critical font-body animate-pulse">
            Recording: {formatTime(recordingTime)}
          </p>
          <p className="text-xs text-gray-500 font-body">(Tap button to stop)</p>
        </div>
      )}

      {isTranscribing && (
        <p className="text-sm text-gray-500 font-body animate-pulse">
          {useWebSpeech
            ? 'Listening with Web Speech...'
            : language === 'ml'
            ? 'Transcribing Malayalam (Whisper)...'
            : 'Converting to text (Whisper)...'}
        </p>
      )}
    </div>
  )
}
