export type RulesetMode = "original" | "simple";

export interface HexPayload {
  q: number;
  r: number;
}

export interface TilePayload {
  coord: HexPayload;
  terrain: string;
  move_cost: number;
  passable: boolean;
}

export interface UnitPayload {
  unit_id: string;
  side: "red" | "blue";
  position: HexPayload;
  move_allowance: number;
  exerts_zoc: boolean;
}

export interface GameStatePayload {
  ruleset: RulesetMode;
  tiles: TilePayload[];
  active_side: "red" | "blue";
  units: UnitPayload[];
}

export interface RulesetsPayload {
  rulesets: RulesetMode[];
}

export interface ActionResponsePayload {
  ok: boolean;
  reason: string;
  state: GameStatePayload;
}
