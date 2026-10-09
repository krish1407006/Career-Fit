import assert from 'node:assert/strict'
import test from 'node:test'

import { coverageBucket } from '../src/lib/skillGap.js'

test('coverageBucket marks a strong match as ok', () => {
  assert.equal(coverageBucket(70), 'ok')
  assert.equal(coverageBucket(100), 'ok')
})

test('coverageBucket marks a partial match as warn', () => {
  assert.equal(coverageBucket(40), 'warn')
  assert.equal(coverageBucket(69), 'warn')
})

test('coverageBucket marks a weak match as bad', () => {
  assert.equal(coverageBucket(0), 'bad')
  assert.equal(coverageBucket(39), 'bad')
})

test('coverageBucket treats missing or malformed scores as zero', () => {
  assert.equal(coverageBucket(undefined), 'bad')
  assert.equal(coverageBucket(null), 'bad')
  assert.equal(coverageBucket('not-a-number'), 'bad')
})

test('coverageBucket accepts numeric strings from JSON', () => {
  assert.equal(coverageBucket('66.7'), 'warn')
  assert.equal(coverageBucket('80'), 'ok')
})
