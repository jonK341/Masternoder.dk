import type { CapacitorConfig } from '@capacitor/cli';

const podcastRemoteUrl =
  process.env.PODCAST_APP_URL || 'https://YOUR_HOST/podcast/?app=podcast-capacitor&tab=episodes';
const useLocal = process.env.PODCAST_APP_LOCAL === '1';

const config: CapacitorConfig = {
  appId: 'dk.masternoder.podcast',
  appName: 'MasterNoder Podcast',
  webDir: 'www',
  server: useLocal
    ? {
        url: podcastRemoteUrl,
        cleartext: false,
        androidScheme: 'https',
        allowNavigation: ['YOUR_HOST', '*.YOUR_HOST'],
      }
    : {
        url: podcastRemoteUrl,
        cleartext: false,
        androidScheme: 'https',
        allowNavigation: ['YOUR_HOST', '*.YOUR_HOST'],
      },
  android: {
    allowMixedContent: false,
    backgroundColor: '#0A0E14',
  },
  ios: {
    backgroundColor: '#0A0E14',
    contentInset: 'automatic',
    scheme: 'masternoder',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      launchAutoHide: true,
      backgroundColor: '#0A0E14',
      androidSplashResourceName: 'splash',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#1A1035',
    },
  },
};

export default config;
