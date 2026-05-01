import type { StateCreator } from 'zustand';
import type { Creator } from '@/lib/api';
import { getCreators } from '@/lib/api';
import type { StoreState } from '../useStore';

const CREATORS_CACHE_TTL = 30_000;

export interface CreatorSlice {
  creators: Creator[];
  creatorsLoadedAt: number;
  fetchCreators: (force?: boolean) => Promise<Creator[]>;
  _fetchingCreators: Promise<Creator[]> | null;
}

export const createCreatorSlice: StateCreator<StoreState, [], [], CreatorSlice> = (set, get) => ({
  creators: [],
  creatorsLoadedAt: 0,
  _fetchingCreators: null,
  fetchCreators: async (force = false) => {
    const { creatorsLoadedAt, creators, _fetchingCreators } = get();
    if (!force && creatorsLoadedAt > 0 && Date.now() - creatorsLoadedAt < CREATORS_CACHE_TTL) {
      return creators;
    }
    if (_fetchingCreators) return _fetchingCreators;
    const promise = (async () => {
      try {
        const data = await getCreators();
        set({ creators: data, creatorsLoadedAt: Date.now(), _fetchingCreators: null });
        return data;
      } catch (error) {
        console.error('Failed to fetch creators', error);
        set({ _fetchingCreators: null });
        return get().creators;
      }
    })();
    set({ _fetchingCreators: promise });
    return promise;
  },
});
