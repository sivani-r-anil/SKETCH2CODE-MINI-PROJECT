import { useEffect, useRef } from "react";
import { motion, useAnimationControls, useInView, useReducedMotion } from "framer-motion";

type PathGroupProps = { position: number; running: boolean };

// The supplied component's two mirrored groups and original curve equations.
// Stable durations avoid changing animation speed whenever React rerenders.
function createPaths(position: number) {
  return Array.from({ length: 36 }, (_, i) => ({
    id: i,
    d: `M-${380 - i * 5 * position} -${189 + i * 6}C-${
      380 - i * 5 * position
    } -${189 + i * 6} -${312 - i * 5 * position} ${216 - i * 6} ${
      152 - i * 5 * position
    } ${343 - i * 6}C${616 - i * 5 * position} ${470 - i * 6} ${
      684 - i * 5 * position
    } ${875 - i * 6} ${684 - i * 5 * position} ${875 - i * 6}`,
    width: 0.5 + i * 0.03,
    opacity: Math.min(0.1 + i * 0.03, 1),
    duration: 20 + ((i * 7) % 11),
  }));
}

const RIGHT_PATHS = createPaths(1);
const LEFT_PATHS = createPaths(-1);

function FloatingPaths({ position, running }: PathGroupProps) {
  const controls = useAnimationControls();
  const paths = position === 1 ? RIGHT_PATHS : LEFT_PATHS;

  useEffect(() => {
    if (running) {
      void controls.start((index: number) => ({
        pathLength: 1,
        opacity: [0.3, 0.6, 0.3],
        pathOffset: [0, 1, 0],
        transition: {
          duration: paths[index].duration,
          repeat: Infinity,
          ease: "linear",
        },
      }));
    } else {
      controls.stop();
    }
    return () => controls.stop();
  }, [controls, paths, running]);

  return (
    <svg
      viewBox="0 0 696 316"
      fill="none"
      focusable="false"
      aria-hidden="true"
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        color: position === 1 ? "var(--sc-coral, #ff8a7e)" : "var(--sc-amber, #ffbf75)",
      }}
    >
      {paths.map(path => (
        <motion.path
          key={path.id}
          custom={path.id}
          d={path.d}
          stroke="currentColor"
          strokeWidth={path.width}
          strokeOpacity={path.opacity}
          initial={{ pathLength: 0.3, pathOffset: 0, opacity: 0.4 }}
          animate={controls}
        />
      ))}
    </svg>
  );
}

export type BackgroundPathsProps = {
  /** Connected to the landing hero's existing Pause motion button. */
  paused?: boolean;
  className?: string;
};

/** Decorative background only: the existing hero owns its heading and CTA. */
export function BackgroundPaths({ paused = false, className = "" }: BackgroundPathsProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: "some" });
  const reducedMotion = useReducedMotion();
  const running = inView && !paused && reducedMotion === false;

  return (
    <div
      ref={ref}
      className={className}
      aria-hidden="true"
      style={{
        position: "absolute",
        inset: 0,
        zIndex: 0,
        overflow: "hidden",
        pointerEvents: "none",
        opacity: 0.2,
        maskImage: "radial-gradient(ellipse at 50% 45%, #000 15%, transparent 75%)",
        WebkitMaskImage: "radial-gradient(ellipse at 50% 45%, #000 15%, transparent 75%)",
      }}
    >
      <FloatingPaths position={1} running={running} />
      <FloatingPaths position={-1} running={running} />
    </div>
  );
}

export default BackgroundPaths;
