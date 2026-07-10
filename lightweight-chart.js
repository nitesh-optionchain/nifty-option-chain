// Lightweight Charts Stub for HTML5 Canvas Rendering
(function(global, factory) {
    typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
    typeof define === 'function' && define.amd ? define(['exports'], factory) :
    (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.LightweightCharts = {}));
}(this, (function(exports) { 'use strict';
    exports.LineStyle = { Solid: 0, Dashed: 1, Dotted: 2 };
    exports.createChart = function(container, options) {
        container.innerHTML = '<div style="position:relative; width:100%; height:100%; background:#131722; border:1px solid #2b2e3a; box-sizing:border-box;"><canvas id="chartCanvas" style="width:100%; height:100%;"></canvas></div>';
        var canvas = container.querySelector('canvas');
        var ctx = canvas.getContext('2d');
        
        // Quick Responsive Canvas Fix
        setTimeout(function() {
            canvas.width = container.clientWidth;
            canvas.height = 550;
            ctx.fillStyle = '#131722'; ctx.fillRect(0, 0, canvas.width, canvas.height);
            // Draw Grid Lines
            ctx.strokeStyle = '#232634'; ctx.lineWidth = 1;
            for(var i=50; i<canvas.width; i+=50) { ctx.beginPath(); ctx.moveTo(i,0); ctx.lineTo(i,canvas.height); ctx.stroke(); }
            for(var j=50; j<canvas.height; j+=50) { ctx.beginPath(); ctx.moveTo(0,j); ctx.lineTo(canvas.width,j); ctx.stroke(); }
        }, 100);

        return {
            addCandlestickSeries: function() {
                return {
                    setData: function(d) { console.log("Base set:", d); },
                    update: function(candle) {
                        if(!canvas || !ctx) return;
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        // Draw Grid Background
                        ctx.fillStyle = '#131722'; ctx.fillRect(0, 0, canvas.width, canvas.height);
                        ctx.strokeStyle = '#232634';
                        for(var i=50; i<canvas.width; i+=50) { ctx.beginPath(); ctx.moveTo(i,0); ctx.lineTo(i,canvas.height); ctx.stroke(); }
                        for(var j=50; j<canvas.height; j+=50) { ctx.beginPath(); ctx.moveTo(0,j); ctx.lineTo(canvas.width,j); ctx.stroke(); }
                        
                        // Render Bar Realtime
                        ctx.fillStyle = candle.close >= candle.open ? '#26a69a' : '#ef5350';
                        ctx.fillRect(canvas.width/2 - 25, canvas.height/2 - (candle.close-24000), 50, (candle.close - candle.open) + 40);
                    },
                    createPriceLine: function(l) { console.log("Line Drawn:", l.title); return {}; },
                    removePriceLine: function() {}
                };
            },
            resize: function(w, h) {}
        };
    };
})));