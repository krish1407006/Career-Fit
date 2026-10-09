/**
 * Presentation helpers for the skill-gap screens.
 *
 * The backend owns the matching maths (apps/jobs/matching.py); the frontend
 * only maps the returned coverage/score onto a display class so the same
 * thresholds are not re-declared in more than one component.
 */

export const coverageBucket = (score) => {
  const value = Number(score) || 0
  if (value >= 70) return 'ok'
  if (value >= 40) return 'warn'
  return 'bad'
}
