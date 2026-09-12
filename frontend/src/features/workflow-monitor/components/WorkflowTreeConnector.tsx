interface WorkflowTreeConnectorProps {
  count: number;
}

export function WorkflowTreeConnector({ count }: WorkflowTreeConnectorProps) {
  return (
    <div className="flex flex-col items-center justify-center my-1 select-none" aria-hidden="true">
      {/* Top vertical stem from Orchestrator */}
      <div className="w-[2px] h-4 bg-[#b8d5f2]" />

      {/* Horizontal connector bar if more than 1 specialist */}
      {count > 1 && (
        <div className="w-3/4 max-w-xl h-[2px] bg-[#b8d5f2] relative flex justify-between">
          <div className="w-[2px] h-3 bg-[#b8d5f2] absolute -left-[1px] top-0" />
          {count === 3 && (
            <div className="w-[2px] h-3 bg-[#b8d5f2] absolute left-1/2 -translate-x-1/2 top-0" />
          )}
          <div className="w-[2px] h-3 bg-[#b8d5f2] absolute -right-[1px] top-0" />
        </div>
      )}

      {/* Bottom vertical spacer */}
      <div className="h-2" />
    </div>
  );
}
