import { useState } from 'react';
import { Dice } from './components/Dice';
import { DiceSelector } from './components/DiceSelector';
import { diceSets } from './diceData';
import type { DiceFace } from './types';
import './App.css';

function App() {
  const [selectedDice, setSelectedDice] = useState<Set<string>>(new Set());
  const [rollResults, setRollResults] = useState<Map<string, DiceFace>>(new Map());
  const [isRolling, setIsRolling] = useState(false);

  const toggleDice = (id: string) => {
    setSelectedDice((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const rollDice = () => {
    if (selectedDice.size === 0 || isRolling) return;

    setIsRolling(true);

    // Simulate rolling animation
    setTimeout(() => {
      const newResults = new Map<string, DiceFace>();
      selectedDice.forEach((diceId) => {
        const diceSet = diceSets.find((d) => d.id === diceId);
        if (diceSet) {
          const randomIndex = Math.floor(Math.random() * diceSet.faces.length);
          newResults.set(diceId, diceSet.faces[randomIndex]);
        }
      });
      setRollResults(newResults);
      setIsRolling(false);
    }, 600);
  };

  const clearResults = () => {
    setRollResults(new Map());
    setSelectedDice(new Set());
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎲 Story Dice for TTRPGs</h1>
        <p>Roll dice to get creative inspiration for your tabletop RPG sessions!</p>
      </header>

      <main className="app-main">
        <DiceSelector
          diceSets={diceSets}
          selectedDice={selectedDice}
          onToggle={toggleDice}
        />

        <div className="roll-controls">
          <button
            className="roll-button"
            onClick={rollDice}
            disabled={selectedDice.size === 0 || isRolling}
          >
            {isRolling ? 'Rolling...' : 'Roll Dice'}
          </button>
          {rollResults.size > 0 && (
            <button className="clear-button" onClick={clearResults}>
              Clear Results
            </button>
          )}
        </div>

        {rollResults.size > 0 && (
          <div className="results">
            <h2>Results</h2>
            <div className="dice-grid">
              {Array.from(selectedDice).map((diceId) => {
                const diceSet = diceSets.find((d) => d.id === diceId);
                const face = rollResults.get(diceId);
                return diceSet ? (
                  <div key={diceId} className="dice-container">
                    <h3>{diceSet.name}</h3>
                    <Dice color={diceSet.color} face={face || null} isRolling={isRolling} />
                  </div>
                ) : null;
              })}
            </div>
          </div>
        )}

        {rollResults.size === 0 && selectedDice.size > 0 && (
          <div className="placeholder">
            <p>Click "Roll Dice" to get your story inspiration!</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
