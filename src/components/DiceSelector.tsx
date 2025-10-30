import type { DiceSet } from '../types';
import './DiceSelector.css';

interface DiceSelectorProps {
  diceSets: DiceSet[];
  selectedDice: Set<string>;
  onToggle: (id: string) => void;
}

export const DiceSelector = ({ diceSets, selectedDice, onToggle }: DiceSelectorProps) => {
  return (
    <div className="dice-selector">
      <h2>Select Dice to Roll</h2>
      <div className="dice-options">
        {diceSets.map((diceSet) => (
          <button
            key={diceSet.id}
            className={`dice-option ${selectedDice.has(diceSet.id) ? 'selected' : ''}`}
            onClick={() => onToggle(diceSet.id)}
            style={{
              backgroundColor: selectedDice.has(diceSet.id) ? diceSet.color : '#f0f0f0',
              color: selectedDice.has(diceSet.id) ? 'white' : '#333',
            }}
          >
            <span className="dice-option-name">{diceSet.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
