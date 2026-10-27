// SPDX-License-Identifier: Apache-2.0
// Concept model. All drawing coordinates are illustrative units, not hardware dimensions.
export const concept = {
  title: 'A personal data workspace',
  kind: 'Product direction / concept',
  link: { stage: 'Engineering prototype', depiction: 'Generic exposed development board; not a PCB1 layout or finished enclosure' },
  base: { stage: 'Data Core software prototype', depiction: 'An ordinary personal computer; not a dedicated EgoBase appliance' },
  integration: { complete: false, label: 'Link → Base integration is not yet complete.' },
  permission: 'Evidence and context support actions authorized by the user.',
  physicalMeaning: {
    board: 'Physical observations',
    computer: 'User-controlled storage and personal context',
    paper: 'Traceable evidence, source and time',
    selectedControl: 'User authorization before an action',
  },
};

export const plans = {
  mat: { x: -180, y: -62, w: 360, d: 188, r: 12 },
  laptop: { x: -61, y: -36, w: 146, d: 105, r: 5 },
  screen: { x: -61, y: -39, w: 146, d: 5, r: 2 },
  board: { x: -151, y: 20, w: 59, d: 74, r: 3 },
  tray: { x: 106, y: 10, w: 54, d: 76, r: 3 },
};

// Each row is a physical part, rather than a decorative texture stroke.
export const partGroups = {
  workspace: ['felt underside', 'work mat'],
  computer: ['lower chassis', 'keyboard deck', 'left hinge', 'right hinge', 'display housing', 'display bezel', 'display glass', 'keyboard recess', 'trackpad recess', 'trackpad', 'left speaker grille', 'right speaker grille', 'front opening notch'],
  keys: Array.from({ length: 30 }, (_, i) => `keycap ${String(i + 1).padStart(2, '0')}`),
  observations: ['board support', 'exposed circuit board', 'controller package', 'radio shield', 'antenna zone', 'USB connector', 'button body', 'button cap', 'sensor package', 'header rail one', 'header rail two', 'passive one', 'passive two'],
  evidence: ['tray base', 'tray rear wall', 'tray side wall', 'tray front lip', 'archive card', 'source receipt', 'receipt retaining clip'],
};

export const partCount = Object.values(partGroups).reduce((n, list) => n + list.length, 0);
if (partCount < 40 || partCount > 80) throw new Error('Figure must contain 40–80 purposeful physical parts');
