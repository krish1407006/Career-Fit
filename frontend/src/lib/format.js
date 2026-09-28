export const plural = (count, singular, pluralForm = `${singular}s`) =>
  `${count} ${Number(count) === 1 ? singular : pluralForm}`