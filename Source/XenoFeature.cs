using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Xenobiology
{
    public enum FeatureKind { Geyser, Fumarole }

    /// <summary>
    /// XENO_FEATURE {}: scenery that is not alive and not catalogued - geysers, fumaroles - scattered over a body's
    /// biomes by the same deterministic cells as territories, so a geyser field is always where it was. A feature can
    /// `attract` a species, which then tends to be found circling it.
    /// </summary>
    public class FeatureDef
    {
        public string name, body, displayName;
        public FeatureKind kind = FeatureKind.Geyser;
        public string[] biomes = new string[0];
        public float chance = 0.35f;          // chance a territory cell holds a field of these
        public int minCount = 1, maxCount = 3; // vents per field
        public float fieldRadius = 150f;      // metres; vents are scattered within this of the field centre
        public float minAltitude = 1f;        // terrain height above sea level (no vents underwater)
        public float viewDistance = 5000f;
        public float moundRadius = 4f, moundHeight = 0.7f;
        public Color sinter = new Color(0.86f, 0.84f, 0.78f), mat = new Color(0.78f, 0.45f, 0.18f), pool = new Color(0.25f, 0.55f, 0.62f);
        // geysers
        public float intervalMin = 45f, intervalMax = 120f, duration = 10f, jetHeight = 25f;
        public string sound;                  // played when a geyser erupts (GameData path, no extension)
        public float volume = 0.8f, soundRange = 600f;
        public PlumeInfo plume;
        public EmitterInfo steam;
        // creatures
        public string attracts;               // XENO_LIFEFORM name
        public float attractChance = 0.6f, attractLeash = 250f;
        public LifeformDef attractDef;
        public CelestialBody celestialBody;
        public string url;

        public bool InBiome(string biome)
        {
            if (biomes.Length == 0) return true;
            string b = XenoDatabase.NormBiome(biome);
            for (int i = 0; i < biomes.Length; i++) if (biomes[i] == b || biomes[i] == "any") return true;
            return false;
        }

        public static FeatureDef Parse(ConfigNode n)
        {
            var f = new FeatureDef();
            f.name = n.GetValue("name"); f.body = n.GetValue("body");
            if (string.IsNullOrEmpty(f.name) || string.IsNullOrEmpty(f.body)) return null;
            f.displayName = n.GetValue("displayName") ?? f.name;
            f.kind = XenoDatabase.ParseEnum(n.GetValue("kind"), FeatureKind.Geyser);
            n.TryGetValue("chance", ref f.chance); n.TryGetValue("minCount", ref f.minCount); n.TryGetValue("maxCount", ref f.maxCount);
            n.TryGetValue("fieldRadius", ref f.fieldRadius); n.TryGetValue("minAltitude", ref f.minAltitude); n.TryGetValue("viewDistance", ref f.viewDistance);
            n.TryGetValue("moundRadius", ref f.moundRadius); n.TryGetValue("moundHeight", ref f.moundHeight);
            n.TryGetValue("sinterColor", ref f.sinter); n.TryGetValue("matColor", ref f.mat); n.TryGetValue("poolColor", ref f.pool);
            n.TryGetValue("intervalMin", ref f.intervalMin); n.TryGetValue("intervalMax", ref f.intervalMax);
            n.TryGetValue("duration", ref f.duration); n.TryGetValue("jetHeight", ref f.jetHeight);
            f.sound = n.GetValue("sound"); n.TryGetValue("volume", ref f.volume); n.TryGetValue("soundRange", ref f.soundRange);
            f.attracts = n.GetValue("attracts"); n.TryGetValue("attractChance", ref f.attractChance); n.TryGetValue("attractLeash", ref f.attractLeash);
            f.maxCount = Math.Max(f.minCount, f.maxCount);
            f.intervalMax = Mathf.Max(f.intervalMin, f.intervalMax);
            ConfigNode pn = n.GetNode("PLUME");
            f.plume = pn != null ? PlumeInfo.Parse(pn) : new PlumeInfo
            {
                height = f.kind == FeatureKind.Geyser ? f.jetHeight * 1.6f : 14f, radius = 0.5f, spread = f.kind == FeatureKind.Geyser ? 7f : 4f,
                rise = 1.2f, lean = 0.12f, sheets = 3, color = new Color(0.92f, 0.93f, 0.95f, 0.75f), colorTop = new Color(0.95f, 0.96f, 1f, 0f)
            };
            ConfigNode en = n.GetNode("EMITTER");
            f.steam = en != null ? EmitterInfo.Parse(en) : new EmitterInfo
            {
                kind = "Smoke", rate = 6f, lifetime = 6f, speed = 1.6f, size = 1.4f, sizeGrow = 4f, radius = 0.4f,
                color = new Color(0.95f, 0.95f, 0.97f, 0.55f), colorEnd = new Color(1f, 1f, 1f, 0f)
            };
            return f;
        }
    }

    /// <summary>One vent on the ground: a sinter mound with a hot pool and bacterial mats, a steam column, and - for
    /// geysers - periodic eruptions. Glued to the terrain like a fossil site.</summary>
    public class XenoFeature : MonoBehaviour
    {
        public FeatureDef def;
        public CelestialBody body;
        public double lat, lon, alt;
        public string id;
        public bool attractRolled;

        VentPlume plume;
        Renderer moundRenderer;
        ParticleSystem steam, jet;
        AudioSource audioSrc;
        System.Random rnd;
        bool grounded, glued, visible = true;
        float glueTimer, timer, phaseT;
        int phase;           // 0 quiet, 1 erupting, 2 dying down
        float baseRate;

        public Vector3d WorldPos { get { return body.GetWorldSurfacePosition(lat, lon, alt); } }

        public void Init(FeatureDef d, CelestialBody b, double la, double lo, string siteId)
        {
            def = d; body = b; lat = la; lon = lo; id = siteId;
            alt = Geo.Terrain(b, la, lo);
            rnd = new System.Random((int)(XenoHash.Hash(siteId) & 0x7fffffff));
            Build();
            timer = def.kind == FeatureKind.Geyser ? Mathf.Lerp(def.intervalMin * 0.15f, def.intervalMax, (float)rnd.NextDouble()) : 0f;
            Place();
        }

        void Build()
        {
            var mound = new GameObject("mound");
            mound.transform.SetParent(transform, false);
            mound.AddComponent<MeshFilter>().sharedMesh = MoundMesh(def);
            var mr = mound.AddComponent<MeshRenderer>();
            mr.sharedMaterial = MoundMaterial(def);
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            moundRenderer = mr;

            var pg = new GameObject("plume");
            pg.transform.SetParent(transform, false);
            plume = pg.AddComponent<VentPlume>();
            plume.Init((int)(XenoHash.Hash(id) & 0x7fffffff), def.plume);
            plume.transform.localPosition = new Vector3(0, def.moundHeight * 0.5f, 0);
            plume.Visible = () => visible;

            var sg = new GameObject("steam");
            sg.transform.SetParent(transform, false);
            sg.transform.localPosition = new Vector3(0, def.moundHeight * 0.6f, 0);
            steam = CreatureEffects.Build(sg, def.steam);
            baseRate = def.steam.rate;

            if (def.kind == FeatureKind.Geyser)
            {
                float g = (float)(body.gravParameter / (body.Radius * body.Radius));
                float v0 = Mathf.Sqrt(2f * g * Mathf.Max(2f, def.jetHeight));
                var jg = new GameObject("jet");
                jg.transform.SetParent(transform, false);
                jg.transform.localPosition = new Vector3(0, def.moundHeight * 0.6f, 0);
                jg.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);        // emit along +Z -> up
                jet = CreatureEffects.Build(jg, new EmitterInfo
                {
                    kind = "Splash", rate = 0f, lifetime = 2f * v0 / g * 0.85f, speed = v0, size = 0.7f, sizeGrow = 2.6f, radius = 0.25f,
                    color = new Color(0.96f, 0.98f, 1f, 0.85f), colorEnd = new Color(1f, 1f, 1f, 0f)
                });
                var main = jet.main;
                main.startSpeed = new ParticleSystem.MinMaxCurve(v0 * 0.75f, v0 * 1.05f);
                main.maxParticles = 900;
                main.gravityModifier = 0f;
                var sh = jet.shape; sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 4f; sh.radius = 0.3f;
                var force = jet.forceOverLifetime; force.enabled = true; force.space = ParticleSystemSimulationSpace.Local;
                force.x = new ParticleSystem.MinMaxCurve(0f); force.y = new ParticleSystem.MinMaxCurve(0f); force.z = new ParticleSystem.MinMaxCurve(-g);
                var noise = jet.noise; noise.enabled = true; noise.strength = 0.8f; noise.frequency = 0.4f;

                if (!string.IsNullOrEmpty(def.sound))
                {
                    audioSrc = gameObject.AddComponent<AudioSource>();
                    audioSrc.spatialBlend = 1f; audioSrc.rolloffMode = AudioRolloffMode.Linear;
                    audioSrc.minDistance = 15f; audioSrc.maxDistance = Mathf.Max(100f, def.soundRange);
                    audioSrc.playOnAwake = false;
                }
                SetPlume(0.22f);
            }
        }

        void SetPlume(float k)
        {
            if (plume == null) return;
            plume.transform.localScale = new Vector3(Mathf.Lerp(0.5f, 1f, k), Mathf.Max(0.05f, k), Mathf.Lerp(0.5f, 1f, k));
        }

        void Place()
        {
            if (!grounded)
            {
                Vector3 n;
                double g = Geo.GroundAltitude(body, lat, lon, alt, out n);
                if (n != Vector3.zero) { alt = g - 0.25 * def.moundHeight; grounded = true; }
            }
            transform.position = WorldPos;
            Vector3 up, north, east;
            Geo.Frame(body, lat, lon, out up, out north, out east);
            // stay vertical: steam rises straight up, whatever the slope; the mound's skirt hides the gap
            transform.rotation = Quaternion.LookRotation(north, up) * Quaternion.Euler(0, (float)(XenoHash.Hash(id) % 360), 0);
        }

        void LateUpdate()
        {
            if (body == null) return;
            if (!glued)
            {
                Place();
                glueTimer += Time.deltaTime;
                if (grounded || glueTimer > 8f)
                {
                    transform.SetParent(body.pqsController != null ? body.pqsController.transform : body.transform, true);
                    glued = true;
                }
            }

            Camera cam = FlightCamera.fetch != null ? FlightCamera.fetch.mainCamera : Camera.main;
            bool vis = cam != null && (cam.transform.position - transform.position).sqrMagnitude < def.viewDistance * def.viewDistance;
            if (vis != visible)
            {
                visible = vis;
                if (moundRenderer != null) moundRenderer.enabled = vis;
                if (steam != null) { if (vis) steam.Play(); else steam.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear); }
            }
            if (def.kind != FeatureKind.Geyser || TimeWarp.CurrentRate > 4f) return;

            float dt = Time.deltaTime;
            timer -= dt;
            switch (phase)
            {
                case 0:
                    if (timer <= 0f) { phase = 1; phaseT = 0f; timer = def.duration * (0.75f + 0.5f * (float)rnd.NextDouble()); Erupt(true); }
                    break;
                case 1:
                    phaseT += dt;
                    SetPlume(Mathf.Lerp(0.22f, 1f, Mathf.SmoothStep(0f, 1f, phaseT / 1.2f)));
                    if (jet != null)
                    {   // the jet pulses as the column surges
                        var em = jet.emission; em.rateOverTime = visible ? 160f * (0.7f + 0.3f * Mathf.Sin(phaseT * 7f)) : 0f;
                    }
                    if (timer <= 0f) { phase = 2; phaseT = 0f; timer = 5f; Erupt(false); }
                    break;
                case 2:
                    phaseT += dt;
                    SetPlume(Mathf.Lerp(1f, 0.22f, Mathf.SmoothStep(0f, 1f, phaseT / 5f)));
                    if (timer <= 0f) { phase = 0; timer = Mathf.Lerp(def.intervalMin, def.intervalMax, (float)rnd.NextDouble()); }
                    break;
            }
        }

        void Erupt(bool on)
        {
            if (jet != null)
            {
                var em = jet.emission; em.rateOverTime = 0f;
                if (on && visible) jet.Emit(60);
            }
            if (steam != null) { var em = steam.emission; em.rateOverTime = on ? baseRate * 4f : baseRate; }
            if (on && audioSrc != null && visible)
            {
                AudioClip c = GameDatabase.Instance.GetAudioClip(def.sound);
                if (c != null) { audioSrc.volume = Mathf.Clamp01(def.volume * GameSettings.AMBIENCE_VOLUME); audioSrc.PlayOneShot(c); }
            }
        }

        // ------------------------------------------------------------------ mesh + material

        static readonly Dictionary<FeatureDef, Mesh> meshes = new Dictionary<FeatureDef, Mesh>();
        static readonly Dictionary<FeatureDef, Material> materials = new Dictionary<FeatureDef, Material>();

        /// <summary>A low terraced sinter cone with a pool in its throat and a skirt that sinks into the ground.
        /// u runs from the vent (0) to the rim of the skirt (1), so a 1-D gradient texture paints the rings.</summary>
        static Mesh MoundMesh(FeatureDef d)
        {
            Mesh m;
            if (meshes.TryGetValue(d, out m) && m != null) return m;
            const int SEG = 28;
            float[] rs = { 0f, 0.12f, 0.2f, 0.32f, 0.5f, 0.72f, 0.9f, 1f, 1.12f };
            float[] hs = { -0.15f, -0.1f, 0.85f, 1f, 0.8f, 0.5f, 0.22f, 0.05f, -1.2f };
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>();
            var rng = new System.Random(d.name.GetHashCode());
            for (int ring = 0; ring < rs.Length; ring++)
                for (int s = 0; s <= SEG; s++)
                {
                    float a = s / (float)SEG * Mathf.PI * 2f;
                    float wob = ring == 0 || s == SEG ? 1f : 0.85f + 0.3f * (float)rng.NextDouble();
                    float r = rs[ring] * d.moundRadius * (ring >= 3 ? wob : 1f);
                    float h = hs[ring] * d.moundHeight + (ring >= 2 && ring <= 6 ? ((float)rng.NextDouble() - 0.5f) * 0.12f * d.moundHeight : 0f);
                    v.Add(new Vector3(Mathf.Cos(a) * r, h, Mathf.Sin(a) * r));
                    uv.Add(new Vector2(Mathf.Clamp01(rs[ring] / 1.12f), 0.5f));
                }
            // seam vertices must match their twins
            for (int ring = 0; ring < rs.Length; ring++) v[ring * (SEG + 1) + SEG] = v[ring * (SEG + 1)];
            for (int ring = 0; ring < rs.Length - 1; ring++)
                for (int s = 0; s < SEG; s++)
                {
                    int a = ring * (SEG + 1) + s, b = a + SEG + 1;
                    tri.AddRange(new[] { a, b, a + 1, a + 1, b, b + 1 });
                }
            m = new Mesh(); m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(tri, 0);
            m.RecalculateNormals(); m.RecalculateBounds();
            meshes[d] = m;
            return m;
        }

        static Material MoundMaterial(FeatureDef d)
        {
            Material m;
            if (materials.TryGetValue(d, out m) && m != null) return m;
            const int W = 128;
            var t = new Texture2D(W, 4, TextureFormat.RGBA32, true);
            for (int x = 0; x < W; x++)
            {
                float u = x / (float)(W - 1);
                Color c;
                if (d.kind == FeatureKind.Geyser && u < 0.11f) c = Color.Lerp(d.pool * 0.6f, d.pool, u / 0.11f);             // hot pool
                else if (u < 0.2f) c = Color.Lerp(d.sinter * 1.05f, d.sinter, (u - 0.11f) / 0.09f);                    // fresh sinter lip
                else if (u < 0.55f) c = Color.Lerp(d.sinter, Color.Lerp(d.sinter, d.mat, 0.35f), (u - 0.2f) / 0.35f);   // cooling terraces
                else if (u < 0.85f) c = Color.Lerp(Color.Lerp(d.sinter, d.mat, 0.35f), d.mat, (u - 0.55f) / 0.3f);      // thermophile mats
                else c = Color.Lerp(d.mat, d.mat * 0.55f, (u - 0.85f) / 0.15f);                                         // into the soil
                // fine banding
                c *= 0.92f + 0.08f * Mathf.Sin(u * 90f);
                c.a = 1f;
                for (int y = 0; y < 4; y++) t.SetPixel(x, y, c);
            }
            t.wrapMode = TextureWrapMode.Clamp; t.Apply(true);
            Shader sh = Shader.Find("KSP/Diffuse") ?? Shader.Find("Diffuse") ?? Shader.Find("Standard");
            m = new Material(sh) { mainTexture = t, color = Color.white };
            materials[d] = m;
            return m;
        }
    }

    /// <summary>Places and culls XENO_FEATURE vents around the active vessel (called from the spawner's tick).</summary>
    public static class FeatureField
    {
        public static readonly Dictionary<string, XenoFeature> Active = new Dictionary<string, XenoFeature>();

        public static void ClearAll()
        {
            foreach (var f in Active.Values) if (f != null) UnityEngine.Object.Destroy(f.gameObject);
            Active.Clear();
        }

        public static void Update(Vessel v, CelestialBody body, XenoSpawner spawner)
        {
            var defs = XenoDatabase.FeaturesOn(body);
            Vector3d obs = v.GetWorldPos3D();
            foreach (var key in Active.Keys.ToList())
            {
                var f = Active[key];
                if (f == null || (f.WorldPos - obs).magnitude > f.def.viewDistance * 1.3) { if (f != null) UnityEngine.Object.Destroy(f.gameObject); Active.Remove(key); }
            }
            if (defs.Count == 0) return;

            double cell = XenoHash.CellSizeDeg(body);
            int vx = (int)Math.Floor(v.latitude / cell), vy = (int)Math.Floor(v.longitude / cell);
            for (int dx = -1; dx <= 1; dx++)
                for (int dy = -1; dy <= 1; dy++)
                {
                    int cx = vx + dx, cy = vy + dy;
                    foreach (var d in defs)
                    {
                        if (XenoHash.Cell(body.name, cx, cy, "feat:" + d.name) > Mathf.Clamp01(d.chance)) continue;
                        double fla = (cx + 0.15 + 0.7 * XenoHash.Cell(body.name, cx, cy, "featx:" + d.name, 1)) * cell;
                        double flo = (cy + 0.15 + 0.7 * XenoHash.Cell(body.name, cx, cy, "featy:" + d.name, 2)) * cell;
                        if (!d.InBiome(Geo.Biome(body, fla, flo))) continue;
                        int n = d.minCount + (int)Math.Floor(XenoHash.Cell(body.name, cx, cy, "featn:" + d.name, 3) * (d.maxCount - d.minCount + 0.999));
                        for (int i = 0; i < n; i++)
                        {
                            string id = d.name + "@" + body.name + ":" + cx + ":" + cy + ":" + i;
                            if (Active.ContainsKey(id)) continue;
                            double la = fla, lo = flo;
                            if (i > 0)
                            {
                                double a = XenoHash.Cell(body.name, cx, cy, "feata:" + d.name + i, 4) * Math.PI * 2;
                                double r = d.fieldRadius * (0.3 + 0.7 * XenoHash.Cell(body.name, cx, cy, "featr:" + d.name + i, 5));
                                Geo.Offset(body, ref la, ref lo, Math.Cos(a) * r, Math.Sin(a) * r);
                            }
                            double terr = Geo.Terrain(body, la, lo);
                            if (body.ocean && terr < d.minAltitude) continue;
                            if ((body.GetWorldSurfacePosition(la, lo, terr) - obs).magnitude > d.viewDistance) continue;
                            var go = new GameObject("XenoFeature_" + id);
                            var f = go.AddComponent<XenoFeature>();
                            f.Init(d, body, la, lo, id);
                            Active[id] = f;
                        }
                    }
                }

            // geyserkites and the like: when a field comes into view, maybe find its residents circling it
            foreach (var f in Active.Values)
            {
                if (f == null || f.attractRolled || f.def.attractDef == null) continue;
                if ((f.WorldPos - obs).magnitude > Math.Min(f.def.viewDistance, XenoSettings.SpawnRadius * 1.5)) continue;
                f.attractRolled = true;
                if (!f.id.EndsWith(":0")) continue;                                      // one roll per field
                if (XenoHash.Unit(XenoHash.Hash("attract:" + f.id)) > f.def.attractChance) continue;
                spawner.SpawnResidents(f.def.attractDef, body, f.lat, f.lon, f.def.attractLeash);
            }
        }
    }
}
