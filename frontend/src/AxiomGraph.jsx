import React from 'react';
import { ReactFlow, Background, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export default function AxiomGraph({ nodes, edges }) {
  return (
    <div className="flex-1 bg-slate-900 rounded-lg border border-slate-700 overflow-hidden h-full">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#1e293b" gap={16} />
        <Controls className="bg-slate-800 fill-white" />
      </ReactFlow>
    </div>
  );
}