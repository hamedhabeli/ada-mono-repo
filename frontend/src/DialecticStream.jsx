import React from 'react';
import { Brain, Cpu, AlertTriangle } from 'lucide-react';

export default function DialecticStream({ logs }) {
  return (
    <div className="flex-1 bg-slate-800 p-4 rounded-lg overflow-y-auto border border-slate-700 shadow-inner">
      <h2 className="text-lg font-bold text-slate-300 mb-4 border-b border-slate-600 pb-2">Dialectic Stream</h2>
      <div className="space-y-4">
        {logs.map((log, idx) => (
          <div key={idx} className={`p-3 rounded border-l-4 ${
            log.source === 'neural' ? 'bg-slate-900 border-neural text-neural' :
            log.source === 'symbolic' && log.status === 'SUCCESS' ? 'bg-slate-900 border-symbolic text-symbolic' :
            'bg-slate-900 border-error text-error'
          }`}>
            <div className="flex items-center gap-2 font-bold mb-1">
              {log.source === 'neural' ? <Brain size={16} /> : 
               log.status === 'SUCCESS' ? <Cpu size={16} /> : <AlertTriangle size={16} />}
              <span>{log.source.toUpperCase()}</span>
            </div>
            <p className="text-sm font-mono whitespace-pre-wrap">{log.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
}