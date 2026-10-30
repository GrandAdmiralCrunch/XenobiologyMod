using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Keeps a living population around the active vessel and places fossil outcrops.
    /// Which species can appear where is decided by deterministic "territory" cells, so a
    /// valley that had glimmerbacks yesterday will have them again tomorrow.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Flight, false)]
    public class XenoSpawner : MonoBehaviour
    {
        public static XenoSpawner Instance { get; private set; }

        public readonly List<CreatureController> Creatures = new List<CreatureController>();
        public readonly Dictionary<string, FossilSite> Sites = new Dictionary<string, FossilSite>();

        float timer;
        CelestialBody lastBody;
        System.Random rng = new System.Random();
        int serial;
        readonly HashSet<string> notifiedSites = new HashSet<string>();

        void Awake() { Instance = this; }

        void OnDestroy()
        {
            ClearAll();
            if (Instance == this) Instance = null;
        }

        public void ClearAll()
        {
            foreach (var c in Creatures) if (c != null) Destroy(c.gameObject);
            Creatures.Clear();
            foreach (var s in Sites.Values) if (s != null) Destroy(s.gameObject);
            Sites.Clear();
            FeatureField.ClearAll();
        }

        void Update()
        {
            if (!XenoDatabase.Loaded || !FlightGlobals.ready) return;
            Vessel v = FlightGlobals.ActiveVessel;
            if (v == null) return;

            if (v.mainBody != lastBody) { ClearAll(); lastBody = v.mainBody; }

            timer -= Time.deltaTime;
            if (timer > 0) return;
            timer = XenoSettings.SpawnCheckInterval;

            Tick(v);
        }

        void Tick(Vessel v)
        {
            CelestialBody body = v.mainBody;
            Vector3d obs = v.GetWorldPos3D();

            // cull
            for (int i = Creatures.Count - 1; i >= 0; i--)
            {
                var c = Creatures[i];
                if (c == null) { Creatures.RemoveAt(i); continue; }
                if (c.Ridden || c.lair != null) continue;   // lair residents are managed by LairManager
                if ((c.WorldPos - obs).magnitude > c.def.DespawnDistance) { Destroy(c.gameObject); Creatures.RemoveAt(i); }
            }
            foreach (var key in Sites.Keys.ToList())
            {
                var s = Sites[key];
                if (s != null && (s.def.landmark || s.lairOwned)) continue;      // landmarks and lair fossils are managed by LairManager
                if (s == null || (s.WorldPos - obs).magnitude > XenoSettings.FossilSpawnRadius * 1.3) { if (s != null) Destroy(s.gameObject); Sites.Remove(key); }
            }

            try { FeatureField.Update(v, body, this); } catch (Exception e) { XenoLog.Error("Features: " + e); }

            double height = Geo.HasSurface(body) ? v.altitude - Math.Max(body.ocean ? 0.0 : double.MinValue, v.terrainAltitude) : SkyGap(body, v.altitude);
            if (height > XenoSettings.MaxObserverAltitude) return;
            if (MountController.Instance != null && MountController.Instance.Mount != null && MountController.Instance.Mount.airborne && height > 300) return;
            if (TimeWarp.CurrentRate > 4f) return;

            BiosphereDef bio = XenoDatabase.BiosphereFor(body);
            UpdateFossils(v, body);
            if (bio == null || bio.extinct) return;

            int cap = Mathf.RoundToInt(XenoSettings.MaxActiveCreatures * Mathf.Clamp(XenoSettings.DensityMultiplier * bio.spawnDensity, 0f, 3f));
            cap = Mathf.Min(cap, XenoSettings.MaxActiveCreatures * 2);
            for (int attempt = 0; attempt < 4 && Load() < cap && Creatures.Count < XenoSettings.MaxCreatureObjects; attempt++)
                TrySpawnAround(v, body, bio);
            if (Time.time >= nextFarSpawn) { nextFarSpawn = Time.time + 20f; TryFarSpawn(v, body); }
        }

        float nextFarSpawn;

        /// <summary>Giants (spawnDistance) appear kilometres out, one at a time, so they can be seen coming.</summary>
        void TryFarSpawn(Vessel v, CelestialBody body)
        {
            foreach (var l in XenoDatabase.SpeciesOn(body))
            {
                if (l.spawnDistanceMax <= 0f || l.unique || l.colonyHost != null) continue;
                bool present = false;
                foreach (var c in Creatures) if (c != null && c.def == l) { present = true; break; }
                if (present || rng.NextDouble() > l.farSpawnChance * XenoSettings.DensityMultiplier) continue;
                double lat = v.latitude, lon = v.longitude, ang = rng.NextDouble() * Math.PI * 2;
                double dist = l.spawnDistanceMin + rng.NextDouble() * (l.spawnDistanceMax - l.spawnDistanceMin);
                Geo.Offset(body, ref lat, ref lon, Math.Cos(ang) * dist, Math.Sin(ang) * dist);
                if (!Allowed(l, body, lat, lon)) continue;
                SpawnGroup(l, body, lat, lon);
                if (!string.IsNullOrEmpty(l.farSpawnMessage))
                    ScreenMessages.PostScreenMessage(string.Format("<color=#B8D0FF>{0} ({1:F1} km {2})</color>", l.farSpawnMessage, dist / 1000.0,
                        Geo.CompassName(Geo.Bearing(body, v.latitude, v.longitude, lat, lon))), 8f, ScreenMessageStyle.UPPER_CENTER);
            }
        }

        bool Allowed(LifeformDef l, CelestialBody body, double lat, double lon)
        {
            if (!l.LivesInBiome(Geo.Biome(body, lat, lon))) return false;
            bool day = Geo.IsDaylight(body, lat, lon);
            if (l.activeTime == ActivityTime.Day && !day) return false;
            if (l.activeTime == ActivityTime.Night && day) return false;
            double terr = Geo.Terrain(body, lat, lon);
            if ((l.habitat == Habitat.Water || l.habitat == Habitat.Underwater) && (!body.ocean || terr > -l.size)) return false;
            if ((l.habitat == Habitat.Ground || l.habitat == Habitat.Flyer) && body.ocean && terr < 1 && !l.amphibious && !l.swims && !l.walkOnWater) return false;
            if (l.maxWadeDepth > 0f && body.ocean && terr < -l.maxWadeDepth) return false;
            double cell = XenoHash.CellSizeDeg(body);
            return XenoHash.Cell(body.name, (int)Math.Floor(lat / cell), (int)Math.Floor(lon / cell), l.name) <= l.territoryChance;
        }

        /// <summary>Gas giants: how far the observer is (vertically) from the nearest band where something lives.</summary>
        static double SkyGap(CelestialBody body, double altitude)
        {
            double gap = double.MaxValue;
            foreach (var l in XenoDatabase.SpeciesOn(body))
            {
                if (l.habitat != Habitat.Air) continue;
                double g = altitude < l.minAltitude ? l.minAltitude - altitude : (altitude > l.maxAltitude ? altitude - l.maxAltitude : 0.0);
                if (g < gap) gap = g;
            }
            return gap;
        }

        // -------------------------------------------------------------------- creatures

        void TrySpawnAround(Vessel v, CelestialBody body, BiosphereDef bio)
        {
            double lat = v.latitude, lon = v.longitude;
            double ang = rng.NextDouble() * Math.PI * 2;
            double dist = XenoSettings.MinSpawnDistance + rng.NextDouble() * (XenoSettings.SpawnRadius - XenoSettings.MinSpawnDistance);
            Geo.Offset(body, ref lat, ref lon, Math.Cos(ang) * dist, Math.Sin(ang) * dist);

            LifeformDef pick = PickSpecies(body, lat, lon);
            if (pick == null) return;
            SpawnGroup(pick, body, lat, lon);
        }

        /// <summary>Spawn-cap load: members of big schools count a quarter each.</summary>
        float Load()
        {
            float n = 0f;
            foreach (var c in Creatures) if (c != null) n += c.def.CapWeight;
            return n;
        }

        public List<LifeformDef> CandidatesAt(CelestialBody body, double lat, double lon)
        {
            string biome = Geo.Biome(body, lat, lon);
            double terr = Geo.Terrain(body, lat, lon);
            bool day = Geo.IsDaylight(body, lat, lon);
            double cell = XenoHash.CellSizeDeg(body);
            int cx = (int)Math.Floor(lat / cell), cy = (int)Math.Floor(lon / cell);
            var list = new List<LifeformDef>();
            foreach (var l in XenoDatabase.SpeciesOn(body))
            {
                if (l.unique || l.colonyHost != null || l.spawnDistanceMax > 0f || !l.LivesInBiome(biome)) continue;
                if (l.activeTime == ActivityTime.Day && !day) continue;
                if (l.activeTime == ActivityTime.Night && day) continue;
                switch (l.habitat)
                {
                    case Habitat.Ground:
                    case Habitat.Flyer: if (body.ocean && terr < 1 && !l.amphibious && !l.walkOnWater && !l.swims) continue; break;
                    case Habitat.Water: if (!body.ocean || terr > -(l.sessile ? Math.Min(l.size * 0.3, 6.0) : l.size * 0.6 + 1.0)) continue; break;
                    case Habitat.Underwater: if (!body.ocean || terr > (l.seafloor ? -(l.size * 0.6 + 3) : -(l.size * 2 + 2))) continue; break;
                }
                if (XenoHash.Cell(body.name, cx, cy, l.name) > l.territoryChance) continue;
                list.Add(l);
            }
            return list;
        }

        LifeformDef PickSpecies(CelestialBody body, double lat, double lon)
        {
            var list = CandidatesAt(body, lat, lon);
            if (list.Count == 0) return null;
            float total = list.Sum(l => Mathf.Max(0f, l.rarity));
            if (total <= 0) return null;
            float r = (float)rng.NextDouble() * total;
            foreach (var l in list) { r -= Mathf.Max(0f, l.rarity); if (r <= 0) return l; }
            return list[list.Count - 1];
        }

        /// <summary>A group that keeps to one spot (e.g. kites circling a geyser field): honours the spawn cap and the
        /// species' active hours, but not territories.</summary>
        public void SpawnResidents(LifeformDef def, CelestialBody body, double lat, double lon, float leash)
        {
            if (def == null || Load() >= XenoSettings.MaxActiveCreatures * Mathf.Clamp(XenoSettings.DensityMultiplier, 0.2f, 3f)) return;
            bool day = Geo.IsDaylight(body, lat, lon);
            if ((def.activeTime == ActivityTime.Day && !day) || (def.activeTime == ActivityTime.Night && day)) return;
            foreach (var c in Creatures)
                if (c != null && c.def == def && (c.WorldPos - body.GetWorldSurfacePosition(lat, lon, Geo.Terrain(body, lat, lon))).magnitude < leash * 3) return;
            var made = SpawnGroup(def, body, lat, lon, rng.Next(def.minGroup, def.maxGroup + 1));
            foreach (var c in made) { c.homeLat = lat; c.homeLon = lon; c.homeRadius = leash; }
        }

        public void SpawnGroup(LifeformDef def, CelestialBody body, double lat, double lon)
        {
            SpawnGroup(def, body, lat, lon, rng.Next(def.minGroup, def.maxGroup + 1));
        }

        public List<CreatureController> SpawnGroup(LifeformDef def, CelestialBody body, double lat, double lon, int n)
        {
            var made = new List<CreatureController>();
            CreatureController leader = null;
            // schools and herds count less against the spawn cap, but every animal still costs a skinned mesh:
            // never exceed the hard limit on creature objects (lair residents and colony members excepted)
            if (def.colonyHost == null) n = Mathf.Min(n, Mathf.Max(1, XenoSettings.MaxCreatureObjects - Creatures.Count));
            float spacing = def.groupSpread > 0f ? def.groupSpread : Mathf.Max(2f, def.size * 2.5f);
            for (int i = 0; i < n; i++)
            {
                double la = lat, lo = lon;
                Vector2 off = Vector2.zero;
                if (i > 0)
                {
                    float a = (float)(rng.NextDouble() * Math.PI * 2);
                    float d = spacing * (1f + (float)rng.NextDouble() * Mathf.Sqrt(i));
                    off = new Vector2(Mathf.Cos(a) * d, Mathf.Sin(a) * d);
                    Geo.Offset(body, ref la, ref lo, off.x, off.y);
                }
                var c = Spawn(def, body, la, lo);
                if (c == null) continue;
                made.Add(c);
                if (leader == null) leader = c;
                else { c.leader = leader; c.groupOffset = off; }
            }
            return made;
        }

        public CreatureController Spawn(LifeformDef def, CelestialBody body, double lat, double lon)
        {
            string objName = "Xeno_" + def.name + "_" + (serial++);
            GameObject go = null;
            try
            {
                if (def.model != null) go = ModelRig.Build(def, def.model, objName);
                if (go == null) go = ProceduralRig.Build(def, objName);
            }
            catch (Exception e) { XenoLog.Error("Failed to build " + def.name + ": " + e); if (go != null) Destroy(go); return null; }

            var c = go.AddComponent<CreatureController>();
            c.Init(def, body, lat, lon, rng.Next());
            Creatures.Add(c);
            XenoLog.Dbg("Spawned " + def.name + " at " + lat.ToString("F4") + "," + lon.ToString("F4"));
            if (def.colony != null && def.colony.def != null)
            {
                int n = rng.Next(def.colony.min, def.colony.max + 1);
                for (int i = 0; i < n; i++) SpawnColonist(c);
            }
            return c;
        }

        /// <summary>Hatch one colonist onto a host's perch.</summary>
        public CreatureController SpawnColonist(CreatureController host)
        {
            if (host == null || host.def.colony == null || host.def.colony.def == null) return null;
            var c = Spawn(host.def.colony.def, host.body, host.lat, host.lon);
            if (c != null) c.AttachToHost(host);
            return c;
        }

        public void DebugSleepAll()
        {
            foreach (var c in Creatures) if (c != null && c.def.sleep != null && !c.Ridden && !c.airborne) c.ForceSleep(120f);
        }

        public CreatureController NearestCreature(Vector3d pos, float maxRange, out double dist)
        {
            dist = double.MaxValue;
            CreatureController best = null;
            foreach (var c in Creatures)
            {
                if (c == null || c.state == CreatureState.Underground) continue;
                double d = (c.WorldPos - pos).magnitude;
                if (d <= Math.Max(maxRange, c.def.ObserveRange) && d < dist) { dist = d; best = c; }
            }
            return best;
        }

        // -------------------------------------------------------------------- fossils

        void UpdateFossils(Vessel v, CelestialBody body)
        {
            var fossils = XenoDatabase.FossilsOn(body).Where(f => !f.landmark).ToList();
            if (fossils.Count == 0) return;
            double cell = XenoHash.CellSizeDeg(body);
            int vx = (int)Math.Floor(v.latitude / cell), vy = (int)Math.Floor(v.longitude / cell);
            Vector3d obs = v.GetWorldPos3D();
            var scen = XenoScenario.Instance;

            for (int dx = -1; dx <= 1; dx++)
                for (int dy = -1; dy <= 1; dy++)
                {
                    int cx = vx + dx, cy = vy + dy;
                    foreach (var f in fossils)
                    {
                        if (f.unique) continue;                    // lair-only fossils are placed by their lair
                        // ~ one site per cell per fossil type at rarity 1, density 1
                        float chance = Mathf.Clamp01(0.5f * f.rarity * XenoSettings.FossilDensity);
                        if (XenoHash.Cell(body.name, cx, cy, "fossil:" + f.name) > chance) continue;
                        double la = (cx + XenoHash.Cell(body.name, cx, cy, "fx:" + f.name, 1)) * cell;
                        double lo = (cy + XenoHash.Cell(body.name, cx, cy, "fy:" + f.name, 2)) * cell;
                        string id = f.name + "@" + body.name + ":" + cx + ":" + cy;
                        if (Sites.ContainsKey(id)) continue;
                        if (Sites.Count >= XenoSettings.MaxFossilSites) return;
                        Vector3d wp = body.GetWorldSurfacePosition(la, lo, Geo.Terrain(body, la, lo));
                        if ((wp - obs).magnitude > XenoSettings.FossilSpawnRadius) continue;
                        if (!f.InBiome(Geo.Biome(body, la, lo))) continue;
                        if (body.ocean && Geo.Terrain(body, la, lo) < 0.5) continue;
                        bool studied = scen != null && scen.StudiedSites.Contains(id);
                        GameObject go = FossilSite.Build(f, "XenoFossil_" + id, studied);
                        var site = go.AddComponent<FossilSite>();
                        site.Init(f, body, la, lo, id, studied);
                        Sites[id] = site;
                    }
                }

            // gentle proximity hint for kerbals on foot
            if (v.isEVA)
                foreach (var s in Sites.Values)
                {
                    if (s == null || s.studied || notifiedSites.Contains(s.siteId)) continue;
                    double d = (s.WorldPos - obs).magnitude;
                    if (d < 150)
                    {
                        notifiedSites.Add(s.siteId);
                        double brg = Geo.Bearing(body, v.latitude, v.longitude, s.lat, s.lon);
                        ScreenMessages.PostScreenMessage(string.Format("<color=#C8B08A>Exposed fossil-bearing rock {0:F0} m {1}</color>", d, Geo.CompassName(brg)), 5f, ScreenMessageStyle.UPPER_CENTER);
                    }
                }
        }

        public FossilSite NearestSite(Vector3d pos, float maxRange, out double dist)
        {
            dist = double.MaxValue;
            FossilSite best = null;
            foreach (var s in Sites.Values)
            {
                if (s == null) continue;
                double d = s.DistanceTo(pos);
                if (d <= maxRange && d < dist) { dist = d; best = s; }
            }
            return best;
        }

        /// <summary>Debug: drop a fossil outcrop right next to the observer.</summary>
        public void DebugSpawnFossil(FossilDef f, Vessel v)
        {
            double la = v.latitude, lo = v.longitude;
            Geo.Offset(v.mainBody, ref la, ref lo, 8, 0);
            string id = f.name + "@debug" + (serial++);
            GameObject go = FossilSite.Build(f, "XenoFossil_" + id, false);
            var site = go.AddComponent<FossilSite>();
            site.Init(f, v.mainBody, la, lo, id, false);
            Sites[id] = site;
        }
    }
}
