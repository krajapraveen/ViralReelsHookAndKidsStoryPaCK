/**
 * WebSocket Progress Hook
 * Real-time progress updates for long-running generation jobs
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';

const WS_RECONNECT_DELAY = 3000;
const WS_MAX_RETRIES = 5;

export const useWebSocketProgress = (jobId = null, onProgress = null, onComplete = null, onError = null) => {
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const retriesRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);

  // Get WebSocket URL from backend URL
  const getWsUrl = useCallback(() => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL || window.location.origin;
    const wsProtocol = backendUrl.startsWith('https') ? 'wss' : 'ws';
    const baseUrl = backendUrl.replace(/^https?/, wsProtocol);
    const token = localStorage.getItem('token');
    
    if (!token) {
      console.warn('No auth token for WebSocket');
      return null;
    }
    
    let url = `${baseUrl}/ws/progress?token=${token}`;
    if (jobId) {
      url += `&job_id=${jobId}`;
    }
    return url;
  }, [jobId]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    const url = getWsUrl();
    if (!url) return;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
        retriesRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.type) {
            case 'connected':
              console.log('WebSocket authenticated:', data.user_id);
              break;
              
            case 'subscribed':
              console.log('Subscribed to job:', data.job_id);
              break;
              
            case 'progress':
              setProgress(data);
              onProgress?.(data);
              
              // Show toast for key milestones
              if (data.status === 'running' && data.current_step === 1) {
                toast.info(data.message);
              }
              break;
              
            case 'complete':
              setProgress({ ...data, status: 'completed' });
              onComplete?.(data);
              toast.success(data.message || 'Generation complete!');
              break;
              
            case 'error':
              setError(data.message);
              onError?.(data);
              toast.error(data.message || 'Generation failed');
              break;
              
            case 'pong':
              // Keep-alive response
              break;
              
            default:
              console.log('Unknown WebSocket message:', data);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;
        
        // Attempt reconnection if not a clean close
        if (event.code !== 1000 && retriesRef.current < WS_MAX_RETRIES) {
          retriesRef.current++;
          console.log(`Reconnecting in ${WS_RECONNECT_DELAY}ms (attempt ${retriesRef.current}/${WS_MAX_RETRIES})`);
          reconnectTimeoutRef.current = setTimeout(connect, WS_RECONNECT_DELAY);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error');
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      setError('Failed to connect');
    }
  }, [getWsUrl, onProgress, onComplete, onError]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect');
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Subscribe to a specific job
  const subscribeToJob = useCallback((newJobId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        job_id: newJobId
      }));
    }
  }, []);

  // Unsubscribe from a job
  const unsubscribeFromJob = useCallback((jobIdToUnsub) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'unsubscribe',
        job_id: jobIdToUnsub
      }));
    }
  }, []);

  // Send ping to keep connection alive
  const ping = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  }, []);

  // Auto-connect when component mounts
  useEffect(() => {
    connect();
    
    // Set up ping interval
    const pingInterval = setInterval(ping, 30000);
    
    return () => {
      clearInterval(pingInterval);
      disconnect();
    };
  }, [connect, disconnect, ping]);

  // Subscribe to new jobId when it changes
  useEffect(() => {
    if (jobId && isConnected) {
      subscribeToJob(jobId);
    }
  }, [jobId, isConnected, subscribeToJob]);

  return {
    isConnected,
    progress,
    error,
    connect,
    disconnect,
    subscribeToJob,
    unsubscribeFromJob
  };
};

export default useWebSocketProgress;
