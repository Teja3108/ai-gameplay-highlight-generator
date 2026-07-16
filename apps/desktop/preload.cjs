const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('desktop', Object.freeze({}));
