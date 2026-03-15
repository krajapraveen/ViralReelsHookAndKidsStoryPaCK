import { useRef, useEffect, useCallback, useState } from 'react';

const WS_RECONNECT_DELAY = 3000;
const WS_PING_INTERVAL = 25000;

export function useJobWebSocket(jobId, token) {
  const wsRef = useRef(null);
  const pingRef = useRef(null);
  const reconnectRef = useRef(null);
  const [connected, setConnected] = useState(false);

  const getWsUrl = useCallback(() => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
    const wsProto = backendUrl.startsWith('https') ? 'wss' : 'ws';
    const host = backendUrl.replace(/^https?:\/\//, '');
    return `${wsProto}://${host}/ws/progress?token=${token}${jobId ? `&job_id=${jobId}` : ''}`;
  }, [jobId, token]);

  const connect = useCallback(() => {
    if (!token) return;
    try {
      const url = getWsUrl();
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setConnected(true);
        // Start ping keepalive
        pingRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, WS_PING_INTERVAL);
      };

      ws.onclose = () => {
        setConnected(false);
        clearInterval(pingRef.current);
        // Auto-reconnect
        reconnectRef.current = setTimeout(connect, WS_RECONNECT_DELAY);
      };

      ws.onerror = () => {
        setConnected(false);
      };

      wsRef.current = ws;
    } catch {
      setConnected(false);
    }
  }, [token, getWsUrl]);

  const subscribe = useCallback((newJobId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', job_id: newJobId }));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearInterval(pingRef.current);
      clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on cleanup
        wsRef.current.close();
      }
    };
  }, [connect]);

  // Re-subscribe when jobId changes
  useEffect(() => {
    if (jobId && connected) {
      subscribe(jobId);
    }
  }, [jobId, connected, subscribe]);

  return { wsRef, connected, subscribe };
}
