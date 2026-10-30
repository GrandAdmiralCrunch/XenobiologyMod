using System;
using System.Collections.Generic;

namespace Xenobiology
{
    /// <summary>One placed tree or undergrowth piece, in forest-local metres (x east, z north, y up = ground height).</summary>
    public struct ForestInstance
    {
        public int kind;        // tree species index, or (int)ForestProp for undergrowth
        public int variant;
        public float x, y, z, scale, yaw, tilt, tiltDir;
    }

    public enum ForestProp { Fern, Shrub, Sapling, Log, Rock, StreamRock, Mushroom, Stump, Litter, Reed, Lily, Count }

    public class ForestSpecies
    {
        public string name;
        public float weight = 1f;          // overall share
        public float wet;                  // > 0 likes the stream banks
        public float high;                 // > 0 likes higher ground, < 0 hollows
        public float edge;                 // > 0 likes the forest edge
        public float pathside;             // > 0 likes being near the path (lanterns)
        public float cluster = 1f;         // how strongly it grows in groves
        public float minScale = 0.85f, maxScale = 1.2f;
        public float footprint = 1f;       // spacing multiplier (big crowns need room)
        public int variants = 3;
    }

    /// <summary>
    /// The plan of a forest lair: ground surface (the PQS terrain lifted into a forest floor, with a stream channel cut
    /// into it, a spring pool, a pond and a flattened path), the stream's water levels, the path, the bridge, the
    /// clearing, and every tree and undergrowth piece. Pure C# (no Unity), deterministic for a given seed and terrain,
    /// so it can run on a worker thread and be tested outside the game.
    /// Terrain: a grid of PQS heights (pqsStep apart) covering [-E, E] in x and z, filled in by the caller.
    /// </summary>
    public class ForestLayout
    {
        // ---------------------------------------------------------------- parameters
        public double R = 500;                 // forest radius (the edge wobbles around this)
        public int seed = 1;
        public double spacing = 6.6;           // mean tree spacing (m)
        public double entranceBearing = 90;    // the path starts on this side (deg, 0 = north)
        public double lift = 1.3;              // forest floor sits this far above the PQS terrain (hides it)
        public double skirt = 2.2;             // and dips this far below it at the rim
        public double pathHalfWidth = 1.1;
        public double streamMinHW = 1.3, streamMaxHW = 2.1;
        public double waterDepth = 0.5, minWaterAbovePqs = 1.25;
        public double poolRadius = 7.5, pondRadius = 15, clearingRadius = 24;
        public double bridgeHalf;              // computed: half the span between abutments
        public double propDensity = 1.0;
        public readonly List<ForestSpecies> species = new List<ForestSpecies>();

        // ---------------------------------------------------------------- terrain input
        public double E;                       // half-extent of the grids
        public double pqsStep = 8;
        public int pqsN;
        public float[] pqs;                    // pqsN x pqsN, row-major (z, x)
        public void InitPqs() { E = Math.Ceiling((R * 1.1 + 45) / pqsStep) * pqsStep; pqsN = (int)(2 * E / pqsStep) + 1; pqs = new float[pqsN * pqsN]; }
        public double PqsX(int i) { return -E + i * pqsStep; }

        // ---------------------------------------------------------------- outputs
        public const double GStep = 1.0;
        public int gN;                         // ground grid: gN x gN at 1 m
        public float[] ground;
        public float[] wetness;                // 0..1 near water (moss, ferns)
        public readonly List<double[]> stream = new List<double[]>();   // x, z, waterLevel, halfWidth, s
        public readonly List<double[]> path = new List<double[]>();     // x, z, surface, halfWidth, s, onBridge(0/1)
        public double[] pool = new double[4];      // x, z, waterLevel, radius
        public double[] pond = new double[4];
        public double[] clearing = new double[3];  // x, z, radius
        public double[] elder = new double[4];     // x, z, y, yaw
        public double[] bridge = new double[7];    // x, z, heading(deg), span, deckY at a end, deckY at b end, midWater
        public double[] cascade = new double[4];   // x, z, y (rock base), heading toward the pool (deg)
        public double[] entrance = new double[3];  // x, z, y
        public readonly List<ForestInstance> trees = new List<ForestInstance>();
        public readonly List<ForestInstance> props = new List<ForestInstance>();
        public string log = "";
        public int mainPathCount;              // path[0..mainPathCount) is the trail, the rest the side trail to the pond

        float[] dStream, dPath; int[] iStream, iPath;   // per ground cell: distance to (and index of) the nearest centreline point
        Random rng;

        // ---------------------------------------------------------------- noise
        static double Hash(int x, int y, int s)
        {
            unchecked
            {
                uint h = (uint)(x * 374761393 + y * 668265263 + s * 1442695041);
                h = (h ^ (h >> 13)) * 1274126177u; h ^= h >> 16;
                return (h & 0xFFFFFF) / (double)0x1000000;
            }
        }
        public static double Noise(double x, double y, int s)
        {
            int x0 = (int)Math.Floor(x), y0 = (int)Math.Floor(y); double tx = x - x0, ty = y - y0;
            tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty);
            double a = Hash(x0, y0, s), b = Hash(x0 + 1, y0, s), c = Hash(x0, y0 + 1, s), d = Hash(x0 + 1, y0 + 1, s);
            return (a + (b - a) * tx) + ((c + (d - c) * tx) - (a + (b - a) * tx)) * ty;
        }
        public static double Fbm(double x, double y, int s, int oct = 3)
        {
            double v = 0, amp = 0.5, tot = 0;
            for (int o = 0; o < oct; o++) { v += Noise(x, y, s + o * 31) * amp; tot += amp; x *= 2.03; y *= 2.03; amp *= 0.5; }
            return v / tot;
        }
        static double Smooth(double e0, double e1, double v) { double t = Math.Max(0, Math.Min(1, (v - e0) / (e1 - e0))); return t * t * (3 - 2 * t); }

        // ---------------------------------------------------------------- terrain sampling
        /// <summary>PQS height (Catmull-Rom over the coarse grid).</summary>
        public double Pqs(double x, double z)
        {
            double fx = (x + E) / pqsStep, fz = (z + E) / pqsStep;
            int ix = (int)Math.Floor(fx), iz = (int)Math.Floor(fz); double tx = fx - ix, tz = fz - iz;
            double r = 0;
            for (int j = -1; j <= 2; j++)
            {
                double row = 0;
                for (int i = -1; i <= 2; i++) row += P(ix + i, iz + j) * Cr(i, tx);
                r += row * Cr(j, tz);
            }
            return r;
        }
        double P(int i, int j) { i = Math.Max(0, Math.Min(pqsN - 1, i)); j = Math.Max(0, Math.Min(pqsN - 1, j)); return pqs[j * pqsN + i]; }
        static double Cr(int k, double t)
        {
            switch (k)
            {
                case -1: return ((-t + 2) * t - 1) * t * 0.5;
                case 0: return (((3 * t - 5) * t) * t + 2) * 0.5;
                case 1: return ((-3 * t + 4) * t + 1) * t * 0.5;
                default: return ((t - 1) * t * t) * 0.5;
            }
        }

        /// <summary>The forest floor at any point (bilinear over the 1 m ground grid: the same surface the ground mesh draws).</summary>
        public double Ground(double x, double z)
        {
            double fx = (x + E) / GStep, fz = (z + E) / GStep;
            int ix = (int)Math.Floor(fx), iz = (int)Math.Floor(fz);
            if (ix < 0 || iz < 0 || ix >= gN - 1 || iz >= gN - 1) return Pqs(x, z);
            double tx = fx - ix, tz = fz - iz;
            int k = iz * gN + ix;
            // same diagonal split as the mesh: (0,0)-(1,1)
            double h00 = ground[k], h10 = ground[k + 1], h01 = ground[k + gN], h11 = ground[k + gN + 1];
            if (tx >= tz) return h00 + (h10 - h00) * tx + (h11 - h10) * tz;
            return h00 + (h11 - h01) * tx + (h01 - h00) * tz;
        }
        public double GroundAt(int ix, int iz) { return ground[iz * gN + ix]; }
        public double Wet(double x, double z)
        {
            int ix = (int)Math.Round((x + E) / GStep), iz = (int)Math.Round((z + E) / GStep);
            if (ix < 0 || iz < 0 || ix >= gN || iz >= gN) return 0;
            return wetness[iz * gN + ix];
        }

        /// <summary>The wobbly forest edge: radius of the tree line at bearing a (rad).</summary>
        double[] edgeTab;
        public double EdgeR(double a)
        {
            if (edgeTab == null)
            {
                var t = new double[1025];
                for (int i = 0; i <= 1024; i++) { double aa = i / 1024.0 * 2 * Math.PI; t[i] = R * (0.93 + 0.16 * Fbm(Math.Cos(aa) * 2.2 + 11, Math.Sin(aa) * 2.2 + 7, seed + 5, 3)); }
                edgeTab = t;
            }
            double f = (a / (2 * Math.PI) % 1.0 + 1.0) % 1.0 * 1024; int k = (int)f; double u = f - k;
            return edgeTab[k] + (edgeTab[k + 1] - edgeTab[k]) * u;
        }
        public double RimR(double a) { return EdgeR(a) + 10; }
        public bool InForest(double x, double z, double margin = 0) { return Math.Sqrt(x * x + z * z) < EdgeR(Math.Atan2(z, x)) - margin; }

        public double DistStream(double x, double z) { int k = Cell(x, z); return k < 0 ? 1e9 : dStream[k]; }
        public double DistPath(double x, double z) { int k = Cell(x, z); return k < 0 ? 1e9 : dPath[k]; }
        int Cell(double x, double z)
        {
            int ix = (int)Math.Round((x + E) / GStep), iz = (int)Math.Round((z + E) / GStep);
            if (ix < 0 || iz < 0 || ix >= gN || iz >= gN) return -1;
            return iz * gN + ix;
        }

        // ================================================================ cache (so a saved game loads its forest at once)
        public const int CacheVersion = 4;
        public void Save(string file)
        {
            using (var w = new System.IO.BinaryWriter(System.IO.File.Create(file)))
            {
                w.Write(CacheVersion); w.Write(seed); w.Write(R); w.Write(E); w.Write(gN); w.Write(mainPathCount); w.Write(bridgeHalf);
                Action<float[]> fa = a => { w.Write(a.Length); var b = new byte[a.Length * 4]; Buffer.BlockCopy(a, 0, b, 0, b.Length); w.Write(b); };
                fa(ground); fa(wetness); fa(dPath); fa(dStream); fa(pqs);
                Action<List<double[]>> fl = l => { w.Write(l.Count); foreach (var r in l) { w.Write(r.Length); foreach (var v in r) w.Write(v); } };
                fl(stream); fl(path);
                foreach (var a in new[] { pool, pond, clearing, elder, bridge, cascade, entrance }) { w.Write(a.Length); foreach (var v in a) w.Write(v); }
                Action<List<ForestInstance>> fi = l => { w.Write(l.Count); foreach (var t in l) { w.Write(t.kind); w.Write(t.variant); w.Write(t.x); w.Write(t.y); w.Write(t.z); w.Write(t.scale); w.Write(t.yaw); w.Write(t.tilt); w.Write(t.tiltDir); } };
                fi(trees); fi(props);
                w.Write(log ?? "");
            }
        }
        public bool Load(string file)
        {
            try
            {
                using (var r = new System.IO.BinaryReader(System.IO.File.OpenRead(file)))
                {
                    if (r.ReadInt32() != CacheVersion || r.ReadInt32() != seed || r.ReadDouble() != R || r.ReadDouble() != E) return false;
                    gN = r.ReadInt32(); mainPathCount = r.ReadInt32(); bridgeHalf = r.ReadDouble();
                    Func<float[]> fa = () => { int n = r.ReadInt32(); var b = r.ReadBytes(n * 4); var a = new float[n]; Buffer.BlockCopy(b, 0, a, 0, b.Length); return a; };
                    ground = fa(); wetness = fa(); dPath = fa(); dStream = fa(); pqs = fa();
                    Action<List<double[]>> fl = l => { l.Clear(); int n = r.ReadInt32(); for (int i = 0; i < n; i++) { var a = new double[r.ReadInt32()]; for (int k = 0; k < a.Length; k++) a[k] = r.ReadDouble(); l.Add(a); } };
                    fl(stream); fl(path);
                    foreach (var a in new[] { pool, pond, clearing, elder, bridge, cascade, entrance }) { int n = r.ReadInt32(); for (int k = 0; k < n; k++) a[k] = r.ReadDouble(); }
                    Action<List<ForestInstance>> fi = l => { l.Clear(); int n = r.ReadInt32(); for (int i = 0; i < n; i++) l.Add(new ForestInstance { kind = r.ReadInt32(), variant = r.ReadInt32(), x = r.ReadSingle(), y = r.ReadSingle(), z = r.ReadSingle(), scale = r.ReadSingle(), yaw = r.ReadSingle(), tilt = r.ReadSingle(), tiltDir = r.ReadSingle() }); };
                    fi(trees); fi(props);
                    log = "from cache: " + r.ReadString();
                }
                return true;
            }
            catch (Exception) { return false; }
        }

        // ================================================================ generate
        public void Generate()
        {
            rng = new Random(seed);
            var t0 = DateTime.Now;
            gN = (int)(2 * E / GStep) + 1;
            var sw = System.Diagnostics.Stopwatch.StartNew(); string tm = "";
            PlanStream(); tm += " stream " + sw.ElapsedMilliseconds;
            PlanPath(); tm += " path " + sw.ElapsedMilliseconds;
            BuildGround(); tm += " ground " + sw.ElapsedMilliseconds;
            PlaceFeatures();
            ScatterTrees(); tm += " trees " + sw.ElapsedMilliseconds;
            ScatterProps(); tm += " props " + sw.ElapsedMilliseconds;
            log += "timing (ms):" + tm + "\n";
            log += string.Format("generated in {0:F0} ms: {1} trees, {2} props, stream {3:F0} m, path {4:F0} m\n",
                (DateTime.Now - t0).TotalMilliseconds, trees.Count, props.Count, stream.Count > 0 ? stream[stream.Count - 1][4] : 0, path.Count > 0 ? path[path.Count - 1][4] : 0);
        }

        // ---------------------------------------------------------------- grid search (Dijkstra on a 4 m lattice)
        const double RS = 4.0;
        int rN;
        class Heap
        {
            readonly List<KeyValuePair<double, int>> a = new List<KeyValuePair<double, int>>();
            public int Count { get { return a.Count; } }
            public void Push(double k, int v)
            {
                a.Add(new KeyValuePair<double, int>(k, v)); int i = a.Count - 1;
                while (i > 0) { int p = (i - 1) / 2; if (a[p].Key <= a[i].Key) break; var t = a[p]; a[p] = a[i]; a[i] = t; i = p; }
            }
            public KeyValuePair<double, int> Pop()
            {
                var top = a[0]; var last = a[a.Count - 1]; a.RemoveAt(a.Count - 1);
                if (a.Count > 0)
                {
                    a[0] = last; int i = 0;
                    while (true)
                    {
                        int l = 2 * i + 1, r = l + 1, m = i;
                        if (l < a.Count && a[l].Key < a[m].Key) m = l;
                        if (r < a.Count && a[r].Key < a[m].Key) m = r;
                        if (m == i) break;
                        var t = a[m]; a[m] = a[i]; a[i] = t; i = m;
                    }
                }
                return top;
            }
        }

        /// <summary>Cheapest route from a to any cell where goal() is true. cost(x0,z0,x1,z1) per step (infinity = blocked).</summary>
        List<double[]> Route(double ax, double az, Func<double, double, bool> goal, Func<double, double, double, double, double> cost)
        {
            rN = (int)(2 * E / RS) + 1;
            var dist = new double[rN * rN]; var prev = new int[rN * rN];
            for (int i = 0; i < dist.Length; i++) { dist[i] = double.MaxValue; prev[i] = -1; }
            int s = Idx(ax, az); dist[s] = 0;
            var h = new Heap(); h.Push(0, s);
            int[] dx = { 1, -1, 0, 0, 1, 1, -1, -1, 2, 2, -2, -2, 1, 1, -1, -1 };
            int[] dz = { 0, 0, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 2, -2, 2, -2 };
            int found = -1;
            while (h.Count > 0)
            {
                var top = h.Pop(); int c = top.Value;
                if (top.Key > dist[c]) continue;
                int cx = c % rN, cz = c / rN; double x0 = -E + cx * RS, z0 = -E + cz * RS;
                if (c != s && goal(x0, z0)) { found = c; break; }
                for (int k = 0; k < dx.Length; k++)
                {
                    int nx = cx + dx[k], nz = cz + dz[k];
                    if (nx < 1 || nz < 1 || nx >= rN - 1 || nz >= rN - 1) continue;
                    double x1 = -E + nx * RS, z1 = -E + nz * RS;
                    double w = cost(x0, z0, x1, z1);
                    if (double.IsInfinity(w)) continue;
                    int n = nz * rN + nx; double nd = dist[c] + w;
                    if (nd < dist[n]) { dist[n] = nd; prev[n] = c; h.Push(nd, n); }
                }
            }
            var pts = new List<double[]>();
            if (found < 0) return pts;
            for (int c = found; c >= 0; c = prev[c]) pts.Add(new[] { -E + (c % rN) * RS, -E + (c / rN) * RS });
            pts.Reverse();
            pts[0] = new[] { ax, az };
            return pts;
        }
        int Idx(double x, double z)
        {
            int ix = Math.Max(0, Math.Min(rN - 1, (int)Math.Round((x + E) / RS))), iz = Math.Max(0, Math.Min(rN - 1, (int)Math.Round((z + E) / RS)));
            return iz * rN + ix;
        }

        /// <summary>Douglas-Peucker: drop lattice stair-steps so the smoothing gives long, natural curves.</summary>
        static List<double[]> Simplify(List<double[]> p, double tol)
        {
            if (p.Count < 3) return p;
            var keep = new bool[p.Count]; keep[0] = keep[p.Count - 1] = true;
            var st = new Stack<int[]>(); st.Push(new[] { 0, p.Count - 1 });
            while (st.Count > 0)
            {
                var seg = st.Pop(); int a = seg[0], b = seg[1]; double best = 0; int bi = -1;
                double ax = p[a][0], az = p[a][1], bx = p[b][0], bz = p[b][1], L = Math.Sqrt((bx - ax) * (bx - ax) + (bz - az) * (bz - az)) + 1e-9;
                for (int i = a + 1; i < b; i++)
                {
                    double d = Math.Abs((bx - ax) * (az - p[i][1]) - (ax - p[i][0]) * (bz - az)) / L;
                    if (d > best) { best = d; bi = i; }
                }
                if (bi >= 0 && best > tol) { keep[bi] = true; st.Push(new[] { a, bi }); st.Push(new[] { bi, b }); }
            }
            var o = new List<double[]>();
            for (int i = 0; i < p.Count; i++) if (keep[i]) o.Add(p[i]);
            return o;
        }

        static List<double[]> Chaikin(List<double[]> p, int iters)
        {
            for (int it = 0; it < iters; it++)
            {
                if (p.Count < 3) return p;
                var q = new List<double[]> { p[0] };
                for (int i = 0; i < p.Count - 1; i++)
                {
                    q.Add(new[] { p[i][0] * 0.75 + p[i + 1][0] * 0.25, p[i][1] * 0.75 + p[i + 1][1] * 0.25 });
                    q.Add(new[] { p[i][0] * 0.25 + p[i + 1][0] * 0.75, p[i][1] * 0.25 + p[i + 1][1] * 0.75 });
                }
                q.Add(p[p.Count - 1]);
                p = q;
            }
            return p;
        }
        /// <summary>Resample a polyline to fixed steps; returns x, z, s.</summary>
        static List<double[]> Resample(List<double[]> p, double step)
        {
            var o = new List<double[]>();
            if (p.Count == 0) return o;
            o.Add(new[] { p[0][0], p[0][1], 0 });
            double carry = 0, s = 0;
            for (int i = 0; i < p.Count - 1; i++)
            {
                double ax = p[i][0], az = p[i][1], bx = p[i + 1][0], bz = p[i + 1][1];
                double L = Math.Sqrt((bx - ax) * (bx - ax) + (bz - az) * (bz - az));
                double t = step - carry;
                while (t <= L) { s += step; o.Add(new[] { ax + (bx - ax) * t / L, az + (bz - az) * t / L, s }); t += step; }
                carry = L - (t - step);
            }
            var last = p[p.Count - 1];
            double lx = o[o.Count - 1][0], lz = o[o.Count - 1][1];
            double rem = Math.Sqrt((last[0] - lx) * (last[0] - lx) + (last[1] - lz) * (last[1] - lz));
            if (rem > step * 0.3) o.Add(new[] { last[0], last[1], s + rem });
            return o;
        }
        /// <summary>Sideways meander: offset each point along the normal by a smooth noise wave (ends pinned).</summary>
        static void Meander(List<double[]> p, double amp, double wave, int s, double pinA = 8, double pinB = 8)
        {
            if (p.Count < 3) return;
            double total = p[p.Count - 1][2];
            var o = new double[p.Count, 2];
            for (int i = 0; i < p.Count; i++)
            {
                int a = Math.Max(0, i - 1), b = Math.Min(p.Count - 1, i + 1);
                double tx = p[b][0] - p[a][0], tz = p[b][1] - p[a][1], L = Math.Sqrt(tx * tx + tz * tz) + 1e-9;
                double nx = -tz / L, nz = tx / L, sv = p[i][2];
                double pin = Smooth(0, pinA, sv) * Smooth(0, pinB, total - sv);
                double off = (Fbm(sv / wave, 3.7, s, 2) - 0.5) * 2 * amp * pin;
                o[i, 0] = p[i][0] + nx * off; o[i, 1] = p[i][1] + nz * off;
            }
            for (int i = 0; i < p.Count; i++) { p[i][0] = o[i, 0]; p[i][1] = o[i, 1]; }
        }

        // ---------------------------------------------------------------- stream: spring pool -> pond, downhill
        float[] hs; // smoothed PQS on the routing lattice (water follows the broad shape of the land, not every bump)
        double Hs(double x, double z)
        {
            int ix = Math.Max(0, Math.Min(rN - 1, (int)Math.Round((x + E) / RS))), iz = Math.Max(0, Math.Min(rN - 1, (int)Math.Round((z + E) / RS)));
            return hs[iz * rN + ix];
        }
        void SmoothedTerrain()
        {
            rN = (int)(2 * E / RS) + 1;
            var a = new float[rN * rN];
            for (int k = 0; k < a.Length; k++) a[k] = (float)Pqs(-E + (k % rN) * RS, -E + (k / rN) * RS);
            var b = new float[a.Length];
            for (int pass = 0; pass < 3; pass++)
            {
                for (int z = 0; z < rN; z++) for (int x = 0; x < rN; x++)
                    {   // horizontal box blur, radius 3
                        double acc = 0; int c = 0;
                        for (int d = -3; d <= 3; d++) { int xx = x + d; if (xx < 0 || xx >= rN) continue; acc += a[z * rN + xx]; c++; }
                        b[z * rN + x] = (float)(acc / c);
                    }
                for (int z = 0; z < rN; z++) for (int x = 0; x < rN; x++)
                    {
                        double acc = 0; int c = 0;
                        for (int d = -3; d <= 3; d++) { int zz = z + d; if (zz < 0 || zz >= rN) continue; acc += b[zz * rN + x]; c++; }
                        a[z * rN + x] = (float)(acc / c);
                    }
            }
            hs = a;
        }

        /// <summary>Follow the land downhill from a spring: steepest descent on the smoothed terrain, escaping small pits
        /// over their lowest rim. Stops in a real hollow, at the forest margin or after maxLen.</summary>
        List<double[]> Descend(double sx, double sz, int salt, out bool pit)
        {
            var pts = new List<double[]> { new[] { sx, sz } };
            var visited = new HashSet<int>();
            int cx = (int)Math.Round((sx + E) / RS), cz = (int)Math.Round((sz + E) / RS);
            double len = 0; pit = false;
            int[] dx = { 1, -1, 0, 0, 1, 1, -1, -1 }, dz = { 0, 0, 1, -1, 1, -1, 1, -1 };
            double heading = double.NaN;
            while (len < R * 1.9)
            {
                visited.Add(cz * rN + cx);
                double h0 = hs[cz * rN + cx], best = double.MaxValue; int bx = -1, bz = -1;
                for (int k = 0; k < 8; k++)
                {
                    int nx = cx + dx[k], nz = cz + dz[k];
                    if (nx < 1 || nz < 1 || nx >= rN - 1 || nz >= rN - 1 || visited.Contains(nz * rN + nx)) continue;
                    double L = (k < 4 ? 1 : 1.4142) * RS;
                    double drop = (h0 - hs[nz * rN + nx]) / L;
                    if (drop <= 0) continue;
                    // prefer keeping direction a little (long, sweeping reaches) and a dash of noise
                    double turn = 0;
                    if (!double.IsNaN(heading)) { double hh = Math.Atan2(dz[k], dx[k]); turn = 1 - Math.Cos(hh - heading); }
                    double sc = -drop * 40 + turn * 0.35 + Noise((cx + dx[k]) * 0.37, (cz + dz[k]) * 0.37, seed + salt) * 0.25;
                    if (sc < best) { best = sc; bx = nx; bz = nz; }
                }
                if (bx < 0)
                {   // a pit: find the lowest way out within 60 m (minimax), give up if it climbs more than 1.2 m
                    var esc = Escape(cx, cz, h0, visited);
                    if (esc == null) { pit = true; break; }
                    foreach (var e in esc) { pts.Add(e); }
                    var last = esc[esc.Count - 1];
                    cx = (int)Math.Round((last[0] + E) / RS); cz = (int)Math.Round((last[1] + E) / RS);
                    len += esc.Count * RS;
                    foreach (var e in esc) visited.Add((int)Math.Round((e[1] + E) / RS) * rN + (int)Math.Round((e[0] + E) / RS));
                    continue;
                }
                heading = Math.Atan2(bz - cz, bx - cx);
                cx = bx; cz = bz; len += RS;
                double x = -E + cx * RS, z = -E + cz * RS;
                pts.Add(new[] { x, z });
                if (!InForest(x, z, R * 0.24)) break;
            }
            return pts;
        }
        List<double[]> Escape(int cx, int cz, double h0, HashSet<int> visited)
        {
            var key = new Dictionary<int, double>(); var prev = new Dictionary<int, int>();
            var heap = new Heap(); int s = cz * rN + cx; key[s] = h0; heap.Push(h0, s);
            int[] dx = { 1, -1, 0, 0, 1, 1, -1, -1 }, dz = { 0, 0, 1, -1, 1, -1, 1, -1 };
            int found = -1;
            while (heap.Count > 0)
            {
                var t = heap.Pop(); int c = t.Value; if (t.Key > key[c]) continue;
                if (t.Key > h0 + 1.2) break;
                int x = c % rN, z = c / rN;
                if (Math.Abs(x - cx) > 15 || Math.Abs(z - cz) > 15) continue;
                if (c != s && hs[c] < h0 - 0.05 && !visited.Contains(c)) { found = c; break; }
                for (int k = 0; k < 8; k++)
                {
                    int nx = x + dx[k], nz = z + dz[k]; if (nx < 1 || nz < 1 || nx >= rN - 1 || nz >= rN - 1) continue;
                    int n = nz * rN + nx; double kk = Math.Max(t.Key, hs[n]);
                    double old; if (key.TryGetValue(n, out old) && old <= kk) continue;
                    key[n] = kk; prev[n] = c; heap.Push(kk, n);
                }
            }
            if (found < 0) return null;
            var o = new List<double[]>();
            for (int c = found; c != s; c = prev[c]) o.Add(new[] { -E + (c % rN) * RS, -E + (c / rN) * RS });
            o.Reverse();
            return o;
        }

        // ---------------------------------------------------------------- stream: spring pool -> pond, downhill
        void PlanStream()
        {
            SmoothedTerrain();
            // the general fall of the land: least-squares plane over the disc
            double sxx = 0, szz = 0, sxz = 0, sxh = 0, szh = 0; int n = 0;
            for (double z = -R; z <= R; z += 24) for (double x = -R; x <= R; x += 24)
                {
                    if (x * x + z * z > R * R) continue;
                    double h = Pqs(x, z); sxx += x * x; szz += z * z; sxz += x * z; sxh += x * h; szh += z * h; n++;
                }
            double det = sxx * szz - sxz * sxz;
            double gx = (sxh * szz - szh * sxz) / det, gz = (szh * sxx - sxh * sxz) / det;      // dh/dx, dh/dz
            double gl = Math.Sqrt(gx * gx + gz * gz);
            double ux, uz;    // uphill unit
            if (gl < 1e-5) { double a = rng.NextDouble() * Math.PI * 2; ux = Math.Cos(a); uz = Math.Sin(a); }
            else { ux = gx / gl; uz = gz / gl; }
            log += string.Format("slope {0:F3} ({1:F1} m over the forest), uphill toward {2:F0} deg\n", gl, gl * 2 * R, (Math.Atan2(ux, uz) * 180 / Math.PI + 360) % 360);
            // spring candidates high on the uphill side, pond candidates in low, flat ground on the far side
            var springs = new List<double[]>(); var ponds = new List<double[]>();
            for (int k = 0; k < 90; k++)
            {
                double ang = (rng.NextDouble() - 0.5) * 2.2, rr = R * (0.5 + rng.NextDouble() * 0.28);
                double cx = (ux * Math.Cos(ang) - uz * Math.Sin(ang)) * rr, cz = (ux * Math.Sin(ang) + uz * Math.Cos(ang)) * rr;
                if (!InForest(cx, cz, 95)) continue;
                springs.Add(new[] { cx, cz, -Hs(cx, cz) });
                double px0 = -cx * 0.95 + (rng.NextDouble() - 0.5) * 60, pz0 = -cz * 0.95 + (rng.NextDouble() - 0.5) * 60;
                if (!InForest(px0, pz0, pondRadius * 2 + 70)) continue;
                double h = Pqs(px0, pz0), rough = 0;
                for (int j = 0; j < 8; j++) { double aq = j * Math.PI / 4; rough = Math.Max(rough, Math.Abs(Pqs(px0 + Math.Cos(aq) * pondRadius * 1.3, pz0 + Math.Sin(aq) * pondRadius * 1.3) - h)); }
                ponds.Add(new[] { px0, pz0, Hs(px0, pz0) + rough * 2 });
            }
            springs.Sort((p1, p2) => p1[2].CompareTo(p2[2]));
            ponds.Sort((p1, p2) => p1[2].CompareTo(p2[2]));
            List<double[]> bestRoute = null; double bestScore = double.MaxValue;
            int ns = seed + 101;
            for (int si = 0; si < Math.Min(2, springs.Count); si++)
                for (int pi = 0; pi < Math.Min(3, ponds.Count); pi++)
                {
                    double sx = springs[si][0], sz = springs[si][1], tx = ponds[pi][0], tz = ponds[pi][1];
                    double hEnd = Hs(tx, tz);
                    var rt = Route(sx, sz, (x, z) => (x - tx) * (x - tx) + (z - tz) * (z - tz) < RS * RS * 2.1,
                        (x0, z0, x1, z1) =>
                        {
                            double L = Math.Sqrt((x1 - x0) * (x1 - x0) + (z1 - z0) * (z1 - z0));
                            if (L > RS * 1.5) return double.PositiveInfinity;          // 8-neighbour only
                            if (!InForest(x1, z1, 45)) return double.PositiveInfinity;
                            double h1 = Hs(x1, z1), climb = Math.Max(0, h1 - Hs(x0, z0));
                            double below = Math.Max(0, hEnd - h1);                     // never dip below the pond
                            return L * (1 + 0.8 * Fbm(x1 / 70, z1 / 70, ns, 2)) + climb * 260 + below * 40;
                        });
                    if (rt.Count < 10) continue;
                    // how much would the water have to be banked up above the land? (suffix max of the terrain)
                    double runH = double.MinValue, bank = 0, L2 = rt.Count * RS;
                    for (int i = rt.Count - 1; i >= 0; i--) { double h = Pqs(rt[i][0], rt[i][1]); runH = Math.Max(runH, h); bank = Math.Max(bank, runH - h); }
                    double sc = bank * 120 - Math.Min(L2, 800) * 0.6 - (Hs(sx, sz) - hEnd) * 2;
                    if (sc < bestScore) { bestScore = sc; bestRoute = rt; }
                    log += string.Format("  stream option {0}/{1}: {2:F0} m, banked {3:F1} m\n", si, pi, L2, bank);
                }
            if (bestRoute == null)
            {   // flat land: a gentle meander across the middle
                bestRoute = new List<double[]> { new[] { ux * R * 0.5, uz * R * 0.5 }, new[] { -uz * R * 0.1, ux * R * 0.1 }, new[] { -ux * R * 0.5, -uz * R * 0.5 } };
                log += "stream: no route found, straight route\n";
            }
            bestRoute = Simplify(bestRoute, 9.0);
            // pull the end back inside the forest if needed (the pond needs room)
            while (bestRoute.Count > 3)
            {
                var e = bestRoute[bestRoute.Count - 1];
                if (Math.Sqrt(e[0] * e[0] + e[1] * e[1]) < R * 0.74) break;
                bestRoute.RemoveAt(bestRoute.Count - 1);
            }
            double sx0 = bestRoute[0][0], sz0 = bestRoute[0][1];
            var endp = bestRoute[bestRoute.Count - 1];
            double px = endp[0], pz = endp[1];
            // the pond spreads out beyond the end of the stream, downhill
            if (bestRoute.Count > 1)
            {
                var pr = bestRoute[bestRoute.Count - 2]; double tx = px - pr[0], tz = pz - pr[1], tl = Math.Sqrt(tx * tx + tz * tz) + 1e-9;
                px += tx / tl * pondRadius * 0.7; pz += tz / tl * pondRadius * 0.7;
            }
            // and the spring pool sits just above the first reach
            if (bestRoute.Count > 1)
            {
                var pr = bestRoute[1]; double tx = sx0 - pr[0], tz = sz0 - pr[1], tl = Math.Sqrt(tx * tx + tz * tz) + 1e-9;
                sx0 += tx / tl * poolRadius * 0.6; sz0 += tz / tl * poolRadius * 0.6;
            }
            // keep both basins (and their banks) well inside the trees
            for (int it = 0; it < 40 && !InForest(px, pz, pondRadius * 1.6 + 30); it++) { px *= 0.96; pz *= 0.96; }
            for (int it = 0; it < 40 && !InForest(sx0, sz0, poolRadius * 1.6 + 30); it++) { sx0 *= 0.96; sz0 *= 0.96; }
            pool[0] = sx0; pool[1] = sz0; pool[3] = poolRadius;
            pond[0] = px; pond[1] = pz; pond[3] = pondRadius;
            double hp = Pqs(px, pz);
            var route2 = new List<double[]> { new[] { sx0, sz0 } };
            route2.AddRange(bestRoute);
            route2.Add(new[] { px, pz });
            var route = route2;
            var pts = Resample(Chaikin(route, 4), 2.0);
            Meander(pts, 7.0, 55, seed + 7, pinA: poolRadius + 10, pinB: pondRadius + 10);
            pts = Resample(Chaikin(pts, 1), 1.0);
            // water level: never above the bank upstream, never rising downstream, always clear of the PQS terrain
            int m = pts.Count;
            var req = new double[m]; var hw = new double[m];
            for (int i = 0; i < m; i++)
            {
                double s = pts[i][2];
                hw[i] = streamMinHW + (streamMaxHW - streamMinHW) * (0.35 * s / Math.Max(1, pts[m - 1][2]) + 0.65 * Fbm(s / 45, 9.1, seed + 13, 2));
                double hmax = double.MinValue;
                for (int j = 0; j < 5; j++)
                {
                    double ox = (j % 3 - 1) * hw[i], oz = (j / 3 - 0.5) * hw[i];
                    hmax = Math.Max(hmax, Pqs(pts[i][0] + ox, pts[i][1] + oz));
                }
                req[i] = hmax + minWaterAbovePqs;
            }
            var wl = new double[m];
            double run = double.MinValue;
            for (int i = m - 1; i >= 0; i--) { run = Math.Max(run, req[i]); wl[i] = run; }
            stream.Clear();
            for (int i = 0; i < m; i++) stream.Add(new[] { pts[i][0], pts[i][1], wl[i], hw[i], pts[i][2] });
            // the pool and the pond: their water levels must also clear the PQS ground under their whole basin
            pool[2] = Math.Max(wl[0], BasinReq(pool[0], pool[1], poolRadius, 0.9));
            pond[2] = Math.Min(wl[m - 1], pool[2]);
            pond[2] = Math.Max(pond[2], BasinReq(pond[0], pond[1], pondRadius, 0.8));
            for (int i = 0; i < m; i++) { stream[i][2] = Math.Min(Math.Max(stream[i][2], pond[2]), pool[2]); }
            log += string.Format("stream {0} pts, water {1:F1} -> {2:F1} m (pqs {3:F1} -> {4:F1})\n", m, pool[2], pond[2], Pqs(sx0, sz0), hp);
        }
        double BasinReq(double cx, double cz, double r, double depth)
        {
            double hmax = double.MinValue;
            for (int j = 0; j < 13; j++)
            {
                double a = j * Math.PI * 2 / 12, rr = j == 12 ? 0 : r * 0.9;
                hmax = Math.Max(hmax, Pqs(cx + Math.Cos(a) * rr, cz + Math.Sin(a) * rr));
            }
            return hmax + depth + 0.7;
        }

        float[] rsd; int[] rsi;    // coarse (routing lattice) distance to the stream
        void CoarseStreamDist()
        {
            rN = (int)(2 * E / RS) + 1;
            rsd = new float[rN * rN]; rsi = new int[rN * rN];
            for (int k = 0; k < rsd.Length; k++)
            {
                double x = -E + (k % rN) * RS, z = -E + (k / rN) * RS;
                int idx; rsd[k] = (float)StreamDistBrute(x, z, out idx); rsi[k] = idx;
            }
        }
        double StreamDistRaw(double x, double z, out int idx)
        {
            if (rsd == null) return StreamDistBrute(x, z, out idx);
            double fx = (x + E) / RS, fz = (z + E) / RS;
            int ix = (int)Math.Round(fx), iz = (int)Math.Round(fz);
            if (ix < 0 || iz < 0 || ix >= rN || iz >= rN) return StreamDistBrute(x, z, out idx);
            int k = iz * rN + ix;
            if (Math.Abs(fx - ix) < 1e-6 && Math.Abs(fz - iz) < 1e-6) { idx = rsi[k]; return rsd[k]; }
            // off-lattice: refine around the lattice's nearest point
            int c = rsi[k]; double best = double.MaxValue; idx = c;
            for (int i = Math.Max(0, c - 12); i <= Math.Min(stream.Count - 1, c + 12); i++)
            {
                double dx = stream[i][0] - x, dz = stream[i][1] - z, d = dx * dx + dz * dz;
                if (d < best) { best = d; idx = i; }
            }
            double alt = rsd[k] - RS * 0.75;
            return alt > Math.Sqrt(best) ? StreamDistBrute(x, z, out idx) : Math.Sqrt(best);
        }
        double StreamDistBrute(double x, double z, out int idx)
        {
            double best = double.MaxValue; idx = 0;
            for (int i = 0; i < stream.Count; i += 2)
            {
                double dx = stream[i][0] - x, dz = stream[i][1] - z, d = dx * dx + dz * dz;
                if (d < best) { best = d; idx = i; }
            }
            return Math.Sqrt(best);
        }

        // ---------------------------------------------------------------- path: edge -> clearing -> bridge -> spring pool
        void PlanPath()
        {
            CoarseStreamDist();
            double eb = entranceBearing * Math.PI / 180;
            double ea = Math.Atan2(Math.Cos(eb), Math.Sin(eb));     // bearing (from north, clockwise) -> math angle
            double er = EdgeR(ea) - 3;
            double ex = Math.Cos(ea) * er, ez = Math.Sin(ea) * er;
            // which side of the stream is the entrance on?
            int ei; StreamDistRaw(ex, ez, out ei);
            double sideE = SideOf(ex, ez, ei);
            // bridge: a straight-ish stretch, 30-65 % of the way down, preferring one near the middle of the forest
            int bi = stream.Count / 2; double bestB = double.MaxValue;
            for (int i = (int)(stream.Count * 0.28); i < stream.Count * 0.68; i++)
            {
                int a = Math.Max(0, i - 8), b = Math.Min(stream.Count - 1, i + 8);
                double t1x = stream[i][0] - stream[a][0], t1z = stream[i][1] - stream[a][1], t2x = stream[b][0] - stream[i][0], t2z = stream[b][1] - stream[i][1];
                double c = (t1x * t2x + t1z * t2z) / (Math.Sqrt(t1x * t1x + t1z * t1z) * Math.Sqrt(t2x * t2x + t2z * t2z) + 1e-9);
                double r = Math.Sqrt(stream[i][0] * stream[i][0] + stream[i][1] * stream[i][1]);
                double sc = (1 - c) * 60 + r / R * 3 + stream[i][3] * 0.6;
                if (sc < bestB) { bestB = sc; bi = i; }
            }
            int ia = Math.Max(0, bi - 3), ib = Math.Min(stream.Count - 1, bi + 3);
            double tx = stream[ib][0] - stream[ia][0], tz = stream[ib][1] - stream[ia][1], tl = Math.Sqrt(tx * tx + tz * tz);
            tx /= tl; tz /= tl;
            double nx = -tz, nz = tx;               // normal: +side
            double bx = stream[bi][0], bz = stream[bi][1], hwB = stream[bi][3];
            bridgeHalf = hwB + 2.4;
            double sgn = sideE >= 0 ? 1 : -1;
            double ax = bx + nx * bridgeHalf * sgn, az = bz + nz * bridgeHalf * sgn;    // entrance side abutment
            double cx2 = bx - nx * bridgeHalf * sgn, cz2 = bz - nz * bridgeHalf * sgn;  // far side abutment
            // clearing: on the entrance side, between the entrance and the bridge, away from the stream
            double best = double.MaxValue, clx = 0, clz = 0;
            for (int k = 0; k < 80; k++)
            {
                double t = 0.35 + rng.NextDouble() * 0.4;
                double qx = ex + (ax - ex) * t + (rng.NextDouble() - 0.5) * 160, qz = ez + (az - ez) * t + (rng.NextDouble() - 0.5) * 160;
                if (!InForest(qx, qz, 90)) continue;
                int qi; double ds = StreamDistRaw(qx, qz, out qi);
                if (ds < clearingRadius + 25 || Math.Sign(SideOf(qx, qz, qi)) != Math.Sign(sideE)) continue;
                if (Dist(qx, qz, pool[0], pool[1]) < 80 || Dist(qx, qz, pond[0], pond[1]) < 80) continue;
                double h = Pqs(qx, qz), rough = 0;
                for (int j = 0; j < 8; j++) { double aq = j * Math.PI / 4; rough = Math.Max(rough, Math.Abs(Pqs(qx + Math.Cos(aq) * clearingRadius, qz + Math.Sin(aq) * clearingRadius) - h)); }
                double sc = rough + Math.Abs(ds - 70) * 0.02;
                if (sc < best) { best = sc; clx = qx; clz = qz; }
            }
            if (best == double.MaxValue) { clx = (ex + ax) * 0.5; clz = (ez + az) * 0.5; log += "clearing: fallback\n"; }
            clearing[0] = clx; clearing[1] = clz; clearing[2] = clearingRadius;
            // path viewpoint at the spring pool: on the far side, downstream of the cascade
            int pi0 = Math.Min(stream.Count - 1, 14);
            double vtx = stream[pi0][0] - stream[0][0], vtz = stream[pi0][1] - stream[0][1], vl = Math.Sqrt(vtx * vtx + vtz * vtz) + 1e-9;
            double vnx = -vtz / vl, vnz = vtx / vl;
            double vx = pool[0] - vnx * sgn * (poolRadius + 3.2) + vtx / vl * 2, vz = pool[1] - vnz * sgn * (poolRadius + 3.2) + vtz / vl * 2;
            cascade[0] = pool[0] - vtx / vl * (poolRadius + 1.0); cascade[1] = pool[1] - vtz / vl * (poolRadius + 1.0);
            cascade[3] = (Math.Atan2(vtx, vtz) * 180 / Math.PI + 360) % 360;
            int np = seed + 211;
            double cl = clearingRadius;
            Func<double, double, double, double, double> cost = (x0, z0, x1, z1) =>
            {
                double L = Math.Sqrt((x1 - x0) * (x1 - x0) + (z1 - z0) * (z1 - z0));
                if (!InForest(x1, z1, 4)) return double.PositiveInfinity;
                int si; double ds = StreamDistRaw(x1, z1, out si);
                if (ds < stream[si][3] + 4.5) return double.PositiveInfinity;
                if (Dist(x1, z1, pond[0], pond[1]) < pondRadius + 6) return double.PositiveInfinity;
                if (Dist(x1, z1, pool[0], pool[1]) < poolRadius + 2.5) return double.PositiveInfinity;
                if (Dist(x1, z1, cascade[0], cascade[1]) < 7) return double.PositiveInfinity;
                double slope = Math.Abs(Pqs(x1, z1) - Pqs(x0, z0)) / L;
                double near = ds < 14 ? (14 - ds) * 0.08 : 0;
                return L * (1 + 30 * slope * slope + near + 2.6 * Fbm(x1 / 38, z1 / 38, np, 3));
            };
            Func<double, double, Func<double, double, bool>> at = (gx, gz) => (x, z) => (x - gx) * (x - gx) + (z - gz) * (z - gz) < RS * RS * 1.1;
            // approach the bridge square-on: route to a point 7 m out, then straight to the abutment
            double apx = ax + nx * 7 * sgn, apz = az + nz * 7 * sgn, fpx = cx2 - nx * 7 * sgn, fpz = cz2 - nz * 7 * sgn;
            var seg1 = Route(ex, ez, at(clx - (clx - ex) / Dist(clx, clz, ex, ez) * cl * 0.5, clz - (clz - ez) / Dist(clx, clz, ex, ez) * cl * 0.5), cost);
            var seg2 = Route(clx, clz, at(apx, apz), cost);
            var seg3 = Route(fpx, fpz, at(vx, vz), cost);
            var all = new List<double[]>();
            all.AddRange(seg1);
            all.Add(new[] { clx, clz });     // the path runs into the clearing and leaves from its centre
            all.AddRange(seg2.Count > 1 ? seg2.GetRange(1, seg2.Count - 1) : seg2);
            all.Add(new[] { apx, apz }); all.Add(new[] { ax, az });
            int bridgeStart = all.Count - 1;
            all.Add(new[] { cx2, cz2 }); all.Add(new[] { fpx, fpz });
            all.AddRange(seg3.Count > 1 ? seg3.GetRange(1, seg3.Count - 1) : seg3);
            all.Add(new[] { vx, vz });
            // smooth everything except the bridge span (kept straight)
            var before = Chaikin(all.GetRange(0, bridgeStart + 1), 3);
            var after = Chaikin(all.GetRange(bridgeStart + 1, all.Count - bridgeStart - 1), 3);
            var a1 = Resample(before, 1.0); Meander(a1, 2.8, 30, seed + 17, 12, 10);
            var a2 = Resample(after, 1.0); Meander(a2, 2.8, 30, seed + 19, 10, 6);
            // a side trail from the clearing down to the pond
            var spur = Route(clx, clz, (x, z) => { double d = Dist(x, z, pond[0], pond[1]); return d > pondRadius * 1.25 + 6 && d < pondRadius * 1.25 + 10; }, cost);
            List<double[]> a3 = null;
            if (spur.Count > 3)
            {
                spur = Simplify(spur, 3.0);
                a3 = Resample(Chaikin(spur, 3), 1.0); Meander(a3, 2.4, 26, seed + 29, 14, 6);
                // start where it leaves the main path at the clearing's edge
                int cut = 0; while (cut < a3.Count - 5 && Dist(a3[cut][0], a3[cut][1], clx, clz) < clearingRadius * 0.8) cut++;
                a3 = a3.GetRange(cut, a3.Count - cut);
            }
            path.Clear();
            int pnp = seed + 23;
            foreach (var p in a1) path.Add(new[] { p[0], p[1], 0, pathHalfWidth * (0.85 + 0.35 * Fbm(p[2] / 18, 1.7, pnp, 2)), 0, 0 });
            // bridge span: one straight line of points flagged "on bridge"
            int nb = (int)Math.Ceiling(bridgeHalf * 2);
            for (int k = 1; k < nb; k++) { double t = k / (double)nb; path.Add(new[] { ax + (cx2 - ax) * t, az + (cz2 - az) * t, 0, pathHalfWidth, 0, 1 }); }
            foreach (var p in a2) path.Add(new[] { p[0], p[1], 0, pathHalfWidth * (0.85 + 0.35 * Fbm((p[2] + 999) / 18, 1.7, pnp, 2)), 0, 0 });
            mainPathCount = path.Count;
            if (a3 != null) foreach (var p in a3) path.Add(new[] { p[0], p[1], 0, pathHalfWidth * 0.8 * (0.85 + 0.35 * Fbm((p[2] + 555) / 18, 1.7, pnp, 2)), 0, 0 });
            double s = 0;
            for (int i = 0; i < path.Count; i++)
            {
                if (i > 0 && i != mainPathCount) s += Dist(path[i][0], path[i][1], path[i - 1][0], path[i - 1][1]);
                if (i == mainPathCount) s = 0;
                path[i][4] = s;
            }
            bridge[0] = bx; bridge[1] = bz; bridge[2] = (Math.Atan2(-nx * sgn, -nz * sgn) * 180 / Math.PI + 360) % 360; bridge[3] = bridgeHalf * 2;
            bridge[6] = stream[bi][2];
            entrance[0] = ex; entrance[1] = ez;
            log += string.Format("bridge at {0:F0},{1:F0} span {2:F1}; clearing {3:F0},{4:F0}; path {5:F0} m\n", bx, bz, bridgeHalf * 2, clx, clz, s);
        }
        double SideOf(double x, double z, int i)
        {
            int a = Math.Max(0, i - 2), b = Math.Min(stream.Count - 1, i + 2);
            double tx = stream[b][0] - stream[a][0], tz = stream[b][1] - stream[a][1];
            return tx * (z - stream[i][1]) - tz * (x - stream[i][0]) >= 0 ? 1 : -1;
        }
        static double Dist(double ax, double az, double bx, double bz) { return Math.Sqrt((ax - bx) * (ax - bx) + (az - bz) * (az - bz)); }

        // ---------------------------------------------------------------- ground surface
        void Splat(List<double[]> line, float[] d, int[] idx, double reach)
        {
            int r = (int)Math.Ceiling(reach / GStep);
            for (int i = 0; i < line.Count; i++)
            {
                double px = line[i][0], pz = line[i][1];
                int cx = (int)Math.Round((px + E) / GStep), cz = (int)Math.Round((pz + E) / GStep);
                for (int jz = Math.Max(0, cz - r); jz <= Math.Min(gN - 1, cz + r); jz++)
                    for (int jx = Math.Max(0, cx - r); jx <= Math.Min(gN - 1, cx + r); jx++)
                    {
                        double x = -E + jx * GStep, z = -E + jz * GStep;
                        float dd = (float)Math.Sqrt((x - px) * (x - px) + (z - pz) * (z - pz));
                        int k = jz * gN + jx;
                        if (dd < d[k]) { d[k] = dd; idx[k] = i; }
                    }
            }
        }

        double Lift(double x, double z)
        {
            double r = Math.Sqrt(x * x + z * z), rim = RimR(Math.Atan2(z, x));
            return lift + (-skirt - lift) * Smooth(rim - 16, rim + 2, r);
        }

        void BuildGround()
        {
            int N = gN * gN;
            ground = new float[N]; wetness = new float[N];
            dStream = new float[N]; dPath = new float[N]; iStream = new int[N]; iPath = new int[N];
            for (int k = 0; k < N; k++) { dStream[k] = 1e9f; dPath[k] = 1e9f; }
            Splat(stream, dStream, iStream, streamMaxHW + 16);
            Splat(path, dPath, iPath, pathHalfWidth * 1.4 + 4);
            // base: PQS + lift
            var baseH = new float[N]; var liftG = new float[N];
            for (int jz = 0; jz < gN; jz++)
            {
                double z = -E + jz * GStep;
                for (int jx = 0; jx < gN; jx++)
                {
                    double x = -E + jx * GStep;
                    // small mounds and hollows of the forest floor (roots, old logs rotted away)
                    double mound = (Fbm(x / 9, z / 9, seed + 41, 2) - 0.5) * 0.35, lf = Lift(x, z);
                    liftG[jz * gN + jx] = (float)lf;
                    baseH[jz * gN + jx] = (float)(Pqs(x, z) + lf + mound * Smooth(0, 1, lf + 0.2));
                }
            }
            // path surface: the floor along the path, smoothed lengthways and levelled across
            var raw = new double[path.Count];
            for (int i = 0; i < path.Count; i++) raw[i] = Bil(baseH, path[i][0], path[i][1]);
            for (int i = 0; i < path.Count; i++)
            {
                double acc = 0, w = 0;
                int lo = i < mainPathCount ? 0 : mainPathCount, hi = i < mainPathCount ? mainPathCount - 1 : path.Count - 1;
                for (int j = Math.Max(lo, i - 5); j <= Math.Min(hi, i + 5); j++) { double ww = 1 - Math.Abs(j - i) / 6.0; acc += raw[j] * ww; w += ww; }
                path[i][2] = Math.Max(acc / w - 0.04, Pqs(path[i][0], path[i][1]) + 0.7);
            }
            // abutments meet the banks
            for (int jz = 0; jz < gN; jz++)
            {
                double z = -E + jz * GStep;
                for (int jx = 0; jx < gN; jx++)
                {
                    double x = -E + jx * GStep;
                    int k = jz * gN + jx;
                    double h = baseH[k];
                    double pq = Pqs(x, z);   // (cheap enough; the lift is cached)
                    double inside = Smooth(-0.6, 0.6, liftG[k]);     // nothing is raised out on the open grass
                    // banks of the stream: the floor never sits below the bank top beside the water
                    double wet = 0;
                    if (dStream[k] < 1e8)
                    {
                        var sp = stream[iStream[k]]; double hw = sp[3], bank = sp[2] + 0.45 + 0.25 * Fbm(x / 6, z / 6, seed + 51, 2);
                        double d = dStream[k];
                        double wgt = 1 - Smooth(hw + 1.6, hw + 13, d);
                        if (bank > h) h = h + (bank - h) * wgt * inside;
                        wet = Math.Max(wet, 1 - Smooth(hw + 1, hw + 12, d));
                    }
                    double hb = h;
                    wet = Math.Max(wet, BasinBank(x, z, pool, 1.6, 10, ref hb));
                    wet = Math.Max(wet, BasinBank(x, z, pond, 2.2, 14, ref hb));
                    h = h + (hb - h) * inside;
                    // the path
                    if (dPath[k] < 1e8)
                    {
                        var pp = path[iPath[k]];
                        if (pp[5] < 0.5)
                        {
                            double d = dPath[k], hw = pp[3];
                            double wgt = 1 - Smooth(hw + 0.3, hw + 2.6, d);
                            h = h + (pp[2] - h) * wgt;
                        }
                    }
                    // the clearing is a little more level
                    double dc = Dist(x, z, clearing[0], clearing[1]);
                    if (dc < clearingRadius + 8) { double cw = 1 - Smooth(clearingRadius * 0.4, clearingRadius + 8, dc); h = h + (Bil(baseH, clearing[0], clearing[1]) + 0.1 - h) * cw * 0.6; }
                    // carve the water: channel, pool, pond
                    double carve = double.MaxValue;
                    if (dStream[k] < 1e8)
                    {
                        var sp = stream[iStream[k]]; double hw = sp[3], d = dStream[k];
                        if (d < hw + 1.6)
                        {
                            double c;
                            if (d < hw) { double t = d / hw; c = sp[2] - waterDepth * (1 - t * t) - 0.04 + 0.08 * (Noise(x * 1.3, z * 1.3, seed + 61) - 0.5); }
                            else c = sp[2] - 0.04 + (d - hw) / 1.6 * 0.6;
                            carve = Math.Min(carve, c);
                        }
                    }
                    carve = Math.Min(carve, BasinCarve(x, z, pool, 0.95, 1.6));
                    carve = Math.Min(carve, BasinCarve(x, z, pond, 0.85, 2.2));
                    if (carve < h) h = carve;
                    // never let the PQS terrain show through inside the forest
                    double rimFade = liftG[k];
                    if (rimFade > 0.3) h = Math.Max(h, pq + 0.55);
                    ground[k] = (float)h;
                    wetness[k] = (float)wet;
                }
            }
        }
        double BasinR(double[] b, double x, double z)
        {
            double a = Math.Atan2(z - b[1], x - b[0]);
            return b[3] * (0.85 + 0.3 * Fbm(Math.Cos(a) * 1.5 + b[0] * 0.01, Math.Sin(a) * 1.5, seed + 71, 2));
        }
        double BasinBank(double x, double z, double[] b, double bankW, double reach, ref double h)
        {
            double d = Dist(x, z, b[0], b[1]); if (d > b[3] * 1.4 + reach) return 0;
            double r = BasinR(b, x, z), bank = b[2] + 0.4;
            double wgt = 1 - Smooth(r + bankW, r + reach, d);
            if (bank > h) h = h + (bank - h) * wgt;
            return 1 - Smooth(r + 1, r + reach, d);
        }
        double BasinCarve(double x, double z, double[] b, double depth, double bankW)
        {
            double d = Dist(x, z, b[0], b[1]); if (d > b[3] * 1.4 + bankW) return double.MaxValue;
            double r = BasinR(b, x, z);
            if (d < r) { double t = d / r; return b[2] - depth * (1 - t * t * t) - 0.04; }
            if (d < r + bankW) return b[2] - 0.04 + (d - r) / bankW * 0.55;
            return double.MaxValue;
        }
        double Bil(float[] g, double x, double z)
        {
            double fx = (x + E) / GStep, fz = (z + E) / GStep;
            int ix = Math.Max(0, Math.Min(gN - 2, (int)fx)), iz = Math.Max(0, Math.Min(gN - 2, (int)fz));
            double tx = fx - ix, tz = fz - iz; int k = iz * gN + ix;
            return (g[k] * (1 - tx) + g[k + 1] * tx) * (1 - tz) + (g[k + gN] * (1 - tx) + g[k + gN + 1] * tx) * tz;
        }

        // ---------------------------------------------------------------- set pieces
        void PlaceFeatures()
        {
            // elder tree: in the clearing, off-centre so the path passes beside it
            double a = rng.NextDouble() * Math.PI * 2, best = -1;
            for (int k = 0; k < 24; k++)
            {
                double aa = k * Math.PI / 12, ex = clearing[0] + Math.Cos(aa) * clearingRadius * 0.38, ez = clearing[1] + Math.Sin(aa) * clearingRadius * 0.38;
                double dp = DistPath(ex, ez);
                if (dp > 6 && dp < 12 && dp > best) { best = dp; a = aa; }
            }
            elder[0] = clearing[0] + Math.Cos(a) * clearingRadius * 0.38; elder[1] = clearing[1] + Math.Sin(a) * clearingRadius * 0.38;
            elder[2] = Ground(elder[0], elder[1]); elder[3] = rng.NextDouble() * 360;
            cascade[2] = Ground(cascade[0], cascade[1]);
            entrance[2] = Ground(entrance[0], entrance[1]);
            // bridge deck ends sit on the banks at the abutments
            double hr = bridge[2] * Math.PI / 180, dx = Math.Sin(hr), dz = Math.Cos(hr);
            bridge[4] = Ground(bridge[0] - dx * bridgeHalf, bridge[1] - dz * bridgeHalf);
            bridge[5] = Ground(bridge[0] + dx * bridgeHalf, bridge[1] + dz * bridgeHalf);
        }

        bool Clear(double x, double z, double treeR)
        {
            if (DistPath(x, z) < pathHalfWidth + 0.9 + treeR) return false;
            double ds = DistStream(x, z);
            if (ds < streamMaxHW + 1.8 + treeR) return false;
            if (Dist(x, z, pool[0], pool[1]) < poolRadius * 1.25 + 2.5 + treeR) return false;
            if (Dist(x, z, pond[0], pond[1]) < pondRadius * 1.2 + 3 + treeR) return false;
            if (Dist(x, z, clearing[0], clearing[1]) < clearingRadius - 2 + treeR) return false;
            if (Dist(x, z, bridge[0], bridge[1]) < bridgeHalf + 5) return false;
            if (Dist(x, z, cascade[0], cascade[1]) < 6 + treeR) return false;
            return true;
        }

        void ScatterTrees()
        {
            trees.Clear();
            int nsp = species.Count;
            if (nsp == 0) return;
            double cell = spacing;
            int n = (int)Math.Ceiling(E / cell);
            var cache = new double[nsp];
            var occupied = new List<double[]>();
            for (int j = -n; j <= n; j++)
                for (int i = -n; i <= n; i++)
                {
                    double x = (i + 0.5 + (rng.NextDouble() - 0.5) * 0.9) * cell, z = (j + 0.5 + (rng.NextDouble() - 0.5) * 0.9) * cell;
                    double r = Math.Sqrt(x * x + z * z), er = EdgeR(Math.Atan2(z, x));
                    if (r > er) continue;
                    // thinning toward the edge, and patchy density inside
                    double dens = 0.82 + 0.3 * (Fbm(x / 70, z / 70, seed + 81, 2) - 0.5);
                    dens *= 1 - 0.55 * Smooth(er - 45, er, r);
                    if (rng.NextDouble() > dens) continue;
                    // species: weighted by habitat and groves
                    double wet = Math.Max(0, 1 - Smooth(4, 40, Math.Min(DistStream(x, z), Math.Min(Dist(x, z, pond[0], pond[1]) - pondRadius, Dist(x, z, pool[0], pool[1]) - poolRadius))));
                    double high = (Pqs(x, z) - pool[2]) / Math.Max(1, pool[2] - pond[2] + 1);
                    double edgeF = Smooth(er - 80, er - 10, r);
                    double side = Math.Max(0, 1 - Smooth(3, 16, DistPath(x, z)));
                    double tot = 0;
                    for (int s = 0; s < nsp; s++)
                    {
                        var sp = species[s];
                        double grove = Fbm(x / 55 + s * 13.1, z / 55 - s * 7.7, seed + 91 + s, 2) - 0.5;
                        double w = sp.weight * Math.Exp(sp.cluster * grove * 7 + sp.wet * wet * 2.2 + sp.high * high * 1.2 + sp.edge * edgeF * 1.8 + sp.pathside * side * 2.5);
                        cache[s] = w; tot += w;
                    }
                    double pick = rng.NextDouble() * tot; int k = 0;
                    for (; k < nsp - 1; k++) { pick -= cache[k]; if (pick <= 0) break; }
                    var spc = species[k];
                    double sc = spc.minScale + (spc.maxScale - spc.minScale) * rng.NextDouble();
                    double treeR = 0.6 * sc * spc.footprint;
                    if (!Clear(x, z, treeR)) continue;
                    // big crowns need more room: reject if a neighbour is too close (cheap: last few rows only)
                    bool tooClose = false;
                    for (int q = occupied.Count - 1; q >= 0 && q >= occupied.Count - 2 * (2 * n + 1); q--)
                    {
                        var o = occupied[q];
                        if (Dist(x, z, o[0], o[1]) < (o[2] + spc.footprint) * cell * 0.36) { tooClose = true; break; }
                    }
                    if (tooClose) continue;
                    occupied.Add(new[] { x, z, spc.footprint });
                    var t = new ForestInstance { kind = k, variant = rng.Next(spc.variants), x = (float)x, z = (float)z, scale = (float)sc, yaw = (float)(rng.NextDouble() * 360), tilt = (float)(rng.NextDouble() * 3.5), tiltDir = (float)(rng.NextDouble() * 360) };
                    t.y = (float)Ground(x, z);
                    trees.Add(t);
                }
            // a few trees right at the clearing's rim, leaning in
            for (int k = 0; k < 9; k++)
            {
                double a = k * Math.PI * 2 / 9 + rng.NextDouble() * 0.4, rr = clearingRadius + 1.5 + rng.NextDouble() * 3;
                double x = clearing[0] + Math.Cos(a) * rr, z = clearing[1] + Math.Sin(a) * rr;
                if (DistPath(x, z) < pathHalfWidth + 2.5 || DistStream(x, z) < 6) continue;
                int sp = rng.Next(species.Count);
                if (species[sp].footprint > 1.3) sp = 0;
                trees.Add(new ForestInstance { kind = sp, variant = rng.Next(species[sp].variants), x = (float)x, z = (float)z, y = (float)Ground(x, z), scale = (float)(species[sp].maxScale * (0.95 + rng.NextDouble() * 0.15)), yaw = (float)(rng.NextDouble() * 360), tilt = 4f, tiltDir = (float)((Math.Atan2(clearing[0] - x, clearing[1] - z) * 180 / Math.PI + 360) % 360) });
            }
        }

        void Prop(ForestProp p, int variants, double x, double z, double scale, double sink = 0)
        {
            props.Add(new ForestInstance
            {
                kind = (int)p, variant = rng.Next(variants), x = (float)x, z = (float)z, y = (float)(Ground(x, z) - sink),
                scale = (float)scale, yaw = (float)(rng.NextDouble() * 360), tilt = (float)(rng.NextDouble() * 6), tiltDir = (float)(rng.NextDouble() * 360)
            });
        }

        void ScatterProps()
        {
            props.Clear();
            double cell = 3.2;
            int n = (int)Math.Ceiling(E / cell);
            for (int j = -n; j <= n; j++)
                for (int i = -n; i <= n; i++)
                {
                    double x = (i + rng.NextDouble()) * cell, z = (j + rng.NextDouble()) * cell;
                    double r = Math.Sqrt(x * x + z * z), er = EdgeR(Math.Atan2(z, x));
                    if (r > er + 12) continue;
                    double dp = DistPath(x, z), ds = DistStream(x, z);
                    bool onPath = dp < pathHalfWidth + 0.35;
                    double dPool = Dist(x, z, pool[0], pool[1]), dPond = Dist(x, z, pond[0], pond[1]);
                    bool inWater = ds < streamMaxHW + 0.2 || dPool < poolRadius * 1.15 || dPond < pondRadius * 1.15;
                    double wet = Wet(x, z);
                    double edgeF = Smooth(er - 50, er + 5, r);
                    double u = rng.NextDouble() / propDensity;
                    if (onPath || inWater) continue;
                    if (Dist(x, z, bridge[0], bridge[1]) < bridgeHalf + 2) continue;
                    if (Dist(x, z, elder[0], elder[1]) < 5) continue;
                    double inClear = Dist(x, z, clearing[0], clearing[1]) < clearingRadius - 3 ? 1 : 0;
                    // ferns: everywhere in the shade, thick by the water
                    double pf = 0.16 + 0.5 * wet - 0.12 * inClear - 0.1 * edgeF;
                    if (dp < pathHalfWidth + 1.2) pf *= 0.4;
                    if (u < pf) { Prop(ForestProp.Fern, 3, x, z, 0.7 + rng.NextDouble() * 0.6, 0.05); continue; }
                    u -= pf;
                    double ps = 0.035 + 0.22 * edgeF + 0.05 * (dp < 5 ? 1 : 0);
                    if (u < ps) { Prop(ForestProp.Shrub, 3, x, z, 0.7 + rng.NextDouble() * 0.7, 0.1); continue; }
                    u -= ps;
                    double pl = 0.11 + 0.1 * inClear;     // leaf drifts piled against roots and logs
                    if (u < pl) { Prop(ForestProp.Litter, 4, x, z, 0.8 + rng.NextDouble() * 0.8, 0.02); continue; }
                    u -= pl;
                    if (u < 0.012) { Prop(ForestProp.Sapling, 2, x, z, 0.6 + rng.NextDouble() * 0.6); continue; }
                    u -= 0.012;
                    if (u < 0.01 && dp > 3) { Prop(ForestProp.Rock, 4, x, z, 0.5 + Math.Pow(rng.NextDouble(), 2) * 1.6, 0.15); continue; }
                    u -= 0.01;
                    if (u < 0.006 && dp > 3) { Prop(ForestProp.Log, 3, x, z, 0.8 + rng.NextDouble() * 0.5, 0.1); continue; }
                    u -= 0.006;
                    if (u < 0.016) { Prop(ForestProp.Mushroom, 3, x, z, 0.7 + rng.NextDouble() * 0.7); continue; }
                    u -= 0.016;
                    if (u < 0.003 && dp > 2.5) { Prop(ForestProp.Stump, 2, x, z, 0.8 + rng.NextDouble() * 0.5, 0.05); continue; }
                }
            // stones along the stream banks and the pool rim
            for (int i = 0; i < stream.Count; i++)
            {
                var sp = stream[i];
                if (rng.NextDouble() > 0.32) continue;
                double a = rng.NextDouble() < 0.5 ? 1 : -1;
                int b = Math.Min(stream.Count - 1, i + 1), c = Math.Max(0, i - 1);
                double tx = stream[b][0] - stream[c][0], tz = stream[b][1] - stream[c][1], L = Math.Sqrt(tx * tx + tz * tz) + 1e-9;
                double off = sp[3] * (0.75 + rng.NextDouble() * 0.6) * a;
                double x = sp[0] - tz / L * off, z = sp[1] + tx / L * off;
                if (Dist(x, z, bridge[0], bridge[1]) < bridgeHalf + 1.5) continue;
                Prop(ForestProp.StreamRock, 4, x, z, 0.35 + rng.NextDouble() * 0.6, 0.12);
                if (rng.NextDouble() < 0.25 && Math.Abs(off) < sp[3]) props[props.Count - 1] = Wet(props[props.Count - 1], sp[2]);
            }
            foreach (var b in new[] { pool, pond })
            {
                int cnt = b == pool ? 26 : 30;
                for (int k = 0; k < cnt; k++)
                {
                    double a = rng.NextDouble() * Math.PI * 2, rr = BasinRAt(b, a) + (rng.NextDouble() - 0.35) * 1.6;
                    double x = b[0] + Math.Cos(a) * rr, z = b[1] + Math.Sin(a) * rr;
                    if (DistPath(x, z) < pathHalfWidth + 0.6) continue;
                    if (b == pond && rng.NextDouble() < 0.6) Prop(ForestProp.Reed, 3, x, z, 0.8 + rng.NextDouble() * 0.5);
                    else Prop(ForestProp.StreamRock, 4, x, z, 0.4 + rng.NextDouble() * 0.8, 0.15);
                }
            }
            // lily pads on the pond
            for (int k = 0; k < 40; k++)
            {
                double a = rng.NextDouble() * Math.PI * 2, rr = Math.Sqrt(rng.NextDouble()) * pondRadius * 0.85;
                double x = pond[0] + Math.Cos(a) * rr, z = pond[1] + Math.Sin(a) * rr;
                if (Dist(x, z, pond[0], pond[1]) > BasinRAt(pond, a) - 1.2) continue;
                props.Add(new ForestInstance { kind = (int)ForestProp.Lily, variant = rng.Next(2), x = (float)x, z = (float)z, y = (float)(pond[2] + 0.01), scale = (float)(0.6 + rng.NextDouble() * 0.7), yaw = (float)(rng.NextDouble() * 360) });
            }
        }
        double BasinRAt(double[] b, double a) { return BasinR(b, b[0] + Math.Cos(a), b[1] + Math.Sin(a)); }
        static ForestInstance Wet(ForestInstance p, double water) { p.y = (float)Math.Max(p.y, water - 0.3); return p; }
    }
}
