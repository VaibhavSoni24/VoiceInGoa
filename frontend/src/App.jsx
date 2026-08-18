import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Play, Send, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { startTour } from './tour';
import './index.css';

// WAV Encoder Utilities
function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

function encodeWAV(samples, sampleRate, numChannels) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * 2, true);
  view.setUint16(32, numChannels * 2, true);
  view.setUint16(34, 16, true); // 16-bit
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);
  
  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  
  return new Blob([view], { type: 'audio/wav' });
}

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [answer, setAnswer] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    // Start the tour if it's the first time
    const hasSeenTour = localStorage.getItem('hasSeenTour');
    if (!hasSeenTour) {
      setTimeout(() => startTour(), 500);
      localStorage.setItem('hasSeenTour', 'true');
    }
  }, []);

  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = handleStopRecordingComplete;
      
      mediaRecorder.start();
      setIsRecording(true);
      setError(null);
      setTranscript('');
      setAnswer(null);
      setMetrics(null);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      setError('Microphone access denied. Please allow microphone permissions.');
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  const handleStopRecordingComplete = async () => {
    setIsProcessing(true);
    
    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      const arrayBuffer = await audioBlob.arrayBuffer();
      
      const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      
      let pcmData;
      if (audioBuffer.numberOfChannels === 2) {
        const left = audioBuffer.getChannelData(0);
        const right = audioBuffer.getChannelData(1);
        pcmData = new Float32Array(left.length + right.length);
        for (let i = 0; i < left.length; i++) {
          pcmData[i * 2] = left[i];
          pcmData[i * 2 + 1] = right[i];
        }
      } else {
        pcmData = audioBuffer.getChannelData(0);
      }
      
      const wavBlob = encodeWAV(pcmData, audioBuffer.sampleRate, audioBuffer.numberOfChannels);
      
      const formData = new FormData();
      formData.append('file', wavBlob, 'recording.wav');
      // Assuming backend is running on localhost:8000
      const response = await fetch('http://localhost:8000/api/ask-voice', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.status === 'answered' || data.status === 'answered_partial') {
        setTranscript(data.transcribed_query);
        setAnswer({
          content: data.answer,
          citations: data.citations?.map(c => ({ id: c.passage_id, text: c.snippet })) || []
        });
        setMetrics({
          stt_ms: data.latency_ms?.stt || 0,
          retrieval_ms: data.latency_ms?.retrieval || 0,
          generation_ms: data.latency_ms?.generation || 0,
          total_rag_ms: data.latency_ms?.total || 0
        });
        
        // Autoplay TTS
        if (data.audio_base64) {
          const audio = new Audio(`data:audio/wav;base64,${data.audio_base64}`);
          audio.play().catch(e => console.error("Audio playback failed:", e));
        }
        
      } else if (data.status === 'refused') {
        setTranscript(data.transcribed_query);
        setAnswer({
          refused: true,
          content: data.message || 'Request refused.',
          reason: data.guardrail_triggered || 'Unknown'
        });
        setMetrics({
          stt_ms: data.latency_ms?.stt || 0,
          retrieval_ms: data.latency_ms?.retrieval || 0,
          generation_ms: data.latency_ms?.generation || 0,
          total_rag_ms: data.latency_ms?.total || 0
        });
      } else {
        throw new Error(data.message || 'Unknown error occurred');
      }
      
    } catch (err) {
      console.error('Error processing audio:', err);
      setError(err.message || 'Failed to process audio. Ensure backend is running.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fdfaf2] text-[#1a1a1a] font-inter overflow-hidden relative">
      {/* ReactBits inspired Animated Background Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#0e6e3c] opacity-20 rounded-full blur-[100px] animate-pulse"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#ff007f] opacity-10 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '1s' }}></div>

      <div className="container mx-auto px-4 py-12 max-w-4xl relative z-10">
        
        {/* Header */}
        <header className="text-center mb-16">
          <div className="inline-block px-3 py-1 bg-[#ff007f] text-white text-xs font-bold tracking-widest rounded-full mb-4 uppercase">Task #2</div>
          <h1 className="text-5xl font-extrabold text-[#0e6e3c] mb-4 tracking-tight">Voice-Enabled RAG Model</h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Speak a question, get a grounded answer. Sub-200ms latency with engineered chunking and guardrails.
          </p>
        </header>

        {/* Main Interaction Area */}
        <div className="flex flex-col items-center justify-center space-y-12">
          
          {/* Microphone Button */}
          <div id="mic-container" className="relative group">
            {/* Animated dashed border */}
            <div className={`absolute -inset-4 rounded-full border-2 border-dashed ${isRecording ? 'border-[#ff007f] animate-spin-slow' : 'border-gray-300 group-hover:border-[#0e6e3c]'} transition-colors duration-500`}></div>
            
            <button
              onClick={isRecording ? handleStopRecording : handleStartRecording}
              disabled={isProcessing}
              className={`relative z-10 w-32 h-32 rounded-full flex items-center justify-center transition-all duration-300 shadow-2xl ${
                isRecording 
                  ? 'bg-red-500 hover:bg-red-600 scale-110' 
                  : isProcessing
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-[#0e6e3c] hover:bg-[#0c5c32] hover:scale-105'
              }`}
            >
              {isProcessing ? (
                <Loader2 className="w-12 h-12 text-white animate-spin" />
              ) : isRecording ? (
                <MicOff className="w-12 h-12 text-white" />
              ) : (
                <Mic className="w-12 h-12 text-white" />
              )}
            </button>
            
            {/* Status indicator badge */}
            <div className="absolute -top-2 -right-2 bg-[#ffd700] p-2 rounded-full shadow-lg border-2 border-white z-20">
              {isRecording ? (
                <div className="w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
              ) : (
                <Mic className="w-4 h-4 text-gray-800" />
              )}
            </div>
          </div>
          
          <div className="text-center font-medium text-gray-500 uppercase tracking-widest text-sm">
            {isProcessing ? 'Processing pipeline...' : isRecording ? 'Listening... Tap to stop' : 'Tap to speak'}
          </div>

          {/* Results Area */}
          <div className="w-full max-w-3xl space-y-6">
            
            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-2xl flex items-start space-x-3 shadow-sm animate-fade-in">
                <AlertCircle className="w-6 h-6 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold">Pipeline Error</h3>
                  <p>{error}</p>
                </div>
              </div>
            )}

            {/* Transcript & Answer */}
            {transcript && (
              <div id="results-container" className="bg-white rounded-3xl p-8 shadow-xl border border-gray-100 animate-fade-in-up">
                
                {/* Transcript */}
                <div className="mb-8">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center">
                    <Send className="w-3 h-3 mr-2" /> You asked
                  </h3>
                  <p className="text-xl font-medium text-gray-800 italic">"{transcript}"</p>
                </div>
                
                <div className="h-px bg-gray-100 w-full mb-8"></div>
                
                {/* Answer */}
                <div>
                  <h3 className="text-xs font-bold text-[#0e6e3c] uppercase tracking-wider mb-3 flex items-center">
                    <CheckCircle2 className="w-4 h-4 mr-2" /> Grounded Answer
                  </h3>
                  {answer?.refused ? (
                    <div className="bg-amber-50 border-l-4 border-amber-400 p-4 rounded-r-lg text-amber-800">
                      <p className="font-semibold mb-1">Guardrail Triggered</p>
                      <p>{answer.content}</p>
                      <p className="text-xs mt-2 opacity-80">Reason: {answer.reason}</p>
                    </div>
                  ) : (
                    <div className="prose prose-lg max-w-none text-gray-700">
                      <p>{answer?.content}</p>
                      {answer?.citations?.length > 0 && (
                        <div className="mt-6 pt-4 border-t border-gray-50 text-sm">
                          <h4 className="font-semibold text-gray-500 mb-2">Sources:</h4>
                          <ul className="space-y-2">
                            {answer.citations.map((cite, idx) => (
                              <li key={idx} className="bg-gray-50 p-3 rounded-lg border border-gray-100 text-gray-600">
                                <span className="font-medium block text-gray-800 mb-1">Passage #{cite.id}</span>
                                {cite.text}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Latency Analytics */}
            {metrics && (
              <div id="metrics-container" className="grid grid-cols-1 md:grid-cols-4 gap-4 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
                <div className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 text-center">
                  <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">STT</div>
                  <div className="text-2xl font-bold text-gray-800">{metrics.stt_ms}<span className="text-sm font-normal text-gray-500 ml-1">ms</span></div>
                </div>
                <div className="bg-white p-5 rounded-2xl shadow-sm border border-[#0e6e3c]/20 text-center relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-[#0e6e3c]"></div>
                  <div className="text-xs font-bold text-[#0e6e3c] uppercase tracking-widest mb-1">Retrieval</div>
                  <div className="text-2xl font-bold text-gray-800">{metrics.retrieval_ms}<span className="text-sm font-normal text-gray-500 ml-1">ms</span></div>
                </div>
                <div className="bg-white p-5 rounded-2xl shadow-sm border border-[#ff007f]/20 text-center relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-[#ff007f]"></div>
                  <div className="text-xs font-bold text-[#ff007f] uppercase tracking-widest mb-1">Generation</div>
                  <div className="text-2xl font-bold text-gray-800">{metrics.generation_ms}<span className="text-sm font-normal text-gray-500 ml-1">ms</span></div>
                </div>
                <div className="bg-gray-900 p-5 rounded-2xl shadow-md text-center">
                  <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Total RAG</div>
                  <div className="text-2xl font-bold text-white">{metrics.total_rag_ms}<span className="text-sm font-normal text-gray-400 ml-1">ms</span></div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-20 text-center text-sm font-medium text-gray-400">
          <p>#RAGInGoa &bull; Team Hacker House Goa 2026</p>
        </footer>
      </div>
      
      {/* Start Tour Button */}
      <button 
        onClick={startTour}
        className="fixed bottom-6 right-6 bg-white shadow-lg border border-gray-200 text-gray-700 px-4 py-2 rounded-full text-sm font-medium hover:bg-gray-50 transition-colors z-50 flex items-center"
      >
        <Play className="w-4 h-4 mr-2" /> Replay Tour
      </button>
    </div>
  );
}

export default App;
