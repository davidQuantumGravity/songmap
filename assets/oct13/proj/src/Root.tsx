import React from 'react';
import { Composition } from 'remotion';
import '@fontsource/space-grotesk/500.css';
import '@fontsource/space-grotesk/600.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/700.css';
import { VideoA } from './VideoA';
import { VideoB } from './VideoB';
import { VideoC } from './VideoC';

export const Root: React.FC = () => (
  <>
    <Composition id="WeekBench" component={VideoA} durationInFrames={4530} fps={30} width={1920} height={1080} />
    <Composition id="WeekSwarm" component={VideoB} durationInFrames={3690} fps={30} width={1920} height={1080} />
    <Composition id="DeepDive" component={VideoC} durationInFrames={9090} fps={30} width={1920} height={1080} />
  </>
);
