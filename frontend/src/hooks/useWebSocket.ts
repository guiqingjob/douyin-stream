import { useEffect, useCallback, useRef } from 'react';
import { useStore } from '@/store/useStore';

const WS_URL = `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/ws`;

export function useWebSocket() {
  const updateTask = useStore((state) => state.updateTask);
  const reconnectDelayRef = useRef(1000);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
      reconnectDelayRef.current = 1000;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = () => {
      console.error('WebSocket error');
    };

    ws.onclose = () => {
      console.log('WebSocket closed, reconnecting in', reconnectDelayRef.current, 'ms');
      setTimeout(connect, reconnectDelayRef.current);
      reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000);
    };

    wsRef.current = ws;
  }, []);

  const handleMessage = (data: unknown) => {
    if (typeof data !== 'object' || data === null) return;

    const message = data as { type: string; payload?: unknown };

    switch (message.type) {
      case 'task_update':
        if (message.payload && typeof message.payload === 'object') {
          const payload = message.payload as { task_id?: string };
          if (payload.task_id) {
            updateTask({ task_id: payload.task_id });
          }
        }
        break;
      case 'task_created':
        if (message.payload && typeof message.payload === 'object') {
          const payload = message.payload as { task_id?: string };
          if (payload.task_id) {
            updateTask({ task_id: payload.task_id });
          }
        }
        break;
      case 'task_priority_change':
        if (message.payload && typeof message.payload === 'object') {
          const payload = message.payload as { task_id?: string };
          if (payload.task_id) {
            updateTask({ task_id: payload.task_id });
          }
        }
        break;
      case 'ping':
        break;
    }
  };

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { connect, disconnect };
}