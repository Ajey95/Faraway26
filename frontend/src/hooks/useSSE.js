import { useEffect, useState } from 'react';
import { streamUrl } from '../api';

const EVENT_NAMES = ['paper_fetched', 'claims_extracted', 'repo_mapped', 'code_audited', 'claims_verified', 'report_written', 'failed'];

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
    const append = (event) => setEvents((items) => [...items, parseEvent(event)]);

    source.onopen = () => setConnectionState('connected');
    source.onmessage = append;
    source.onerror = () => setConnectionState(source.readyState === EventSource.CLOSED ? 'closed' : 'disconnected');
    EVENT_NAMES.forEach((name) => source.addEventListener(name, append));

    return () => {
      source.close();
      setConnectionState('closed');
    };
  }, [auditId]);

  return { events, connectionState };
}
