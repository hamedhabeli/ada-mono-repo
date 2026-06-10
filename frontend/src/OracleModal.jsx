import React, { useState } from 'react';

export default function OracleModal({ isOpen, unsatCore, onSubmit }) {
  const [axiom, setAxiom] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (axiom.trim()) {
      onSubmit(axiom.trim());
      setAxiom('');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center p-4 z-50">
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 max-w-md w-full text-white">
        <h2 className="text-xl font-bold text-amber-500 mb-4">Gödelian Deadlock</h2>
        <p className="text-sm text-slate-300 mb-4">
          A deadlock has been detected in the symbolic verification engine.
        </p>
        
        {unsatCore && unsatCore.length > 0 && (
          <div className="mb-4 p-3 bg-slate-900 rounded border border-rose-500/30">
            <span className="text-xs text-rose-400 block mb-1">Unsatisfiable Core:</span>
            <code className="text-sm font-mono text-rose-300 break-all">
              {unsatCore.join(' AND ')}
            </code>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Inject New Meta-Axiom</label>
            <input
              type="text"
              placeholder="Enter a new Meta-Axiom"
              className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white outline-none focus:border-amber-500 transition-colors"
              value={axiom}
              onChange={(e) => setAxiom(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="w-full bg-amber-500 hover:bg-amber-600 text-slate-900 font-bold py-2 px-4 rounded transition-colors"
          >
            Inject Axiom
          </button>
        </form>
      </div>
    </div>
  );
}
