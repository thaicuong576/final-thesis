import React from 'react';
import { ReasoningTimeline, type ReasoningTimelineProps } from './ReasoningTimeline';

export type AgentStageProps = ReasoningTimelineProps;

export const AgentStage: React.FC<AgentStageProps> = (props) => {
  return <ReasoningTimeline {...props} />;
};
