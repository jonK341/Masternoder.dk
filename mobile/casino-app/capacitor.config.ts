import type { CapacitorConfig } from '@capacitor/cli';

const productionUrl = 'https://masternoder.dk/casino/?app=casino-capacitor&tab=lobby';
const useLocal = process.env.CASINO_APP_LOCAL === '1';

const config: CapacitorConfig = {
  appId: 'dk.masternoder.casino',
  appName: 'MasterNoder Casino Social',
  webDir: 'www',
  server: useLocal
    ? {
        url: productionUrl,
        cleartext: false,
        androidScheme: 'https',
        allowNavigation: ['masternoder.dk', '*.masternoder.dk'],
      }
    : {
        url: productionUrl,
        cleartext: false,
        androidScheme: 'https',
        allowNavigation: ['masternoder.dk', '*.masternoder.dk'],
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
