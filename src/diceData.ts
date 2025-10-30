import type { DiceSet } from './types';

export const diceSets: DiceSet[] = [
  {
    id: 'character',
    name: 'Character',
    color: '#e74c3c',
    faces: [
      { symbol: '👑', label: 'Royalty' },
      { symbol: '⚔️', label: 'Warrior' },
      { symbol: '🧙', label: 'Wizard' },
      { symbol: '🗡️', label: 'Rogue' },
      { symbol: '🛡️', label: 'Knight' },
      { symbol: '🏹', label: 'Ranger' },
    ],
  },
  {
    id: 'action',
    name: 'Action',
    color: '#3498db',
    faces: [
      { symbol: '⚡', label: 'Attack' },
      { symbol: '🛡️', label: 'Defend' },
      { symbol: '🏃', label: 'Escape' },
      { symbol: '🔍', label: 'Search' },
      { symbol: '💬', label: 'Negotiate' },
      { symbol: '🎭', label: 'Deceive' },
    ],
  },
  {
    id: 'object',
    name: 'Object',
    color: '#f39c12',
    faces: [
      { symbol: '🗝️', label: 'Key' },
      { symbol: '📜', label: 'Scroll' },
      { symbol: '💎', label: 'Gem' },
      { symbol: '⚗️', label: 'Potion' },
      { symbol: '📖', label: 'Book' },
      { symbol: '🔮', label: 'Crystal' },
    ],
  },
  {
    id: 'setting',
    name: 'Setting',
    color: '#27ae60',
    faces: [
      { symbol: '🏰', label: 'Castle' },
      { symbol: '🌲', label: 'Forest' },
      { symbol: '⛰️', label: 'Mountain' },
      { symbol: '🏛️', label: 'Temple' },
      { symbol: '🏚️', label: 'Ruins' },
      { symbol: '🌊', label: 'Ocean' },
    ],
  },
  {
    id: 'emotion',
    name: 'Emotion',
    color: '#9b59b6',
    faces: [
      { symbol: '😡', label: 'Anger' },
      { symbol: '😨', label: 'Fear' },
      { symbol: '😊', label: 'Joy' },
      { symbol: '😢', label: 'Sadness' },
      { symbol: '😲', label: 'Surprise' },
      { symbol: '🤔', label: 'Confusion' },
    ],
  },
  {
    id: 'twist',
    name: 'Plot Twist',
    color: '#e91e63',
    faces: [
      { symbol: '🔄', label: 'Reversal' },
      { symbol: '👥', label: 'Ally appears' },
      { symbol: '😈', label: 'Betrayal' },
      { symbol: '💫', label: 'Magic surge' },
      { symbol: '⏰', label: 'Time limit' },
      { symbol: '❓', label: 'Mystery' },
    ],
  },
];
