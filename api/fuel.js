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

export default async function handler(req, res) {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const lat = parseFloat(url.searchParams.get('lat')) || 51.5074;
    const lng = parseFloat(url.searchParams.get('lng')) || -0.1278;
    const mode = url.searchParams.get('mode') || 'ev';
    
    const radius = parseFloat(url.searchParams.get('radius')) || 5;
    const excludeCostco = url.searchParams.get('excludeCostco') === 'true';
    const connector = (url.searchParams.get('connector') || 'any').toLowerCase();

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
            if (connector && connector !== 'any') {
                chargers = chargers.filter(c => (c.Connections || []).some(conn => {
                    const title = (conn.ConnectionType?.Title || '').toLowerCase();
                    return title.includes(connector) || (connector === 'ccs' && title.includes('combo')) || (connector === 'tesla' && title.includes('tesla'));
                }));
            }
            
            if (!chargers || chargers.length === 0) {
                return res.status(404).json({ error: "No chargers found nearby" });
            }
            
            let validChargers = chargers.filter(c => c.AddressInfo.Distance <= radius);
            if (validChargers.length === 0) {
                chargers.sort((a, b) => a.AddressInfo.Distance - b.AddressInfo.Distance);
                validChargers = [chargers[0]];
            }
            
            const charger = validChargers[0];
            const cost = (charger.UsageCost || "").toLowerCase();
            const isFree = cost.includes("free") || cost === "0";
            
            return res.status(200).json({
                price: isFree ? "FREE" : (cost.match(/\d+/) || ["65"])[0],
                unit: isFree ? "" : "p/kWh",
                name: charger.AddressInfo.Title || "EV Charger",
                dist: `${charger.AddressInfo.Distance.toFixed(1)} mi`,
                updated: "Live Feed",
                lat: charger.AddressInfo.Latitude, lng: charger.AddressInfo.Longitude,
                opening: 'Check operator before travelling',
                address: [charger.AddressInfo.AddressLine1, charger.AddressInfo.Town, charger.AddressInfo.Postcode].filter(Boolean).join(', '),
                allPrices: charger.UsageCost || 'EV pricing varies by operator',
                results: validChargers.slice(0, 8).map(c => {
                    const cCost = (c.UsageCost || '').toLowerCase();
                    const cFree = cCost.includes('free') || cCost === '0';
                    return {
                        name: c.AddressInfo.Title || 'EV Charger',
                        dist: `${c.AddressInfo.Distance.toFixed(1)} mi`,
                        price: cFree ? 'FREE' : ((cCost.match(/\d+/) || ['Varies'])[0]),
                        unit: cFree ? '' : 'p/kWh',
                        opening: 'Check operator',
                        allPrices: c.UsageCost || ((c.Connections || []).map(x => x.ConnectionType?.Title).filter(Boolean).join(' · '))
                    };
                })
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

                    if (!isNaN(sLat) && !isNaN(sLng) && !isNaN(price) && price > 0) {
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
                            if (cols[21]) prices.push(`E10 ${parseFloat(cols[21]).toFixed(1)}p`);
                            if (cols[18]) prices.push(`E5 ${parseFloat(cols[18]).toFixed(1)}p`);
                            if (cols[24]) prices.push(`Diesel ${parseFloat(cols[24]).toFixed(1)}p`);
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
            }

            if (!p || isNaN(parseFloat(p))) return false;
            
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
            phone: best.phone || "",
            results: (stationsInRadius.length > 0 ? stationsInRadius : validStations).slice(0, 8).map(s => ({
                name: s.name || s.brand || 'Fuel Station',
                dist: `${parseFloat(s.dist).toFixed(1)} mi`,
                price: `${parseFloat(s.price).toFixed(1)}`,
                unit: 'p',
                opening: s.opening || '',
                allPrices: s.allPrices || ''
            }))
        });
        
    } catch (error) {
        console.error("Handler Error: ", error);
        return res.status(500).json({ error: "System Error." });
    }
}
