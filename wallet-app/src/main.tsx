import { render } from 'preact';
import { App } from './App';
import './styles/wallet-sharpened.css';

const root = document.getElementById('wallet-root');
if (root) {
  render(<App />, root);
}
