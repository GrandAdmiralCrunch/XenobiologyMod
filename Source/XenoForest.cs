using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using UnityEngine;
using UnityEngine.Rendering;

namespace Xenobiology
{
    /// <summary>A tree species of a FOREST {} (layout preferences plus what it looks like and which lifeform it is).</summary>
    public class ForestSpeciesDef : ForestSpecies
    {
        public string model;              // kit child prefix: t_<model>_<variant>_0 / _1, t_<model>_imp
        public string lifeform;           // field-guide entry (spec_ markers are put on trees beside the path)
        public LifeformDef def;
        public float trunkRadius = 0.3f;  // collider radius at scale 1
        public float trunkHeight = 5f;
    }

    /// <summary>FOREST {} inside a XENO_LAIR: a forest generated around the lair site (see ForestLayout).</summary>
    public class ForestDef
    {
        public string kit, bridge, spring, texDir;
        public float radius = 500f, spacing = 6.6f, lift = 1.3f, propDensity = 1f, entranceBearing = -1f;
        public int seed;
        public float nearRange = 50f, midRange = 190f, propRange = 100f, colliderRange = 60f;
        public float groundFine = 110f, groundMid = 320f, groundCoarse = 700f;
        public float floorTile = 6f, leafRate = 26f;
        public string fernLifeform, shrubLifeform, reedLifeform, elderFossil;
        public LifeformDef fernDef, shrubDef, reedDef;
        public readonly List<ForestSpeciesDef> species = new List<ForestSpeciesDef>();

        public static ForestDef Parse(ConfigNode n, string lairName)
        {
            var f = new ForestDef();
            f.kit = n.GetValue("kit"); f.bridge = n.GetValue("bridge"); f.spring = n.GetValue("spring");
            f.texDir = n.GetValue("textures") ?? (string.IsNullOrEmpty(f.kit) ? "" : f.kit.Substring(0, Math.Max(0, f.kit.LastIndexOf('/'))));
            n.TryGetValue("radius", ref f.radius); n.TryGetValue("spacing", ref f.spacing); n.TryGetValue("lift", ref f.lift);
            n.TryGetValue("propDensity", ref f.propDensity); n.TryGetValue("entranceBearing", ref f.entranceBearing);
            f.seed = (int)(XenoHash.Hash(lairName) & 0x7fffffff); n.TryGetValue("seed", ref f.seed);
            n.TryGetValue("nearRange", ref f.nearRange); n.TryGetValue("midRange", ref f.midRange); n.TryGetValue("propRange", ref f.propRange);
            n.TryGetValue("colliderRange", ref f.colliderRange); n.TryGetValue("groundFine", ref f.groundFine); n.TryGetValue("groundMid", ref f.groundMid);
            n.TryGetValue("groundCoarse", ref f.groundCoarse); n.TryGetValue("floorTile", ref f.floorTile); n.TryGetValue("leafRate", ref f.leafRate);
            f.elderFossil = n.GetValue("elderFossil"); f.fernLifeform = n.GetValue("fernLifeform"); f.shrubLifeform = n.GetValue("shrubLifeform"); f.reedLifeform = n.GetValue("reedLifeform");
            foreach (ConfigNode s in n.GetNodes("SPECIES"))
            {
                var d = new ForestSpeciesDef { name = s.GetValue("name"), model = s.GetValue("model") ?? s.GetValue("name"), lifeform = s.GetValue("lifeform") };
                s.TryGetValue("weight", ref d.weight); s.TryGetValue("wet", ref d.wet); s.TryGetValue("high", ref d.high); s.TryGetValue("edge", ref d.edge);
                s.TryGetValue("pathside", ref d.pathside); s.TryGetValue("cluster", ref d.cluster); s.TryGetValue("minScale", ref d.minScale);
                s.TryGetValue("maxScale", ref d.maxScale); s.TryGetValue("footprint", ref d.footprint); s.TryGetValue("variants", ref d.variants);
                s.TryGetValue("trunkRadius", ref d.trunkRadius); s.TryGetValue("trunkHeight", ref d.trunkHeight);
                if (!string.IsNullOrEmpty(d.name)) f.species.Add(d);
            }
            return f;
        }

        public void Link(Func<string, LifeformDef> find)
        {
            foreach (var s in species) if (!string.IsNullOrEmpty(s.lifeform)) s.def = find(s.lifeform);
            if (!string.IsNullOrEmpty(fernLifeform)) fernDef = find(fernLifeform);
            if (!string.IsNullOrEmpty(shrubLifeform)) shrubDef = find(shrubLifeform);
            if (!string.IsNullOrEmpty(reedLifeform)) reedDef = find(reedLifeform);
        }
    }

    /// <summary>
    /// Runtime forest: samples the PQS terrain around the lair, runs ForestLayout on a worker thread, then draws it as
    /// a grid of 80 m chunks. Each chunk merges its trees into one mesh per material, at three levels of detail
    /// (full trees near, simplified trees in the middle distance, three-quad cards far away), plus a forest-floor mesh
    /// at 1/2/4/8 m resolution and, near the camera, the undergrowth. Only full-detail chunks cast shadows. Colliders
    /// (floor mesh, trunk capsules, big rocks) exist only around the active vessel. Path, streambed and water are
    /// separate ribbons laid on the floor. Everything is built a few pieces per frame, nearest first.
    /// </summary>
    public class XenoForest : MonoBehaviour
    {
        public const float Chunk = 80f, Cell = 40f;   // LOD1/card/floor chunks; full-detail trees and undergrowth use 40 m cells
        LairInstance lair; ForestDef def; ForestLayout L;
        CelestialBody body;
        Vector3 E, N, U;            // lair-local axes: east, north, up
        double baseAlt, bodyR;
        bool ready, failed;
        Thread worker; volatile bool workerDone; string workerError;
        int nC;                     // chunks per side
        ChunkState[] chunks;
        readonly Dictionary<string, KitMesh> kit = new Dictionary<string, KitMesh>();
        readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();
        readonly List<Material> matList = new List<Material>();
        Material floorMat, pathMat, bedMat, waterMat, pondMat;
        readonly List<Material> scrollMats = new List<Material>();
        readonly List<GameObject> overlays = new List<GameObject>();
        Transform elder; Renderer[] elderLods = new Renderer[3]; int elderLod = -1;
        Material cascadeMat;
        public Vector3 CascadeLocal { get; private set; }
        public bool Ready { get { return ready; } }
        public ForestLayout Layout { get { return L; } }
        public double FloorOffset { get { return floorOffset; } }
        double floorOffset;         // metres the whole forest has been raised to clear the PQS terrain actually drawn here
        float lodTimer, colTimer, probeTimer = 2f;

        /// <summary>A kit mesh with its arrays copied out once, so the worker thread can merge instances without touching Unity.</summary>
        class KitMesh
        {
            public Mesh mesh; public Material[] mats;
            public Vector3[] v, n; public Vector4[] t; public Vector2[] uv; public int[][] tris; public int[] mat;   // mat: index into matList per submesh
        }
        class ChunkState
        {
            public int i, j, index; public float x0, z0;
            public List<int> trees = new List<int>(), props = new List<int>();
            public List<int>[] qTrees = { new List<int>(), new List<int>(), new List<int>(), new List<int>() };
            public List<int>[] qProps = { new List<int>(), new List<int>(), new List<int>(), new List<int>() };
            public GameObject go;
            public MeshRenderer[] tree0 = new MeshRenderer[4];   // full trees, one per 40 m cell
            public MeshRenderer[] tree1 = new MeshRenderer[4];   // simplified trees, per cell
            public MeshRenderer tree2;                            // cards, for the whole chunk
            public MeshRenderer[] props4 = new MeshRenderer[4];
            public MeshRenderer[] ground = new MeshRenderer[4];   // 1, 2, 4, 8 m
            public bool[] built0 = new bool[4], built1 = new bool[4], builtP = new bool[4];
            public int[] cellShown = { -9, -9, -9, -9 };
            public int treeShown = -9, groundShown = -9;
            public int wantTree = 2, wantGround = 3; public bool[] wantProps = new bool[4];
            public MeshCollider groundCol; public bool colPending;
            public float dist; public float[] qDist = new float[4];
            public bool CellReady(int q, int lvl) { return qTrees[q].Count == 0 || (lvl == 0 ? built0[q] : built1[q]); }
        }

        // ---------------------------------------------------------------- background mesh building
        enum JobKind { Tree0, Tree1, Tree2, Props, Ground, Collider }
        class MeshData
        {
            public List<Vector3> v = new List<Vector3>(), n = new List<Vector3>(); public List<Vector4> t = new List<Vector4>(); public List<Vector2> uv = new List<Vector2>();
            public Dictionary<int, List<int>> tris = new Dictionary<int, List<int>>();       // material index -> triangles
            public Vector3 min = new Vector3(1e9f, 1e9f, 1e9f), max = new Vector3(-1e9f, -1e9f, -1e9f);
        }
        class Job { public ChunkState c; public JobKind kind; public int sub; public long key; public float dist; public MeshData data; }
        readonly List<Job> pending = new List<Job>();
        readonly Queue<Job> done = new Queue<Job>();
        readonly HashSet<long> inFlight = new HashSet<long>();
        readonly object jobLock = new object();
        readonly AutoResetEvent wake = new AutoResetEvent(false);
        Thread builder; volatile bool stopping;
        static long Key(ChunkState c, JobKind k, int sub) { return ((long)c.index * 8 + (int)k) * 8 + sub; }

        void Enqueue(ChunkState c, JobKind k, int sub, float dist)
        {
            long key = Key(c, k, sub);
            lock (jobLock)
            {
                if (inFlight.Contains(key)) { foreach (var j in pending) if (j.key == key) j.dist = dist; return; }
                inFlight.Add(key); pending.Add(new Job { c = c, kind = k, sub = sub, key = key, dist = dist });
            }
            wake.Set();
        }

        void BuilderLoop()
        {
            while (!stopping)
            {
                Job job = null;
                lock (jobLock)
                {
                    float best = float.MaxValue;
                    foreach (var j in pending) if (j.dist < best) { best = j.dist; job = j; }
                    if (job != null) pending.Remove(job);
                }
                if (job == null) { wake.WaitOne(200); continue; }
                try { job.data = Build(job); }
                catch (Exception e) { job.data = null; XenoLog.Warn("Forest build " + job.kind + ": " + e.Message); }
                lock (jobLock) done.Enqueue(job);
            }
        }

        MeshData Build(Job j)
        {
            var c = j.c;
            switch (j.kind)
            {
                case JobKind.Tree0: return Instances(c.qTrees[j.sub], true, 0);
                case JobKind.Tree1: return Instances(c.qTrees[j.sub], true, 1);
                case JobKind.Tree2: return Instances(c.trees, true, 2);
                case JobKind.Props: return Instances(c.qProps[j.sub], false, 0);
                case JobKind.Ground: return GroundData(c, GroundStep[j.sub], true);
                default: return GroundData(c, 2, false);
            }
        }

        static readonly string[] PropNames = { "fern", "shrub", "sapling", "log", "rock", "streamrock", "mushroom", "stump", "litter", "reed", "lily" };
        MeshData Instances(List<int> idx, bool trees, int lod)
        {
            var d = new MeshData();
            foreach (int k in idx)
            {
                ForestInstance t; string key;
                if (trees)
                {
                    t = L.trees[k]; var sp = def.species[t.kind];
                    key = lod == 2 ? "t_" + sp.model + "_imp" : "t_" + sp.model + "_" + t.variant + "_" + lod;
                    if (lod == 2) t.tilt = 0;
                }
                else
                {
                    t = L.props[k]; key = "p_" + PropNames[t.kind] + "_" + t.variant;
                    if (t.kind == (int)ForestProp.Lily || t.kind == (int)ForestProp.Litter) t.tilt = 0;
                }
                KitMesh km; if (!kit.TryGetValue(key, out km) || km.v == null) continue;
                Append(d, km, t, trees ? 0.25f : 0f);
            }
            return d;
        }

        /// <summary>Rodrigues rotation (managed: safe off the main thread).</summary>
        static Vector3 Rot(Vector3 v, Vector3 axis, float deg)
        {
            float a = deg * Mathf.Deg2Rad, c = (float)Math.Cos(a), s = (float)Math.Sin(a);
            return v * c + Vector3.Cross(axis, v) * s + axis * (Vector3.Dot(axis, v) * (1 - c));
        }

        void Append(MeshData d, KitMesh km, ForestInstance t, float sink)
        {
            // model axes: +x, +y up, +z forward -> lair axes (X0, U, N), then yaw about up, then lean
            Vector3 X0 = Vector3.Cross(U, N).normalized;
            Vector3 ax = Rot(X0, U, t.yaw), az = Rot(N, U, t.yaw), ay = U;
            if (t.tilt > 0.01f)
            {
                Vector3 tiltAxis = Rot(X0, U, t.tiltDir);
                ax = Rot(ax, tiltAxis, t.tilt); ay = Rot(ay, tiltAxis, t.tilt); az = Rot(az, tiltAxis, t.tilt);
            }
            float s = t.scale;
            Vector3 o = Local(t.x, t.z, t.y - sink * s);
            int b = d.v.Count;
            var v = km.v; var n = km.n; var tg = km.t; var uv = km.uv;
            for (int i = 0; i < v.Length; i++)
            {
                Vector3 p = o + (ax * v[i].x + ay * v[i].y + az * v[i].z) * s;
                d.v.Add(p);
                if (p.x < d.min.x) d.min.x = p.x; if (p.y < d.min.y) d.min.y = p.y; if (p.z < d.min.z) d.min.z = p.z;
                if (p.x > d.max.x) d.max.x = p.x; if (p.y > d.max.y) d.max.y = p.y; if (p.z > d.max.z) d.max.z = p.z;
                d.n.Add(ax * n[i].x + ay * n[i].y + az * n[i].z);
                Vector4 q = tg[i]; Vector3 tq = ax * q.x + ay * q.y + az * q.z; d.t.Add(new Vector4(tq.x, tq.y, tq.z, q.w));
                d.uv.Add(uv[i]);
            }
            for (int sm = 0; sm < km.tris.Length; sm++)
            {
                if (km.mat[sm] < 0) continue;
                List<int> l; if (!d.tris.TryGetValue(km.mat[sm], out l)) d.tris[km.mat[sm]] = l = new List<int>();
                var tr = km.tris[sm];
                for (int i = 0; i < tr.Length; i++) l.Add(b + tr[i]);
            }
        }

        /// <summary>Main thread: turn finished mesh data into meshes, a few milliseconds' worth per frame.</summary>
        void ProcessDone()
        {
            var sw = Stopwatch.StartNew();
            while (sw.ElapsedMilliseconds < 3)
            {
                Job j;
                lock (jobLock) { if (done.Count == 0) return; j = done.Dequeue(); inFlight.Remove(j.key); }
                var c = j.c;
                try { Install(j); }
                catch (Exception e) { XenoLog.Error("Forest chunk " + c.i + "," + c.j + " " + j.kind + ": " + e.Message); }
                c.treeShown = -9; c.groundShown = -9; for (int q = 0; q < 4; q++) c.cellShown[q] = -9;
                Apply(c);
            }
        }

        Mesh ToMesh(MeshData d, string name, out Material[] ms)
        {
            ms = null;
            if (d == null || d.v.Count == 0) return null;
            var m = new Mesh { name = name };
            if (d.v.Count > 65000) m.indexFormat = IndexFormat.UInt32;
            m.SetVertices(d.v); m.SetNormals(d.n); m.SetTangents(d.t); m.SetUVs(0, d.uv);
            var keys = new List<int>(d.tris.Keys); keys.Sort();
            m.subMeshCount = keys.Count; ms = new Material[keys.Count];
            for (int s = 0; s < keys.Count; s++) { m.SetTriangles(d.tris[keys[s]], s, false); ms[s] = matList[keys[s]]; }
            var bounds = new Bounds(); bounds.SetMinMax(d.min, d.max); m.bounds = bounds;
            return m;
        }
        MeshRenderer Renderer_(ChunkState c, MeshData d, string name, bool shadows)
        {
            Material[] ms; var mesh = ToMesh(d, name, out ms);
            if (mesh == null) return null;
            var go = new GameObject(name); go.layer = 15; go.transform.SetParent(c.go.transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>(); r.sharedMaterials = ms;
            r.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off; r.receiveShadows = true; r.enabled = false;
            return r;
        }

        void Install(Job j)
        {
            var c = j.c; var d = j.data;
            switch (j.kind)
            {
                case JobKind.Tree0: Free(ref c.tree0[j.sub]); c.tree0[j.sub] = Renderer_(c, d, "trees0_" + j.sub, true); c.built0[j.sub] = true; break;
                case JobKind.Tree1: Free(ref c.tree1[j.sub]); c.tree1[j.sub] = Renderer_(c, d, "trees1_" + j.sub, false); c.built1[j.sub] = true; break;
                case JobKind.Tree2: Free(ref c.tree2); c.tree2 = Renderer_(c, d, "trees2", false); break;
                case JobKind.Props: Free(ref c.props4[j.sub]); c.props4[j.sub] = Renderer_(c, d, "props_" + j.sub, false); c.builtP[j.sub] = true; break;
                case JobKind.Ground: Free(ref c.ground[j.sub]); c.ground[j.sub] = Renderer_(c, d, "ground" + j.sub, false); break;
                case JobKind.Collider:
                    c.colPending = false;
                    if (c.groundCol != null || d == null || d.v.Count == 0) break;
                    if (!ColliderWanted(c)) break;
                    Material[] ms; var mesh = ToMesh(d, "ground_col", out ms);
                    var go = new GameObject("ground_col"); go.layer = 15; go.transform.SetParent(c.go.transform, false);
                    c.groundCol = go.AddComponent<MeshCollider>(); c.groundCol.sharedMesh = mesh;
                    break;
            }
        }

        // ================================================================ floor for everyone else (creatures walk on it too)
        static readonly List<XenoForest> active = new List<XenoForest>();
        /// <summary>Raise a ground height to the forest floor where a ready forest covers (lat, lon).</summary>
        public static double Floor(CelestialBody b, double lat, double lon, double terr)
        {
            for (int i = 0; i < active.Count; i++)
            {
                var f = active[i];
                if (f == null || !f.ready || f.body != b) continue;
                double n, e; Geo.Delta(b, f.lair.lat, f.lair.lon, lat, lon, out n, out e);
                if (Math.Abs(n) > f.L.E - 2 || Math.Abs(e) > f.L.E - 2) continue;
                if (!f.L.InForest(e, n, -25)) continue;
                double g = f.L.Ground(e, n) + f.floorOffset;
                if (g > terr) terr = g;
            }
            return terr;
        }
        void OnEnable() { if (!active.Contains(this)) active.Add(this); }
        void OnDisable() { active.Remove(this); }

        // ================================================================ setup
        public void Init(LairInstance l, ForestDef d)
        {
            lair = l; def = d; body = l.body; bodyR = body.Radius; baseAlt = l.alt;
            Vector3 up, north, east;
            Geo.Frame(body, l.lat, l.lon, out up, out north, out east);
            U = transform.InverseTransformDirection(up).normalized; N = transform.InverseTransformDirection(north).normalized; E = transform.InverseTransformDirection(east).normalized;
            StartCoroutine(Setup());
        }

        public Vector3 Local(double x, double z, double y)
        {
            double curv = (x * x + z * z) / (2 * bodyR);
            return E * (float)x + N * (float)z + U * (float)(y - baseAlt - curv);
        }
        public void LatLon(double x, double z, out double la, out double lo) { la = lair.lat; lo = lair.lon; Geo.Offset(body, ref la, ref lo, z, x); }
        void ToXZ(Vector3 local, out float x, out float z) { x = Vector3.Dot(local, E); z = Vector3.Dot(local, N); }

        IEnumerator Setup()
        {
            L = new ForestLayout { R = def.radius, seed = def.seed, spacing = def.spacing, lift = def.lift, propDensity = def.propDensity };
            foreach (var s in def.species) L.species.Add(s);
            L.entranceBearing = def.entranceBearing >= 0 ? def.entranceBearing : BearingToHome();
            L.InitPqs();
            string cache = CachePath();
            if (cache != null && System.IO.File.Exists(cache) && L.Load(cache)) { XenoLog.Info("Forest " + lair.def.name + ": layout from cache"); }
            else
            {
            // PQS heights, a few thousand per frame (they must be read on the main thread)
            var sw = Stopwatch.StartNew();
            for (int j = 0; j < L.pqsN; j++)
            {
                for (int i = 0; i < L.pqsN; i++)
                {
                    double la, lo; LatLon(L.PqsX(i), L.PqsX(j), out la, out lo);
                    L.pqs[j * L.pqsN + i] = (float)Geo.Terrain(body, la, lo);
                }
                if (sw.ElapsedMilliseconds > 6) { yield return null; sw.Reset(); sw.Start(); }
            }
            worker = new Thread(() => { try { L.Generate(); } catch (Exception e) { workerError = e.ToString(); } workerDone = true; });
            worker.IsBackground = true; worker.Start();
            while (!workerDone) yield return null;
            if (workerError != null) { XenoLog.Error("Forest " + lair.def.name + ": " + workerError); failed = true; yield break; }
            if (cache != null) try { System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(cache)); L.Save(cache); } catch (Exception e) { XenoLog.Warn("Forest cache: " + e.Message); }
            }
            XenoLog.Info("Forest " + lair.def.name + ": " + L.log.Replace("\n", " | "));
            if (!LoadKit()) { failed = true; yield break; }
            MakeMaterials();
            floorIndex = matList.IndexOf(floorMat); if (floorIndex < 0) { matList.Add(floorMat); floorIndex = matList.Count - 1; }
            LoadOffset();
            SetupChunks();
            yield return null;
            BuildOverlays();
            yield return null;
            PlaceSetPieces();
            AddSpecimens();
            RegisterSpots();
            var amb = gameObject.AddComponent<ForestAmbience>(); amb.Init(this, lair, def);
            ready = true;
        }

        /// <summary>One file per site and settings: a saved game loads its forest instantly (and identically).</summary>
        string CachePath()
        {
            try
            {
                string key = string.Format("{0}_{1}_{2:F5}_{3:F5}_{4:F0}_{5:F2}_{6:F0}", lair.def.name, def.seed, lair.lat, lair.lon, def.radius, def.spacing, L.entranceBearing);
                return System.IO.Path.Combine(KSPUtil.ApplicationRootPath, "GameData/Xenobiology/PluginData/ForestCache/" + key.Replace('.', 'p').Replace('-', 'm') + ".bin");
            }
            catch { return null; }
        }

        double BearingToHome()
        {
            // toward the space centre (if on the home world), so the trail starts on the side visitors arrive from
            if (body != FlightGlobals.GetHomeBody()) return 90;
            return Geo.Bearing(body, lair.lat, lair.lon, -0.0972, -74.5577);
        }

        bool LoadKit()
        {
            GameObject prefab = GameDatabase.Instance.GetModelPrefab(def.kit);
            if (prefab == null) { XenoLog.Warn("Forest " + lair.def.name + ": kit '" + def.kit + "' not found"); return false; }
            int unreadable = 0;
            foreach (MeshFilter mf in prefab.GetComponentsInChildren<MeshFilter>(true))
            {
                var mr = mf.GetComponent<MeshRenderer>(); if (mr == null || mf.sharedMesh == null) continue;
                var km = new KitMesh { mesh = mf.sharedMesh, mats = mr.sharedMaterials };
                km.mat = new int[km.mats.Length];
                for (int k = 0; k < km.mats.Length; k++)
                {
                    var m = km.mats[k];
                    if (m == null) { km.mat[k] = -1; continue; }
                    string nm = m.name.Replace(" (Instance)", "");
                    if (!mats.ContainsKey(nm)) { mats[nm] = m; }
                    int ix = matList.IndexOf(mats[nm]); if (ix < 0) { matList.Add(mats[nm]); ix = matList.Count - 1; }
                    km.mat[k] = ix;
                }
                if (!km.mesh.isReadable) { unreadable++; continue; }
                Extract(mf.gameObject.name, km);
                kit[mf.gameObject.name] = km;
            }
            if (unreadable > 0) XenoLog.Warn("Forest kit: " + unreadable + " meshes are not readable and were skipped");
            XenoLog.Info("Forest kit: " + kit.Count + " meshes, materials " + string.Join(", ", new List<string>(mats.Keys).ToArray()));
            return kit.Count > 0;
        }

        /// <summary>Copy the arrays out (for the builder thread). Leaf cards get normals pointing out of the crown so the
        /// foliage is lit as one soft volume; far cards and lily pads are lit mostly from above.</summary>
        void Extract(string name, KitMesh km)
        {
            Mesh m = km.mesh;
            km.v = m.vertices; km.n = m.normals; km.uv = m.uv; km.t = m.tangents;
            if (km.n == null || km.n.Length != km.v.Length) { var c = Instantiate(m); c.RecalculateNormals(); km.n = c.normals; Destroy(c); }
            if (km.uv == null || km.uv.Length != km.v.Length) km.uv = new Vector2[km.v.Length];
            if (km.t == null || km.t.Length != km.v.Length) { km.t = new Vector4[km.v.Length]; for (int i = 0; i < km.t.Length; i++) km.t[i] = new Vector4(1, 0, 0, 1); }
            km.tris = new int[m.subMeshCount][];
            for (int s = 0; s < m.subMeshCount; s++) km.tris[s] = m.GetTriangles(s);
            if (km.mat.Length < km.tris.Length) { var mm = new int[km.tris.Length]; for (int s = 0; s < mm.Length; s++) mm[s] = s < km.mat.Length ? km.mat[s] : -1; km.mat = mm; }
            for (int s = 0; s < km.tris.Length && s < km.mats.Length; s++)
            {
                string mn = km.mats[s] != null ? km.mats[s].name : "";
                bool leaf = mn.StartsWith("forest_leaves"), flat = mn.StartsWith("forest_imp") || mn.StartsWith("forest_lily");
                if (!leaf && !flat) continue;
                var idx = new HashSet<int>(km.tris[s]);
                Vector3 ctr = Vector3.zero; foreach (int k in idx) ctr += km.v[k]; ctr /= Mathf.Max(1, idx.Count);
                foreach (int k in idx)
                {
                    Vector3 d = km.v[k] - ctr;
                    if (flat) { d.y = 0; km.n[k] = (d.normalized * 0.45f + Vector3.up).normalized; }
                    else km.n[k] = (d.normalized + Vector3.up * 0.55f).normalized;
                }
            }
        }

        Material Mat(string name) { Material m; return mats.TryGetValue(name, out m) ? m : null; }
        Texture2D Tex(string n, bool normal = false) { return GameDatabase.Instance.GetTexture(def.texDir + "/" + n, normal); }

        void MakeMaterials()
        {
            floorMat = Mat("forest_litter");
            if (floorMat == null)
            {
                floorMat = new Material(Shader.Find("KSP/Bumped")); floorMat.mainTexture = Tex("forest_floor");
                floorMat.SetTexture("_BumpMap", Tex("forest_floor_NRM", true));
            }
            Shader cut = Shader.Find("KSP/Alpha/Cutoff"), tr = Shader.Find("KSP/Alpha/Translucent") ?? Shader.Find("KSP/Alpha/Translucent Specular");
            pathMat = new Material(cut) { name = "forest_path" }; pathMat.mainTexture = Tex("forest_path"); pathMat.SetFloat("_Cutoff", 0.5f);
            bedMat = new Material(cut) { name = "forest_bed" }; bedMat.mainTexture = Tex("forest_streambed"); bedMat.SetFloat("_Cutoff", 0.5f);
            waterMat = new Material(tr) { name = "forest_water" }; waterMat.mainTexture = Tex("forest_water"); waterMat.renderQueue = 3001;
            pondMat = new Material(tr) { name = "forest_pond" }; pondMat.mainTexture = Tex("forest_pondwater"); pondMat.renderQueue = 3001;
            foreach (var m in new[] { pathMat, bedMat, waterMat, pondMat }) if (m.HasProperty("_Color")) m.SetColor("_Color", Color.white);
            scrollMats.Add(waterMat);
        }

        // ================================================================ chunks
        void SetupChunks()
        {
            nC = (int)Math.Ceiling(2 * L.E / Chunk);
            chunks = new ChunkState[nC * nC];
            for (int j = 0; j < nC; j++)
                for (int i = 0; i < nC; i++)
                    chunks[j * nC + i] = new ChunkState { i = i, j = j, index = j * nC + i, x0 = (float)(-L.E + i * Chunk), z0 = (float)(-L.E + j * Chunk) };
            for (int k = 0; k < L.trees.Count; k++) { var t = L.trees[k]; var c = ChunkAt(t.x, t.z); if (c != null) { c.trees.Add(k); c.qTrees[Quad(c, t.x, t.z)].Add(k); } }
            for (int k = 0; k < L.props.Count; k++) { var p = L.props[k]; var c = ChunkAt(p.x, p.z); if (c != null) { c.props.Add(k); c.qProps[Quad(c, p.x, p.z)].Add(k); } }
            foreach (var c in chunks)
            {
                c.go = new GameObject("forest_chunk_" + c.i + "_" + c.j);
                c.go.transform.SetParent(transform, false);
                c.go.layer = 15;
            }
            wind = Winding();
            builder = new Thread(BuilderLoop) { IsBackground = true, Name = "XenoForestBuilder" };
            builder.Start();
        }
        static int Quad(ChunkState c, float x, float z) { return (x - c.x0 >= Cell ? 1 : 0) + (z - c.z0 >= Cell ? 2 : 0); }
        ChunkState ChunkAt(double x, double z)
        {
            int i = (int)Math.Floor((x + L.E) / Chunk), j = (int)Math.Floor((z + L.E) / Chunk);
            if (i < 0 || j < 0 || i >= nC || j >= nC) return null;
            return chunks[j * nC + i];
        }
        bool ChunkHasGround(ChunkState c)
        {   // skip chunks entirely beyond the rim (the floor is under the PQS terrain there)
            float cx = c.x0 + Chunk / 2, cz = c.z0 + Chunk / 2;
            double r = Math.Sqrt(cx * cx + cz * cz) - Chunk * 0.71;
            return r < L.R * 1.1 + 20;
        }
        static float BoxDist(float x0, float z0, float size, float x, float z)
        {
            float dx = Mathf.Max(0, Mathf.Max(x0 - x, x - (x0 + size))), dz = Mathf.Max(0, Mathf.Max(z0 - z, z - (z0 + size)));
            return Mathf.Sqrt(dx * dx + dz * dz);
        }

        void Update()
        {
            if (!ready) return;
            float t = Time.time;
            foreach (var m in scrollMats) if (m != null) m.mainTextureOffset = new Vector2(0, -t * 0.12f);
            if (pondMat != null) pondMat.mainTextureOffset = new Vector2(Mathf.Sin(t * 0.02f) * 0.3f, t * 0.004f);
            if (cascadeMat != null) cascadeMat.mainTextureOffset = new Vector2(0, t * 0.9f);
            lodTimer -= Time.deltaTime;
            if (lodTimer <= 0) { lodTimer = 0.25f; UpdateLods(); }
            colTimer -= Time.deltaTime;
            if (colTimer <= 0) { colTimer = 0.5f; UpdateColliders(); }
            probeTimer -= Time.deltaTime;
            if (probeTimer <= 0) { probeTimer = 2f; ProbeTerrain(); }
            ProcessDone();
        }

        Vector3 CamLocal()
        {
            Camera cam = FlightCamera.fetch != null ? FlightCamera.fetch.mainCamera : Camera.main;
            return cam != null ? transform.InverseTransformPoint(cam.transform.position) : Vector3.zero;
        }

        void UpdateLods()
        {
            Vector3 cl = CamLocal(); float cx, cz; ToXZ(cl, out cx, out cz);
            float dh = Mathf.Max(0, Mathf.Abs(Vector3.Dot(cl, U)) - 30f);
            foreach (var c in chunks)
            {
                float d = Mathf.Sqrt(Sq(BoxDist(c.x0, c.z0, Chunk, cx, cz)) + dh * dh); c.dist = d;
                for (int q = 0; q < 4; q++) c.qDist[q] = Mathf.Sqrt(Sq(BoxDist(c.x0 + (q & 1) * Cell, c.z0 + (q >> 1) * Cell, Cell, cx, cz)) + dh * dh);
                const float hy = 8f;     // hysteresis
                int wt = d < def.midRange + (c.wantTree <= 1 ? hy : 0) ? 1 : 2;     // chunk: cells, or cards
                int wg = d < def.groundFine ? 0 : d < def.groundMid ? 1 : d < def.groundCoarse ? 2 : 3;
                c.wantTree = wt; c.wantGround = wg;
                if (c.trees.Count > 0)
                {
                    if (c.tree2 == null) Enqueue(c, JobKind.Tree2, 0, d + 400);
                    if (wt == 1)
                        for (int q = 0; q < 4; q++)
                        {
                            if (c.qTrees[q].Count == 0) continue;
                            bool near = c.qDist[q] < def.nearRange + (c.cellShown[q] == 0 ? hy : 0);
                            if (!c.built1[q]) Enqueue(c, JobKind.Tree1, q, c.qDist[q] + 10);
                            if (near && !c.built0[q]) Enqueue(c, JobKind.Tree0, q, c.qDist[q]);
                        }
                }
                if (ChunkHasGround(c) && c.ground[wg] == null) Enqueue(c, JobKind.Ground, wg, d - 50);
                for (int q = 0; q < 4; q++)
                {
                    c.wantProps[q] = c.qDist[q] < def.propRange;
                    if (c.wantProps[q] && c.qProps[q].Count > 0 && !c.builtP[q]) Enqueue(c, JobKind.Props, q, c.qDist[q] + 20);
                }
                Apply(c);
                // free detail nobody is near any more
                for (int q = 0; q < 4; q++)
                {
                    if (c.built0[q] && c.qDist[q] > def.nearRange * 2.2f) { Free(ref c.tree0[q]); c.built0[q] = false; }
                    if (c.built1[q] && c.qDist[q] > def.midRange * 1.6f) { Free(ref c.tree1[q]); c.built1[q] = false; }
                }
                if (c.ground[0] != null && d > def.groundFine * 2f) Free(ref c.ground[0]);
                if (c.ground[1] != null && d > def.groundMid * 1.8f) Free(ref c.ground[1]);
                for (int q = 0; q < 4; q++) if (c.builtP[q] && c.qDist[q] > def.propRange * 1.8f) { Free(ref c.props4[q]); c.builtP[q] = false; }
            }
            // the elder tree swaps its own levels
            if (elder != null)
            {
                float ex, ez; ToXZ(elder.localPosition, out ex, out ez);
                float d = Mathf.Sqrt((ex - cx) * (ex - cx) + (ez - cz) * (ez - cz));
                int want = d < def.nearRange * 2 ? 0 : d < def.midRange * 1.5f ? 1 : 2;
                if (want != elderLod) { elderLod = want; for (int k = 0; k < 3; k++) if (elderLods[k] != null) elderLods[k].enabled = k == want; }
            }
        }
        static float Sq(float x) { return x * x; }

        void Free(ref MeshRenderer r)
        {
            if (r == null) return;
            var mf = r.GetComponent<MeshFilter>(); if (mf != null && mf.sharedMesh != null) Destroy(mf.sharedMesh);
            Destroy(r.gameObject); r = null;
        }

        void Apply(ChunkState c)
        {
            // trees: per 40 m cell (full or simplified) while the chunk is in range and every cell has something to show,
            // otherwise the chunk's cards
            bool cells = c.wantTree == 1;
            if (cells) for (int q = 0; q < 4; q++) if (!c.CellReady(q, 1) && !c.CellReady(q, 0)) { cells = false; break; }
            if (!cells && c.tree2 == null) cells = true;                     // nothing else to show yet
            for (int q = 0; q < 4; q++)
            {
                int lv = -1;
                if (cells && c.qTrees[q].Count > 0)
                {
                    bool near = c.qDist[q] < def.nearRange + (c.cellShown[q] == 0 ? 8f : 0);
                    lv = near && c.built0[q] ? 0 : c.built1[q] ? 1 : c.built0[q] ? 0 : -1;
                }
                if (lv != c.cellShown[q])
                {
                    c.cellShown[q] = lv;
                    if (c.tree0[q] != null) c.tree0[q].enabled = lv == 0;
                    if (c.tree1[q] != null) c.tree1[q].enabled = lv == 1;
                }
            }
            int show = cells ? 1 : 2;
            if (show != c.treeShown || (c.tree2 != null && c.tree2.enabled != (show == 2))) { c.treeShown = show; if (c.tree2 != null) c.tree2.enabled = show == 2; }
            int g = -1;
            if (c.ground[c.wantGround] != null) g = c.wantGround;
            else for (int k = 0; k < 4; k++) if (c.ground[k] != null && (g < 0 || Math.Abs(k - c.wantGround) < Math.Abs(g - c.wantGround))) g = k;
            if (g != c.groundShown) { for (int k = 0; k < 4; k++) if (c.ground[k] != null) c.ground[k].enabled = k == g; c.groundShown = g; }
            for (int q = 0; q < 4; q++) if (c.props4[q] != null) c.props4[q].enabled = c.wantProps[q];
        }

        // ---------------------------------------------------------------- forest floor (built on the worker thread)
        static readonly int[] GroundStep = { 1, 2, 4, 8 };
        int wind;
        int Winding()
        {   // which triangle order faces up in this frame (Unity's front face is the side Cross(b - a, c - a) points to)
            Vector3 a = Local(0, 0, 0), b = Local(1, 0, 0), cc = Local(0, 1, 0);
            return Vector3.Dot(Vector3.Cross(b - a, cc - a), U) > 0 ? 0 : 1;
        }

        MeshData GroundData(ChunkState c, int step, bool visual)
        {
            var d = new MeshData();
            int n = (int)(Chunk / step) + 1;
            int gx0 = (int)Math.Round((c.x0 + L.E) / ForestLayout.GStep), gz0 = (int)Math.Round((c.z0 + L.E) / ForestLayout.GStep);
            float tile = def.floorTile;
            Vector4 tangent = new Vector4(E.x, E.y, E.z, -1f);
            for (int j = 0; j < n; j++)
                for (int i = 0; i < n; i++)
                {
                    int gx = Math.Min(L.gN - 1, gx0 + i * step), gz = Math.Min(L.gN - 1, gz0 + j * step);
                    double x = -L.E + gx * ForestLayout.GStep, z = -L.E + gz * ForestLayout.GStep;
                    Vector3 p = Local(x, z, L.GroundAt(gx, gz));
                    d.v.Add(p);
                    if (p.x < d.min.x) d.min.x = p.x; if (p.y < d.min.y) d.min.y = p.y; if (p.z < d.min.z) d.min.z = p.z;
                    if (p.x > d.max.x) d.max.x = p.x; if (p.y > d.max.y) d.max.y = p.y; if (p.z > d.max.z) d.max.z = p.z;
                    if (!visual) { d.n.Add(U); d.t.Add(tangent); d.uv.Add(Vector2.zero); continue; }
                    double hx = L.GroundAt(Math.Min(L.gN - 1, gx + 1), gz) - L.GroundAt(Math.Max(0, gx - 1), gz);
                    double hz = L.GroundAt(gx, Math.Min(L.gN - 1, gz + 1)) - L.GroundAt(gx, Math.Max(0, gz - 1));
                    d.n.Add((U * 2f - E * (float)hx - N * (float)hz).normalized);
                    double w1 = (ForestLayout.Fbm(x / 23, z / 23, 7, 2) - 0.5) * 7, w2 = (ForestLayout.Fbm(x / 23 + 40, z / 23, 8, 2) - 0.5) * 7;
                    d.uv.Add(new Vector2((float)((x + w1) / tile), (float)((z + w2) / tile)));
                    d.t.Add(tangent);
                }
            var tri = new List<int>(n * n * 6);
            for (int j = 0; j < n - 1; j++)
                for (int i = 0; i < n - 1; i++)
                {
                    int a = j * n + i, b = a + 1, e = a + n + 1, f = a + n;
                    // the same diagonal as ForestLayout.Ground: (0,0)-(1,1)
                    if (wind == 0) { tri.Add(a); tri.Add(b); tri.Add(e); tri.Add(a); tri.Add(e); tri.Add(f); }
                    else { tri.Add(a); tri.Add(e); tri.Add(b); tri.Add(a); tri.Add(f); tri.Add(e); }
                }
            if (visual && step > 1)
            {   // flaps hanging down along the chunk border hide cracks between levels of detail
                int[][] edges = { new int[n], new int[n], new int[n], new int[n] };
                for (int k = 0; k < n; k++) { edges[0][k] = k; edges[1][k] = (n - 1) * n + (n - 1 - k); edges[2][k] = (n - 1 - k) * n; edges[3][k] = k * n + (n - 1); }
                foreach (var ed in edges)
                {
                    int s0 = d.v.Count;
                    foreach (int k in ed) { d.v.Add(d.v[k] - U * (0.25f * step)); d.n.Add(d.n[k]); d.uv.Add(d.uv[k]); d.t.Add(d.t[k]); }
                    for (int k = 0; k < n - 1; k++)
                    {
                        int a = ed[k], b = ed[k + 1], e = s0 + k, f = s0 + k + 1;
                        tri.Add(a); tri.Add(e); tri.Add(b); tri.Add(b); tri.Add(e); tri.Add(f);
                        tri.Add(a); tri.Add(b); tri.Add(e); tri.Add(b); tri.Add(f); tri.Add(e);    // both sides: no winding doubts
                    }
                }
            }
            d.tris[floorIndex] = tri;
            return d;
        }
        int floorIndex;

        // ---------------------------------------------------------------- colliders around the active vessel
        readonly List<CapsuleCollider> trunkPool = new List<CapsuleCollider>();
        readonly List<SphereCollider> rockPool = new List<SphereCollider>();
        GameObject colRoot;
        float vesX, vesZ; bool vesNear;
        bool ColliderWanted(ChunkState c)
        {
            float R = def.colliderRange;
            return vesNear && ChunkHasGround(c) && BoxDist(c.x0, c.z0, Chunk, vesX, vesZ) < R;
        }
        void UpdateColliders()
        {
            Vessel v = FlightGlobals.ActiveVessel;
            if (v == null) return;
            Vector3 vl = transform.InverseTransformPoint(v.transform.position); ToXZ(vl, out vesX, out vesZ);
            float vh = Vector3.Dot(vl, U);
            vesNear = Mathf.Sqrt(vesX * vesX + vesZ * vesZ) < L.R * 1.2f + def.colliderRange && Mathf.Abs(vh) < 400f;
            if (colRoot == null) { colRoot = new GameObject("forest_colliders"); colRoot.layer = 15; colRoot.transform.SetParent(transform, false); }
            float R = def.colliderRange;
            foreach (var c in chunks)
            {
                bool want = ColliderWanted(c);
                if (want && c.groundCol == null && !c.colPending) { c.colPending = true; Enqueue(c, JobKind.Collider, 0, BoxDist(c.x0, c.z0, Chunk, vesX, vesZ) - 100); }
                else if (!want && c.groundCol != null && BoxDist(c.x0, c.z0, Chunk, vesX, vesZ) > R + 20) { Destroy(c.groundCol.sharedMesh); Destroy(c.groundCol.gameObject); c.groundCol = null; }
            }
            // trunks and big rocks within range
            int ti = 0, ri = 0;
            if (vesNear)
            {
                foreach (var c in chunks)
                {
                    if (BoxDist(c.x0, c.z0, Chunk, vesX, vesZ) > R) continue;
                    foreach (int k in c.trees)
                    {
                        var t = L.trees[k]; float ddx = t.x - vesX, ddz = t.z - vesZ;
                        if (ddx * ddx + ddz * ddz > R * R) continue;
                        var sp = def.species[t.kind];
                        if (ti >= trunkPool.Count) { var g = new GameObject("trunk"); g.layer = 15; g.transform.SetParent(colRoot.transform, false); var cc = g.AddComponent<CapsuleCollider>(); cc.direction = 1; trunkPool.Add(cc); }
                        var col = trunkPool[ti++]; if (!col.enabled) col.enabled = true;
                        float h = sp.trunkHeight * t.scale, r = sp.trunkRadius * t.scale;
                        col.transform.localPosition = Local(t.x, t.z, t.y) + U * (h * 0.5f - 0.3f);
                        col.transform.localRotation = Quaternion.LookRotation(N, U);
                        col.radius = r; col.height = h;
                    }
                    foreach (int k in c.props)
                    {
                        var p = L.props[k];
                        if ((p.kind != (int)ForestProp.Rock && p.kind != (int)ForestProp.Log && p.kind != (int)ForestProp.StreamRock) || p.scale < 0.7f) continue;
                        float ddx = p.x - vesX, ddz = p.z - vesZ; if (ddx * ddx + ddz * ddz > R * R) continue;
                        if (ri >= rockPool.Count) { var g = new GameObject("rock"); g.layer = 15; g.transform.SetParent(colRoot.transform, false); rockPool.Add(g.AddComponent<SphereCollider>()); }
                        var sc = rockPool[ri++]; if (!sc.enabled) sc.enabled = true;
                        bool log = p.kind == (int)ForestProp.Log;
                        sc.radius = log ? 0.35f * p.scale : 0.65f * p.scale;
                        sc.transform.localPosition = Local(p.x, p.z, p.y) + U * (log ? 0.3f * p.scale : 0.15f * p.scale);
                    }
                }
            }
            for (int k = ti; k < trunkPool.Count; k++) if (trunkPool[k].enabled) trunkPool[k].enabled = false;
            for (int k = ri; k < rockPool.Count; k++) if (rockPool[k].enabled) rockPool[k].enabled = false;
        }

        // ---------------------------------------------------------------- keeping the floor above the terrain KSP really draws
        /// <summary>The PQS terrain is drawn (and collides) as a mesh between vertices up to ~16 m apart, so in hollows it
        /// can sit above the heights sampled for the layout. Near the vessel, cast rays at the terrain colliders; if any
        /// point of the stock ground comes within 0.3 m of the forest floor, raise the whole forest (only ever up).</summary>
        void ProbeTerrain()
        {
            Vessel v = FlightGlobals.ActiveVessel;
            if (v == null || !vesNear || v.altitude - (L.Ground(vesX, vesZ) + floorOffset) > 300) return;
            Vector3 upW = transform.TransformDirection(U).normalized;
            double worst = double.MinValue;
            var rnd = new System.Random((int)(Time.time * 10));
            for (int k = 0; k < 40; k++)
            {
                double a = rnd.NextDouble() * Math.PI * 2, r = 5 + rnd.NextDouble() * 140;
                double x = vesX + Math.Cos(a) * r, z = vesZ + Math.Sin(a) * r;
                if (!L.InForest(x, z, 12)) continue;
                double floor = L.Ground(x, z);
                Vector3 top = transform.TransformPoint(Local(x, z, floor + 40));
                foreach (var hit in Physics.RaycastAll(top, -upW, 120f, Geo.SceneryMask, QueryTriggerInteraction.Ignore))
                {
                    if (hit.collider == null || hit.collider.GetComponent<PQ>() == null) continue;      // stock terrain only
                    double pqsLocal = Vector3.Dot(transform.InverseTransformPoint(hit.point), U);
                    double floorLocal = Vector3.Dot(Local(x, z, floor), U);
                    worst = Math.Max(worst, pqsLocal - floorLocal);
                }
            }
            if (worst == double.MinValue) return;
            double need = worst + 0.3;          // worst is measured in the forest's own (already raised) frame
            if (need > 0.05 && floorOffset < 3.0)
            {
                need = Math.Min(need, 3.0 - floorOffset);
                floorOffset += need;
                transform.position += upW * (float)need;
                lair.LiftFossils(need);
                XenoLog.Info(string.Format("Forest {0}: stock terrain within {1:F2} m of the floor here; forest raised to +{2:F2} m", lair.def.name, worst, floorOffset));
                SaveOffset();
            }
        }
        string OffsetPath() { string c = CachePath(); return c == null ? null : c + ".offset"; }
        void SaveOffset() { try { var p = OffsetPath(); if (p != null) System.IO.File.WriteAllText(p, floorOffset.ToString("R", System.Globalization.CultureInfo.InvariantCulture)); } catch { } }
        void LoadOffset()
        {
            try
            {
                var p = OffsetPath(); double o;
                if (p != null && System.IO.File.Exists(p) && double.TryParse(System.IO.File.ReadAllText(p), System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out o) && o > 0)
                {
                    floorOffset = Math.Min(o, 3.0);
                    transform.position += transform.TransformDirection(U).normalized * (float)floorOffset;
                }
            }
            catch { }
        }

        // ---------------------------------------------------------------- path, stream, pool and pond
        GameObject Strip(string name, List<Vector3> v, List<Vector2> uv, int across, Material m, bool shadows = false)
        {
            if (v.Count < across * 2) return null;
            var tri = new List<int>(); int rows = v.Count / across;
            var nm = new List<Vector3>(); for (int k = 0; k < v.Count; k++) nm.Add(U);
            for (int r = 0; r < rows - 1; r++)
                for (int k = 0; k < across - 1; k++)
                {
                    int a = r * across + k, b = a + 1, d = a + across, e = d + 1;
                    // Unity's front face is the side Cross(b - a, c - a) points to: pick the order that faces up
                    bool up = Vector3.Dot(Vector3.Cross(v[b] - v[a], v[e] - v[a]), U) > 0;
                    if (up) { tri.Add(a); tri.Add(b); tri.Add(e); tri.Add(a); tri.Add(e); tri.Add(d); }
                    else { tri.Add(a); tri.Add(e); tri.Add(b); tri.Add(a); tri.Add(d); tri.Add(e); }
                }
            var mesh = new Mesh { name = name }; if (v.Count > 65000) mesh.indexFormat = IndexFormat.UInt32;
            mesh.SetVertices(v); mesh.SetUVs(0, uv); mesh.SetNormals(nm); mesh.SetTriangles(tri, 0); mesh.RecalculateBounds();
            var tg = new List<Vector4>(); for (int k = 0; k < v.Count; k++) tg.Add(new Vector4(E.x, E.y, E.z, -1)); mesh.SetTangents(tg);
            var go = new GameObject(name); go.layer = 15; go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r_ = go.AddComponent<MeshRenderer>(); r_.sharedMaterial = m; r_.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off; r_.receiveShadows = true;
            overlays.Add(go);
            return go;
        }

        /// <summary>A ribbon along a centreline: rows of `across` points, cut into ~60 m pieces (so each can be culled).</summary>
        void Ribbon(string name, List<double[]> line, int from, int to, Func<int, double> halfW, Func<double, double, int, double> height,
                    int across, double vTile, Material m, Func<int, bool> skip = null)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); int piece = 0, rowsInPiece = 0;
            for (int i = from; i < to; i++)
            {
                if (skip != null && skip(i)) { if (rowsInPiece > 1) Strip(name + piece++, v, uv, across, m); v = new List<Vector3>(); uv = new List<Vector2>(); rowsInPiece = 0; continue; }
                int a = Math.Max(from, i - 1), b = Math.Min(to - 1, i + 1);
                double tx = line[b][0] - line[a][0], tz = line[b][1] - line[a][1], tl = Math.Sqrt(tx * tx + tz * tz) + 1e-9;
                double nx = -tz / tl, nz = tx / tl, hw = halfW(i);
                double s = line[i].Length > 4 ? line[i][4] : i;
                for (int k = 0; k < across; k++)
                {
                    double o = (k / (double)(across - 1) * 2 - 1) * hw;
                    double x = line[i][0] + nx * o, z = line[i][1] + nz * o;
                    v.Add(Local(x, z, height(x, z, i)));
                    uv.Add(new Vector2(k / (float)(across - 1), (float)(s / vTile)));
                }
                rowsInPiece++;
                if (rowsInPiece >= 60 && i < to - 1)
                {   // start the next piece on this same row so there is no gap
                    Strip(name + piece++, v, uv, across, m);
                    var lv = v.GetRange(v.Count - across, across); var lu = uv.GetRange(uv.Count - across, across);
                    v = new List<Vector3>(lv); uv = new List<Vector2>(lu); rowsInPiece = 1;
                }
            }
            if (rowsInPiece > 1) Strip(name + piece, v, uv, across, m);
        }

        void BuildOverlays()
        {
            var st = L.stream;
            if (st.Count > 2)
            {
                Ribbon("forest_bed", st, 0, st.Count, i => st[i][3] + 1.3, (x, z, i) => L.Ground(x, z) + 0.03, 7, 2 * (st[0][3] + 1.3), bedMat);
                Ribbon("forest_water", st, 0, st.Count, i => st[i][3] + 0.35, (x, z, i) => st[i][2] - 0.03, 3, 4.0, waterMat);
            }
            var pa = L.path;
            Func<int, double> pw = i => pa[i][3] * 1.25;
            Func<double, double, int, double> ph = (x, z, i) => L.Ground(x, z) + 0.04;
            Ribbon("forest_path", pa, 0, L.mainPathCount, pw, ph, 5, 2.75, pathMat, i => pa[i][5] > 0.5);
            if (L.mainPathCount < pa.Count) Ribbon("forest_trail", pa, L.mainPathCount, pa.Count, pw, ph, 5, 2.75, pathMat);
            Disc("forest_pool", L.pool, 1.35); Disc("forest_pond", L.pond, 1.35);
        }

        void Disc(string name, double[] b, double scale)
        {
            int seg = 32; var v = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>(); var nm = new List<Vector3>();
            double r = b[3] * scale;
            v.Add(Local(b[0], b[1], b[2] - 0.02)); uv.Add(new Vector2(0.5f, 0.5f)); nm.Add(U);
            for (int k = 0; k < seg; k++)
            {
                double a = k * Math.PI * 2 / seg, x = b[0] + Math.Cos(a) * r, z = b[1] + Math.Sin(a) * r;
                v.Add(Local(x, z, b[2] - 0.02)); uv.Add(new Vector2((float)(Math.Cos(a) * r / 8), (float)(Math.Sin(a) * r / 8))); nm.Add(U);
            }
            int windD = Winding();
            for (int k = 0; k < seg; k++)
            {
                int a = 1 + k, c = 1 + (k + 1) % seg;
                // counter-clockwise in (x east, z north) seen from above
                if (windD == 0) { tri.Add(0); tri.Add(c); tri.Add(a); } else { tri.Add(0); tri.Add(a); tri.Add(c); }
            }
            var mesh = new Mesh { name = name }; mesh.SetVertices(v); mesh.SetUVs(0, uv); mesh.SetNormals(nm); mesh.SetTriangles(tri, 0); mesh.RecalculateBounds();
            // make sure it faces up whatever the frame's handedness
            var t0 = mesh.triangles; Vector3 fn = Vector3.Cross(v[t0[1]] - v[t0[0]], v[t0[2]] - v[t0[0]]);
            if (Vector3.Dot(fn, U) < 0) { for (int k = 0; k < t0.Length; k += 3) { int q = t0[k + 1]; t0[k + 1] = t0[k + 2]; t0[k + 2] = q; } mesh.triangles = t0; }
            var go = new GameObject(name); go.layer = 15; go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh; var rr = go.AddComponent<MeshRenderer>(); rr.sharedMaterial = pondMat; rr.shadowCastingMode = ShadowCastingMode.Off;
            overlays.Add(go);
        }

        // ---------------------------------------------------------------- bridge, spring, elder
        GameObject Prefab(string url, string name)
        {
            if (string.IsNullOrEmpty(url)) return null;
            var p = GameDatabase.Instance.GetModelPrefab(url);
            if (p == null) { XenoLog.Warn("Forest: model '" + url + "' not found"); return null; }
            var go = Instantiate(p); go.name = name; go.SetActive(true);
            foreach (Collider c in go.GetComponentsInChildren<Collider>(true)) { c.gameObject.layer = 15; c.enabled = true; }
            foreach (MeshCollider mc in go.GetComponentsInChildren<MeshCollider>(true)) mc.convex = false;
            foreach (Rigidbody rb in go.GetComponentsInChildren<Rigidbody>(true)) Destroy(rb);
            go.transform.SetParent(transform, false);
            return go;
        }
        Vector3 Dir(double headingDeg) { double h = headingDeg * Math.PI / 180; return (E * (float)Math.Sin(h) + N * (float)Math.Cos(h)).normalized; }

        void PlaceSetPieces()
        {
            var br = Prefab(def.bridge, "forest_bridge");
            if (br != null)
            {
                Vector3 dir = Dir(L.bridge[2]);
                double y = Math.Max(L.bridge[4], L.bridge[5]) - 0.08;
                br.transform.localPosition = Local(L.bridge[0], L.bridge[1], y);
                br.transform.localRotation = Quaternion.LookRotation(Vector3.Cross(dir, U), U);    // the model's +x runs along the span
                br.transform.localScale = new Vector3((float)Math.Max(1.0, (L.bridge[3] + 2.2) / 11.0), 1, 1);
            }
            var sp = Prefab(def.spring, "forest_spring");
            if (sp != null)
            {
                sp.transform.localPosition = Local(L.cascade[0], L.cascade[1], L.pool[2] - 0.05);
                sp.transform.localRotation = Quaternion.LookRotation(Dir(L.cascade[3]), U);
                CascadeLocal = sp.transform.localPosition + Dir(L.cascade[3]) * 0.9f + U * 0.2f;
                foreach (Renderer r in sp.GetComponentsInChildren<Renderer>(true))
                    if (r.gameObject.name.StartsWith("cascade")) { cascadeMat = r.material; r.shadowCastingMode = ShadowCastingMode.Off; }
            }
            KitMesh e0, e1, ei;
            if (kit.TryGetValue("elder_0", out e0))
            {
                var go = new GameObject("forest_elder"); go.layer = 15; go.transform.SetParent(transform, false);
                go.transform.localPosition = Local(L.elder[0], L.elder[1], L.elder[2] - 0.4);
                go.transform.localRotation = Quaternion.LookRotation(Rot(N, U, (float)L.elder[3]), U);
                elder = go.transform;
                kit.TryGetValue("elder_1", out e1); kit.TryGetValue("elder_imp", out ei);
                var src = new[] { e0, e1, ei };
                for (int k = 0; k < 3; k++)
                {
                    if (src[k] == null) continue;
                    var g = new GameObject("elder_" + k); g.layer = 15; g.transform.SetParent(go.transform, false);
                    g.AddComponent<MeshFilter>().sharedMesh = src[k].mesh;
                    var r = g.AddComponent<MeshRenderer>(); r.sharedMaterials = src[k].mats; r.shadowCastingMode = k == 2 ? ShadowCastingMode.Off : ShadowCastingMode.On;
                    elderLods[k] = r; r.enabled = false;
                }
                var cc = go.AddComponent<CapsuleCollider>(); cc.direction = 1; cc.radius = 1.3f; cc.height = 9f; cc.center = new Vector3(0, 4f, 0);
                if (!string.IsNullOrEmpty(def.elderFossil))
                {   // tucked between two buttress roots, on the side away from the trail
                    var fm = new GameObject("fossil_" + def.elderFossil + "_00"); fm.transform.SetParent(transform, false);
                    double a = (L.elder[3] + 20) * Math.PI / 180, fx = L.elder[0] + Math.Sin(a) * 2.6, fz = L.elder[1] + Math.Cos(a) * 2.6;
                    fm.transform.localPosition = Local(fx, fz, L.Ground(fx, fz) + 0.05);
                    lair.PlaceFossil(fm.transform);
                }
            }
        }

        // ---------------------------------------------------------------- field guide and named spots
        void AddSpecimens()
        {
            var markers = new GameObject("forest_specimens"); markers.transform.SetParent(transform, false);
            int total = 0;
            for (int s = 0; s < def.species.Count; s++)
            {
                var sp = def.species[s]; if (sp.def == null) continue;
                var picked = new List<ForestInstance>();
                var cands = new List<KeyValuePair<double, ForestInstance>>();
                foreach (var t in L.trees) if (t.kind == s) { double d = L.DistPath(t.x, t.z); if (d < 9) cands.Add(new KeyValuePair<double, ForestInstance>(d, t)); }
                cands.Sort((a, b) => a.Key.CompareTo(b.Key));
                foreach (var c in cands)
                {
                    bool far = true; foreach (var p in picked) if ((p.x - c.Value.x) * (p.x - c.Value.x) + (p.z - c.Value.z) * (p.z - c.Value.z) < 35 * 35) { far = false; break; }
                    if (!far) continue; picked.Add(c.Value); if (picked.Count >= 6) break;
                }
                for (int k = 0; k < picked.Count; k++) total += Marker(markers.transform, sp.def, k, picked[k], 1.5f);
            }
            if (elder != null) foreach (var sp in def.species) if (sp.model == "copperoak" && sp.def != null)
                    {
                        var go = new GameObject("spec_" + sp.def.name + "_elder"); go.transform.SetParent(elder, false); go.transform.localPosition = new Vector3(0, 1.5f, 0);
                        lair.specimens.Add(new LairInstance.Specimen { t = go.transform, def = sp.def }); total++;
                    }
            // understory flora by the path
            var under = new[] { new KeyValuePair<LifeformDef, ForestProp>(def.fernDef, ForestProp.Fern), new KeyValuePair<LifeformDef, ForestProp>(def.shrubDef, ForestProp.Shrub), new KeyValuePair<LifeformDef, ForestProp>(def.reedDef, ForestProp.Reed) };
            foreach (var u in under)
            {
                if (u.Key == null) continue;
                int n = 0; var picked = new List<ForestInstance>();
                foreach (var p in L.props)
                {
                    if (p.kind != (int)u.Value) continue;
                    if (u.Value != ForestProp.Reed && L.DistPath(p.x, p.z) > 4) continue;
                    bool far = true; foreach (var q in picked) if ((q.x - p.x) * (q.x - p.x) + (q.z - p.z) * (q.z - p.z) < 40 * 40) { far = false; break; }
                    if (!far) continue;
                    picked.Add(p); total += Marker(markers.transform, u.Key, n++, p, 0.4f);
                    if (n >= 8) break;
                }
            }
            XenoLog.Info("Forest " + lair.def.name + ": " + total + " specimen markers");
        }
        int Marker(Transform parent, LifeformDef d, int k, ForestInstance t, float up)
        {
            var go = new GameObject("spec_" + d.name + "_" + k.ToString("00")); go.transform.SetParent(parent, false);
            go.transform.localPosition = Local(t.x, t.z, t.y) + U * up;
            lair.specimens.Add(new LairInstance.Specimen { t = go.transform, def = d });
            return 1;
        }

        void RegisterSpots()
        {
            Action<string, double, double> add = (n, x, z) => { double la, lo; LatLon(x, z, out la, out lo); lair.spots[n] = new[] { la, lo }; };
            add("clearing", L.clearing[0], L.clearing[1]); add("bridge", L.bridge[0], L.bridge[1]); add("pond", L.pond[0], L.pond[1]);
            add("pool", L.pool[0], L.pool[1]); add("entrance", L.entrance[0], L.entrance[1]); add("elder", L.elder[0], L.elder[1]);
            // the middle of the stream, between the bridge and the pond
            var st = L.stream; if (st.Count > 4) { var m = st[st.Count * 3 / 4]; add("stream", m[0], m[1]); }
            add("pen", L.clearing[0], L.clearing[1]);
        }

        /// <summary>Forest-local position of a world point, and whether it is under the trees.</summary>
        public bool InForest(Vector3 world, out float x, out float z, out float heightAboveFloor)
        {
            x = z = heightAboveFloor = 0;
            if (!ready) return false;
            Vector3 l = transform.InverseTransformPoint(world); ToXZ(l, out x, out z);
            double floor = L.Ground(x, z) - baseAlt - (x * (double)x + z * (double)z) / (2 * bodyR);   // (local frame moves with the offset)
            heightAboveFloor = (float)(Vector3.Dot(l, U) - floor);
            return L.InForest(x, z, 5);
        }
        public float WetAt(float x, float z) { return ready ? (float)L.Wet(x, z) : 0f; }

        void OnDestroy()
        {
            stopping = true; wake.Set();
            if (chunks != null)
                foreach (var c in chunks)
                {
                    if (c == null) continue;
                    for (int k = 0; k < 4; k++) { Free(ref c.tree0[k]); Free(ref c.tree1[k]); Free(ref c.props4[k]); Free(ref c.ground[k]); }
                    Free(ref c.tree2);
                    if (c.groundCol != null) Destroy(c.groundCol.sharedMesh);
                }
            foreach (var go in overlays) if (go != null) { var mf = go.GetComponent<MeshFilter>(); if (mf != null) Destroy(mf.sharedMesh); }
            foreach (var k in kit.Values) if (k.mesh != null) Destroy(k.mesh);
            foreach (var m in new[] { pathMat, bedMat, waterMat, pondMat }) if (m != null) Destroy(m);
        }
    }

    /// <summary>
    /// Life in the air of a forest lair: leaves drifting down around the camera (in gusts now and then), and on still
    /// nights, lantern-motes (glowing seeds or insects) hanging over the water and the clearing; mist at the spring.
    /// </summary>
    public class ForestAmbience : MonoBehaviour
    {
        XenoForest forest; LairInstance lair; ForestDef def;
        ParticleSystem leaves, motes, mist; Transform leavesT, motesT;
        Material leafMat;
        float timer, gust, gustTimer = 20f;
        bool leavesOn, motesOn;

        public void Init(XenoForest f, LairInstance l, ForestDef d)
        {
            forest = f; lair = l; def = d;
            leaves = MakeLeaves(out leavesT);
            motes = MakeMotes(out motesT);
            mist = MakeMist();
        }

        ParticleSystem Base(string name, Transform parent, out Transform t, bool world)
        {
            var go = new GameObject(name); t = go.transform; if (parent != null) t.SetParent(parent, false);
            var ps = go.AddComponent<ParticleSystem>(); ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var m = ps.main; m.playOnAwake = false; m.loop = true; m.simulationSpace = world ? ParticleSystemSimulationSpace.World : ParticleSystemSimulationSpace.Local;
            var em = ps.emission; em.rateOverTime = 0f;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
            return ps;
        }

        static Mesh quad;
        static Mesh Quad()
        {
            if (quad != null) return quad;
            quad = new Mesh { name = "leafquad" };
            quad.vertices = new[] { new Vector3(-0.5f, -0.5f, 0), new Vector3(0.5f, -0.5f, 0), new Vector3(0.5f, 0.5f, 0), new Vector3(-0.5f, 0.5f, 0) };
            quad.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
            quad.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.back };
            quad.triangles = new[] { 0, 2, 1, 0, 3, 2, 0, 1, 2, 0, 2, 3 };    // two-sided
            return quad;
        }

        ParticleSystem MakeLeaves(out Transform t)
        {
            var ps = Base("xeno_fallingleaves", null, out t, true);
            var m = ps.main; m.startLifetime = new ParticleSystem.MinMaxCurve(10f, 16f); m.startSpeed = new ParticleSystem.MinMaxCurve(0f, 0.3f);
            m.startSize = new ParticleSystem.MinMaxCurve(0.07f, 0.14f); m.maxParticles = 300; m.gravityModifier = 0.012f;
            m.startRotation3D = true;
            m.startRotationX = new ParticleSystem.MinMaxCurve(0f, 6.28f); m.startRotationY = new ParticleSystem.MinMaxCurve(0f, 6.28f); m.startRotationZ = new ParticleSystem.MinMaxCurve(0f, 6.28f);
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(44f, 8f, 44f);
            var rot = ps.rotationOverLifetime; rot.enabled = true; rot.separateAxes = true;
            rot.x = new ParticleSystem.MinMaxCurve(-3f, 3f); rot.y = new ParticleSystem.MinMaxCurve(-1.5f, 1.5f); rot.z = new ParticleSystem.MinMaxCurve(-4f, 4f);
            var nz = ps.noise; nz.enabled = true; nz.strength = 0.6f; nz.frequency = 0.35f; nz.scrollSpeed = 0.2f; nz.damping = true;
            var lv = ps.limitVelocityOverLifetime; lv.enabled = true; lv.limit = 1.4f; lv.dampen = 0.15f;
            var ts = ps.textureSheetAnimation; ts.enabled = true; ts.numTilesX = 4; ts.numTilesY = 4; ts.animation = ParticleSystemAnimationType.WholeSheet;
            ts.frameOverTime = new ParticleSystem.MinMaxCurve(0f); ts.startFrame = new ParticleSystem.MinMaxCurve(0f, 15.99f); ts.cycleCount = 1;
            var col = ps.colorOverLifetime; col.enabled = true;
            var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, 0.05f), new GradientAlphaKey(1, 0.9f), new GradientAlphaKey(0, 1) });
            col.color = g;
            var c = ps.collision; c.enabled = true; c.type = ParticleSystemCollisionType.World; c.mode = ParticleSystemCollisionMode.Collision3D;
            c.collidesWith = 1 << 15; c.quality = ParticleSystemCollisionQuality.Low; c.lifetimeLoss = 1f; c.radiusScale = 0.5f; c.maxCollisionShapes = 32; c.enableDynamicColliders = false;
            var r = ps.GetComponent<ParticleSystemRenderer>();
            r.renderMode = ParticleSystemRenderMode.Mesh; r.mesh = Quad();
            // a particle shader (lit part shaders show up magenta on particles): unlit, so the tint follows the daylight
            leafMat = new Material(Shader.Find("KSP/Particles/Alpha Blended") ?? Shader.Find("Legacy Shaders/Particles/Alpha Blended"));
            leafMat.mainTexture = GameDatabase.Instance.GetTexture(def.texDir + "/forest_fallleaves", false);
            r.sharedMaterial = leafMat;
            ps.Play();
            return ps;
        }

        ParticleSystem MakeMotes(out Transform t)
        {
            var ps = Base("xeno_lanternmotes", null, out t, true);
            var m = ps.main; m.startLifetime = new ParticleSystem.MinMaxCurve(5f, 9f); m.startSpeed = new ParticleSystem.MinMaxCurve(0f, 0.15f);
            m.startSize = new ParticleSystem.MinMaxCurve(0.06f, 0.12f); m.maxParticles = 220; m.startColor = new Color(1f, 0.78f, 0.35f, 1f);
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(50f, 4f, 50f);
            var nz = ps.noise; nz.enabled = true; nz.strength = 0.5f; nz.frequency = 0.5f; nz.scrollSpeed = 0.3f;
            var col = ps.colorOverLifetime; col.enabled = true;
            var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(new Color(1f, 0.85f, 0.4f), 0), new GradientColorKey(new Color(1f, 0.55f, 0.25f), 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, 0.2f), new GradientAlphaKey(0.2f, 0.4f), new GradientAlphaKey(1, 0.6f), new GradientAlphaKey(0.3f, 0.8f), new GradientAlphaKey(0, 1) });
            col.color = g;
            var r = ps.GetComponent<ParticleSystemRenderer>();
            var mat = new Material(Shader.Find("KSP/Particles/Additive") ?? Shader.Find("Legacy Shaders/Particles/Additive")); mat.mainTexture = ReefAmbience.Dot();
            r.sharedMaterial = mat;
            ps.Play();
            return ps;
        }

        ParticleSystem MakeMist()
        {
            Transform t;
            var ps = Base("xeno_springmist", forest.transform, out t, false);
            t.localPosition = forest.CascadeLocal;
            var m = ps.main; m.startLifetime = new ParticleSystem.MinMaxCurve(2.5f, 4f); m.startSpeed = new ParticleSystem.MinMaxCurve(0.2f, 0.5f);
            m.startSize = new ParticleSystem.MinMaxCurve(0.6f, 1.3f); m.maxParticles = 60; m.startColor = new Color(0.9f, 0.93f, 0.95f, 0.18f); m.gravityModifier = -0.01f;
            var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 0.6f;
            var col = ps.colorOverLifetime; col.enabled = true;
            var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(0.2f, 0.25f), new GradientAlphaKey(0, 1) });
            col.color = g;
            var sz = ps.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0, 0.6f, 1, 1.6f));
            var r = ps.GetComponent<ParticleSystemRenderer>();
            var mat = new Material(Shader.Find("KSP/Particles/Alpha Blended") ?? Shader.Find("Legacy Shaders/Particles/Alpha Blended")); mat.mainTexture = ReefAmbience.Dot();
            r.sharedMaterial = mat;
            var em = ps.emission; em.rateOverTime = 0f;
            ps.Play();
            return ps;
        }

        void LateUpdate()
        {
            Camera cam = FlightCamera.fetch != null ? FlightCamera.fetch.mainCamera : null;
            if (cam == null || forest == null || !forest.Ready) return;
            Vector3 cp = cam.transform.position;
            timer -= Time.deltaTime; gustTimer -= Time.deltaTime;
            if (gustTimer <= 0) { gust = 4f; gustTimer = UnityEngine.Random.Range(18f, 45f); }
            gust = Mathf.Max(0, gust - Time.deltaTime);
            if (timer <= 0)
            {
                timer = 0.5f;
                float x, z, h; bool inside = forest.InForest(cp, out x, out z, out h);
                bool low = h < 70f && h > -5f;
                leavesOn = inside && low;
                bool night = !Geo.IsDaylight(lair.body, lair.lat, lair.lon);
                if (leafMat != null && leafMat.HasProperty("_TintColor"))
                {   // light on the leaves: sun height above the horizon, dim under the canopy
                    Vector3d p = lair.body.GetWorldSurfacePosition(lair.lat, lair.lon, 0);
                    double sun = Planetarium.fetch != null && Planetarium.fetch.Sun != null ? Vector3d.Dot(lair.body.GetSurfaceNVector(lair.lat, lair.lon), (Planetarium.fetch.Sun.position - p).normalized) : 1;
                    float k = Mathf.Lerp(0.08f, 0.42f, Mathf.Clamp01((float)sun * 2.5f + 0.1f));
                    leafMat.SetColor("_TintColor", new Color(k, k * 0.97f, k * 0.92f, 0.5f));
                }
                motesOn = inside && low && night;
                float wet = forest.WetAt(x, z);
                var e = leaves.emission; e.rateOverTime = leavesOn ? def.leafRate : 0f;
                var e2 = motes.emission; e2.rateOverTime = motesOn ? 6f + 34f * wet : 0f;
                float dm = (cp - mist.transform.position).magnitude;
                var e3 = mist.emission; e3.rateOverTime = dm < 160f ? 9f : 0f;
            }
            Vector3 up = (cp - lair.body.position).normalized;
            if (leavesOn)
            {
                leavesT.position = cp + up * 9f;
                leavesT.rotation = Quaternion.FromToRotation(Vector3.up, up);
                var m = leaves.main; m.gravityModifier = 0.012f;
                var e = leaves.emission; e.rateOverTime = def.leafRate * (gust > 0 ? 4f : 1f);
                var f = leaves.forceOverLifetime; f.enabled = gust > 0; if (gust > 0) { f.space = ParticleSystemSimulationSpace.World; Vector3 w = Vector3.ProjectOnPlane(Vector3.Cross(up, Vector3.right), up).normalized * 0.6f; f.x = w.x; f.y = w.y; f.z = w.z; }
            }
            if (motesOn) { motesT.position = cp - up * 0.5f; motesT.rotation = Quaternion.FromToRotation(Vector3.up, up); }
        }

        void OnDestroy()
        {
            if (leaves != null) Destroy(leaves.gameObject);
            if (motes != null) Destroy(motes.gameObject);
        }
    }
}
