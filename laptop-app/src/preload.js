'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// Minimal, explicit bridge. The renderer can only call these named channels;
// it never touches Node, the filesystem, or the admin key directly.
contextBridge.exposeInMainWorld('pdc', {
  config: {
    get: () => ipcRenderer.invoke('config:get'),
    setServerUrl: (url) => ipcRenderer.invoke('config:setServerUrl', url),
    setDaemon: (opts) => ipcRenderer.invoke('config:setDaemon', opts),
  },
  key: {
    set: (k) => ipcRenderer.invoke('key:set', k),
    clear: () => ipcRenderer.invoke('key:clear'),
  },
  api: {
    status: () => ipcRenderer.invoke('api:status'),
    instances: () => ipcRenderer.invoke('api:instances'),
    controlOverview: () => ipcRenderer.invoke('api:controlOverview'),
    killSwitch: (on) => ipcRenderer.invoke('api:killSwitch', on),
    runAll: (force) => ipcRenderer.invoke('api:runAll', force),
    payoutStatus: () => ipcRenderer.invoke('api:payoutStatus'),
    payoutSweep: (minUsd) => ipcRenderer.invoke('api:payoutSweep', minUsd),
  },
  daemon: {
    status: () => ipcRenderer.invoke('daemon:status'),
    start: (opts) => ipcRenderer.invoke('daemon:start', opts),
    stop: () => ipcRenderer.invoke('daemon:stop'),
    onLog: (cb) => ipcRenderer.on('daemon:log', (_e, line) => cb(line)),
    onExit: (cb) => ipcRenderer.on('daemon:exit', (_e, code) => cb(code)),
  },
});
