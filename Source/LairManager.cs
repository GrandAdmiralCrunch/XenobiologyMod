using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Places XENO_LAIR models (caves, nests...) on the surface, keeps their unique resident alive
    /// while a vessel is near, runs the door and marks discovered lairs with a waypoint.
    /// The exact site is picked once per save (the flattest dry spot in the search area) and stored
    /// in XenoScenario so it never moves.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Flight, false)]
    public class LairManager : MonoBehaviour
    {
        public static LairManager Instance { get; private set; }
        readonly Dictionary<string, LairInstance> live = new Dictionary<string, LairInstance>();
        float timer;
        CelestialBody lastBody;

        void Awake() { Instance = this; }

        /// <summary>The nearest specimen marker (spec_<lifeform>_NN in a lair model: corals and other fixed life) within maxDist.
        /// Undiscovered species win over known ones when both are within their observe range.</summary>
        public LairInstance NearestSpecimen(Vector3d pos, double maxDist, out LifeformDef def, out double dist)
        {
            def = null; dist = double.MaxValue; LairInstance best = null;
            bool bestNew = false;
            var scen = XenoScenario.Instance;
            foreach (var l in live.Values)
            {
                if (l == null) continue;
                foreach (var sp in l.specimens)
                {
                    if (sp.t == null) continue;
                    double d = ((Vector3d)sp.t.position - pos).magnitude;
                    if (d > maxDist) continue;
                    bool isNew = scen != null && !scen.IsDiscovered(sp.def) && d <= sp.def.ObserveRange;
                    if ((isNew && !bestNew) || (isNew == bestNew && d < dist)) { def = sp.def; dist = d; best = l; bestNew = isNew; }
                }
            }
            return best;
        }

        /// <summary>The loaded lair whose interior contains this vessel, if any.</summary>
        public LairInstance InsideOf(Vessel v)
        {
            if (v == null) return null;
            foreach (var l in live.Values)
                if (l != null && l.body == v.mainBody && l.Inside(v.latitude, v.longitude) && (!l.def.underwater || v.altitude < -1.0)) return l;
            return null;
        }

        void OnDestroy()
        {
            foreach (var l in live.Values) if (l != null) Destroy(l.gameObject);
            live.Clear();
            if (Instance == this) Instance = null;
        }

        void Update()
        {
            if (!XenoDatabase.Loaded || !FlightGlobals.ready || XenoScenario.Instance == null) return;
            Vessel v = FlightGlobals.ActiveVessel;
            if (v == null) return;
            if (v.mainBody != lastBody)
            {
                foreach (var l in live.Values) if (l != null) Destroy(l.gameObject);
                live.Clear();
                lastBody = v.mainBody;
            }
            timer -= Time.deltaTime;
            if (timer > 0) return;
            timer = 1f;

            UpdateLandmarks(v);
            RegisterAnomalies();
            foreach (var d in XenoDatabase.Lairs.Values)
            {
                if (d.celestialBody != v.mainBody) continue;
                LairRecord rec = Site(d);
                if (rec == null) continue;
                if (d.clearScatters) ParallaxCompat.ClearAround(d.celestialBody, d.name, rec.lat, rec.lon, d.scatterClearRadius > 0 ? d.scatterClearRadius : d.footprint * 1.5, v);
                Vector3d site = v.mainBody.GetWorldSurfacePosition(rec.lat, rec.lon, Geo.Terrain(v.mainBody, rec.lat, rec.lon));
                double dist = (v.GetWorldPos3D() - site).magnitude;

                if (!rec.discovered && dist < d.discoverRange && v.altitude < 25000)
                {
                    rec.discovered = true;
                    string msg = string.IsNullOrEmpty(d.discoverMessage) ? "Something enormous has been moving boulders around" : d.discoverMessage;
                    ScreenMessages.PostScreenMessage(string.Format("<color=#C8B08A>{3} {0:F0} km {1} of here...</color>",
                        dist / 1000.0, Geo.CompassName(Geo.Bearing(v.mainBody, v.latitude, v.longitude, rec.lat, rec.lon)), msg), 8f, ScreenMessageStyle.UPPER_CENTER);
                }
                if (rec.discovered && d.waypoint && XenoSettings.LairWaypoints) EnsureWaypoint(d, rec);

                LairInstance inst;
                live.TryGetValue(d.name, out inst);
                if (dist < d.loadRange)
                {
                    if (inst == null)
                    {
                        inst = LairInstance.Build(d, rec, v.mainBody);
                        if (inst == null) continue;
                        live[d.name] = inst;
                    }
                    inst.Tick(v, dist);
                }
                else if (inst != null) { Destroy(inst.gameObject); live.Remove(d.name); }
            }
        }

        // ------------------------------------------------------------------ anomalies

        bool anomaliesDone;
        readonly HashSet<string> landmarkAnomalies = new HashSet<string>();

        /// <summary>Every lair (on every body) and every sited landmark is listed as a surface anomaly,
        /// so KerbNet's anomaly scan (and mods that read pqsSurfaceObjects, like SCANsat) can find them.</summary>
        void RegisterAnomalies()
        {
            var scen = XenoScenario.Instance;
            if (!anomaliesDone)
            {
                anomaliesDone = true;
                foreach (var d in XenoDatabase.Lairs.Values)
                {
                    if (!d.anomaly || d.celestialBody == null) continue;
                    LairRecord rec = Site(d);
                    if (rec != null) XenoAnomaly.Register(d.celestialBody, "XenoLair_" + d.name, d.displayName, rec.lat, rec.lon);
                }
            }
            foreach (var kv in scen.Lairs)
            {
                if (!kv.Key.StartsWith("landmark:") || landmarkAnomalies.Contains(kv.Key)) continue;
                FossilDef f; if (!XenoDatabase.Fossils.TryGetValue(kv.Key.Substring(9), out f) || f.celestialBody == null) continue;
                landmarkAnomalies.Add(kv.Key);
                XenoAnomaly.Register(f.celestialBody, "XenoLandmark_" + f.name, f.displayName, kv.Value.lat, kv.Value.lon);
            }
        }

        // ------------------------------------------------------------------ site selection

        public static LairRecord Site(LairDef d)
        {
            var scen = XenoScenario.Instance;
            if (scen == null) return null;
            LairRecord rec;
            if (scen.Lairs.TryGetValue(d.name, out rec))
            {   // keep the stored site unless the config has moved the lair somewhere else entirely
                double n, e; Geo.Delta(d.celestialBody, d.latitude, d.longitude, rec.lat, rec.lon, out n, out e);
                bool ok = Math.Sqrt(n * n + e * e) <= d.searchRadius * (d.underwater ? 40 : 4.5) + 500;
                if (ok && d.underwater)
                {   // sea-floor lairs must sit in their depth band (older versions could store a site that was far too deep)
                    double h = Geo.Terrain(d.celestialBody, rec.lat, rec.lon);
                    ok = h >= d.minAltitude - 8 && h <= d.maxAltitude + 4;
                    if (!ok) XenoLog.Info(string.Format("Lair {0}: stored site is {1:F0} m, outside {2:F0}..{3:F0}; choosing a new site", d.name, h, d.minAltitude, d.maxAltitude));
                }
                if (ok) return rec;
                if (!d.underwater) XenoLog.Info("Lair " + d.name + " has moved in its config; choosing a new site");
            }
            rec = d.underwater ? FindSeabedSite(d) : FindSite(d);
            scen.Lairs[d.name] = rec;
            XenoLog.Info(string.Format("Lair {0} sited at {1:F4},{2:F4} facing {3:F0}, ground {4:F1} m", d.name, rec.lat, rec.lon, rec.heading, Geo.Terrain(d.celestialBody, rec.lat, rec.lon)));
            return rec;
        }

        /// <summary>Sea-floor sites: search outward from the centre in rings (step growing with distance) for flat ground
        /// whose depth stays inside the band across the whole footprint. Stops once enough candidates are found, so the
        /// nearest good patch wins. Falls back to the shallowest-in-band point seen, then to the least-bad one.</summary>
        static LairRecord FindSeabedSite(LairDef d)
        {
            CelestialBody b = d.celestialBody;
            double mid = (d.minAltitude + d.maxAltitude) * 0.5;
            double bestScore = double.MaxValue, bestLat = d.latitude, bestLon = d.longitude;
            double nearScore = double.MaxValue, nearLat = d.latitude, nearLon = d.longitude;     // closest to the band at all
            int found = 0, samples = 0;
            double maxR = Math.Max(d.searchRadius * 10.0, 60000.0);
            for (double r = 0; r <= maxR; r += Math.Max(250.0, r / 30.0))
            {
                int n = r < 1 ? 1 : (int)Math.Ceiling(2 * Math.PI * r / Math.Max(250.0, r / 30.0));
                for (int k = 0; k < n; k++)
                {
                    double a = 2 * Math.PI * k / n, la = d.latitude, lo = d.longitude;
                    Geo.Offset(b, ref la, ref lo, Math.Cos(a) * r, Math.Sin(a) * r);
                    double h = Geo.Terrain(b, la, lo); samples++;
                    double miss = h > d.maxAltitude ? h - d.maxAltitude : h < d.minAltitude ? d.minAltitude - h : 0;
                    if (h < 0 && miss + r / 20000.0 < nearScore) { nearScore = miss + r / 20000.0; nearLat = la; nearLon = lo; }
                    if (miss > 0) continue;
                    double rough = 0;
                    for (int j = 0; j < 12; j++)
                    {
                        double aa = j * Math.PI / 6, rr = (j % 2 == 0) ? d.footprint : d.footprint * 0.5;
                        double sla = la, slo = lo;
                        Geo.Offset(b, ref sla, ref slo, Math.Cos(aa) * rr, Math.Sin(aa) * rr);
                        double sh = Geo.Terrain(b, sla, slo);
                        if (sh > d.maxAltitude + 3 || sh < d.minAltitude - 6) { rough = double.MaxValue; break; }
                        rough = Math.Max(rough, Math.Abs(sh - h));
                    }
                    if (rough == double.MaxValue) continue;
                    found++;
                    double score = rough + Math.Abs(h - mid) * 0.08 + r / 4000.0;
                    if (score < bestScore) { bestScore = score; bestLat = la; bestLon = lo; }
                }
                if (found >= 25) break;
            }
            if (bestScore == double.MaxValue)
            {
                XenoLog.Warn(string.Format("Lair {0}: no flat sea floor between {1:F0} and {2:F0} m found within {3:F0} km ({4} samples); using the nearest in-band water", d.name, d.minAltitude, d.maxAltitude, maxR / 1000, samples));
                bestLat = nearLat; bestLon = nearLon;
            }
            else XenoLog.Info(string.Format("Lair {0}: {1} flat sea-floor candidates after {2} samples", d.name, found, samples));
            var rec = new LairRecord { id = d.name, lat = bestLat, lon = bestLon, heading = d.heading >= 0 ? d.heading : 0 };
            return rec;
        }

        static LairRecord FindSite(LairDef d)
        {
            CelestialBody b = d.celestialBody;
            double bestScore = double.MaxValue, bestLat = d.latitude, bestLon = d.longitude;
            const int N = 12;
            // widen the search (up to 4x, 16x for sea-floor sites) if nothing in the circle is in the altitude band
            double maxWiden = d.underwater ? 16.01 : 4.01;
            for (double radius = d.searchRadius; bestScore == double.MaxValue && radius <= d.searchRadius * maxWiden; radius *= 2)
            for (int i = -N; i <= N; i++)
                for (int j = -N; j <= N; j++)
                {
                    double dn = i * radius / N, de = j * radius / N;
                    double r = Math.Sqrt(dn * dn + de * de);
                    if (r > radius) continue;
                    double la = d.latitude, lo = d.longitude;
                    Geo.Offset(b, ref la, ref lo, dn, de);
                    double h = Geo.Terrain(b, la, lo);
                    if (h < d.minAltitude || h > d.maxAltitude) continue;
                    double rough = 0;
                    for (int k = 0; k < 12; k++)
                    {
                        double a = k * Math.PI / 6, rr = (k % 2 == 0) ? d.footprint : d.footprint * 0.5;
                        double sla = la, slo = lo;
                        Geo.Offset(b, ref sla, ref slo, Math.Cos(a) * rr, Math.Sin(a) * rr);
                        double sh = Geo.Terrain(b, sla, slo);
                        if (d.underwater ? (sh > d.maxAltitude + 3 || sh < d.minAltitude - 8) : sh < d.minAltitude * 0.5) { rough = double.MaxValue; break; }
                        rough = Math.Max(rough, Math.Abs(sh - h));
                    }
                    if (rough == double.MaxValue) continue;
                    double score = rough + r / radius * 2.0;
                    if (score < bestScore) { bestScore = score; bestLat = la; bestLon = lo; }
                }

            var rec = new LairRecord { id = d.name, lat = bestLat, lon = bestLon };
            if (d.heading >= 0) rec.heading = d.heading;
            else
            {
                // face the entrance downhill so the mouth opens onto the lowest ground
                double low = double.MaxValue;
                for (int k = 0; k < 16; k++)
                {
                    double a = k * 22.5, sla = bestLat, slo = bestLon;
                    Geo.Offset(b, ref sla, ref slo, Math.Cos(a * Geo.Deg2Rad) * d.footprint * 2.5, Math.Sin(a * Geo.Deg2Rad) * d.footprint * 2.5);
                    double sh = Geo.Terrain(b, sla, slo);
                    if (sh < low) { low = sh; rec.heading = a; }
                }
            }
            return rec;
        }

        // ------------------------------------------------------------------ waypoint

        readonly HashSet<string> waypointsChecked = new HashSet<string>();

        // ------------------------------------------------------------------ landmark fossils (the Fallen Titan)

        readonly HashSet<string> landmarkWaypoints = new HashSet<string>();

        void UpdateLandmarks(Vessel v)
        {
            var sp = XenoSpawner.Instance; var scen = XenoScenario.Instance;
            if (sp == null) return;
            foreach (var f in XenoDatabase.FossilsOn(v.mainBody))
            {
                if (!f.landmark) continue;
                string key = "landmark:" + f.name;
                LairRecord rec;
                if (!scen.Lairs.TryGetValue(key, out rec))
                {
                    rec = FindLandmarkSite(f);
                    if (rec == null) continue;
                    scen.Lairs[key] = rec;
                    XenoLog.Info(string.Format("Landmark {0} sited at {1:F4},{2:F4} facing {3:F0}", f.name, rec.lat, rec.lon, rec.heading));
                }
                Vector3d site = v.mainBody.GetWorldSurfacePosition(rec.lat, rec.lon, Geo.Terrain(v.mainBody, rec.lat, rec.lon));
                double dist = (v.GetWorldPos3D() - site).magnitude;
                if (!rec.discovered && dist < f.discoverRange && v.altitude < 40000)
                {
                    rec.discovered = true;
                    ScreenMessages.PostScreenMessage(string.Format("<color=#E0C890>{0} ({1:F0} km {2})</color>",
                        string.IsNullOrEmpty(f.discoverMessage) ? "Something vast lies across the land" : f.discoverMessage,
                        dist / 1000.0, Geo.CompassName(Geo.Bearing(v.mainBody, v.latitude, v.longitude, rec.lat, rec.lon))), 10f, ScreenMessageStyle.UPPER_CENTER);
                }
                if (rec.discovered && XenoSettings.LairWaypoints && landmarkWaypoints.Add(key)) AddWaypoint(f.displayName, f.celestialBody, rec, f.name);
                FossilSite s; sp.Sites.TryGetValue(key, out s);
                if (dist < f.loadRange)
                {
                    if (s == null)
                    {
                        bool studied = scen.StudiedSites.Contains(key);
                        GameObject go = FossilSite.Build(f, "XenoLandmark_" + f.name, studied);
                        s = go.AddComponent<FossilSite>();
                        s.heading = rec.heading;
                        s.Init(f, v.mainBody, rec.lat, rec.lon, key, studied);
                        sp.Sites[key] = s;
                    }
                }
                else if (s != null) { Destroy(s.gameObject); sp.Sites.Remove(key); }
            }
        }

        /// <summary>Scan for the biggest, flattest patch of the landmark's biome (or search round its centre).</summary>
        static LairRecord FindLandmarkSite(FossilDef f)
        {
            CelestialBody b = f.celestialBody;
            var cands = new List<KeyValuePair<double, double>>();
            if (!double.IsNaN(f.searchLat) && f.searchRadius > 0)
            {
                const int N = 16;
                for (int i = -N; i <= N; i++)
                    for (int j = -N; j <= N; j++)
                    {
                        double la = f.searchLat, lo = f.searchLon;
                        Geo.Offset(b, ref la, ref lo, i * f.searchRadius / N, j * f.searchRadius / N);
                        if (f.InBiome(Geo.Biome(b, la, lo))) cands.Add(new KeyValuePair<double, double>(la, lo));
                    }
            }
            else
            {
                const double step = 0.5;
                for (double la = -70; la <= 70; la += step)
                    for (double lo = -180; lo < 180; lo += step)
                    {
                        if (!f.InBiome(Geo.Biome(b, la, lo))) continue;
                        // deep inside the biome: all eight neighbours a step away are the same biome
                        bool deep = true;
                        for (int k = 0; k < 8 && deep; k++)
                        {
                            double a = k * Math.PI / 4;
                            if (!f.InBiome(Geo.Biome(b, la + Math.Cos(a) * step, lo + Math.Sin(a) * step))) deep = false;
                        }
                        if (deep) cands.Add(new KeyValuePair<double, double>(la, lo));
                    }
            }
            if (cands.Count == 0) { XenoLog.Warn("Landmark " + f.name + ": no " + string.Join("/", f.biomes) + " found"); return null; }
            // prefer flat ground, and somewhere reachable from the space centre (but not on its doorstep)
            CelestialBody home = FlightGlobals.GetHomeBody();
            double hLat = -0.0972, hLon = -74.5577;
            double bestScore = double.MaxValue; double bLa = cands[0].Key, bLo = cands[0].Value;
            var rng = new System.Random((int)XenoHash.Hash(f.name));
            if (cands.Count > 600) cands = cands.OrderBy(c => rng.Next()).Take(600).ToList();
            foreach (var c in cands)
            {
                double la = c.Key, lo = c.Value, h = Geo.Terrain(b, la, lo);
                if (b.ocean && h < 20) continue;
                double rough = 0;
                for (int k = 0; k < 12; k++)
                {
                    double a = k * Math.PI / 6, rr = (k % 2 == 0) ? f.footprint : f.footprint * 0.5;
                    double sla = la, slo = lo;
                    Geo.Offset(b, ref sla, ref slo, Math.Cos(a) * rr, Math.Sin(a) * rr);
                    double sh = Geo.Terrain(b, sla, slo);
                    if (b.ocean && sh < 1) { rough = double.MaxValue; break; }
                    rough = Math.Max(rough, Math.Abs(sh - h));
                }
                if (rough == double.MaxValue) continue;
                double km = 0;
                if (b == home) { double n, e; Geo.Delta(b, hLat, hLon, la, lo, out n, out e); km = Math.Sqrt(n * n + e * e) / 1000.0; }
                double score = rough + (b == home ? Math.Abs(km - 400) * 0.15 : 0);
                if (score < bestScore) { bestScore = score; bLa = la; bLo = lo; }
            }
            var rec = new LairRecord { id = "landmark:" + f.name, lat = bLa, lon = bLo };
            if (f.heading >= 0) rec.heading = f.heading;
            else
            {   // lay it along the direction where the ground changes least, so it rests along a valley rather than across ridges
                double bestVar = double.MaxValue;
                for (int k = 0; k < 12; k++)
                {
                    double a = k * 15.0, var_ = 0, h0 = Geo.Terrain(b, bLa, bLo);
                    foreach (double s in new[] { -1.0, -0.5, 0.5, 1.0 })
                    {
                        double sla = bLa, slo = bLo;
                        Geo.Offset(b, ref sla, ref slo, Math.Cos(a * Geo.Deg2Rad) * f.footprint * s, Math.Sin(a * Geo.Deg2Rad) * f.footprint * s);
                        var_ += Math.Abs(Geo.Terrain(b, sla, slo) - h0);
                    }
                    if (var_ < bestVar) { bestVar = var_; rec.heading = a; }
                }
            }
            return rec;
        }

        void AddWaypoint(string name, CelestialBody body, LairRecord rec, string seedName)
        {
            try
            {
                var mgr = FinePrint.WaypointManager.Instance();
                if (mgr != null && mgr.Waypoints != null && mgr.Waypoints.Any(w => w != null && w.name == name && w.celestialName == body.name)) return;
                var wp = new FinePrint.Waypoint();
                wp.celestialName = body.name; wp.latitude = rec.lat; wp.longitude = rec.lon; wp.altitude = 0; wp.height = 0;
                wp.name = name; wp.id = "custom"; wp.seed = (int)XenoHash.Hash(seedName);
                wp.isOnSurface = true; wp.isNavigatable = true; wp.isCustom = true; wp.visible = true; wp.navigationId = Guid.NewGuid();
                FinePrint.WaypointManager.AddWaypoint(wp);
            }
            catch (Exception e) { XenoLog.Warn("Could not add landmark waypoint: " + e.Message); }
        }

        void EnsureWaypoint(LairDef d, LairRecord rec)
        {
            if (!waypointsChecked.Add(d.name)) return;
            try
            {
                var mgr = FinePrint.WaypointManager.Instance();
                if (mgr != null && mgr.Waypoints != null && mgr.Waypoints.Any(w => w != null && w.name == d.displayName && w.celestialName == d.celestialBody.name)) return;
                var wp = new FinePrint.Waypoint();
                wp.celestialName = d.celestialBody.name;
                wp.latitude = rec.lat; wp.longitude = rec.lon;
                wp.altitude = 0;
                wp.height = 0;
                wp.name = d.displayName;
                wp.id = "custom";
                wp.seed = (int)XenoHash.Hash(d.name);
                wp.isOnSurface = true;
                wp.isNavigatable = true;
                wp.isCustom = true;
                wp.visible = true;
                wp.navigationId = Guid.NewGuid();
                FinePrint.WaypointManager.AddWaypoint(wp);
            }
            catch (Exception e) { XenoLog.Warn("Could not add lair waypoint: " + e.Message); }
        }
    }

    /// <summary>One placed lair model plus its resident.</summary>
    public class LairInstance : MonoBehaviour
    {
        public LairDef def;
        public CelestialBody body;
        public double lat, lon, heading, alt;
        public double entranceLat, entranceLon, denLat, denLon, penLat, penLon;
        double entranceZ, denZ;
        Animation[] anims;
        Light[] lights;
        bool lightsOn = true;
        int door = -1;            // -1 unknown, 0 closed, 1 open
        public CreatureController resident;
        public XenoForest forest;
        public readonly Dictionary<string, double[]> spots = new Dictionary<string, double[]>();   // named places (lat, lon)
        bool flockSpawned; bool[] flockDone;
        static int serial;

        public static LairInstance Build(LairDef d, LairRecord rec, CelestialBody b)
        {
            GameObject prefab = string.IsNullOrEmpty(d.model) ? null : GameDatabase.Instance.GetModelPrefab(d.model);
            if (prefab == null && d.forest == null) { XenoLog.Warn("Lair " + d.name + ": model '" + d.model + "' not found"); return null; }
            GameObject go = prefab != null ? Instantiate(prefab) : new GameObject();
            go.name = "XenoLair_" + d.name;
            go.SetActive(true);
            var L = go.AddComponent<LairInstance>();
            L.def = d; L.body = b; L.lat = rec.lat; L.lon = rec.lon; L.heading = rec.heading;
            L.alt = Geo.Terrain(b, rec.lat, rec.lon) - d.sink;

            // colliders behave like terrain: kerbals and wheels stand on them, creature ground rays hit them
            foreach (Collider c in go.GetComponentsInChildren<Collider>(true)) { c.gameObject.layer = 15; c.enabled = true; }
            // a convex mesh collider is a solid hull: it would seal the tunnel and fill the cave
            foreach (MeshCollider mc in go.GetComponentsInChildren<MeshCollider>(true)) mc.convex = false;
            foreach (Rigidbody rb in go.GetComponentsInChildren<Rigidbody>(true)) Destroy(rb);

            // glue to the planet (like a PQSCity): floating origin and rotation are then handled for us
            Vector3 up, north, east;
            Geo.Frame(b, rec.lat, rec.lon, out up, out north, out east);
            Vector3 fwd = north * (float)Math.Cos(rec.heading * Geo.Deg2Rad) + east * (float)Math.Sin(rec.heading * Geo.Deg2Rad);
            go.transform.position = b.GetWorldSurfacePosition(rec.lat, rec.lon, L.alt);
            go.transform.rotation = Quaternion.LookRotation(fwd, up);
            Transform parent = b.pqsController != null ? b.pqsController.transform : b.transform;
            go.transform.SetParent(parent, true);

            L.anims = go.GetComponentsInChildren<Animation>(true);
            // point lights are expensive in KSP's forward renderer (every lit object is drawn again per light): no
            // shadows, and they only switch on when someone is close enough to be inside or at the mouth
            L.lights = go.GetComponentsInChildren<Light>(true);
            foreach (Light lt in L.lights) { lt.shadows = LightShadows.None; lt.renderMode = LightRenderMode.Auto; }
            L.SetLights(false);
            foreach (Animation a in L.anims) { a.playAutomatically = false; a.cullingType = AnimationCullingType.AlwaysAnimate; }
            L.InitAmbient(go);
            L.PlaceFossils(go);
            if (d.underwater) go.AddComponent<ReefAmbience>().Init(L);
            if (d.forest != null) L.forest = go.AddComponent<XenoForest>(); 

            L.Point(d.entrance, 0, 0, out L.entranceLat, out L.entranceLon);
            L.Point(d.den, 0, 0, out L.denLat, out L.denLon);
            L.Point(d.pen, 0, 0, out L.penLat, out L.penLon);
            double x;
            L.Local(L.entranceLat, L.entranceLon, out x, out L.entranceZ);
            L.Local(L.denLat, L.denLon, out x, out L.denZ);
            if (L.forest != null) L.forest.Init(L, d.forest);
            XenoLog.Info("Lair " + d.name + " placed");
            return L;
        }

        void Point(string child, double fbN, double fbE, out double la, out double lo)
        {
            Transform t = null;
            if (!string.IsNullOrEmpty(child)) foreach (Transform c in GetComponentsInChildren<Transform>(true)) if (c.name == child) { t = c; break; }
            if (t != null) { la = body.GetLatitude(t.position); lo = body.GetLongitude(t.position); return; }
            la = lat; lo = lon; Geo.Offset(body, ref la, ref lo, fbN, fbE);
        }

        /// <summary>Metres across (x, right of the entrance axis) and along (z, toward the entrance) the lair.</summary>
        public void Local(double la, double lo, out double x, out double z)
        {
            double n, e; Geo.Delta(body, lat, lon, la, lo, out n, out e);
            double h = heading * Geo.Deg2Rad;
            z = n * Math.Cos(h) + e * Math.Sin(h);
            x = e * Math.Cos(h) - n * Math.Sin(h);
        }

        public bool Inside(double la, double lo)
        {
            if (def.surveyRadius > 0)
            {
                double n, e; Geo.Delta(body, lat, lon, la, lo, out n, out e);
                return n * n + e * e < def.surveyRadius * def.surveyRadius;
            }
            double x, z; Local(la, lo, out x, out z);
            return z < entranceZ - 6 && z > denZ - 40 && Math.Abs(x) < 45;
        }

        public double DistFromEntrance(double la, double lo)
        {
            double n, e; Geo.Delta(body, entranceLat, entranceLon, la, lo, out n, out e);
            return Math.Sqrt(n * n + e * e);
        }

        public void SetDoor(bool open, bool instant = false)
        {
            int want = open ? 1 : 0;
            if (door == want) return;
            instant |= door < 0;
            door = want;
            string clip = open ? def.doorOpenAnim : def.doorCloseAnim;
            foreach (Animation a in anims)
            {
                AnimationState st = a[clip];
                if (st == null) continue;
                st.wrapMode = WrapMode.ClampForever;
                a.Stop();
                a.Play(clip);
                st.normalizedTime = instant ? 1f : 0f;
                if (instant) a.Sample();
            }
        }

        void SetLights(bool on)
        {
            if (on == lightsOn || lights == null) return;
            lightsOn = on;
            foreach (Light lt in lights) if (lt != null) lt.enabled = on;
        }

        // ------------------------------------------------------------------ ambient motion: swaying fans, breathing glow
        Transform[] swayers; Quaternion[] swayBase; float[] swayPhase, swayRate;
        Material[] glowMats; Color[] glowBase; float[] glowPhase;
        double lastDist = double.MaxValue;
        bool isDay = true;

        void InitAmbient(GameObject go)
        {
            var sw = new List<Transform>();
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) if (t.name.StartsWith("sway", StringComparison.OrdinalIgnoreCase)) sw.Add(t);
            swayers = sw.ToArray();
            swayBase = swayers.Select(t => t.localRotation).ToArray();
            swayPhase = swayers.Select(t => (float)(XenoHash.Hash(t.name) % 6283u) / 1000f).ToArray();
            swayRate = swayers.Select(t => 0.55f + (float)(XenoHash.Hash(t.name + "r") % 500u) / 1000f).ToArray();
            var mats = new List<Material>();
            foreach (Renderer r in go.GetComponentsInChildren<Renderer>(true))
                foreach (Material m in r.sharedMaterials)
                    if (m != null && m.HasProperty("_EmissiveColor") && !mats.Contains(m)) mats.Add(m);
            glowMats = mats.ToArray();
            glowBase = glowMats.Select(m => m.GetColor("_EmissiveColor")).ToArray();
            glowPhase = glowMats.Select((m, i) => i * 2.1f).ToArray();
            var dl = new List<GameObject>();
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) if (t.name.StartsWith("dayonly", StringComparison.OrdinalIgnoreCase)) dl.Add(t.gameObject);
            dayOnly = dl.ToArray();
            var det = new List<Renderer>();
            foreach (Renderer r in go.GetComponentsInChildren<Renderer>(true))
            {
                string n = r.gameObject.name;
                if (n.StartsWith("coral_", StringComparison.OrdinalIgnoreCase) || n.StartsWith("sway", StringComparison.OrdinalIgnoreCase) || n.StartsWith("dayonly", StringComparison.OrdinalIgnoreCase)) det.Add(r);
            }
            detail = det.ToArray();
            var dets = new List<Renderer>();
            foreach (Renderer r in detail) if (r.gameObject.name.StartsWith("coral_s_", StringComparison.OrdinalIgnoreCase)) dets.Add(r);
            detailSmall = dets.ToArray();
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true))
            {
                if (!t.name.StartsWith("spec_", StringComparison.OrdinalIgnoreCase)) continue;
                string id = t.name.Substring(5); int u = id.LastIndexOf('_'); if (u > 0) id = id.Substring(0, u);
                LifeformDef ld;
                if (XenoDatabase.Lifeforms.TryGetValue(id, out ld)) specimens.Add(new Specimen { t = t, def = ld });
                else XenoLog.Warn("Lair " + def.name + ": specimen marker " + t.name + " names no lifeform");
            }
        }
        Renderer[] detail, detailSmall; int detailShown = -1, smallShown = -1;
        readonly List<FossilSite> fossils = new List<FossilSite>();

        /// <summary>fossil_<fossilname>_## markers become studyable fossil sites pinned exactly where the marker is.</summary>
        void PlaceFossils(GameObject go)
        {
            var sp = XenoSpawner.Instance; var scen = XenoScenario.Instance;
            if (sp == null) return;
            foreach (Transform t in go.GetComponentsInChildren<Transform>(true)) PlaceFossil(t);
        }

        /// <summary>Turn one fossil_<name>_## marker into a studyable site (also used by generated lairs like forests).</summary>
        public void PlaceFossil(Transform t)
        {
            var sp = XenoSpawner.Instance; var scen = XenoScenario.Instance;
            if (sp == null) return;
            {
                if (!t.name.StartsWith("fossil_", StringComparison.OrdinalIgnoreCase)) return;
                string id = t.name.Substring(7); int u = id.LastIndexOf('_'); if (u > 0) id = id.Substring(0, u);
                FossilDef f;
                if (!XenoDatabase.Fossils.TryGetValue(id, out f)) { XenoLog.Warn("Lair " + def.name + ": fossil marker " + t.name + " names no fossil"); return; }
                string key = "lairfossil:" + def.name + ":" + t.name;
                bool studied = scen != null && scen.StudiedSites.Contains(key);
                GameObject fg = FossilSite.Build(f, "XenoLairFossil_" + t.name, studied);
                var site = fg.AddComponent<FossilSite>();
                site.lairOwned = true;
                double fla = body.GetLatitude(t.position), flo = body.GetLongitude(t.position);
                site.Init(f, body, fla, flo, key, studied);
                // the sea floor (PQS terrain) can rise inside a cave above the model's rock floor: never bury the slab
                site.Pin(Math.Max(body.GetAltitude(t.position), Geo.Terrain(body, fla, flo) - 0.05));
                sp.Sites[key] = site;
                fossils.Add(site);
            }
        }
        /// <summary>Move this lair's fossil sites up by d metres (a generated forest floor raised itself).</summary>
        public void LiftFossils(double d) { foreach (var f in fossils) if (f != null) f.Pin(f.alt + d); }
        public struct Specimen { public Transform t; public LifeformDef def; }
        public readonly List<Specimen> specimens = new List<Specimen>();

        /// <summary>True when every species with a marker in this lair has been discovered.</summary>
        public bool AllCatalogued()
        {
            var scen = XenoScenario.Instance;
            if (scen == null || specimens.Count == 0) return false;
            foreach (var sp in specimens) if (!scen.IsDiscovered(sp.def)) return false;
            return true;
        }
        public int CataloguedCount(out int total)
        {
            var seen = new HashSet<string>(); var known = new HashSet<string>(); var scen = XenoScenario.Instance;
            foreach (var sp in specimens) { seen.Add(sp.def.name); if (scen != null && scen.IsDiscovered(sp.def)) known.Add(sp.def.name); }
            total = seen.Count; return known.Count;
        }
        GameObject[] dayOnly; int dayShown = -1;

        void Update()
        {
            if (lastDist > 600) return;                                 // nobody close enough to notice
            float t = Time.time;
            float amp = def.swayAngle;
            for (int i = 0; i < swayers.Length; i++)
            {
                if (swayers[i] == null) continue;
                float ph = t * swayRate[i] + swayPhase[i];
                swayers[i].localRotation = swayBase[i] * Quaternion.Euler(Mathf.Sin(ph) * amp, Mathf.Sin(ph * 0.63f + 1.3f) * amp * 0.3f, Mathf.Sin(ph * 0.81f + 0.4f) * amp * 0.6f);
            }
            float lvl = isDay ? def.dayGlow : 1f;
            for (int i = 0; i < glowMats.Length; i++)
            {
                if (glowMats[i] == null) continue;
                float k = lvl * (1f + def.glowPulse * Mathf.Sin(t * 0.8f + glowPhase[i]) * Mathf.Sin(t * 0.23f + glowPhase[i] * 0.5f));
                Color c = glowBase[i] * k; c.a = glowBase[i].a;
                glowMats[i].SetColor("_EmissiveColor", c);
            }
        }

        public void Tick(Vessel v, double dist)
        {
            lastDist = dist;
            bool day = Geo.IsDaylight(body, lat, lon);
            isDay = day;
            if (def.detailRange > 0 && detail != null)
            {   // small corals are invisible (and fogged out) from far away: don't draw them
                int want = dist < def.detailRange ? 1 : 0;
                if (want != detailShown) { detailShown = want; smallShown = -1; foreach (var r in detail) if (r != null) r.enabled = want == 1; }
                float smallR = def.detailRangeSmall > 0 ? def.detailRangeSmall : def.detailRange * 0.3f;
                int ws = want == 1 && dist < smallR ? 1 : 0;
                if (ws != smallShown && detailSmall != null) { smallShown = ws; foreach (var r in detailSmall) if (r != null) r.enabled = ws == 1; }
            }
            if (dayOnly != null && dayOnly.Length > 0 && dayShown != (day ? 1 : 0))
            {   // sun shafts and the like
                dayShown = day ? 1 : 0;
                foreach (var g in dayOnly) if (g != null) g.SetActive(day);
            }
            SetLights(dist < XenoSettings.LairLightRange && (!def.lightsNightOnly || !day));
            var sp = XenoSpawner.Instance;
            if (def.residentDef != null && sp != null)
            {
                if (resident == null && dist < def.residentRange) SpawnResident(sp, day);
                else if (resident != null && dist > def.residentRange * 1.25 && !resident.Ridden)
                {
                    sp.Creatures.Remove(resident);
                    Destroy(resident.gameObject);
                    resident = null;
                }
            }
            if (resident == null) SetDoor(day);

            if (forest != null && !forest.Ready) return;      // spots aren't known until the forest is laid out
            if (!flockSpawned && sp != null && day && dist < def.residentRange && def.flockDef != null)
            {
                flockSpawned = true;
                int n = UnityEngine.Random.Range(def.flockMin, def.flockMax + 1);
                if (n > 0) sp.SpawnGroup(def.flockDef, body, penLat, penLon, n);
            }
            if (sp != null && dist < def.residentRange && def.flocks.Count > 0)
            {
                if (flockDone == null) flockDone = new bool[def.flocks.Count];
                for (int fi = 0; fi < def.flocks.Count; fi++)
                {
                    var f = def.flocks[fi];
                    if (flockDone[fi] || f.def == null) continue;
                    // each visitor arrives at its own time of day (owls at night, the rest by day)
                    var at = f.def.activeTime;
                    if ((at == ActivityTime.Day && !day) || (at == ActivityTime.Night && day)) continue;
                    flockDone[fi] = true;
                    int k = UnityEngine.Random.Range(f.min, f.max + 1);
                    if (k <= 0) continue;
                    double la = penLat, lo = penLon;
                    double[] spot; Transform tt;
                    if (!string.IsNullOrEmpty(f.at) && spots.TryGetValue(f.at, out spot)) { la = spot[0]; lo = spot[1]; }
                    else if (!string.IsNullOrEmpty(f.at) && (tt = FindChild(f.at)) != null) { la = body.GetLatitude(tt.position); lo = body.GetLongitude(tt.position); }
                    float a = UnityEngine.Random.Range(0f, Mathf.PI * 2f), r = UnityEngine.Random.Range(0f, f.spread);
                    Geo.Offset(body, ref la, ref lo, Math.Cos(a) * r, Math.Sin(a) * r);
                    var made = sp.SpawnGroup(f.def, body, la, lo, k);
                    if (f.leash > 0) foreach (var c in made) { c.homeLat = la; c.homeLon = lo; c.homeRadius = f.leash; }
                }
            }
        }

        Transform FindChild(string n) { foreach (Transform c in GetComponentsInChildren<Transform>(true)) if (c.name == n) return c; return null; }

        void SpawnResident(XenoSpawner sp, bool day)
        {
            double la, lo;
            if (def.residentDef.sessile)
            {   // a fixed colony (e.g. glowworms) lives in the den day and night and never wanders out
                resident = sp.Spawn(def.residentDef, body, denLat, denLon);
                if (resident == null) return;
                resident.lair = this;
                resident.gameObject.name = "Xeno_" + def.residentDef.name + "_resident" + (serial++);
                resident.ResetGround(Geo.Terrain(body, denLat, denLon));
                SetDoor(true, door < 0);
                return;
            }
            if (day)
            {
                la = penLat; lo = penLon;
                float a = UnityEngine.Random.Range(0f, Mathf.PI * 2f), r = UnityEngine.Random.Range(0f, def.leash * 0.4f);
                Geo.Offset(body, ref la, ref lo, Math.Cos(a) * r, Math.Sin(a) * r);
            }
            else { la = denLat; lo = denLon; }
            resident = sp.Spawn(def.residentDef, body, la, lo);
            if (resident == null) return;
            resident.lair = this;
            resident.gameObject.name = "Xeno_" + def.residentDef.name + "_resident" + (serial++);
            if (!day)
            {
                resident.ResetGround(Geo.Terrain(body, la, lo));   // inside the hill: don't let the first ground ray land on the roof
                resident.heading = Geo.Bearing(body, la, lo, entranceLat, entranceLon);
                resident.ForceSleep(9999f);
                SetDoor(false, true);
            }
            else SetDoor(true, door < 0);
        }

        void OnDestroy()
        {
            var spn = XenoSpawner.Instance;
            foreach (var fs in fossils) if (fs != null) { if (spn != null) spn.Sites.Remove(fs.siteId); Destroy(fs.gameObject); }
            if (glowMats != null)                                       // the materials are shared with the prefab: put them back
                for (int i = 0; i < glowMats.Length; i++) if (glowMats[i] != null) glowMats[i].SetColor("_EmissiveColor", glowBase[i]);
            if (resident != null)
            {
                if (XenoSpawner.Instance != null) XenoSpawner.Instance.Creatures.Remove(resident);
                Destroy(resident.gameObject);
            }
        }
    }
}
