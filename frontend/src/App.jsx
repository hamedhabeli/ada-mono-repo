import React, { useState, useRef, useCallback, useEffect } from 'react';
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
  const [selectedNode, setSelectedNode] = useState(null);
  
  const wsRef = useRef(null);

  // Re-hydrate session from localStorage on mount
  useEffect(() => {
    const savedThreadId = localStorage.getItem('ada_thread_id');
    if (savedThreadId) {
      hydrateSession(savedThreadId);
    }
  }, []);

  // Hydrate an active session from the backend
  const hydrateSession = async (id) => {
    setLogs([{ source: 'system', message: 'Hydrating active session...', status: 'INFO' }]);
    try {
      const res = await fetch(`${API_URL}/api/v1/threads/${id}/history`);
      if (res.ok) {
        const data = await res.json();
        setThreadId(id);
        setProblem(data.problem || '');
        
        // Populate logs, nodes, and edges from historical run
        if (data.logs && data.logs.length > 0) {
          reconstructStateFromLogs(data.logs);
        } else {
          setLogs([{ source: 'system', message: 'Session exists, awaiting updates...', status: 'INFO' }]);
        }
        
        // Re-establish WebSocket connection
        connectWebSocket(id);
      } else {
        localStorage.removeItem('ada_thread_id');
        setLogs([{ source: 'system', message: 'Previous session not found.', status: 'INFO' }]);
      }
    } catch (err) {
      setLogs([{ source: 'system', message: `Hydration Error: ${err.message}`, status: 'ERROR' }]);
    }
  };

  // Completely reconstruct graph and logs from log entries
  const reconstructStateFromLogs = (logEntries) => {
    let godelianDeadlockDetected = false;
    const mappedLogs = [];
    const newNodes = [];
    const newEdges = [];

    logEntries.forEach((log) => {
      const source = log.event_type;
      let message = '';
      if (source === 'neural') {
        const decs = log.hypothesis?.declarations || '';
        const consts = log.hypothesis?.constraints?.join(', ') || '';
        message = `Generating logical hypothesis...\nDeclarations: ${decs}\nConstraints: ${consts}`;
      } else if (source === 'symbolic') {
        message = `Verification: ${log.status}\n${log.unsat_core?.join(' AND ') || ''}`;
      } else if (source === 'oracle') {
        message = `Oracle Intervention: ${log.status}\nResolved issues using external axioms.`;
      }

      mappedLogs.push({
        source,
        message,
        status: log.status
      });

      // Construct visualization elements
      const yPos = log.iteration * 120;
      if (source === 'neural') {
        // Main neural hypothesis node
        const neuralNodeId = `n_${log.iteration}`;
        newNodes.push({
          id: neuralNodeId,
          position: { x: 150, y: yPos },
          data: { label: `Hypothesis ${log.iteration}`, details: `Declarations:\n${log.hypothesis?.declarations || ''}\nConstraints:\n${log.hypothesis?.constraints?.join('\n') || ''}` },
          style: { background: '#0f172a', color: '#06b6d4', border: '1px solid #06b6d4' }
        });

        // Specialized memory retrieval node connected to neural node
        if (log.hypothesis) {
          const memoryNodeId = `mem_${log.iteration}`;
          newNodes.push({
            id: memoryNodeId,
            position: { x: -80, y: yPos - 30 },
            data: { label: `Memory Retrieved`, details: `Vector Qdrant + Graph Neo4j historical knowledge injection.` },
            style: { background: '#1e1b4b', color: '#c084fc', border: '1px solid #c084fc', fontSize: '10px' }
          });
          newEdges.push({
            id: `em_${log.iteration}`,
            source: memoryNodeId,
            target: neuralNodeId,
            style: { stroke: '#c084fc', strokeDasharray: '5,5' }
          });
        }
      } else if (source === 'symbolic') {
        const isSuccess = log.status === 'SUCCESS';
        const isDeadlock = log.status === 'SYNTAX_DEADLOCK';
        const nodeId = `s_${log.iteration}`;

        newNodes.push({
          id: nodeId,
          position: { x: 450, y: yPos },
          data: { 
            label: isSuccess ? 'Verified' : isDeadlock ? 'Syntax Deadlock' : 'Contradiction', 
            details: isSuccess ? 'Z3 Solver verified correctness.' : isDeadlock ? `Parser failed: ${log.unsat_core?.join(', ')}` : `Unsat Core conflict: ${log.unsat_core?.join(', ')}`
          },
          style: { 
            background: '#0f172a', 
            color: isSuccess ? '#10b981' : isDeadlock ? '#fb7185' : '#e11d48', 
            border: `1px solid ${isSuccess ? '#10b981' : isDeadlock ? '#fb7185' : '#e11d48'}` 
          }
        });

        newEdges.push({
          id: `e_${log.iteration}`,
          source: `n_${log.iteration}`,
          target: nodeId,
          animated: true,
          style: { stroke: isSuccess ? '#10b981' : isDeadlock ? '#fb7185' : '#e11d48' }
        });

        if (!isSuccess) {
          setCurrentCore(log.unsat_core);
          // If syntax error limit was reached or iteration limit exceeded, we are in Godelian Deadlock
          if (isDeadlock || log.iteration >= 5) {
            godelianDeadlockDetected = true;
          }
        }
      } else if (source === 'oracle') {
        newNodes.push({
          id: `oracle_${log.timestamp}`,
          position: { x: 300, y: newNodes.length * 50 },
          data: { label: `Meta-Axiom Injected`, details: `An external rule was supplied by the Human Oracle.` },
          style: { background: '#f59e0b', color: '#0f172a', fontWeight: 'bold', border: 'none' }
        });
      }
    });

    setLogs(mappedLogs);
    setNodes(newNodes);
    setEdges(newEdges);
    if (godelianDeadlockDetected) {
      setIsDeadlock(true);
    }
  };

  // 1. شروع دیالکتیک (REST API + WebSocket)
  const handleStart = async () => {
    if (!problem.trim()) return;
    
    setLogs([{ source: 'system', message: `Initializing ADA for: ${problem}`, status: 'INFO' }]);
    setNodes([]); setEdges([]);
    setSelectedNode(null);
    
    try {
      const generatedThreadId = crypto.randomUUID();
      const response = await fetch(`${API_URL}/api/v1/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thread_id: generatedThreadId, problem: problem })
      });
      
      const data = await response.json();
      setThreadId(data.thread_id);
      localStorage.setItem('ada_thread_id', data.thread_id);
      
      // اتصال به WebSocket برای دریافت لاگ‌های زنده
      connectWebSocket(data.thread_id);
    } catch (error) {
      setLogs(prev => [...prev, { source: 'system', message: `Connection Error: ${error.message}`, status: 'ERROR' }]);
    }
  };

  // Reset Session
  const handleReset = () => {
    if (wsRef.current) wsRef.current.close();
    localStorage.removeItem('ada_thread_id');
    setThreadId(null);
    setProblem('');
    setLogs([]);
    setNodes([]);
    setEdges([]);
    setIsDeadlock(false);
    setSelectedNode(null);
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

      if (msg.logs) {
        reconstructStateFromLogs(msg.logs);
      }
    };

    ws.onclose = () => {
      // Automatic retry reconnection after 3 seconds
      setTimeout(() => {
        const currentSaved = localStorage.getItem('ada_thread_id');
        if (currentSaved === id) {
          connectWebSocket(id);
        }
      }, 3000);
    };

    wsRef.current = ws;
  }, []);

  // 4. تزریق اصل موضوعه جدید (Oracle Intervention)
  const handleOracleSubmit = async (metaAxiom) => {
    setIsDeadlock(false);
    setLogs(prev => [...prev, { source: 'oracle', message: `Injected Meta-Axiom: ${metaAxiom}`, status: 'INFO' }]);
    
    // اضافه کردن گره اوراکل به گراف
    setNodes(prev => [...prev, {
      id: `oracle_${Date.now()}`,
      position: { x: 300, y: prev.length * 50 },
      data: { label: `Meta-Axiom: ${metaAxiom}`, details: `Axiom injected dynamically: ${metaAxiom}` },
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

  // Interactive Node Inspection Details
  const handleNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-slate-900 p-4 font-sans text-white">
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
        {threadId && (
          <button 
            onClick={handleReset}
            className="bg-slate-700 hover:bg-slate-600 text-white font-semibold px-4 rounded transition-colors border border-slate-600"
          >
            New Session
          </button>
        )}
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        <div className="w-64 bg-slate-800 rounded-lg border border-slate-700 p-4 hidden md:flex flex-col justify-between">
          <div>
            <h2 className="text-slate-400 font-bold mb-2">Epistemic Memory</h2>
            <p className="text-xs text-slate-500 mb-4 font-semibold">Connected to Qdrant & Neo4j</p>
            <div className="mt-4 text-xs text-slate-400 leading-relaxed">
              Status: <span className="text-symbolic font-bold">Online</span><br/>
              Thread ID: <span className="font-mono text-[10px] break-all block mt-1 text-slate-400">{threadId || 'None'}</span>
            </div>
          </div>
          <div className="text-[10px] text-slate-500 border-t border-slate-700 pt-3 leading-relaxed">
            Click nodes inside the visualization graph to inspect generated constraints, contradictions, or memory.
          </div>
        </div>

        <DialecticStream logs={logs} />
        <AxiomGraph nodes={nodes} edges={edges} onNodeClick={handleNodeClick} />
      </div>

      <OracleModal 
        isOpen={isDeadlock} 
        unsatCore={currentCore} 
        onSubmit={handleOracleSubmit} 
      />

      {selectedNode && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
          <div className="bg-slate-800 border border-slate-700 rounded-lg max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-neural mb-4 border-b border-slate-700 pb-2 flex justify-between items-center">
              <span>Node Inspector</span>
              <span className="text-[10px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded uppercase">{selectedNode.id.split('_')[0]}</span>
            </h3>
            <div className="space-y-4 text-xs font-mono">
              <div>
                <span className="text-slate-500 block mb-1">NODE TYPE / LABEL</span>
                <span className="text-white text-sm font-semibold">{selectedNode.data?.label}</span>
              </div>
              {selectedNode.data?.details && (
                <div>
                  <span className="text-slate-500 block mb-1">INTERNAL DETAILS</span>
                  <pre className="bg-slate-900 p-3 rounded text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-60">
                    {selectedNode.data.details}
                  </pre>
                </div>
              )}
            </div>
            <button 
              onClick={() => setSelectedNode(null)}
              className="mt-6 w-full bg-neural hover:bg-cyan-400 text-slate-900 font-bold py-2 rounded transition-colors"
            >
              Close Inspector
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
