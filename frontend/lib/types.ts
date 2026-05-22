export type CoordinatePoint = {
  x: number | null;
  y: number | null;
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
};

export type TrackingSequenceFrame = {
  frame: number;
  coordinates: CoordinateMap;
};

export type TrackingSequence = {
  event_frame: number;
  start_frame: number;
  end_frame: number;
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
};

export type AnalysisContext = {
  query: string;
  frame: number | null;
  event: EventContext | null;
  mode: "event" | "frame";
};

export type DataRenderPayload = {
  view: "PITCH_HOME";
  data: CoordinateMap;
  sequence: TrackingSequence | null;
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
