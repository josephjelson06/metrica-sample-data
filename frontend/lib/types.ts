export type CoordinatePoint = {
  x: number | null;
  y: number | null;
  vx?: number | null;
  vy?: number | null;
  speed?: number | null;
};

export type CoordinateMap = Record<string, CoordinatePoint>;

export type SequenceEvent = {
  team: string | null;
  type: string;
  subtype: string | null;
  period: number;
  start_frame: number;
  start_time_s: number | null;
  end_frame: number | null;
  end_time_s: number | null;
  from_player: string | null;
  to_player: string | null;
  start_x: number | null;
  start_y: number | null;
  end_x: number | null;
  end_y: number | null;
  frame: number;
  phase?: string | null;
};

export type TrackingSequenceFrame = {
  frame: number;
  coordinates: CoordinateMap;
};

export type TrackingSequence = {
  event_frame: number;
  start_frame: number;
  end_frame: number;
  sequence_type?: "event" | "buildup" | "transition" | string | null;
  frame_step: number;
  frames_per_second: number;
  frames: TrackingSequenceFrame[];
  events: SequenceEvent[];
};

export type EventContext = {
  team: string | null;
  type: string;
  subtype: string | null;
  period: number;
  start_frame: number;
  start_time_s: number | null;
  end_frame: number | null;
  end_time_s: number | null;
  from_player: string | null;
  to_player: string | null;
  start_x: number | null;
  start_y: number | null;
  end_x: number | null;
  end_y: number | null;
  occurrence: number;
  order: string;
  relation: string;
  anchor_frame: number | null;
  frame: number;
  phase?: string | null;
  pitch_zone?: string | null;
  period_filter?: number | null;
  phase_filter?: string | null;
};

export type MetricValue = number | string | null | MetricMap;

export interface MetricMap {
  [key: string]: MetricValue;
}

export type AggregateFilters = {
  event_type?: string | null;
  team?: string | null;
  subtype_contains?: string | null;
  relation?: string | null;
  anchor_frame?: number | null;
  period?: number | null;
  pitch_zone?: string | null;
  phase?: string | null;
};

export type AggregateContext = {
  query_type: "count" | "list";
  count: number;
  events?: SequenceEvent[];
  filters: AggregateFilters;
};

export type SequenceSegments = {
  anchor_frame: number;
  team: string | null;
  before_events_count: number;
  anchor_events_count: number;
  after_events_count: number;
  before_counts_by_type: Record<string, number>;
  anchor_counts_by_type: Record<string, number>;
  after_counts_by_type: Record<string, number>;
  immediate_pre_event: Record<string, unknown> | null;
  immediate_post_event: Record<string, unknown> | null;
  same_team_before_count?: number;
  same_team_anchor_count?: number;
  same_team_after_count?: number;
  opponent_before_count?: number;
  opponent_after_count?: number;
  same_team_before_counts_by_type?: Record<string, number>;
  same_team_after_counts_by_type?: Record<string, number>;
  continuation_count_before_opponent?: number;
  continuation_counts_by_type?: Record<string, number>;
  last_same_team_before_event?: Record<string, unknown> | null;
  first_same_team_after_event?: Record<string, unknown> | null;
  first_opponent_after_event?: Record<string, unknown> | null;
  first_same_team_shot_after?: Record<string, unknown> | null;
  last_same_team_shot_before?: Record<string, unknown> | null;
};

export type TransitionSummary = {
  team: string;
  anchor_frame: number;
  event_count: number;
  counts_by_type: Record<string, number>;
  window_seconds: number;
  first_shot_seconds_from_anchor: number | null;
  last_event_type: string | null;
};

export type SequenceComparison = {
  left_segments: SequenceSegments;
  right_segments: SequenceSegments;
  deltas: Record<string, number | null>;
};

export type PassNetworkNode = {
  x: number | null;
  y: number | null;
  passes_made: number;
  passes_received: number;
};

export type PassNetworkEdge = {
  from: string;
  to: string;
  pass_count: number;
};

export type PassNetworkData = {
  team: string;
  period: number | null;
  start_minute?: number | null;
  end_minute?: number | null;
  total_passes?: number;
  nodes: Record<string, PassNetworkNode>;
  edges: PassNetworkEdge[];
};

export type PlayerPhysicality = {
  total_distance: number;
  hsr_distance: number;
  sprint_distance: number;
};

export type PhysicalityData = {
  period: number;
  team: string;
  players: Record<string, PlayerPhysicality>;
};

export type PlayerSonar = {
  x: number;
  y: number;
  passes: number;
  buckets: number[];
  bucket_dist: number[];
};

export type PassSonarsData = {
  team: string;
  period: number | null;
  sonars: Record<string, PlayerSonar>;
};

export type AutoInsight = {
  start_frame: number;
  end_frame: number;
  period: number;
  start_time: number;
  end_time: number;
};

export type MarkingPair = {
  attacker: string;
  defender: string;
  distance: number;
};

export type SetPieceAnalysis = {
  event: any;
  frame: number;
  marking_pairs: MarkingPair[];
  coordinates: any;
};

export type ComparisonContext = {
  team: string | null;
  left_label: string;
  right_label: string;
  left_frame: number;
  right_frame: number;
  left_event: EventContext | null;
  right_event: EventContext | null;
  metrics_comparison: MetricMap;
  sequence_comparison?: SequenceComparison | null;
  comparison_kind?: "moment" | "buildup_sequence" | "transition_sequence" | string | null;
};

// ── Orientation types ─────────────────────────────────────────────────────────

export type PlayerLineupInfo = {
  team: string;
  role: string;
  avg_x: number;
  avg_y: number;
  in_period_1: boolean;
  in_period_2: boolean;
  approx_start_min: number | null;
  approx_end_min: number | null;
};

export type SubstitutionEvent = {
  player: string;
  team: string;
  role: string;
  event: "subbed_on" | "subbed_off";
  approx_minute: number | null;
  period: number;
};

export type FormationEstimate = {
  team: string;
  period: number | null;
  formation: string;
  avg_positions: { role: string; avg_x: number; avg_y: number }[];
};

export type OrientationData = {
  lineup: { team: string | null; lineup: Record<string, PlayerLineupInfo> };
  substitutions: SubstitutionEvent[];
  formations: { Home: FormationEstimate; Away: FormationEstimate };
  team: string | null;
  period: number | null;
};

// ── Conversation types ────────────────────────────────────────────────────────

export type SuggestedFollowUp = {
  label: string;
  query: string;
};

export type ConversationTurn = {
  turn: number;
  query: string;
  mode: string | null;
  summary: string;
};

export type ConversationContext = {
  current_team: string | null;
  current_period: number | null;
  current_mode: string | null;
  start_minute: number | null;
  end_minute: number | null;
  turn_count: number;
  history: ConversationTurn[];
};

export type AnalysisMode =
  | "aggregate"
  | "frame"
  | "event"
  | "sequence_event"
  | "comparison"
  | "buildup"
  | "transition"
  | "pass_network"
  | "pass_sonars"
  | "physicality"
  | "synthesis"
  | "auto_insights"
  | "set_piece"
  | "orientation";

export type AnalysisContext = {
  query: string;
  frame: number | null;
  event: EventContext | null;
  anchor_event?: EventContext | null;
  metrics?: MetricMap | null;
  aggregate?: AggregateContext | null;
  comparison?: ComparisonContext | null;
  sequence_segments?: SequenceSegments | null;
  transition_summary?: TransitionSummary | null;
  mode: AnalysisMode;
  period?: number | null;
  explanation?: string | null;
  report?: string | null;
  response_contract_version?: string;
  query_family?: string;
  has_event?: boolean;
  has_anchor_event?: boolean;
  has_metrics?: boolean;
  has_sequence?: boolean;
  sequence_type?: string | null;
  has_aggregate?: boolean;
  has_comparison?: boolean;
  comparison_kind?: string | null;
  has_pass_network?: boolean;
  has_pass_sonars?: boolean;
  has_physicality?: boolean;
  has_auto_insights?: boolean;
  has_set_piece_analysis?: boolean;
  has_report?: boolean;
  has_explanation?: boolean;
};

export type DataRenderPayload = {
  view: "PITCH_HOME";
  data: CoordinateMap;
  sequence: TrackingSequence | null;
  pass_network?: PassNetworkData | null;
  pass_sonars?: PassSonarsData | null;
  physicality?: PhysicalityData | null;
  auto_insights?: AutoInsight[] | null;
  set_piece_analysis?: SetPieceAnalysis | null;
  orientation?: OrientationData | null;
  follow_up_suggestions?: SuggestedFollowUp[] | null;
  conversation_context?: ConversationContext | null;
  context: AnalysisContext;
};

export type DataRenderMessage = {
  type: "DATA_RENDER";
  payload: DataRenderPayload;
};

export type ErrorMessage = {
  type: "ERROR";
  payload: {
    message: string;
  };
};

export type ServerMessage = DataRenderMessage | ErrorMessage;

export type ConnectionStatus = "idle" | "connecting" | "connected" | "error";
