import fs from 'fs';
import path from 'path';

function getDistance(lat1, lon1, lat2, lon2) {
    const R = 3958.8;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function splitCSV(row) {
    const result = [];
    let startValueIndex = 0;
    let inQuotes = false;
    for (let i = 0; i < row.length; i++) {
        if (row[i] === '"') inQuotes = !inQuotes;
        if (row[i] === ',' && !inQuotes) {
            result.push(row.substring(startValueIndex, i).replace(/^"|"$/g, ''));
            startValueIndex = i + 1;
        }
    }
    result.push(row.substring(startValueIndex).replace(/^"|"$/g, ''));
    return result;
}


function parseFuelPrice(value) {
    if (value === null || typeof value === 'undefined') return NaN;
    const n = parseFloat(String(value).replace(/[^0-9.]/g, ''));
    return Number.isFinite(n) ? n : NaN;
}

function isValidFuelPrice(value) {
    const n = parseFuelPrice(value);
    // Petrol and diesel prices are pence per litre. Reject impossible/outlier values.
    return Number.isFinite(n) && n >= 80 && n <= 300;
}

function formatFuelChip(label, value) {
    const n = parseFuelPrice(value);
    if (!isValidFuelPrice(n)) return null;
    return `${label} ${n.toFixed(1)}p`;
}

function evConnectorSummary(charger) {
    const names = new Set();
    const conns = charger.Connections || [];
    conns.forEach(conn => {
        const title = conn.ConnectionType?.Title || conn.ConnectionType?.FormalName || '';
        const clean = title.replace(/Type 2 Mennekes/i, 'Type 2').replace(/Combined Charging System/i, 'CCS').replace(/CHAdeMO/i, 'CHAdeMO').trim();
        if (clean) names.add(clean);
    });
    const preferred = ['CCS', 'Type 2', 'CHAdeMO'];
    const ordered = [...preferred.filter(x => [...names].some(n => n.toLowerCase().includes(x.toLowerCase()))), ...[...names].filter(n => !preferred.some(p => n.toLowerCase().includes(p.toLowerCase())))];
    return [...new Set(ordered)].slice(0, 5).join(' · ');
}

function evCostToPrice(costText) {
    const cost = String(costText || '').trim().toLowerCase();
    if (!cost || cost.includes('free')) return { price: cost.includes('free') ? 'FREE' : '65', unit: 'p/kWh' };
    if (/^0+(\.0+)?\s*(p|p\/kwh|£|gbp)?/.test(cost) || cost.includes('0.0p')) return { price: 'FREE', unit: '' };
    const match = cost.match(/\d+(?:\.\d+)?/);
    return { price: match ? match[0] : '65', unit: 'p/kWh' };
}

function evDisplayPrice(costText) {
    const raw = String(costText || '').trim();
    const lower = raw.toLowerCase();
    if (!raw) return 'price not listed';
    if (lower.includes('free') || /^0+(\.0+)?\s*(p|p\/kwh|£|gbp)?/.test(lower) || lower.includes('0.0p')) return 'FREE';
    const match = lower.match(/\d+(?:\.\d+)?/);
    if (!match) return 'price not listed';
    const num = parseFloat(match[0]);
    if (!Number.isFinite(num)) return 'price not listed';
    if (lower.includes('£') || lower.includes('gbp')) return `£${num.toFixed(2)}/kWh`;
    return `${num.toFixed(num % 1 ? 1 : 0)}p/kWh`;
}

function evNearbyPriceSummary(chargers, selectedId) {
    const seen = new Set();
    return (chargers || [])
        .filter(c => c && c.ID !== selectedId)
        .sort((a, b) => (a.AddressInfo?.Distance || 999) - (b.AddressInfo?.Distance || 999))
        .map(c => {
            const title = (c.AddressInfo?.Title || 'EV charger').replace(/\s+/g, ' ').trim();
            const shortTitle = title.length > 26 ? title.slice(0, 24).trim() + '…' : title;
            const price = evDisplayPrice(c.UsageCost || '');
            return `${shortTitle} ${price}`;
        })
        .filter(item => {
            const key = item.toLowerCase();
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        })
        .slice(0, 5)
        .join(' · ');
}

function fuelCompareRows(stations, best) {
    const seen = new Set();
    return (stations || [])
        .filter(s => s && isValidFuelPrice(s.price))
        .sort((a, b) => parseFloat(a.price) - parseFloat(b.price) || parseFloat(a.dist || 999) - parseFloat(b.dist || 999))
        .filter(s => {
            const key = `${(s.name || s.brand || '').toLowerCase()}|${(s.address || '').toLowerCase()}|${s.lat}|${s.lng}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        })
        .slice(0, 5)
        .map(s => ({
            price: parseFuelPrice(s.price).toFixed(1),
            unit: 'p',
            priceText: `${parseFuelPrice(s.price).toFixed(1)}p`,
            name: s.name || s.brand || 'Fuel station',
            dist: Number.isFinite(parseFloat(s.dist)) ? `${parseFloat(s.dist).toFixed(1)} mi` : '',
            opening: s.opening || 'Opening times unavailable',
            address: s.address || '',
            lat: s.lat,
            lng: s.lng,
            isBest: best && Math.abs(parseFloat(s.lat) - parseFloat(best.lat)) < 0.00001 && Math.abs(parseFloat(s.lng) - parseFloat(best.lng)) < 0.00001
        }));
}

function evCompareRows(chargers, selectedId) {
    const seen = new Set();
    return (chargers || [])
        .filter(c => c && c.AddressInfo)
        .sort((a, b) => (a.AddressInfo?.Distance || 999) - (b.AddressInfo?.Distance || 999))
        .filter(c => {
            const key = `${(c.AddressInfo?.Title || '').toLowerCase()}|${c.AddressInfo?.Latitude}|${c.AddressInfo?.Longitude}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        })
        .slice(0, 5)
        .map(c => {
            const price = evDisplayPrice(c.UsageCost || '');
            const connectors = evConnectorSummary(c);
            return {
                priceText: price === 'price not listed' ? 'Price not listed' : price,
                name: c.AddressInfo.Title || 'EV charger',
                dist: Number.isFinite(c.AddressInfo.Distance) ? `${c.AddressInfo.Distance.toFixed(1)} mi` : '',
                opening: 'Check operator',
                address: [c.AddressInfo.AddressLine1, c.AddressInfo.Town, c.AddressInfo.Postcode].filter(Boolean).join(', '),
                lat: c.AddressInfo.Latitude,
                lng: c.AddressInfo.Longitude,
                connectors,
                isBest: c.ID === selectedId
            };
        });
}

export default async function handler(req, res) {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const lat = parseFloat(url.searchParams.get('lat')) || 51.5074;
    const lng = parseFloat(url.searchParams.get('lng')) || -0.1278;
    const mode = url.searchParams.get('mode') || 'ev';
    
    const radius = parseFloat(url.searchParams.get('radius')) || 5;
    const excludeCostco = url.searchParams.get('excludeCostco') === 'true';

    const clientId = (process.env.FUEL_CLIENT_ID || "").replace(/\s/g, "");
    const clientSecret = (process.env.FUEL_CLIENT_SECRET || "").replace(/\s/g, "");
    const ocmKey = (process.env.OCM_API_KEY || "").replace(/\s/g, "");

    try {
        // ==========================================
        // 1. EV MODE
        // ==========================================
        if (mode === 'ev') {
            const searchRadius = Math.max(radius, 20);
            const evUrl = `https://api.openchargemap.io/v3/poi/?output=json&latitude=${lat}&longitude=${lng}&distance=${searchRadius}&distanceunit=miles&maxresults=25&compact=true${ocmKey ? `&key=${ocmKey}` : ''}`;
            const evReq = await fetch(evUrl, { signal: AbortSignal.timeout(5000) });
            if (!evReq.ok) {
                return res.status(502).json({ error: 'EV charger feed unavailable. Add OCM_API_KEY in Vercel or try again later.' });
            }
            const evData = await evReq.json();
            
            let chargers = evData || [];
            if (excludeCostco) {
                chargers = chargers.filter(c => !(c.AddressInfo?.Title || '').toLowerCase().includes('costco'));
            }
            
            if (!chargers || chargers.length === 0) {
                return res.status(404).json({ error: "No chargers found nearby" });
            }
            
            let validChargers = chargers.filter(c => c.AddressInfo.Distance <= radius);
            if (validChargers.length === 0) {
                chargers.sort((a, b) => a.AddressInfo.Distance - b.AddressInfo.Distance);
                validChargers = [chargers[0]];
            }
            
            validChargers.sort((a, b) => (a.AddressInfo?.Distance || 999) - (b.AddressInfo?.Distance || 999));
            const charger = validChargers[0];
            const cost = charger.UsageCost || "";
            const parsedCost = evCostToPrice(cost);
            const connectors = evConnectorSummary(charger);
            const nearbyEvPrices = evNearbyPriceSummary(validChargers, charger.ID);
            const compare = evCompareRows(validChargers, charger.ID);
            
            return res.status(200).json({
                price: parsedCost.price,
                unit: parsedCost.price === "FREE" ? "" : parsedCost.unit,
                name: charger.AddressInfo.Title || "EV Charger",
                dist: `${charger.AddressInfo.Distance.toFixed(1)} mi`,
                updated: "Live Feed",
                lat: charger.AddressInfo.Latitude, lng: charger.AddressInfo.Longitude,
                opening: 'Check operator before travelling',
                address: [charger.AddressInfo.AddressLine1, charger.AddressInfo.Town, charger.AddressInfo.Postcode].filter(Boolean).join(', '),
                allPrices: nearbyEvPrices,
                compare,
                ...(connectors ? { connectors } : {})
            });
        }

        // ==========================================
        // 2. FUEL MODE (Petrol or Diesel)
        // ==========================================
        let stations = [];
        let source = "Backup Feed"; // Default fallback
        const apiRadius = Math.max(radius, 20); 

        // --- A. LIVE API ATTEMPT ---
        if (clientId && clientSecret) {
            try {
                const tokenReq = await fetch("https://api.fuelfinder.service.gov.uk/v1/oauth/generate_access_token", {
                    method: "POST",
                    headers: { "Content-Type": "application/x-www-form-urlencoded" },
                    body: `grant_type=client_credentials&client_id=${clientId}&client_secret=${clientSecret}&scope=fuelfinder.read`,
                    signal: AbortSignal.timeout(3000) 
                });
                
                if (tokenReq.ok) {
                    const tokenData = await tokenReq.json();
                    const access_token = tokenData.access_token;
                    
                    if (access_token) {
                        const stationReq = await fetch(`https://api.fuelfinder.service.gov.uk/v1/stations?lat=${lat}&long=${lng}&radius=${apiRadius}`, {
                            headers: { "Authorization": `Bearer ${access_token}` }
                        });
                        
                        if (stationReq.ok) {
                            const apiData = await stationReq.json();
                            if (apiData && apiData.stations && apiData.stations.length > 0) {
                                stations = apiData.stations;
                                source = "Live Feed"; 
                            }
                        }
                    }
                }
            } catch (e) {
                console.log("Live API connection failed or timed out.");
            }
        }

        // --- B. CSV FALLBACK ATTEMPT ---
        if (stations.length === 0) {
            let csvPath = path.join(process.cwd(), 'data', 'fuel_data.csv');
            if (!fs.existsSync(csvPath)) {
                csvPath = path.join(process.cwd(), 'fuel_data.csv'); 
            }

            if (fs.existsSync(csvPath)) {
                // 1 & 2. Fix the Time-Travel Bug and Double "Updated"
                source = "today"; 

                const content = fs.readFileSync(csvPath, 'utf8');
                const rows = content.split(/\r?\n/).slice(1);
                
                rows.forEach(row => {
                    if (!row.trim()) return;
                    const cols = splitCSV(row);
                    if (cols.length < 25) return;
                    
                    const sLat = parseFloat(cols[16]);
                    const sLng = parseFloat(cols[17]);
                    const price = parseFloat(mode === 'diesel' ? cols[24] : cols[21]);

                    if (!isNaN(sLat) && !isNaN(sLng) && isValidFuelPrice(price)) {
                        const dist = getDistance(lat, lng, sLat, sLng);
                        if (dist <= apiRadius) { 
                            
                            // 3. Fix the Double Name Bug (e.g., Costco Costco)
                            let brand = (cols[3] || '').trim();
                            let site = (cols[2] || '').trim();
                            let cleanName = site.toLowerCase().includes(brand.toLowerCase()) ? site : `${brand} ${site}`.trim();

                            const today = new Date().getDay(); // 0 Sun - 6 Sat
                            const dayOffset = {1:36,2:39,3:42,4:45,5:48,6:51,0:54}[today];
                            let opening = 'Opening times unavailable';
                            if ((cols[dayOffset+2] || '').toLowerCase() === 'true') opening = 'Open 24 hours';
                            else if (cols[dayOffset] && cols[dayOffset+1]) opening = `${cols[dayOffset]}–${cols[dayOffset+1]}`;
                            const address = [cols[11], cols[12], cols[13], cols[10]].filter(Boolean).join(', ');
                            const prices = [];
                            const e10 = formatFuelChip('E10', cols[21]);
                            const e5 = formatFuelChip('E5', cols[18]);
                            const diesel = formatFuelChip('Diesel', cols[24]);
                            if (e10) prices.push(e10);
                            if (e5) prices.push(e5);
                            if (diesel) prices.push(diesel);
                            stations.push({
                                name: cleanName,
                                price: price, 
                                dist: dist, 
                                lat: sLat, 
                                lng: sLng,
                                opening,
                                address,
                                allPrices: prices.join(' · '),
                                phone: cols[6] || ''
                            });
                        }
                    }
                });
            }
        }
        // ==========================================
        // 3. FILTER AND SORT RESULTS
        // ==========================================
        let validStations = stations.filter(s => {
            if (excludeCostco) {
                const sName = (s.name || s.brand || '').toLowerCase();
                if (sName.includes('costco')) return false;
            }

            // Standardize format from Live API vs CSV
            let d = s.dist;
            let p = s.price;
            let latVal = s.lat || (s.location && s.location.latitude);
            let lngVal = s.lng || (s.location && s.location.longitude);

            if (typeof d === 'undefined' && latVal && lngVal) { 
                d = getDistance(lat, lng, latVal, lngVal);
                s.dist = d; 
            }
            
            // If Live API returned data, the price is nested.
            if (s.prices) {
                p = mode === 'diesel' ? s.prices.B7 : s.prices.E10;
                s.price = p;

                const livePrices = [];
                const e10 = formatFuelChip('E10', s.prices.E10);
                const e5 = formatFuelChip('E5', s.prices.E5);
                const diesel = formatFuelChip('Diesel', s.prices.B7);
                if (e10) livePrices.push(e10);
                if (e5) livePrices.push(e5);
                if (diesel) livePrices.push(diesel);
                s.allPrices = s.allPrices || livePrices.join(' · ');
            }

            if (!isValidFuelPrice(p)) return false;
            
            s.lat = latVal;
            s.lng = lngVal;
            return true;
        });

        if (validStations.length === 0) {
            return res.status(404).json({ error: `No stations found nearby` });
        }

        // Sort: Cheapest in radius, else closest overall
        let best;
        let stationsInRadius = validStations.filter(s => s.dist <= radius);
        
        if (stationsInRadius.length > 0) {
            stationsInRadius.sort((a, b) => parseFloat(a.price) - parseFloat(b.price));
            best = stationsInRadius[0];
        } else {
            validStations.sort((a, b) => parseFloat(a.dist) - parseFloat(b.dist));
            best = validStations[0];
        }
        const compareSource = stationsInRadius.length > 0 ? stationsInRadius : validStations;
        const compare = fuelCompareRows(compareSource, best);
        
        return res.status(200).json({
            price: best.price.toString(), 
            unit: "p", 
            name: best.name || best.brand || "Fuel Station",
            dist: `${best.dist.toFixed(1)} mi`, 
            updated: source, 
            lat: best.lat, 
            lng: best.lng,
            opening: best.opening || "Opening times unavailable",
            address: best.address || "",
            allPrices: best.allPrices || "",
            compare,
            phone: best.phone || ""
        });
        
    } catch (error) {
        console.error("Handler Error: ", error);
        return res.status(500).json({ error: "System Error." });
    }
}
