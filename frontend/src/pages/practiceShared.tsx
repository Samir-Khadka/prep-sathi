/* Shared bits for the Phase 2 practice runners: countdown timer,
   band label, question inputs and the results view. */

import { useEffect, useRef, useState } from "react";
import {
  BAND_LABEL,
  type PracticeQuestion,
  type QuestionResult,
  type SubmitResult,
} from "../api";

export function formatTime(totalSeconds: number): string {
  const s = Math.max(0, totalSeconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

export function BandLabel() {
  return <span className="band-label">{BAND_LABEL}</span>;
}

/** Countdown in seconds. Calls onExpire once when it reaches 0. */
export function useCountdown(
  startSeconds: number | null,
  active: boolean,
  onExpire: () => void,
) {
  const [remaining, setRemaining] = useState(startSeconds);
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;
  const expiredRef = useRef(false);

  useEffect(() => {
    setRemaining(startSeconds);
    expiredRef.current = false;
  }, [startSeconds]);

  useEffect(() => {
    if (!active || startSeconds === null) return;
    const timer = window.setInterval(() => {
      setRemaining((prev) => {
        if (prev === null) return prev;
        if (prev <= 1) {
          window.clearInterval(timer);
          if (!expiredRef.current) {
            expiredRef.current = true;
            onExpireRef.current();
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [active, startSeconds]);

  return remaining;
}

export type AnswerValue = string | number | undefined;

export function QuestionInput({
  question,
  value,
  onChange,
  disabled,
}: {
  question: PracticeQuestion;
  value: AnswerValue;
  onChange: (value: string | number) => void;
  disabled?: boolean;
}) {
  if (question.type === "mcq" && question.options) {
    return (
      <div className="options">
        {question.options.map((opt, i) => (
          <label key={i} className="option">
            <input
              type="radio"
              name={`q-${question.no}`}
              checked={value === i}
              disabled={disabled}
              onChange={() => onChange(i)}
            />{" "}
            {opt}
          </label>
        ))}
      </div>
    );
  }
  if (question.type === "tfng") {
    return (
      <div className="options">
        {["TRUE", "FALSE", "NOT GIVEN"].map((opt) => (
          <label key={opt} className="option">
            <input
              type="radio"
              name={`q-${question.no}`}
              checked={value === opt}
              disabled={disabled}
              onChange={() => onChange(opt)}
            />{" "}
            {opt}
          </label>
        ))}
      </div>
    );
  }
  return (
    <input
      type="text"
      value={typeof value === "string" ? value : ""}
      disabled={disabled}
      placeholder="Type your answer"
      onChange={(e) => onChange(e.target.value)}
      aria-label={`Answer to question ${question.no}`}
    />
  );
}

function formatAnswer(v: string | number | null): string {
  if (v === null || v === undefined) return "— no answer —";
  return String(v);
}

export function ResultsView({
  result,
  title,
}: {
  result: SubmitResult;
  title: string;
}) {
  return (
    <section className="card">
      <h1>{title} — results</h1>
      <div className="stat-row">
        <div className="stat">
          <div className="num">
            {result.score_raw} / {result.results.length}
          </div>
          <div className="lbl">Correct answers</div>
        </div>
        <div className="stat">
          <div className="num">
            Band {result.band_estimate.toFixed(1)}
          </div>
          <div className="lbl">
            <BandLabel />
          </div>
        </div>
        <div className="stat">
          <div className="num">{formatTime(result.duration_seconds)}</div>
          <div className="lbl">Time taken</div>
        </div>
      </div>
      {result.overtime && (
        <p className="notice">
          You finished after the time limit — the band above is still your
          practice estimate for the answers you gave.
        </p>
      )}
      <h2>Question by question</h2>
      <ul className="clean">
        {result.results.map((r: QuestionResult) => (
          <li
            key={r.no}
            className={r.correct ? "result-correct" : "result-wrong"}
          >
            <p>
              <strong>Q{r.no}</strong>{" "}
              {r.correct ? (
                <span className="badge">Correct</span>
              ) : (
                <span className="badge gold">Not correct</span>
              )}
            </p>
            <p>
              Your answer: <strong>{formatAnswer(r.your_answer)}</strong>
            </p>
            {!r.correct && (
              <p>
                Correct answer:{" "}
                <strong>{formatAnswer(r.correct_answer)}</strong>
              </p>
            )}
            <p>{r.explanation}</p>
            <p className="evidence">“{r.evidence}”</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
