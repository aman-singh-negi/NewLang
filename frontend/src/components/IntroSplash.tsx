import { useEffect, useState } from "react";

type Props = {
  onDone: () => void;
};

/**
 * Full-screen boot sequence: grid, scan line, kinetic title, progress rail.
 * Skips quickly when prefers-reduced-motion is set.
 */
export function IntroSplash({ onDone }: Props) {
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (reduce.matches) {
      onDone();
      return;
    }
    const tExit = window.setTimeout(() => setExiting(true), 2400);
    const tDone = window.setTimeout(() => onDone(), 3200);
    return () => {
      window.clearTimeout(tExit);
      window.clearTimeout(tDone);
    };
  }, [onDone]);

  return (
    <div
      className={`intro-splash${exiting ? " intro-splash--exit" : ""}`}
      aria-hidden="true"
    >
      <div className="intro-splash__noise" />
      <div className="intro-splash__grid" />
      <div className="intro-splash__scan" />
      <div className="intro-splash__ring" />
      <div className="intro-splash__content">
        <p className="intro-splash__eyebrow">SYSTEM ONLINE</p>
        <h1 className="intro-splash__title">
          <span className="intro-splash__bracket">⟨</span>
          <span className="intro-splash__word">language</span>
          <span className="intro-splash__bracket">⟩</span>
        </h1>
        <p className="intro-splash__tagline">LEX · PARSE · EMIT · RUN</p>
        <div className="intro-splash__rail" aria-hidden>
          <div className="intro-splash__rail-fill" />
        </div>
        <ul className="intro-splash__lines">
          <li>linking pipeline…</li>
          <li>binding editor surface…</li>
        </ul>
      </div>
    </div>
  );
}
