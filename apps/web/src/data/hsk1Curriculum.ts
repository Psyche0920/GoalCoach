import { CurriculumConcept, TeachingCard, Exercise } from '../types.ts';
import { HSK1_CONCEPTS_EXPANDED } from './concepts.ts';
import { HSK1_TEACHING_CARDS_EXPANDED } from './cards.ts';
import { HSK1_EXERCISES_EXPANDED } from './exercises.ts';

export * from './curriculumThemes.ts';
export * from './concepts.ts';
export * from './cards.ts';
export * from './exercises.ts';

export const HSK1_CONCEPTS: CurriculumConcept[] = HSK1_CONCEPTS_EXPANDED;
export const HSK1_TEACHING_CARDS: TeachingCard[] = HSK1_TEACHING_CARDS_EXPANDED;
export const HSK1_EXERCISES: Exercise[] = HSK1_EXERCISES_EXPANDED;
