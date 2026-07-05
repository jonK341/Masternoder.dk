/**
 * Atomic Calculator Integration - Hell & Money Satan Edition
 * Advanced atomic calculations for financial/monetary systems
 */

class AtomicCalculatorIntegration {
    constructor() {
        this.baseURL = '/api/atomic-calculator';
        this.userId = this.getUserId();
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        return 'default_user';
    }

    /**
     * Atomic calculate - Hell & Money Satan
     */
    async atomicCalculate(baseValue, calculationType = 'hell_money', params = {}) {
        try {
            const response = await fetch(`${this.baseURL}/calculate`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    base_value: baseValue,
                    calculation_type: calculationType,
                    params: params
                })
            });
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Calculate financial metrics
     */
    async calculateFinancialMetrics(baseValue, metrics = null) {
        try {
            const response = await fetch(`${this.baseURL}/financial-metrics`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    base_value: baseValue,
                    metrics: metrics || ['hell_money', 'satan_compound', 'atomic_interest']
                })
            });
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Calculate Money Satan returns
     */
    async calculateMoneySatanReturns(investment, timePeriods = 1) {
        try {
            const response = await fetch(`${this.baseURL}/money-satan-returns`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    investment: investment,
                    time_periods: timePeriods
                })
            });
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }
}

// Global instance
window.atomicCalculator = new AtomicCalculatorIntegration();

/**
 * Atomic Calculate Hell Money - Main function
 */
async function atomicCalculateHellMoney() {
    const baseValue = parseFloat(prompt('Enter base value for atomic calculation:', '1000')) || 1000;
    const calculationType = prompt('Calculation type (hell_money, satan_compound, atomic_interest, money_satan_growth, hell_compound):', 'hell_money') || 'hell_money';
    
    if (!window.atomicCalculator) {
        alert('Atomic calculator not loaded');
        return;
    }

    try {
        const result = await window.atomicCalculator.atomicCalculate(baseValue, calculationType);
        
        if (result.success) {
            const message = `
Atomic Calculation Result:
Type: ${result.calculation_type}
Base Value: ${result.base_value}
Result: ${result.result}
Atomic Result: ${result.atomic_result}

${result.hell_base ? `Hell Base: ${result.hell_base}` : ''}
${result.satan_multiplier ? `Satan Multiplier: ${result.satan_multiplier}` : ''}
${result.rate ? `Rate: ${result.rate}` : ''}
${result.periods ? `Periods: ${result.periods}` : ''}
            `.trim();
            
            alert(message);
            
            // Display in calculator if available
            const resultDisplay = document.getElementById('calculator-result');
            if (resultDisplay) {
                resultDisplay.textContent = `Atomic Result: ${result.atomic_result}`;
            }
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * Calculate Money Satan Returns
 */
async function calculateMoneySatanReturns() {
    const investment = parseFloat(prompt('Enter investment amount:', '1000')) || 1000;
    const timePeriods = parseInt(prompt('Enter time periods:', '12')) || 12;
    
    if (!window.atomicCalculator) {
        alert('Atomic calculator not loaded');
        return;
    }

    try {
        const result = await window.atomicCalculator.calculateMoneySatanReturns(investment, timePeriods);
        
        if (result.success) {
            const message = `
Money Satan Returns Calculation:
Investment: ${result.investment}
Time Periods: ${result.time_periods}
Final Value: ${result.final_value.toFixed(2)}
Total Growth: ${result.total_growth.toFixed(2)}
Growth Percentage: ${result.growth_percentage.toFixed(2)}%
            `.trim();
            
            alert(message);
            
            // Display in calculator if available
            const resultDisplay = document.getElementById('calculator-result');
            if (resultDisplay) {
                resultDisplay.innerHTML = `
                    <div>Investment: ${result.investment}</div>
                    <div>Final Value: ${result.final_value.toFixed(2)}</div>
                    <div>Growth: ${result.growth_percentage.toFixed(2)}%</div>
                `;
            }
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Make functions globally available
window.atomicCalculateHellMoney = atomicCalculateHellMoney;
window.calculateMoneySatanReturns = calculateMoneySatanReturns;

