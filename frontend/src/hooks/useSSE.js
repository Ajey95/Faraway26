import { useEffect, useState } from 'react';
import { streamUrl } from '../api';

const EVENT_NAMES = ['paper_fetched', 'claims_extracted', 'repo_mapped', 'code_audited', 'claims_verified', 'report_written', 'failed'];
const TERMINAL_EVENTS = new Set(['report_written', 'failed']);

function parseEvent(event) {
  return { ...JSON.parse(event.data), timestamp: new Date().toLocaleTimeString() };
}

export function useSSE(auditId) {
  const [events, setEvents] = useState([]);
  const [connectionState, setConnectionState] = useState('idle');

  useEffect(() => {
    setEvents([]);
    if (!auditId) {
      setConnectionState('idle');
      return undefined;
    }

    setConnectionState('connecting');
    const source = new EventSource(streamUrl(auditId));
    let terminalEventSeen = false;
    const append = (event) => {
      const parsed = parseEvent(event);
      setEvents((items) => [...items, parsed]);
      if (TERMINAL_EVENTS.has(parsed.step)) {
        terminalEventSeen = true;
        setConnectionState(parsed.step === 'failed' ? 'failed' : 'completed');
        source.close();
      }
    };

    source.onopen = () => setConnectionState('connected');
    source.onmessage = append;
    source.onerror = () => {
      if (!terminalEventSeen) {
        setConnectionState(source.readyState === EventSource.CLOSED ? 'closed' : 'disconnected');
      }
    };
    EVENT_NAMES.forEach((name) => source.addEventListener(name, append));

    return () => {
      terminalEventSeen = true;
      source.close();
      setConnectionState('closed');
    };
  }, [auditId]);

  return { events, connectionState };
}
