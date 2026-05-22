import { defineCollection, z } from 'astro:content';

export const CATEGORIES = [
  'Новости',
  'Текстовые обзоры',
  'Видеообзоры',
  'Летсплеи',
  'Обучалки и туториалы',
  'Гайды по классам',
  'Инструменты',
  'Лор',
  'Файлы / принтабли',
  'Цены и лоты',
  'Прочее',
] as const;

export type Category = (typeof CATEGORIES)[number];

const posts = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().default(''),
    date: z.coerce.date(),
    category: z.enum(CATEGORIES),
    tags: z.array(z.string()).default([]),
    sources: z
      .array(
        z.object({
          label: z.string(),
          url: z.string().url(),
        })
      )
      .default([]),
    telegram_url: z.string().url().optional(),
    images: z.array(z.string()).default([]),
    cover: z.string().default(''),
  }),
});

export const collections = { posts };
