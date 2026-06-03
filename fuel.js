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


function formatAgeFromDate(date) {
    if (!(date instanceof Date) || isNaN(date.getTime())) return 'today';
    const diffMs = Date.now() - date.getTime();
    if (diffMs < 0) return 'just now';
    const minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes} min${minutes === 1 ? '' : 's'} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 48) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
    const days = Math.floor(hours / 24);
    if (days < 14) return `${days} day${days === 1 ? '' : 's'} ago`;
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function getCsvUpdatedLabel(csvPath) {
    const candidates = [
        path.join(process.cwd(), 'data', 'fuel_updated.json'),
        path.join(process.cwd(), 'fuel_updated.json')
    ];

    for (const file of candidates) {
        try {
            if (fs.existsSync(file)) {
                const parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
                const value = parsed.checkedAt || parsed.checked_at || parsed.updatedAt || parsed.updated_at || parsed.timestamp;
                if (value) {
                    const label = formatAgeFromDate(new Date(value));
                    return label || 'unknown';
                }
            }
        } catch (e) {
            console.log('Could not read fuel_updated.json');
        }
    }

    // Do not use CSV file modified time as fallback.
    // Some deployed/static hosts return an old build timestamp, which is misleading.
    return 'unknown';
}

function normaliseHeaderName(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function findHeaderIndex(headers, candidates, fallbackIndex) {
    const normalised = headers.map(normaliseHeaderName);
    const wanted = candidates.map(normaliseHeaderName);

    for (const candidate of wanted) {
        const exact = normalised.indexOf(candidate);
        if (exact !== -1) return exact;
    }

    for (const candidate of wanted) {
        const contains = normalised.findIndex(h => h.includes(candidate) || candidate.includes(h));
        if (contains !== -1) return contains;
    }

    return fallbackIndex;
}

function buildCsvIndex(headers) {
    return {
        id: findHeaderIndex(headers, ['forecourts.node_id', 'node_id', 'id', 'station_id', 'site_id'], 0),
        site: findHeaderIndex(headers, ['forecourts.siteName', 'forecourts.name', 'siteName', 'name'], 2),
        brand: findHeaderIndex(headers, ['forecourts.brand', 'brand'], 3),
        phone: findHeaderIndex(headers, ['forecourts.contact.telephone', 'telephone', 'phone'], 6),
        postcode: findHeaderIndex(headers, ['forecourts.address.postcode', 'postcode'], 10),
        line1: findHeaderIndex(headers, ['forecourts.address.line1', 'address.line1', 'line1'], 11),
        line2: findHeaderIndex(headers, ['forecourts.address.line2', 'address.line2', 'line2'], 12),
        town: findHeaderIndex(headers, ['forecourts.address.town', 'town'], 13),
        lat: findHeaderIndex(headers, ['forecourts.location.latitude', 'location.latitude', 'latitude'], 16),
        lng: findHeaderIndex(headers, ['forecourts.location.longitude', 'location.longitude', 'longitude'], 17),
        e5: findHeaderIndex(headers, ['prices.E5', 'prices.E5.price', 'E5'], 18),
        e5Updated: findHeaderIndex(headers, ['forecourts.price_submission_timestamp.E5', 'price_submission_timestamp.E5', 'prices.E5.lastUpdated', 'prices.E5.updatedAt', 'prices.E5.updatedDate', 'prices.E5.lastUpdate', 'E5.lastUpdated'], 19),
        e10: findHeaderIndex(headers, ['prices.E10', 'prices.E10.price', 'E10'], 21),
        e10Updated: findHeaderIndex(headers, ['forecourts.price_submission_timestamp.E10', 'price_submission_timestamp.E10', 'prices.E10.lastUpdated', 'prices.E10.updatedAt', 'prices.E10.updatedDate', 'prices.E10.lastUpdate', 'E10.lastUpdated'], 22),
        b7: findHeaderIndex(headers, ['prices.B7', 'prices.B7.price', 'B7', 'diesel'], 24),
        b7Updated: findHeaderIndex(headers, ['forecourts.price_submission_timestamp.B7S', 'price_submission_timestamp.B7S', 'forecourts.price_submission_timestamp.B7', 'prices.B7.lastUpdated', 'prices.B7.updatedAt', 'prices.B7.updatedDate', 'prices.B7.lastUpdate', 'B7.lastUpdated', 'diesel.lastUpdated'], 25)
    };
}

function getCol(cols, index, fallback = '') {
    return Number.isInteger(index) && index >= 0 && index < cols.length ? cols[index] : fallback;
}

function parseStationDate(value) {
    const raw = String(value || '').trim();
    if (!raw) return null;
    const direct = new Date(raw);
    if (!isNaN(direct.getTime())) return direct;

    // Handles common UK date strings such as 27/01/2026 or 27-01-2026.
    const uk = raw.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
    if (uk) {
        const year = uk[3].length === 2 ? Number('20' + uk[3]) : Number(uk[3]);
        const date = new Date(Date.UTC(year, Number(uk[2]) - 1, Number(uk[1]), Number(uk[4] || 0), Number(uk[5] || 0), Number(uk[6] || 0)));
        if (!isNaN(date.getTime())) return date;
    }

    return null;
}

function formatStationUpdatedLabel(value) {
    const date = parseStationDate(value);
    if (!date) return '';
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    if (diffMs >= 0 && diffMs < 24 * 60 * 60 * 1000) return 'today';
    if (diffMs >= 0 && diffMs < 48 * 60 * 60 * 1000) return 'yesterday';
    const sameYear = date.getUTCFullYear() === now.getUTCFullYear();
    return date.toLocaleDateString('en-US', sameYear
        ? { month: 'short', day: 'numeric', timeZone: 'UTC' }
        : { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
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


function stableTextHash(value) {
    let hash = 5381;
    const text = String(value || '');
    for (let i = 0; i < text.length; i++) {
        hash = ((hash << 5) + hash) + text.charCodeAt(i);
        hash = hash >>> 0;
    }
    return hash.toString(36);
}

function evChargerId(charger) {
    if (charger && charger.ID) return `ev-${charger.ID}`;
    const info = charger?.AddressInfo || {};
    const key = [
        info.Title,
        info.AddressLine1,
        info.Town,
        info.Postcode,
        Number.isFinite(+info.Latitude) ? (+info.Latitude).toFixed(6) : '',
        Number.isFinite(+info.Longitude) ? (+info.Longitude).toFixed(6) : ''
    ].filter(Boolean).join('|').toLowerCase();
    return `ev-${stableTextHash(key)}`;
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

function evPriceValuePence(costText) {
    const raw = String(costText || '').trim();
    const lower = raw.toLowerCase();

    if (!raw) return null;
    if (lower.includes('free')) return 0;
    if (/^0+(\.0+)?\s*(p|p\/kwh|£|gbp)?/.test(lower) || lower.includes('0.0p')) return 0;

    const match = lower.match(/\d+(?:\.\d+)?/);
    if (!match) return null;

    const num = parseFloat(match[0]);
    if (!Number.isFinite(num)) return null;

    // OpenChargeMap UsageCost may be written as £0.59/kWh or 59p/kWh.
    // Convert pound values to pence so sorting and the main price are correct.
    if (lower.includes('£') || lower.includes('gbp')) return Math.round(num * 1000) / 10;

    return Math.round(num * 10) / 10;
}

function evCostToPrice(costText) {
    const pence = evPriceValuePence(costText);

    if (pence === 0) return { price: 'FREE', unit: '' };
    if (pence === null) return { price: 'Price not listed', unit: '' };

    return { price: pence.toString(), unit: 'p/kWh' };
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

function evPriceInfoConfidence(costText) {
    const display = evDisplayPrice(costText || '');
    const lower = String(display || '').toLowerCase();

    if (!display || lower.includes('price not listed')) {
        return { level: 'low', label: 'Price info unavailable', messages: ['Check operator before travelling.'] };
    }

    if (lower.includes('free')) {
        return { level: 'medium', label: 'Price info: FREE', messages: ['Listed as FREE. Check operator before charging.'] };
    }

    const value = evPriceValuePence(costText || display);
    if (Number.isFinite(value) && value >= 0 && value <= 250) {
        return { level: 'high', label: 'Price info available', messages: ['Check operator for live availability.'] };
    }

    return { level: 'medium', label: 'Price info needs checking', messages: ['Check operator before charging.'] };
}

function evNearbyPriceSummary(chargers, selectedId) {
    const seen = new Set();
    return (chargers || [])
        .filter(c => c && c.ID !== selectedId)
        .sort((a, b) => {
            const ap = evPriceValuePence(a.UsageCost);
            const bp = evPriceValuePence(b.UsageCost);
            const aRank = ap === null ? Number.POSITIVE_INFINITY : ap;
            const bRank = bp === null ? Number.POSITIVE_INFINITY : bp;
            return aRank - bRank || (a.AddressInfo?.Distance || 999) - (b.AddressInfo?.Distance || 999);
        })
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

function fuelCompareRows(stations, best, sortMode = 'price') {
    const seen = new Set();
    return (stations || [])
        .filter(s => s && isValidFuelPrice(s.price))
        .sort((a, b) => sortMode === 'distance'
            ? (parseFloat(a.dist || 999) - parseFloat(b.dist || 999) || parseFloat(a.price) - parseFloat(b.price))
            : (parseFloat(a.price) - parseFloat(b.price) || parseFloat(a.dist || 999) - parseFloat(b.dist || 999)))
        .filter(s => {
            const key = `${(s.name || s.brand || '').toLowerCase()}|${(s.address || '').toLowerCase()}|${s.lat}|${s.lng}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        })
        .slice(0, 5)
        .map(s => ({
            id: String(s.id || `${Math.round((s.lat||0) * 1e6)}:${Math.round((s.lng||0) * 1e6)}:${(s.name||s.brand||'station').toLowerCase().replace(/[^a-z0-9]+/g,'-').slice(0,42)}`),
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

function median(values) {
    const nums = (values || []).map(parseFuelPrice).filter(Number.isFinite).sort((a, b) => a - b);
    if (!nums.length) return null;
    const mid = Math.floor(nums.length / 2);
    return nums.length % 2 ? nums[mid] : (nums[mid - 1] + nums[mid]) / 2;
}

function daysSinceStationUpdate(value) {
    const date = parseStationDate(value);
    if (!date) return null;
    const diff = Date.now() - date.getTime();
    if (!Number.isFinite(diff)) return null;
    return Math.max(0, Math.floor(diff / (24 * 60 * 60 * 1000)));
}

function normaliseStationText(value) {
    return String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
}

function sameStationForConfidence(a, b) {
    if (!a || !b) return false;

    const aid = String(a.id || a.stationId || '').trim();
    const bid = String(b.id || b.stationId || '').trim();
    if (aid && bid && aid === bid) return true;

    const alat = parseFloat(a.lat);
    const alng = parseFloat(a.lng);
    const blat = parseFloat(b.lat);
    const blng = parseFloat(b.lng);
    if (Number.isFinite(alat) && Number.isFinite(alng) && Number.isFinite(blat) && Number.isFinite(blng)) {
        if (Math.abs(alat - blat) < 0.00001 && Math.abs(alng - blng) < 0.00001) return true;
    }

    const aname = normaliseStationText(a.name || a.brand);
    const bname = normaliseStationText(b.name || b.brand);
    const apost = normaliseStationText(a.postcode);
    const bpost = normaliseStationText(b.postcode);
    if (aname && bname && aname === bname && apost && bpost && apost === bpost) return true;

    return false;
}

function priceConfidenceFor(station, nearbyStations = []) {
    const messages = [];
    let score = 0;
    const price = parseFuelPrice(station?.price);

    if (!Number.isFinite(price)) {
        return { level: 'low', label: 'Price confidence: Low', messages: ['Price is not currently available.'] };
    }

    if (price < 110) {
        score += 2;
        messages.push('Unusually low price reported.');
    } else if (price > 230) {
        score += 2;
        messages.push('Unusually high price reported.');
    }

    const updatedRaw = station?.stationUpdatedRaw || station?.updated_at || station?.updatedAt || '';
    const ageDays = daysSinceStationUpdate(updatedRaw);
    if (ageDays !== null) {
        if (ageDays > 14) {
            score += 2;
            messages.push(`Updated ${ageDays} days ago.`);
        } else if (ageDays > 7) {
            score += 1;
            messages.push(`Updated ${ageDays} days ago.`);
        }
    }

    const localPrices = (nearbyStations || [])
        .filter(s => s && !sameStationForConfidence(s, station) && Number.isFinite(parseFuelPrice(s.price)))
        .filter(s => !Number.isFinite(parseFloat(s.dist)) || parseFloat(s.dist) <= 5)
        .map(s => s.price);
    const localMedian = median(localPrices);

    if (Number.isFinite(localMedian)) {
        const diff = price - localMedian;
        if (Math.abs(diff) >= 20) {
            score += 2;
            messages.push(diff < 0 ? 'Significantly lower than nearby stations.' : 'Significantly higher than nearby stations.');
        } else if (Math.abs(diff) >= 12) {
            score += 1;
            messages.push(diff < 0 ? 'Lower than most nearby stations.' : 'Higher than most nearby stations.');
        }
    }

    if (score >= 2) {
        if (!messages.some(m => m.includes('Check with station'))) messages.push('Check with station before travelling.');
        return { level: 'low', label: 'Price confidence: Low', messages: messages.slice(0, 3) };
    }

    if (score === 1) {
        return { level: 'medium', label: 'Price confidence: Medium', messages: messages.slice(0, 2) };
    }

    return { level: 'high', label: 'Price confidence: High', messages: ['Looks consistent with nearby stations.'] };
}

function evCompareRows(chargers, selectedId) {
    const seen = new Set();
    return (chargers || [])
        .filter(c => c && c.AddressInfo)
        .sort((a, b) => {
            const ap = evPriceValuePence(a.UsageCost);
            const bp = evPriceValuePence(b.UsageCost);
            const aRank = ap === null ? Number.POSITIVE_INFINITY : ap;
            const bRank = bp === null ? Number.POSITIVE_INFINITY : bp;
            return aRank - bRank || (a.AddressInfo?.Distance || 999) - (b.AddressInfo?.Distance || 999);
        })
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
                id: evChargerId(c),
                priceText: price === 'price not listed' ? 'Price not listed' : price,
                name: c.AddressInfo.Title || 'EV charger',
                dist: Number.isFinite(c.AddressInfo.Distance) ? `${c.AddressInfo.Distance.toFixed(1)} mi` : '',
                opening: 'Check operator',
                address: [c.AddressInfo.AddressLine1, c.AddressInfo.Town, c.AddressInfo.Postcode].filter(Boolean).join(', '),
                lat: c.AddressInfo.Latitude,
                lng: c.AddressInfo.Longitude,
                connectors,
                priceConfidence: evPriceInfoConfidence(c.UsageCost || ''),
                isBest: c.ID === selectedId
            };
        });
}


function loadLatestFuelStations(mode, referenceLat, referenceLng) {
    const candidates = [
        path.join(process.cwd(), 'data', 'latest.json'),
        path.join(process.cwd(), 'latest.json')
    ];

    const file = candidates.find(f => fs.existsSync(f));
    if (!file) return { stations: [], source: 'unknown' };

    let parsed;
    try {
        parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch (e) {
        return { stations: [], source: 'unknown' };
    }

    const rows = Array.isArray(parsed) ? parsed : (parsed.stations || []);
    const source = formatAgeFromDate(new Date(parsed.generated_at || parsed.snapshot_date || Date.now()));

    const stations = rows.map(row => {
        const price = mode === 'diesel' ? row.b7 : row.e10;
        const lat = parseFloat(row.lat);
        const lng = parseFloat(row.lng);

        if (!Number.isFinite(lat) || !Number.isFinite(lng) || !isValidFuelPrice(price)) return null;

        const name = String(row.name || row.brand || 'Fuel station').replace(/\s+/g, ' ').trim();
        const address = [row.address, row.postcode].filter(Boolean).join(', ');
        const dist = (Number.isFinite(referenceLat) && Number.isFinite(referenceLng)) ? getDistance(referenceLat, referenceLng, lat, lng) : 9999;

        const prices = [];
        const e10 = formatFuelChip('E10', row.e10);
        const e5 = formatFuelChip('E5', row.e5);
        const diesel = formatFuelChip('Diesel', row.b7);
        if (e10) prices.push(e10);
        if (e5) prices.push(e5);
        if (diesel) prices.push(diesel);

        const priceUpdatedRaw = mode === 'diesel'
            ? (row.b7_updated_at || row.b7s_updated_at || row.diesel_updated_at || row.updated_at || '')
            : (row.e10_updated_at || row.petrol_updated_at || row.updated_at || '');

        return {
            id: String(row.id || `${Math.round(lat * 1e6)}:${Math.round(lng * 1e6)}:${name.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 42)}`),
            brand: String(row.brand || '').trim(),
            name,
            price: parseFuelPrice(price),
            dist,
            lat,
            lng,
            opening: row.opening || (row.is_motorway ? 'Check operator' : 'Opening times unavailable'),
            address,
            postcode: String(row.postcode || '').trim(),
            allPrices: prices.join(' · '),
            stationUpdated: formatStationUpdatedLabel(priceUpdatedRaw),
            stationUpdatedRaw: priceUpdatedRaw,
            searchText: [row.brand, row.name, row.address, row.postcode].filter(Boolean).join(' ').toLowerCase()
        };
    }).filter(Boolean);

    return { stations, source };
}

function normaliseStationQuery(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function stationMatchesQuery(station, query) {
    const q = normaliseStationQuery(query);
    if (!q || q.length < 2) return false;

    const tokens = q.split(/\s+/).filter(Boolean);
    const text = normaliseStationQuery(station.searchText || [station.name, station.address, station.postcode].join(' '));

    return tokens.every(token => text.includes(token));
}

function stationSearchScore(station, query) {
    const q = normaliseStationQuery(query);
    const name = normaliseStationQuery(station.name);
    const brand = normaliseStationQuery(station.brand);
    const postcode = normaliseStationQuery(station.postcode);
    let score = 0;

    if (postcode && postcode.replace(/\s/g, '').startsWith(q.replace(/\s/g, ''))) score += 80;
    if (name === q || brand === q) score += 70;
    if (name.startsWith(q) || brand.startsWith(q)) score += 45;
    if (name.includes(q) || brand.includes(q)) score += 25;
    if (station.address && normaliseStationQuery(station.address).includes(q)) score += 10;

    const dist = Number(station.dist);
    if (Number.isFinite(dist)) score += Math.max(0, 20 - Math.min(dist, 20));

    return score;
}

function stationSummary(station) {
    return {
        id: station.id,
        name: station.name,
        price: parseFuelPrice(station.price).toFixed(1),
        unit: 'p',
        priceText: `${parseFuelPrice(station.price).toFixed(1)}p`,
        dist: Number.isFinite(station.dist) && station.dist < 9999 ? `${station.dist.toFixed(1)} mi` : '',
        address: station.address || station.postcode || '',
        lat: station.lat,
        lng: station.lng
    };
}

function buildStationSearchResponse({ allStations, selected, query, mode, radius, source }) {
    const selectedWithLocalDistance = { ...selected, dist: 0 };
    const localStations = allStations.map(s => ({
        ...s,
        dist: getDistance(selected.lat, selected.lng, s.lat, s.lng)
    })).filter(s => {
        if (!isValidFuelPrice(s.price)) return false;
        return s.dist <= Math.max(1, radius || 1);
    });

    const compareSource = localStations.length ? localStations : allStations.map(s => ({
        ...s,
        dist: getDistance(selected.lat, selected.lng, s.lat, s.lng)
    })).sort((a, b) => a.dist - b.dist).slice(0, 10);

    const sortedByPrice = [...compareSource].sort((a, b) => parseFloat(a.price) - parseFloat(b.price) || parseFloat(a.dist) - parseFloat(b.dist));
    const cheapest = sortedByPrice[0] || selectedWithLocalDistance;
    const difference = parseFuelPrice(selected.price) - parseFuelPrice(cheapest.price);
    const saving35L = difference > 0 ? difference * 35 / 100 : 0;

    const compareItems = fuelCompareRows(compareSource, cheapest, 'price').map(item => {
        const isSelected = Math.abs(parseFloat(item.lat) - parseFloat(selected.lat)) < 0.00001 && Math.abs(parseFloat(item.lng) - parseFloat(selected.lng)) < 0.00001;
        const isCheapest = Math.abs(parseFloat(item.lat) - parseFloat(cheapest.lat)) < 0.00001 && Math.abs(parseFloat(item.lng) - parseFloat(cheapest.lng)) < 0.00001;
        const original = compareSource.find(s => String(s.id) === String(item.id)) || item;
        return {
            ...item,
            priceConfidence: priceConfidenceFor(original, compareSource),
            badge: isSelected ? 'You searched for' : (isCheapest ? 'Cheapest nearby' : '')
        };
    });

    if (!compareItems.some(item => item.badge === 'You searched for')) {
        compareItems.unshift({
            ...stationSummary({ ...selected, dist: getDistance(selected.lat, selected.lng, selected.lat, selected.lng) }),
            opening: selected.opening,
            priceConfidence: priceConfidenceFor(selected, compareSource),
            badge: 'You searched for'
        });
    }

    const selectedCompareItem = compareItems.find(item => item && item.priceConfidence && sameStationForConfidence(item, selected));
    const selectedPriceConfidence = selectedCompareItem?.priceConfidence || priceConfidenceFor(selected, compareSource);

    const visibleCompareItems = [];
    const selectedItem = compareItems.find(item => item.badge === 'You searched for');
    const cheapestItem = compareItems.find(item => item.badge === 'Cheapest nearby');

    [selectedItem, cheapestItem, ...compareItems].forEach(item => {
        if (!item) return;
        if (visibleCompareItems.some(existing => sameStationForConfidence(existing, item))) return;
        visibleCompareItems.push(item);
    });

    return {
        stationSearch: true,
        stationId: selected.id,
        price: selected.price.toString(),
        unit: 'p',
        name: selected.name || 'Fuel station',
        dist: Number.isFinite(selected.dist) && selected.dist < 9999 ? `${selected.dist.toFixed(1)} mi` : 'Selected station',
        updated: source,
        datasetUpdated: source,
        stationUpdated: selected.stationUpdated || '',
        priceConfidence: selectedPriceConfidence,
        lat: selected.lat,
        lng: selected.lng,
        opening: selected.opening || 'Opening times unavailable',
        address: selected.address || '',
        allPrices: selected.allPrices || '',
        compare: {
            fallback: false,
            items: visibleCompareItems.slice(0, 6)
        },
        searchContext: {
            query,
            selectedName: selected.name,
            selectedPriceText: `${parseFuelPrice(selected.price).toFixed(1)}p`,
            cheapestName: cheapest.name,
            cheapestPriceText: `${parseFuelPrice(cheapest.price).toFixed(1)}p`,
            differencePence: Number.isFinite(difference) ? Math.max(0, difference) : null,
            saving35L: Number.isFinite(saving35L) ? saving35L : null,
            selectedIsCheapest: Math.abs(difference) < 0.05 || difference <= 0,
            priceConfidence: selectedPriceConfidence
        }
    };
}

export default async function handler(req, res) {
    const url = new URL(req.url, `http://${req.headers.host}`);
    const lat = parseFloat(url.searchParams.get('lat')) || 51.5074;
    const lng = parseFloat(url.searchParams.get('lng')) || -0.1278;
    const mode = url.searchParams.get('mode') || 'ev';
    
    const radius = parseFloat(url.searchParams.get('radius')) || 5;
    const excludeCostco = url.searchParams.get('excludeCostco') === 'true';
    const stationSearch = (url.searchParams.get('stationSearch') || '').trim();
    const stationId = (url.searchParams.get('stationId') || '').trim();

    if (stationSearch && mode !== 'ev') {
        const { stations: allStations, source } = loadLatestFuelStations(mode, lat, lng);
        let candidates = allStations.filter(s => stationMatchesQuery(s, stationSearch));

        if (excludeCostco) {
            candidates = candidates.filter(s => !(s.name || '').toLowerCase().includes('costco'));
        }

        candidates.sort((a, b) => stationSearchScore(b, stationSearch) - stationSearchScore(a, stationSearch) || a.dist - b.dist || a.price - b.price);

        if (stationId) {
            const selected = allStations.find(s => s.id === stationId) || candidates[0];
            if (!selected) return res.status(404).json({ error: 'Station not found' });
            return res.status(200).json(buildStationSearchResponse({
                allStations,
                selected,
                query: stationSearch,
                mode,
                radius,
                source
            }));
        }

        return res.status(200).json({
            stationSearch: true,
            query: stationSearch,
            suggestions: candidates.slice(0, 8).map(stationSummary)
        });
    }

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

            // EV favourites must open the saved charger, not just the cheapest/nearest charger around its lat/lng.
            // stationId is a stable id generated by evChargerId(), e.g. ev-92062.
            const selectedEvCharger = stationId
                ? chargers.find(c => evChargerId(c) === stationId)
                : null;
            
            let validChargers = chargers.filter(c => c.AddressInfo.Distance <= radius);
            if (validChargers.length === 0) {
                chargers.sort((a, b) => a.AddressInfo.Distance - b.AddressInfo.Distance);
                validChargers = [chargers[0]];
            }
            if (selectedEvCharger && !validChargers.some(c => evChargerId(c) === stationId)) {
                validChargers.push(selectedEvCharger);
            }
            
            validChargers.sort((a, b) => {
                const ap = evPriceValuePence(a.UsageCost);
                const bp = evPriceValuePence(b.UsageCost);
                const aRank = ap === null ? Number.POSITIVE_INFINITY : ap;
                const bRank = bp === null ? Number.POSITIVE_INFINITY : bp;
                return aRank - bRank || (a.AddressInfo?.Distance || 999) - (b.AddressInfo?.Distance || 999);
            });
            const charger = selectedEvCharger || validChargers[0];
            const cost = charger.UsageCost || "";
            const parsedCost = evCostToPrice(cost);
            const connectors = evConnectorSummary(charger);
            const nearbyEvPrices = evNearbyPriceSummary(validChargers, charger.ID);
            const compare = evCompareRows(validChargers, charger.ID);
            
            return res.status(200).json({
                stationId: evChargerId(charger),
                price: parsedCost.price,
                unit: parsedCost.price === "FREE" ? "" : parsedCost.unit,
                name: charger.AddressInfo.Title || "EV Charger",
                dist: `${charger.AddressInfo.Distance.toFixed(1)} mi`,
                updated: "Live feed",
                datasetUpdated: "Live feed",
                lat: charger.AddressInfo.Latitude, lng: charger.AddressInfo.Longitude,
                opening: 'Check operator before travelling',
                address: [charger.AddressInfo.AddressLine1, charger.AddressInfo.Town, charger.AddressInfo.Postcode].filter(Boolean).join(', '),
                allPrices: nearbyEvPrices,
                priceConfidence: evPriceInfoConfidence(cost),
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
                source = getCsvUpdatedLabel(csvPath);

                const content = fs.readFileSync(csvPath, 'utf8');
                const lines = content.split(/\r?\n/);
                const headers = splitCSV(lines[0] || '');
                const csvIndex = buildCsvIndex(headers);
                const rows = lines.slice(1);
                
                rows.forEach(row => {
                    if (!row.trim()) return;
                    const cols = splitCSV(row);
                    if (cols.length < 25) return;
                    
                    const sLat = parseFloat(getCol(cols, csvIndex.lat));
                    const sLng = parseFloat(getCol(cols, csvIndex.lng));
                    const priceIndex = mode === 'diesel' ? csvIndex.b7 : csvIndex.e10;
                    const price = parseFloat(getCol(cols, priceIndex));
                    const stationUpdatedRaw = getCol(cols, mode === 'diesel' ? csvIndex.b7Updated : csvIndex.e10Updated);
                    const stationUpdated = formatStationUpdatedLabel(stationUpdatedRaw);

                    if (!isNaN(sLat) && !isNaN(sLng) && isValidFuelPrice(price)) {
                        const dist = getDistance(lat, lng, sLat, sLng);
                        if (dist <= apiRadius) { 
                            
                            // 3. Fix the Double Name Bug (e.g., Costco Costco)
                            let brand = (getCol(cols, csvIndex.brand) || '').trim();
                            let site = (getCol(cols, csvIndex.site) || '').trim();
                            let cleanName = site.toLowerCase().includes(brand.toLowerCase()) ? site : `${brand} ${site}`.trim();

                            const today = new Date().getDay(); // 0 Sun - 6 Sat
                            const dayOffset = {1:36,2:39,3:42,4:45,5:48,6:51,0:54}[today];
                            let opening = 'Opening times unavailable';
                            if ((cols[dayOffset+2] || '').toLowerCase() === 'true') opening = 'Open 24 hours';
                            else if (cols[dayOffset] && cols[dayOffset+1]) opening = `${cols[dayOffset]}–${cols[dayOffset+1]}`;
                            const address = [getCol(cols, csvIndex.line1), getCol(cols, csvIndex.line2), getCol(cols, csvIndex.town), getCol(cols, csvIndex.postcode)].filter(Boolean).join(', ');
                            const prices = [];
                            const e10 = formatFuelChip('E10', getCol(cols, csvIndex.e10));
                            const e5 = formatFuelChip('E5', getCol(cols, csvIndex.e5));
                            const diesel = formatFuelChip('Diesel', getCol(cols, csvIndex.b7));
                            if (e10) prices.push(e10);
                            if (e5) prices.push(e5);
                            if (diesel) prices.push(diesel);
                            stations.push({
                                id: String(getCol(cols, csvIndex.id) || `${Math.round(sLat * 1e6)}:${Math.round(sLng * 1e6)}:${cleanName.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 42)}`),
                                name: cleanName,
                                price: price, 
                                dist: dist, 
                                lat: sLat, 
                                lng: sLng,
                                opening,
                                address,
                                allPrices: prices.join(' · '),
                                phone: getCol(cols, csvIndex.phone) || '',
                                stationUpdated,
                                stationUpdatedRaw
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
            s.id = String(s.id || s.site_id || s.siteId || `${Math.round((latVal||0) * 1e6)}:${Math.round((lngVal||0) * 1e6)}:${(s.name||s.brand||'station').toLowerCase().replace(/[^a-z0-9]+/g,'-').slice(0,42)}`);
            s.stationUpdatedRaw = s.stationUpdatedRaw || s.last_updated || s.updated_at || '';
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
        const compareFallback = stationsInRadius.length === 0;
        const compareSource = compareFallback ? validStations : stationsInRadius;
        const compare = {
            fallback: compareFallback,
            items: fuelCompareRows(compareSource, best, compareFallback ? 'distance' : 'price').map(item => {
                const original = compareSource.find(s => String(s.id) === String(item.id)) || item;
                return { ...item, priceConfidence: priceConfidenceFor(original, compareSource) };
            })
        };
        
        return res.status(200).json({
            stationId: best.id,
            price: best.price.toString(), 
            unit: "p", 
            name: best.name || best.brand || "Fuel Station",
            dist: `${best.dist.toFixed(1)} mi`, 
            updated: source,
            datasetUpdated: source,
            stationUpdated: best.stationUpdated || '', 
            priceConfidence: priceConfidenceFor(best, compareSource),
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
