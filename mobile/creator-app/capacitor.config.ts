import type { CapacitorConfig } from '@capacitor/cli';

const productionUrl = 'https://masternoder.dk/creator/?app=creator-capacitor';

const config: CapacitorConfig = {
  appId: 'dk.masternoder.creator',
  appName: 'MasterNoder Super Encoder',
  webDir: 'www',
  server: {
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
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#1A1035',
    },
  },
};

export default config;
