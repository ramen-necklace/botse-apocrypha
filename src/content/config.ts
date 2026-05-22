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
    id: z.number().int(),
    title: z.string(),
    date: z.coerce.date(),
    author: z.string(),
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
    telegram_url: z.string().url(),
    images: z.array(z.string()).default([]),
    cover: z.string().default(''),
    media_unavailable: z.boolean().default(false),
  }),
});

export const collections = { posts };
