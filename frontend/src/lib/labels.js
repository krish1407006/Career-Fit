/**
 * Display labels shared by several screens.
 *
 * These live outside the component files because a component module that also
 * exports plain values only half-reloads during development, which is a
 * confusing way to lose a change while editing.
 */

export const STATUS_LABELS = {
  applied: 'Applied',
  shortlisted: 'Shortlisted',
  interview: 'Interview',
  selected: 'Selected',
  rejected: 'Rejected',
  active: 'Active',
  closed: 'Closed',
}

const CATEGORY_LABELS = {
  python: 'Python',
  javascript: 'JavaScript',
  django: 'Django',
  sql: 'SQL',
  dbms: 'DBMS',
  operating_systems: 'Operating Systems',
  computer_networks: 'Computer Networks',
  data_structures: 'Data Structures',
  aptitude: 'Aptitude',
  logical_reasoning: 'Logical Reasoning',
}

/** Human-readable name for a quiz category, falling back to the raw value. */
export const categoryLabel = (cat) => CATEGORY_LABELS[cat] || cat
