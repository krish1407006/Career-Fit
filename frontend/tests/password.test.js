import assert from 'node:assert/strict'
import test from 'node:test'

import { MIN_PASSWORD_LENGTH, validatePasswordChange } from '../src/lib/password.js'

const valid = {
  current_password: 'Str0ngPass!23',
  new_password: 'BrandNewPass!9',
  confirm: 'BrandNewPass!9',
}

test('a well-formed change passes', () => {
  assert.equal(validatePasswordChange(valid), '')
})

test('the current password is required', () => {
  assert.match(validatePasswordChange({ ...valid, current_password: '' }), /current password/i)
})

test('a short new password is rejected', () => {
  const short = 'a'.repeat(MIN_PASSWORD_LENGTH - 1)
  assert.match(
    validatePasswordChange({ ...valid, new_password: short, confirm: short }),
    /at least/i,
  )
})

test('mismatched confirmation is rejected', () => {
  assert.match(validatePasswordChange({ ...valid, confirm: 'Different!9' }), /do not match/i)
})

test('reusing the current password is rejected', () => {
  assert.match(
    validatePasswordChange({ ...valid, new_password: valid.current_password, confirm: valid.current_password }),
    /differ/i,
  )
})
