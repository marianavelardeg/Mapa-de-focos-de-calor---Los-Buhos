<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Mapa Web de Incendios</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>

  <style>
    html, body { margin: 0; padding: 0; height: 100%; }
    #map { position: absolute; top: 0; bottom: 0; left: 0; right: 400px; z-index: 500; }
    #sidebar {
      position: absolute; top: 0; bottom: 0; right: 0;
      width: 400px; padding: 20px;
      background: #fff; overflow: auto;
      z-index: 1000;
    }
    #chart-img {
      display: block;
      width: 100%;
      max-width: 360px;
      height: auto;
      margin: 20px auto;
    }
    .marker-cluster {
      color: #fff; text-align: center; border-radius: 50%; font-size: 14px;
      width: 40px; height: 40px; line-height: 40px; border: 2px solid white;
    }
    .marker-cluster-small  { background-color: rgba(0,200,0,0.6); }
    .marker-cluster-medium { background-color: rgba(255,200,0,0.6); }
    .marker-cluster-large  { background-color: rgba(255,0,0,0.6); }
    .leaflet-tooltip.fecha-tooltip {
      background: rgba(255,255,255,0.8); border: none; color: #000; font-size: 12px; font-weight: bold;
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="sidebar">
    <h2>Controles</h2>
    <label><input type="checkbox" id="cb-2022" checked> Focos 2022</label><br>
    <label><input type="checkbox" id="cb-2023" checked> Focos 2023</label><br>
    <label><input type="checkbox" id="cb-2024" checked> Focos 2024</label><br>
    <label><input type="checkbox" id="cb-lim"  checked> Límites de predios</label><br>
    <label><input type="checkbox" id="cb-pot"  checked> Potreros</label><br>

    <h2>Estadísticas</h2>
    <img id="chart-img" src="static_focos_chart.png" alt="Gráfico de focos por año">
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
  <script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>

  <script>
  (async()=>{
    const map = L.map('map', { zoomControl:false, attributionControl:false });
    L.control.zoom({ position:'topleft' }).addTo(map);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    const [limGeo, potGeo] = await Promise.all([
      fetch('Data/limites_propiedades.geojson').then(r=>r.json()),
      fetch('Data/potreros.geojson').then(r=>r.json())
    ]);
    const layerLim = L.geoJSON(limGeo, { style:{color:'#000',weight:2} }).addTo(map);
    const layerPot = L.geoJSON(potGeo, { style:{color:'#555',weight:1,dashArray:'4 4'} }).addTo(map);
    map.fitBounds(layerLim.getBounds());

    let unionPoly = limGeo.features[0];
    for (let i=1; i<limGeo.features.length; i++) {
      unionPoly = turf.union(unionPoly, limGeo.features[i]);
    }
    const bufferPoly = turf.buffer(unionPoly, 1, { units:'kilometers' });

    function makeCluster(){
      return L.markerClusterGroup({
        iconCreateFunction: c=>{
          const n=c.getChildCount();
          const cls = n<10? 'small': n<50? 'medium':'large';
          return L.divIcon({ html:n, className:'marker-cluster marker-cluster-'+cls, iconSize:[40,40] });
        }
      });
    }

    const ptInBuffer = pt => turf.booleanPointInPolygon(pt, bufferPoly);
    const ptInUnion  = pt => turf.booleanPointInPolygon(pt, unionPoly);

    const años = [2022,2023,2024];
    const clusters = {};

    for (let año of años) {
      const raw = await fetch(`https://github.com/marianavelardeg/Mapa-de-focos-de-calor---Los-Buhos/releases/download/v1.0/focos_${año}.geojson`).then(r=>r.json());
      const pts = raw.features.filter(pt => ptInBuffer(pt));
      const cl = makeCluster();

      pts.forEach(pt=>{
        const [lon, lat] = pt.geometry.coordinates;
        const inside = ptInUnion(pt);
        const m = L.circleMarker([lat, lon], {
          radius: inside ? 6 : 0,
          fillOpacity: inside ? 0.8 : 0,
          color:      inside ? '#f00' : undefined,
          weight:     inside ? 1   : undefined,
          fillColor:  inside ? '#f00' : undefined
        });
        if (inside) {
          m.on('mouseover', ()=>{
            const fecha = pt.properties.date_text || pt.properties.ACQ_DATE;
            m.bindTooltip(fecha, { permanent:false, direction:'top', className:'fecha-tooltip' }).openTooltip();
          }).on('mouseout', ()=> m.closeTooltip());
        }
        cl.addLayer(m);
      });

      cl.eachLayer(layer=> {
        if (layer.getChildCount && layer.getChildCount()===1) {
          const single = layer.getAllChildMarkers()[0];
          const [lat, lon] = single.getLatLng().toArray();
          cl.removeLayer(layer);
          const fecha = single.feature.properties.date_text || single.feature.properties.ACQ_DATE;
          L.circleMarker([lat, lon], {
            radius:6, fillColor:'#f00', color:'#800', weight:1, fillOpacity:0.8
          })
          .bindTooltip(fecha, { permanent:true, direction:'center', className:'fecha-tooltip' })
          .addTo(map);
        }
      });

      clusters[año] = cl.addTo(map);
    }

    document.getElementById('cb-2022').onchange = e=> e.target.checked? map.addLayer(clusters[2022]) : map.removeLayer(clusters[2022]);
    document.getElementById('cb-2023').onchange = e=> e.target.checked? map.addLayer(clusters[2023]) : map.removeLayer(clusters[2023]);
    document.getElementById('cb-2024').onchange = e=> e.target.checked? map.addLayer(clusters[2024]) : map.removeLayer(clusters[2024]);
    document.getElementById('cb-lim') .onchange = e=> e.target.checked? map.addLayer(layerLim) : map.removeLayer(layerLim);
    document.getElementById('cb-pot') .onchange = e=> e.target.checked? map.addLayer(layerPot) : map.removeLayer(layerPot);

    console.log('✅ Mapa cargado con datos desde Release');
  })();
  </script>
</body>
</html>
