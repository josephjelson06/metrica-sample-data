"use client";

import { useEffect, useEffectEvent, useRef } from "react";

import type { CoordinateMap, SequenceEvent } from "@/lib/types";

type PitchCanvasProps = {
  coordinates: CoordinateMap | null;
  activeFrame?: number | null;
  sequenceEvents?: SequenceEvent[];
  framesPerSecond?: number;
  transitionMs?: number;
};

type PitchSize = {
  width: number;
  height: number;
};

type CanvasPoint = {
  x: number;
  y: number;
};

type EventVectorStyle = {
  color: string;
  width: number;
};

function getPlayerStyle(name: string) {
  if (name === "Ball") {
    return { fill: "#1d1d1d", radius: 5, label: "Ball" };
  }

  if (name.startsWith("Home_")) {
    return {
      fill: "#fbf4e4",
      radius: 8,
      label: name.replace("Home_", "").replace("Player", "P"),
    };
  }

  return {
    fill: "#ff8c60",
    radius: 8,
    label: name.replace("Away_", "").replace("Player", "P"),
  };
}

function drawMarkers(
  context: CanvasRenderingContext2D,
  coordinates: CoordinateMap,
  width: number,
  height: number,
) {
  for (const [name, point] of Object.entries(coordinates)) {
    if (point.x == null || point.y == null) {
      continue;
    }

    const { fill, radius, label } = getPlayerStyle(name);
    const x = point.x * width;
    const y = point.y * height;

    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fillStyle = fill;
    context.fill();
    context.lineWidth = 2;
    context.strokeStyle = "rgba(0, 0, 0, 0.15)";
    context.stroke();

    context.fillStyle = "rgba(18, 29, 18, 0.8)";
    context.font = "11px var(--font-ui), sans-serif";
    context.textAlign = "center";
    context.textBaseline = "bottom";
    context.fillText(label, x, y - radius - 4);
  }
}

function getEventVectorStyle(event: SequenceEvent): EventVectorStyle {
  const upperType = event.type.toUpperCase();
  if (upperType === "SHOT") {
    return { color: "#d75b1f", width: 3 };
  }
  if (upperType === "PASS") {
    return { color: "#2f7d45", width: 2.5 };
  }
  if (upperType === "SET PIECE") {
    return { color: "#1b365c", width: 2.5 };
  }
  return { color: "#425443", width: 2 };
}

function isRenderableSequenceEvent(event: SequenceEvent) {
  return (
    event.start_x != null &&
    event.start_y != null &&
    event.end_x != null &&
    event.end_y != null &&
    (event.start_x !== event.end_x || event.start_y !== event.end_y)
  );
}

function withAlpha(hexColor: string, alpha: number) {
  const sanitized = hexColor.replace("#", "");
  const normalized = sanitized.length === 3
    ? sanitized.split("").map((character) => character + character).join("")
    : sanitized;

  const red = Number.parseInt(normalized.slice(0, 2), 16);
  const green = Number.parseInt(normalized.slice(2, 4), 16);
  const blue = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function drawArrowHead(
  context: CanvasRenderingContext2D,
  tip: CanvasPoint,
  tail: CanvasPoint,
  color: string,
  opacity: number,
) {
  const angle = Math.atan2(tip.y - tail.y, tip.x - tail.x);
  const headLength = 10;

  context.beginPath();
  context.moveTo(tip.x, tip.y);
  context.lineTo(
    tip.x - (headLength * Math.cos(angle - Math.PI / 7)),
    tip.y - (headLength * Math.sin(angle - Math.PI / 7)),
  );
  context.lineTo(
    tip.x - (headLength * Math.cos(angle + Math.PI / 7)),
    tip.y - (headLength * Math.sin(angle + Math.PI / 7)),
  );
  context.closePath();
  context.fillStyle = withAlpha(color, opacity);
  context.fill();
}

function drawEventVectors(
  context: CanvasRenderingContext2D,
  events: SequenceEvent[],
  activeFrame: number,
  framesPerSecond: number,
  width: number,
  height: number,
) {
  const maxFrameDistance = Math.max(framesPerSecond * 2, 1);
  const nearbyEvents = events
    .filter(isRenderableSequenceEvent)
    .map((event) => ({
      event,
      frameDistance: Math.abs(activeFrame - event.frame),
    }))
    .filter(({ frameDistance }) => frameDistance <= maxFrameDistance)
    .sort((left, right) => left.frameDistance - right.frameDistance)
    .slice(0, 4);

  for (const { event, frameDistance } of nearbyEvents) {
    const startPoint = {
      x: (event.start_x as number) * width,
      y: (event.start_y as number) * height,
    };
    const endPoint = {
      x: (event.end_x as number) * width,
      y: (event.end_y as number) * height,
    };
    const proximity = 1 - (frameDistance / maxFrameDistance);
    const opacity = 0.18 + (proximity * 0.64);
    const { color, width: lineWidth } = getEventVectorStyle(event);

    context.beginPath();
    context.moveTo(startPoint.x, startPoint.y);
    context.lineTo(endPoint.x, endPoint.y);
    context.strokeStyle = withAlpha(color, opacity);
    context.lineWidth = lineWidth;
    context.setLineDash(event.type.toUpperCase() === "PASS" ? [] : [8, 6]);
    context.stroke();
    context.setLineDash([]);

    drawArrowHead(context, endPoint, startPoint, color, opacity);

    context.beginPath();
    context.arc(startPoint.x, startPoint.y, 4, 0, Math.PI * 2);
    context.fillStyle = withAlpha(color, opacity * 0.9);
    context.fill();
  }
}

function getTeamCanvasPoints(
  coordinates: CoordinateMap,
  width: number,
  height: number,
  teamPrefix: "Home_" | "Away_",
): CanvasPoint[] {
  return Object.entries(coordinates)
    .filter(([name, point]) => name.startsWith(teamPrefix) && point.x != null && point.y != null)
    .map(([, point]) => ({
      x: (point.x as number) * width,
      y: (point.y as number) * height,
    }));
}

function crossProduct(origin: CanvasPoint, a: CanvasPoint, b: CanvasPoint) {
  return ((a.x - origin.x) * (b.y - origin.y)) - ((a.y - origin.y) * (b.x - origin.x));
}

function getConvexHull(points: CanvasPoint[]) {
  if (points.length < 3) {
    return points;
  }

  const sortedPoints = [...points].sort((left, right) => {
    if (left.x === right.x) {
      return left.y - right.y;
    }
    return left.x - right.x;
  });

  const lowerHull: CanvasPoint[] = [];
  for (const point of sortedPoints) {
    while (lowerHull.length >= 2 && crossProduct(lowerHull[lowerHull.length - 2], lowerHull[lowerHull.length - 1], point) <= 0) {
      lowerHull.pop();
    }
    lowerHull.push(point);
  }

  const upperHull: CanvasPoint[] = [];
  for (let index = sortedPoints.length - 1; index >= 0; index -= 1) {
    const point = sortedPoints[index];
    while (upperHull.length >= 2 && crossProduct(upperHull[upperHull.length - 2], upperHull[upperHull.length - 1], point) <= 0) {
      upperHull.pop();
    }
    upperHull.push(point);
  }

  lowerHull.pop();
  upperHull.pop();
  return [...lowerHull, ...upperHull];
}

function drawTeamHull(
  context: CanvasRenderingContext2D,
  points: CanvasPoint[],
  fillStyle: string,
  strokeStyle: string,
) {
  const hull = getConvexHull(points);
  if (hull.length < 3) {
    return;
  }

  context.beginPath();
  context.moveTo(hull[0].x, hull[0].y);
  for (let index = 1; index < hull.length; index += 1) {
    context.lineTo(hull[index].x, hull[index].y);
  }
  context.closePath();
  context.fillStyle = fillStyle;
  context.strokeStyle = strokeStyle;
  context.lineWidth = 2;
  context.fill();
  context.stroke();
}

function drawPitchBase(context: CanvasRenderingContext2D, width: number, height: number) {
  const stripeWidth = width / 10;
  for (let index = 0; index < 10; index += 1) {
    context.fillStyle = index % 2 === 0 ? "#1f5a33" : "#2f7d45";
    context.fillRect(index * stripeWidth, 0, stripeWidth, height);
  }

  context.strokeStyle = "rgba(252, 253, 245, 0.96)";
  context.lineWidth = 2;
  context.strokeRect(width * 0.035, height * 0.035, width * 0.93, height * 0.93);

  context.beginPath();
  context.moveTo(width / 2, height * 0.035);
  context.lineTo(width / 2, height * 0.965);
  context.stroke();

  context.beginPath();
  context.arc(width / 2, height / 2, width * 0.09, 0, Math.PI * 2);
  context.stroke();

  context.beginPath();
  context.arc(width / 2, height / 2, 4, 0, Math.PI * 2);
  context.fillStyle = "rgba(252, 253, 245, 0.96)";
  context.fill();

  const boxTop = height * 0.21;
  const boxHeight = height * 0.58;
  const sixTop = height * 0.34;
  const sixHeight = height * 0.32;
  context.strokeRect(width * 0.035, boxTop, width * 0.12, boxHeight);
  context.strokeRect(width * 0.845, boxTop, width * 0.12, boxHeight);
  context.strokeRect(width * 0.035, sixTop, width * 0.05, sixHeight);
  context.strokeRect(width * 0.915, sixTop, width * 0.05, sixHeight);

  context.beginPath();
  context.arc(width * 0.14, height / 2, 4, 0, Math.PI * 2);
  context.arc(width * 0.86, height / 2, 4, 0, Math.PI * 2);
  context.fillStyle = "rgba(252, 253, 245, 0.96)";
  context.fill();
}

function lerpNumber(start: number, end: number, progress: number) {
  return start + ((end - start) * progress);
}

function interpolateCoordinates(
  fromCoordinates: CoordinateMap | null,
  toCoordinates: CoordinateMap,
  progress: number,
): CoordinateMap {
  if (!fromCoordinates) {
    return toCoordinates;
  }

  const blendedCoordinates: CoordinateMap = {};
  const entityNames = new Set([
    ...Object.keys(fromCoordinates),
    ...Object.keys(toCoordinates),
  ]);

  for (const entityName of entityNames) {
    const fromPoint = fromCoordinates[entityName];
    const toPoint = toCoordinates[entityName];

    if (!toPoint) {
      continue;
    }

    if (
      !fromPoint ||
      fromPoint.x == null ||
      fromPoint.y == null ||
      toPoint.x == null ||
      toPoint.y == null
    ) {
      blendedCoordinates[entityName] = { ...toPoint };
      continue;
    }

    blendedCoordinates[entityName] = {
      x: lerpNumber(fromPoint.x, toPoint.x, progress),
      y: lerpNumber(fromPoint.y, toPoint.y, progress),
    };
  }

  return blendedCoordinates;
}

export function PitchCanvas({
  coordinates,
  activeFrame = null,
  sequenceEvents = [],
  framesPerSecond = 25,
  transitionMs = 180,
}: PitchCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const sizeRef = useRef<PitchSize>({ width: 0, height: 0 });
  const previousCoordinatesRef = useRef<CoordinateMap | null>(null);
  const currentCoordinatesRef = useRef<CoordinateMap | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const animationTokenRef = useRef(0);

  const renderFrame = useEffectEvent((width: number, height: number, coordinates: CoordinateMap | null) => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);

    drawPitchBase(context, width, height);

    if (coordinates) {
      const homePoints = getTeamCanvasPoints(coordinates, width, height, "Home_");
      const awayPoints = getTeamCanvasPoints(coordinates, width, height, "Away_");

      drawTeamHull(
        context,
        homePoints,
        "rgba(251, 244, 228, 0.12)",
        "rgba(251, 244, 228, 0.68)",
      );
      drawTeamHull(
        context,
        awayPoints,
        "rgba(255, 140, 96, 0.11)",
        "rgba(255, 140, 96, 0.72)",
      );

      if (activeFrame != null && sequenceEvents.length > 0) {
        drawEventVectors(context, sequenceEvents, activeFrame, framesPerSecond, width, height);
      }

      drawMarkers(context, coordinates, width, height);
    }
  });

  const animateToCoordinates = useEffectEvent((nextCoordinates: CoordinateMap | null) => {
    if (!nextCoordinates) {
      currentCoordinatesRef.current = null;
      previousCoordinatesRef.current = null;
      const { width, height } = sizeRef.current;
      if (width > 0 && height > 0) {
        renderFrame(width, height, null);
      }
      return;
    }

    const { width, height } = sizeRef.current;
    if (width <= 0 || height <= 0) {
      currentCoordinatesRef.current = nextCoordinates;
      previousCoordinatesRef.current = nextCoordinates;
      return;
    }

    if (animationFrameRef.current != null) {
      window.cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }

    const previousCoordinates = currentCoordinatesRef.current;
    const durationMs = Math.max(20, transitionMs);

    if (!previousCoordinates) {
      currentCoordinatesRef.current = nextCoordinates;
      previousCoordinatesRef.current = nextCoordinates;
      renderFrame(width, height, nextCoordinates);
      return;
    }

    const animationToken = animationTokenRef.current + 1;
    animationTokenRef.current = animationToken;
    const animationStart = performance.now();

    const tick = (now: number) => {
      if (animationTokenRef.current !== animationToken) {
        return;
      }

      const elapsed = now - animationStart;
      const progress = Math.min(elapsed / durationMs, 1);
      const easedProgress = 1 - ((1 - progress) * (1 - progress));
      const blendedCoordinates = interpolateCoordinates(previousCoordinates, nextCoordinates, easedProgress);

      currentCoordinatesRef.current = blendedCoordinates;
      renderFrame(width, height, blendedCoordinates);

      if (progress < 1) {
        animationFrameRef.current = window.requestAnimationFrame(tick);
        return;
      }

      currentCoordinatesRef.current = nextCoordinates;
      previousCoordinatesRef.current = nextCoordinates;
      animationFrameRef.current = null;
    };

    animationFrameRef.current = window.requestAnimationFrame(tick);
  });

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) {
      return;
    }

    const redraw = () => {
      const width = wrapper.clientWidth;
      const height = Math.round((width * 68) / 105);
      sizeRef.current = { width, height };
      renderFrame(width, height, currentCoordinatesRef.current);
    };

    redraw();
    const observer = new ResizeObserver(redraw);
    observer.observe(wrapper);
    return () => {
      observer.disconnect();
      if (animationFrameRef.current != null) {
        window.cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };
  }, [renderFrame]);

  useEffect(() => {
    animateToCoordinates(coordinates);
  }, [animateToCoordinates, coordinates]);

  useEffect(() => {
    const { width, height } = sizeRef.current;
    if (width > 0 && height > 0) {
      renderFrame(width, height, currentCoordinatesRef.current);
    }
  }, [activeFrame, framesPerSecond, renderFrame, sequenceEvents]);

  return (
    <div
      ref={wrapperRef}
      style={{
        position: "relative",
        width: "100%",
        aspectRatio: "105 / 68",
        borderRadius: "28px",
        overflow: "hidden",
        boxShadow: "inset 0 0 0 2px rgba(255,255,255,0.12)",
      }}
    >
      <canvas ref={canvasRef} />
    </div>
  );
}
