import { contextBridge } from 'electron';

contextBridge.exposeInMainWorld('desktop', Object.freeze({}));
