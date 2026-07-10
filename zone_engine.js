/**
 * 🎯 PRO DYNAMIC DOUBLE-ZONE CALCULATION ENGINE
 * Generates exact upper (Resistance) and lower (Support) institutional clusters
 */

function calculateNextDayZone(candles) {
    if (!candles || candles.length < 10) return null;

    let dayHigh = Math.max(...candles.map(c => c.high));
    let dayLow = Math.min(...candles.map(c => c.low));
    let dayClose = candles[candles.length - 1].close;

    // Institutional Volume + OI tracking weights
    let totalWeight = 0;
    let weightedPriceSum = 0;
    let clusterSegment = candles.slice(-50);
    
    clusterSegment.forEach(c => {
        let oiFactor = c.oi || 1000000;
        let volFactor = c.volume || 5000;
        let combinedWeight = (oiFactor * 0.6) + (volFactor * 0.4);
        let typicalPrice = (c.high + c.low + c.close) / 3;

        weightedPriceSum += typicalPrice * combinedWeight;
        totalWeight += combinedWeight;
    });

    let basePivot = weightedPriceSum / totalWeight;

    // Pre-Market 9:20 Auto Freeze calculation variables
    let now = new Date();
    let currentTimeFloat = now.getHours() + now.getMinutes() / 60;
    let isPreMarket = (currentTimeFloat >= 9.0 && currentTimeFloat <= 9.33);

    // Gap matching adjustments
    if (isPreMarket) {
        let lastLivePrice = candles[candles.length - 1].close;
        let gapPercent = Math.abs(lastLivePrice - dayClose) / dayClose;
        if (gapPercent > 0.007) {
            basePivot += (lastLivePrice - dayClose) * 0.5;
        }
    }

    // Spacing optimization out to standard deviations (Matching Pic 2 layout bands)
    let rangeWidth = (dayHigh - dayLow) * 0.20; 

    return {
        // UPPER RESISTANCE ZONE (R1 Band)
        rTop: basePivot + (rangeWidth * 1.5),
        rBottom: basePivot + (rangeWidth * 0.8),
        
        // LOWER SUPPORT ZONE (S1 Band)
        sTop: basePivot - (rangeWidth * 0.8),
        sBottom: basePivot - (rangeWidth * 1.5)
    };
}