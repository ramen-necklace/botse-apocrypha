import { CATEGORIES, type Category } from '../content/config';

export { CATEGORIES };
export type { Category };

export function categorySlug(cat: Category): string {
  return SLUGS[cat];
}

export function categoryBySlug(slug: string): Category | undefined {
  return (Object.entries(SLUGS) as [Category, string][]).find(
    ([, s]) => s === slug
  )?.[0];
}

const SLUGS: Record<Category, string> = {
  Новости: 'novosti',
  'Текстовые обзоры': 'tekstovye-obzory',
  Видеообзоры: 'videoobzory',
  Летсплеи: 'letsplei',
  'Обучалки и туториалы': 'obuchalki',
  'Гайды по классам': 'gaydy-po-klassam',
  Инструменты: 'instrumenty',
  Лор: 'lor',
  'Файлы / принтабли': 'fayly-printabli',
  'Цены и лоты': 'tseny-i-loty',
  Прочее: 'prochee',
};
