import { create } from 'zustand';
import { createTaskSlice, type TaskSlice } from './slices/taskSlice';
import { createCreatorSlice, type CreatorSlice } from './slices/creatorSlice';
import { createAssetSlice, type AssetSlice } from './slices/assetSlice';
import { createSettingsSlice, type SettingsSlice } from './slices/settingsSlice';
import { createWsSlice, type WsSlice } from './slices/wsSlice';

export type StoreState = TaskSlice & CreatorSlice & AssetSlice & SettingsSlice & WsSlice;

export const useStore = create<StoreState>()((...a) => ({
  ...createTaskSlice(...a),
  ...createCreatorSlice(...a),
  ...createAssetSlice(...a),
  ...createSettingsSlice(...a),
  ...createWsSlice(...a),
}));
