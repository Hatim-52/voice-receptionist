/**
 * sseEvents.ts - Live Event Stream Consumer (Server-Sent Events & WebSocket).
 * Handles real-time appointment updates, cancellations, call state, and live transcripts.
 */

export interface LiveEventPayload {
  event: string;
  timestamp: string;
  data: Record<string, unknown>;
}

type EventCallback = (payload: LiveEventPayload) => void;

class LiveEventService {
  private eventSource: EventSource | null = null;
  private ws: WebSocket | null = null;
  private listeners: Set<EventCallback> = new Set();
  private isConnected = false;
  private reconnectTimer: number | null = null;

  public subscribe(callback: EventCallback): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private notifyAll(payload: LiveEventPayload) {
    this.listeners.forEach((listener) => {
      try {
        listener(payload);
      } catch (err) {
        console.error('[sseEvents] Listener error:', err);
      }
    });
  }

  public connect() {
    if (this.eventSource || this.ws) return;

    // First try Server-Sent Events (SSE)
    try {
      const sseUrl = '/api/events';
      this.eventSource = new EventSource(sseUrl);

      this.eventSource.onopen = () => {
        this.isConnected = true;
        this.notifyAll({
          event: 'connection_status',
          timestamp: new Date().toISOString(),
          data: { status: 'connected', transport: 'sse' }
        });
      };

      // General messages
      this.eventSource.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          this.notifyAll(parsed);
        } catch {
          // heartbeat
        }
      };

      // Named SSE events
      const eventNames = ['appointment_booked', 'appointment_cancelled', 'transcript', 'call_status', 'database_reset'];
      eventNames.forEach((evtName) => {
        this.eventSource?.addEventListener(evtName, (e: MessageEvent) => {
          try {
            const parsed = JSON.parse(e.data);
            this.notifyAll(parsed);
          } catch (err) {
            console.error(`Error parsing ${evtName}:`, err);
          }
        });
      });

      this.eventSource.onerror = () => {
        console.warn('[sseEvents] SSE disconnected, falling back to WebSocket...');
        this.disconnect();
        this.connectWebSocket();
      };
    } catch {
      this.connectWebSocket();
    }
  }

  private connectWebSocket() {
    try {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${proto}//${window.location.host}/ws`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        this.notifyAll({
          event: 'connection_status',
          timestamp: new Date().toISOString(),
          data: { status: 'connected', transport: 'websocket' }
        });
      };

      this.ws.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data);
          this.notifyAll(parsed);
        } catch {
          // ignore ping
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.isConnected = false;
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 3000);
  }

  public disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
  }

  public getConnected(): boolean {
    return this.isConnected;
  }
}

export const liveEvents = new LiveEventService();
