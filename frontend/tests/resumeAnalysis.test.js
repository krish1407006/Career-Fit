import assert from 'node:assert/strict'
import test from 'node:test'

import { analysisPayload, relevanceForJob } from '../src/lib/resumeAnalysis.js'

test('analysisPayload sends a job_id when a job is selected', () => {
  assert.deepEqual(analysisPayload(7), { job_id: 7 })
})

test('analysisPayload sends nothing for a general analysis', () => {
  assert.deepEqual(analysisPayload(undefined), {})
  assert.deepEqual(analysisPayload(null), {})
  assert.deepEqual(analysisPayload(''), {})
  assert.deepEqual(analysisPayload(0), {})
})

test('relevanceForJob returns the relevance when it belongs to the job', () => {
  const relevance = { job_id: 7, match_score: 67, matched_skills: ['python'] }
  assert.equal(relevanceForJob({ job_relevance: relevance }, 7), relevance)
})

test('relevanceForJob compares ids across string and number types', () => {
  const relevance = { job_id: 7, match_score: 67 }
  assert.equal(relevanceForJob({ job_relevance: relevance }, '7'), relevance)
})

test('relevanceForJob hides a relevance block from a different job', () => {
  const relevance = { job_id: 7, match_score: 67 }
  assert.equal(relevanceForJob({ job_relevance: relevance }, 8), null)
})

test('relevanceForJob is null for a general analysis', () => {
  assert.equal(relevanceForJob({ job_relevance: {} }, 7), null)
  assert.equal(relevanceForJob({}, 7), null)
  assert.equal(relevanceForJob(null, 7), null)
})
