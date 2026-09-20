import { HeroComposer, type HeroComposerProps } from './HeroComposer';

export type HeroWorkspaceProps = HeroComposerProps;

/**
 * HeroWorkspace component representing Screen 1 Hero Composer for analytical question input.
 * Aliased for architectural consistency across specifications.
 */
export function HeroWorkspace(props: HeroWorkspaceProps) {
  return <HeroComposer {...props} />;
}

export { HeroComposer };
