import { useCallback, useRef } from "react";
import ReactFlow, { Background, Controls, MiniMap, useReactFlow, type Connection } from "reactflow";
import "reactflow/dist/style.css";

import { getPaletteDropPayload } from "../lib/palette-drag";
import { nodeRegistry } from "../model/node-registry";
import { useWorkflowBuilderStore } from "../model/workflow-builder.store";

const nodeTypes = Object.fromEntries(Object.entries(nodeRegistry).map(([type, def]) => [type, def!.component]));

export function WorkflowCanvas() {
  const nodes = useWorkflowBuilderStore((s) => s.nodes);
  const edges = useWorkflowBuilderStore((s) => s.edges);
  const onNodesChange = useWorkflowBuilderStore((s) => s.onNodesChange);
  const onEdgesChange = useWorkflowBuilderStore((s) => s.onEdgesChange);
  const onConnect = useWorkflowBuilderStore((s) => s.onConnect);
  const addNode = useWorkflowBuilderStore((s) => s.addNode);
  const selectNode = useWorkflowBuilderStore((s) => s.selectNode);
  const selectEdge = useWorkflowBuilderStore((s) => s.selectEdge);

  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const { screenToFlowPosition } = useReactFlow();

  const handleConnect = useCallback((c: Connection) => onConnect(c), [onConnect]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const payload = getPaletteDropPayload(event);
      if (!payload) return;

      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });

      if (payload.kind === "agent") {
        addNode({
          type: "agent",
          position,
          data: { label: payload.name, config: { agentId: payload.agentId, input: "" } },
        });
        return;
      }

      addNode({ type: payload.type, position });
    },
    [addNode, screenToFlowPosition],
  );

  return (
    <div ref={wrapperRef} className="h-full w-full" onDragOver={onDragOver} onDrop={onDrop}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={handleConnect}
        onNodeClick={(_, n) => selectNode(n.id as never)}
        onEdgeClick={(_, e) => selectEdge(e.id as never)}
        onPaneClick={() => {
          selectNode(null);
          selectEdge(null);
        }}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} color="#e6e2d4" />
        <Controls className="!border-canvas-rule !bg-canvas-panel" />
        <MiniMap className="!border-canvas-rule !bg-canvas-panel" nodeColor="#7c3aed" />
      </ReactFlow>
    </div>
  );
}

