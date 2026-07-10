/**
 * 🎯 FIXED INDICATORS ENGINE FOR LIVE DASHBOARD
 * Contains: EMA (9, 20, 50), Safe VWAP, and Stable Supertrend
 */

// 1. 📈 EXPONENTIAL MOVING AVERAGE (EMA)
function calculateEMA(candles, period) {
    let emaValues = [];
    if (!candles || candles.length === 0) return emaValues;

    let k = 2 / (period + 1);
    let sum = 0;
    
    // Initial SMA base
    for (let i = 0; i < Math.min(period, candles.length); i++) {
        sum += candles[i].close;
    }
    let yesterdayEma = sum / Math.min(period, candles.length);

    for (let i = 0; i < candles.length; i++) {
        if (i < period - 1) {
            emaValues.push(candles[i].close);
        } else {
            let currentEma = (candles[i].close * k) + (yesterdayEma * (1 - k));
            emaValues.push(currentEma);
            yesterdayEma = currentEma;
        }
    }
    return emaValues;
}

// 2. 🎯 VOLUME WEIGHTED AVERAGE PRICE (VWAP)
function calculateVWAP(candles) {
    let vwapValues = [];
    if (!candles || candles.length === 0) return vwapValues;

    let cumulativeVolumePrice = 0;
    let cumulativeVolume = 0;

    for (let i = 0; i < candles.length; i++) {
        let c = candles[i];
        let volume = c.volume || 1000;
        let typicalPrice = (c.high + c.low + c.close) / 3;

        cumulativeVolumePrice += typicalPrice * volume;
        cumulativeVolume += volume;

        if (cumulativeVolume === 0) {
            vwapValues.push(c.close);
        } else {
            vwapValues.push(cumulativeVolumePrice / cumulativeVolume);
        }
    }
    return vwapValues;
}

// 3. 🟢🔴 SUPERTREND ENGINE
function calculateSupertrend(candles, period = 7, multiplier = 3) {
    let results = [];
    if (!candles || candles.length === 0) return results;

    let upperBand = 0, lowerBand = 0;
    let trend = "up"; 

    for (let i = 0; i < candles.length; i++) {
        let c = candles[i];
        
        let tr = c.high - c.low;
        if (i > 0) {
            tr = Math.max(tr, Math.abs(c.high - candles[i-1].close), Math.abs(c.low - candles[i-1].close));
        }

        let hl2 = (c.high + c.low) / 2;
        let basicUpperBand = hl2 + (multiplier * tr);
        let basicLowerBand = hl2 - (multiplier * tr);

        if (i === 0) {
            upperBand = basicUpperBand;
            lowerBand = basicLowerBand;
        } else {
            upperBand = (basicUpperBand < upperBand || candles[i-1].close > upperBand) ? basicUpperBand : upperBand;
            lowerBand = (basicLowerBand > lowerBand || candles[i-1].close < lowerBand) ? basicLowerBand : lowerBand;
        }

        if (i > 0) {
            if (trend === "up" && c.close < lowerBand) trend = "down";
            else if (trend === "down" && c.close > upperBand) trend = "up";
        }

        results.push({
            value: (trend === "up") ? lowerBand : upperBand,
            direction: trend
        });
    }
    return results;
}