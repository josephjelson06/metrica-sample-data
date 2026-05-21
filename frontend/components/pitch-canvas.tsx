"use client";

import { useEffect, useEffectEvent, useRef } from "react";

import type { CoordinateMap, DataRenderPayload } from "@/lib/types";

type PitchCanvasProps = {
  payload: DataRenderPayload | null;
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

export function PitchCanvas({ payload }: PitchCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const drawScene = useEffectEvent((width: number, height: number) => {
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

    if (payload) {
      drawMarkers(context, payload.data, width, height);
    }
  });

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) {
      return;
    }

    const redraw = () => {
      const width = wrapper.clientWidth;
      const height = Math.round((width * 68) / 105);
      drawScene(width, height);
    };

    redraw();
    const observer = new ResizeObserver(redraw);
    observer.observe(wrapper);
    return () => observer.disconnect();
  }, [drawScene, payload]);

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
