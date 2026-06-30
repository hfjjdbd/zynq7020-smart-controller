'use client';

import { useState, useEffect, useCallback } from 'react';

const LEDS = [
  { name: 'usr_led1', label: 'LED1', color: '#30d158' },
  { name: 'usr_led2', label: 'LED2', color: '#30d158' },
  { name: 'led_r', label: 'Green', color: '#30d158' },
  { name: 'led_g', label: 'Blue', color: '#0a84ff' },
  { name: 'led_b', label: 'Red', color: '#ff453a' },
];

const NOTES = [
  { freq: 262, label: 'C4' },
  { freq: 294, label: 'D4' },
  { freq: 330, label: 'E4' },
  { freq: 349, label: 'F4' },
  { freq: 392, label: 'G4' },
  { freq: 440, label: 'A4' },
  { freq: 494, label: 'B4' },
  { freq: 523, label: 'C5' },
  { freq: 880, label: 'A5' },
];

async function requestJson<T>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message =
      typeof data?.error === 'string'
        ? data.error
        : `Request failed with HTTP ${response.status}`;
    throw new Error(message);
  }

  return data as T;
}

export default function Home() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [connected, setConnected] = useState<boolean | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [playing, setPlaying] = useState(false);
  const [ledStates, setLedStates] = useState<Record<string, boolean>>({});

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const checkHealth = useCallback(async () => {
    try {
      await requestJson('/api/board/health');
      setConnected(true);
      setError('');
    } catch (err) {
      setConnected(false);
      setError(err instanceof Error ? err.message : 'Board is unavailable');
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const timer = setInterval(checkHealth, 5000);
    return () => clearInterval(timer);
  }, [checkHealth]);

  const setLed = async (name: string, value: 0 | 1) => {
    const oldValue = ledStates[name];
    setLedStates((prev) => ({ ...prev, [name]: value === 1 }));
    setBusy(`led:${name}`);
    setError('');

    try {
      await requestJson('/api/board/led', {
        method: 'POST',
        body: JSON.stringify({ name, value }),
      });
    } catch (err) {
      setLedStates((prev) => ({ ...prev, [name]: oldValue }));
      setError(err instanceof Error ? err.message : 'LED operation failed');
    } finally {
      setBusy('');
    }
  };

  const playNote = async (freq: number) => {
    setBusy('note');
    setError('');
    try {
      await requestJson('/api/board/buzzer', {
        method: 'POST',
        body: JSON.stringify({ freq, duration: 300 }),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Buzzer request failed');
    } finally {
      setBusy('');
    }
  };

  const playSong = async () => {
    setBusy('song');
    setPlaying(true);
    setError('');
    try {
      await requestJson('/api/board/play-song', { method: 'POST' });
    } catch (err) {
      setPlaying(false);
      setError(err instanceof Error ? err.message : 'Play request failed');
    } finally {
      setBusy('');
    }
  };

  const stopSong = async () => {
    setBusy('stop');
    setError('');
    try {
      await requestJson('/api/board/stop-song', { method: 'POST' });
      setPlaying(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stop request failed');
    } finally {
      setBusy('');
    }
  };

  const isConnected = connected === true;
  const isBusy = busy !== '';

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '40px 20px' }}>
      <button
        className="theme-toggle"
        onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
      >
        {theme === 'dark' ? '☀️' : '🌙'}
      </button>

      <h1 style={{ textAlign: 'center', fontSize: 36, fontWeight: 700, marginBottom: 8 }}>
        ZYNQ7020
      </h1>
      <p style={{ textAlign: 'center', color: 'var(--text-secondary)', marginBottom: 8, fontSize: 18 }}>
        Smart Controller
      </p>

      {/* Connection Status */}
      <p style={{
        textAlign: 'center',
        fontSize: 14,
        marginBottom: 40,
        color: connected === null ? 'var(--text-secondary)' : isConnected ? '#30d158' : '#ff453a',
      }}>
        {connected === null ? 'Checking...' : isConnected ? '● Connected' : '● Disconnected'}
      </p>

      {/* Error Display */}
      {error && (
        <div style={{
          background: 'rgba(255,69,58,0.1)',
          border: '1px solid rgba(255,69,58,0.3)',
          borderRadius: 12,
          padding: '12px 16px',
          marginBottom: 24,
          color: '#ff453a',
          fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {/* LED Section */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, marginBottom: 20 }}>LED Control</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 16 }}>
          {LEDS.map((led) => (
            <div key={led.name} className="card" style={{ textAlign: 'center', padding: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 12 }}>{led.label}</div>
              <div
                className={`dot ${ledStates[led.name] ? 'on' : ''}`}
                style={{
                  background: ledStates[led.name] ? led.color : 'var(--border)',
                  color: led.color,
                }}
              />
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                <button
                  className="btn btn-on"
                  disabled={isBusy}
                  onClick={() => setLed(led.name, 1)}
                >
                  ON
                </button>
                <button
                  className="btn btn-off"
                  disabled={isBusy}
                  onClick={() => setLed(led.name, 0)}
                >
                  OFF
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Buzzer Section */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 600, marginBottom: 20 }}>Buzzer</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 20 }}>
          {NOTES.map((n) => (
            <button
              key={n.freq}
              className="btn"
              disabled={isBusy}
              style={{
                background: 'var(--bg-card)',
                color: 'var(--text)',
                border: '1px solid var(--border)',
                padding: '12px 20px',
                borderRadius: 12,
                minWidth: 60,
                opacity: isBusy ? 0.5 : 1,
              }}
              onClick={() => playNote(n.freq)}
            >
              {n.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            className="btn btn-primary"
            disabled={isBusy || playing}
            onClick={playSong}
          >
            ▶ Play Music
          </button>
          <button
            className="btn btn-danger"
            disabled={isBusy}
            onClick={stopSong}
          >
            ■ Stop
          </button>
        </div>
        {playing && (
          <p style={{ marginTop: 12, color: '#30d158', fontSize: 14, fontWeight: 500 }}>
            ● Playing...
          </p>
        )}
      </div>
    </div>
  );
}
