import React, { useState, useRef, useCallback } from 'react';
import DialecticStream from './DialecticStream';
import AxiomGraph from './AxiomGraph';
import OracleModal from './OracleModal';

const API_URL = import.meta.env.VITE_API_BASE_URL;
const WS_URL = import.meta.env.VITE_WS_BASE_URL;

export default function App() {
  const [problem, setProblem] = useState('');
  const [logs, setLogs] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [isDeadlock, setIsDeadlock] = useState(false);
  const [currentCore, setCurrentCore] = useState([]);
  const [threadId, setThreadId] = useState(null);
  
  const wsRef = useRef(null);

  // 1. شروع دیالکتیک (REST API + WebSocket)
  const handleStart = async () => {
    if (!problem.trim()) return;
    
    setLogs([{ source: 'system', message: `Initializing ADA for: ${problem}`, status: 'INFO' }]);
    setNodes([]); setEdges([]);
    
    try {
      // درخواست POST به بک‌اند برای ساخت Thread جدید
      const response = await fetch(`${API_URL}/api/v1/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: crypto.randomUUID(), problem: problem })
      });
      
      const data = await response.json();
      setThreadId(data.thread_id);
      
      // اتصال به WebSocket برای دریافت لاگ‌های زنده
      connectWebSocket(data.thread_id);
    } catch (error) {
      setLogs(prev => [...prev, { source: 'system', message: `Connection Error: ${error.message}`, status: 'ERROR' }]);
    }
  };

  // 2. مدیریت اتصال WebSocket
  const connectWebSocket = useCallback((id) => {
    if (wsRef.current) wsRef.current.close();
    
    const ws = new WebSocket(`${WS_URL}/ws/v1/stream/${id}`);
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      
      if (msg.event_type === 'GODELIAN_DEADLOCK') {
        setIsDeadlock(true);
        return;
      }

      // اضافه کردن لاگ به استریم
      setLogs(prev => [...prev, {
        source: msg.event_type === 'neural' ? 'neural' : 'symbolic',
        message: msg.event_type === 'neural' ? 'Generating logical hypothesis...' : `Verification: ${msg.status}\n${msg.unsat_core?.join(' AND ') || ''}`,
        status: msg.status
      }]);

      // آپدیت زنده گراف (React Flow)
      updateGraph(msg);
    };

    wsRef.current = ws;
  }, []);

  // 3. رندرینگ پویای گراف بر اساس پیام‌های بک‌اند
  const updateGraph = (msg) => {
    const yPos = msg.iteration * 100;
    
    if (msg.event_type === 'neural') {
      setNodes(prev => [...prev, {
        id: `n_${msg.iteration}`,
        position: { x: 100, y: yPos },
        data: { label: `Hypothesis ${msg.iteration}` },
        style: { background: '#0f172a', color: '#06b6d4', border: '1px solid #06b6d4' }
      }]);
    } 
    else if (msg.event_type === 'symbolic') {
      const isSuccess = msg.status === 'SUCCESS';
      const nodeId = `s_${msg.iteration}`;
      
      setNodes(prev => [...prev, {
        id: nodeId,
        position: { x: 400, y: yPos },
        data: { label: isSuccess ? 'Verified' : 'Contradiction' },
        style: { 
          background: '#0f172a', 
          color: isSuccess ? '#10b981' : '#e11d48', 
          border: `1px solid ${isSuccess ? '#10b981' : '#e11d48'}` 
        }
      }]);

      setEdges(prev => [...prev, {
        id: `e_${msg.iteration}`,
        source: `n_${msg.iteration}`,
        target: nodeId,
        animated: true,
        style: { stroke: isSuccess ? '#10b981' : '#e11d48' }
      }]);

      if (!isSuccess) setCurrentCore(msg.unsat_core);
    }
  };

  // 4. تزریق اصل موضوعه جدید (Oracle Intervention)
  const handleOracleSubmit = async (metaAxiom) => {
    setIsDeadlock(false);
    setLogs(prev => [...prev, { source: 'oracle', message: `Injected Meta-Axiom: ${metaAxiom}`, status: 'INFO' }]);
    
    // اضافه کردن گره اوراکل به گراف
    setNodes(prev => [...prev, {
      id: `oracle_${Date.now()}`,
      position: { x: 250, y: prev.length * 60 },
      data: { label: `Meta-Axiom: ${metaAxiom}` },
      style: { background: '#f59e0b', color: '#0f172a', fontWeight: 'bold', border: 'none' }
    }]);

    try {
      await fetch(`${API_URL}/api/v1/oracle/inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: threadId, meta_axiom: metaAxiom })
      });
    } catch (error) {
      console.error("Oracle Injection Failed:", error);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-slate-900 p-4 font-sans">
      <div className="flex gap-4 mb-4">
        <input 
          type="text" 
          className="flex-1 bg-slate-800 border border-slate-700 rounded p-3 text-white focus:border-neural outline-none"
          placeholder="Enter your logical problem here (e.g., Find x, y where x > 5 and x + y = 10)..."
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleStart()}
        />
        <button 
          onClick={handleStart}
          className="bg-neural hover:bg-cyan-400 text-slate-900 font-bold px-8 rounded transition-colors"
        >
          Initialize ADA
        </button>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        <div className="w-64 bg-slate-800 rounded-lg border border-slate-700 p-4 hidden md:block">
          <h2 className="text-slate-400 font-bold mb-2">Epistemic Memory</h2>
          <p className="text-xs text-slate-500">Connected to Qdrant & Neo4j</p>
          <div className="mt-4 text-xs text-slate-400">
            Status: <span className="text-symbolic">Online</span><br/>
            Thread: <span className="font-mono">{threadId?.split('-')[0] || 'None'}</span>
          </div>
        </div>

        <DialecticStream logs={logs} />
        <AxiomGraph nodes={nodes} edges={edges} />
      </div>

      <OracleModal 
        isOpen={isDeadlock} 
        unsatCore={currentCore} 
        onSubmit={handleOracleSubmit} 
      />
    </div>
  );
}