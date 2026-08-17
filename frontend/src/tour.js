import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';

export const startTour = () => {
  const driverObj = driver({
    showProgress: true,
    animate: true,
    steps: [
      {
        element: 'header',
        popover: {
          title: 'Welcome to VoiceInGoa',
          description: 'This is the Task #2 submission for HH Goa 2026: a sub-200ms voice-enabled RAG pipeline.',
          side: 'bottom',
          align: 'center'
        }
      },
      {
        element: '#mic-container',
        popover: {
          title: 'Speak Your Question',
          description: 'Click this microphone button to start recording. Ask a question about the MS MARCO-XI dataset. Click again to stop.',
          side: 'right',
          align: 'start'
        }
      },
      {
        popover: {
          title: 'Guardrails & Latency',
          description: 'Behind the scenes, we use fast Qdrant vector retrieval, InceptionAPI LLM, and Sarvam/ElevenLabs STT to ensure accurate and extremely fast (sub-200ms) answers with strict off-topic guardrails.',
          side: 'center',
          align: 'center'
        }
      }
    ]
  });

  driverObj.drive();
};
