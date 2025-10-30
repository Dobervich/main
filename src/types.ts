export interface DiceFace {
  symbol: string;
  label: string;
}

export interface DiceSet {
  id: string;
  name: string;
  color: string;
  faces: DiceFace[];
}

export interface RollResult {
  diceSetId: string;
  face: DiceFace;
}
