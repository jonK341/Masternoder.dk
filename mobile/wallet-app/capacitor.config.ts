import type { CapacitorConfig } from '@capacitor/cli';

const walletUrl = '[REDACTED]/wallets/?app=wallet-capacitor&tab=overview';
const useLocal = process.env.WALLET_APP_LOCAL === '1';

const config: CapacitorConfig = {
  appId: 'dk.masternoder.wallet',
  appName: 'MN2 Wallet',
  webDir: 'www',
  server: useLocal
    ? {
        url: walletUrl,
        cleartext: false,
        androidScheme: 'https',
        allowNavigation: ['[REDACTED]', '*.[REDACTED]'],
      }
    : {
        url: walletUrl,
        cleartext: false,
        androidScheme: 'https',
        allowNavigation: ['[REDACTED]', '*.[REDACTED]'],
      },
  android: {
    allowMixedContent: false,
    backgroundColor: '#080b10',
  },
  ios: {
    backgroundColor: '#080b10',
    contentInset: 'automatic',
    scheme: 'masternoder',
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1200,
      launchAutoHide: true,
      backgroundColor: '#080b10',
      androidSplashResourceName: 'splash',
      showSpinner: false,
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#080b10',
    },
  },
};

export default config;
