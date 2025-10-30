import { useEffect, useState } from 'react';
import type { DiceFace } from '../types';
import './Dice.css';

interface DiceProps {
  color: string;
  face: DiceFace | null;
  isRolling: boolean;
}

export const Dice = ({ color, face, isRolling }: DiceProps) => {
  const [displayFace, setDisplayFace] = useState<DiceFace | null>(face);

  useEffect(() => {
    if (!isRolling && face) {
      setDisplayFace(face);
    }
  }, [isRolling, face]);

  return (
    <div
      className={`dice ${isRolling ? 'rolling' : ''}`}
      style={{ backgroundColor: color }}
    >
      {displayFace ? (
        <div className="dice-content">
          <div className="dice-symbol">{displayFace.symbol}</div>
          <div className="dice-label">{displayFace.label}</div>
        </div>
      ) : (
        <div className="dice-content">
          <div className="dice-symbol">🎲</div>
        </div>
      )}
    </div>
  );
};
