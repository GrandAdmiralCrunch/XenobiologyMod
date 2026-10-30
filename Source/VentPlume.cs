using System;
using System.Collections.Generic;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>PLUME {} on a lifeform: a continuous, billowing column (hydrothermal smoke, geyser steam, spore jets).</summary>
    public class PlumeInfo
    {
        public Vector3 offset = Vector3.zero;     // vent mouth, creature-local metres
        public float height = 12f;                // column height
        public float radius = 0.25f;              // at the mouth
        public float spread = 3f;                 // radius at the top
        public float rise = 0.6f;                 // apparent rise speed of the turbulence (m/s)
        public float lean = 0.15f;                // how far the column drifts with the current (fraction of height)
        public int sheets = 3;                    // crossed, camera-facing layers
        public Color color = new Color(0.06f, 0.055f, 0.05f, 0.85f);
        public Color colorTop = new Color(0.22f, 0.26f, 0.28f, 0f);
        public static PlumeInfo Parse(ConfigNode n)
        {
            var p = new PlumeInfo();
            n.TryGetValue("offset", ref p.offset); n.TryGetValue("height", ref p.height); n.TryGetValue("radius", ref p.radius);
            n.TryGetValue("spread", ref p.spread); n.TryGetValue("rise", ref p.rise); n.TryGetValue("lean", ref p.lean);
            n.TryGetValue("sheets", ref p.sheets); n.TryGetValue("color", ref p.color); n.TryGetValue("colorTop", ref p.colorTop);
            p.sheets = Mathf.Clamp(p.sheets, 1, 6);
            return p;
        }
    }

    /// <summary>
    /// A fake-volumetric smoke column: a few vertical sheets that turn about the column axis to face the camera, each
    /// textured with tileable turbulence that scrolls upward at its own speed, widening with height and fading out at
    /// the top. Layered, the sheets read as a soft, churning volume from any side (the particles of an EMITTER kind = Smoke
    /// add the detached billows around it). Costs a handful of quads.
    /// </summary>
    public class VentPlume : MonoBehaviour
    {
        PlumeInfo info;
        CreatureController owner;
        readonly List<Transform> sheets = new List<Transform>();
        readonly List<Material> mats = new List<Material>();
        readonly List<Renderer> rends = new List<Renderer>();
        float[] speeds, phases;
        bool shown = true;

        /// <summary>Optional visibility test for plumes without a creature (geysers, fumaroles).</summary>
        public Func<bool> Visible;

        public void Init(CreatureController c, PlumeInfo p) { owner = c; Init(c.GetInstanceID(), p); }

        public void Init(int seed, PlumeInfo p)
        {
            info = p;
            transform.localPosition = p.offset;
            Shader sh = Shader.Find("KSP/Particles/Alpha Blended") ?? Shader.Find("Legacy Shaders/Particles/Alpha Blended") ?? Shader.Find("Particles/Alpha Blended");
            speeds = new float[p.sheets]; phases = new float[p.sheets];
            var rnd = new System.Random(seed);
            for (int i = 0; i < p.sheets; i++)
            {
                var go = new GameObject("xeno_plume_" + i);
                go.transform.SetParent(transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = BuildMesh(p, i);
                var mr = go.AddComponent<MeshRenderer>();
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; mr.receiveShadows = false;
                var m = new Material(sh); m.mainTexture = Tex(i % 2);
                m.mainTextureScale = new Vector2(1f, 1.6f + 0.4f * i);
                if (m.HasProperty("_TintColor")) m.SetColor("_TintColor", new Color(0.5f, 0.5f, 0.5f, 0.5f));
                mr.sharedMaterial = m;
                sheets.Add(go.transform); mats.Add(m); rends.Add(mr);
                speeds[i] = p.rise / p.height * (0.8f + 0.35f * i);       // uv per second
                phases[i] = (float)rnd.NextDouble();
            }
        }

        static Mesh BuildMesh(PlumeInfo p, int layer)
        {
            const int ROWS = 14;
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var col = new List<Color>(); var tri = new List<int>();
            float widen = 1f - 0.15f * layer;                             // inner layers a little narrower (denser core)
            for (int j = 0; j <= ROWS; j++)
            {
                float t = j / (float)ROWS;
                float y = p.height * t;
                float w = (p.radius + (p.spread - p.radius) * Mathf.Pow(t, 0.75f)) * widen;
                float drift = p.lean * p.height * t * t;                  // bends downstream
                Color c = Color.Lerp(p.color, p.colorTop, Mathf.SmoothStep(0f, 1f, t));
                float a = Mathf.SmoothStep(0f, 1f, t / 0.04f) * (1f - Mathf.SmoothStep(0.45f, 1f, t));
                c.a = Mathf.Lerp(p.color.a, p.colorTop.a, t) * a * (layer == 0 ? 1f : 0.75f);
                v.Add(new Vector3(-w + drift, y, 0)); v.Add(new Vector3(w + drift, y, 0));
                uv.Add(new Vector2(0, t)); uv.Add(new Vector2(1, t));
                col.Add(c); col.Add(c);
                if (j > 0) { int b = (j - 1) * 2; tri.AddRange(new[] { b, b + 2, b + 1, b + 1, b + 2, b + 3 }); }
            }
            var m = new Mesh(); m.SetVertices(v); m.SetUVs(0, uv); m.SetColors(col); m.SetTriangles(tri, 0);
            m.bounds = new Bounds(new Vector3(0, p.height * 0.5f, 0), new Vector3(p.spread * 2 + p.lean * p.height * 2, p.height, p.spread * 2 + p.lean * p.height * 2));
            return m;
        }

        static readonly Texture2D[] texs = new Texture2D[2];
        /// <summary>Tileable turbulence across a soft column profile: dense in the middle, wispy, ragged edges.</summary>
        static Texture2D Tex(int seed)
        {
            if (texs[seed] != null) return texs[seed];
            const int W = 64, H = 256;
            var t = new Texture2D(W, H, TextureFormat.RGBA32, true);
            var rnd = new System.Random(311 + seed * 17);
            // value-noise lattices that wrap vertically (and horizontally, harmlessly)
            int[] gw = { 4, 8, 16, 32 }; int[] gh = { 8, 16, 32, 64 }; float[] amp = { 0.5f, 0.27f, 0.15f, 0.08f };
            var lat = new float[4][,];
            for (int o = 0; o < 4; o++) { lat[o] = new float[gw[o], gh[o]]; for (int x = 0; x < gw[o]; x++) for (int y = 0; y < gh[o]; y++) lat[o][x, y] = (float)rnd.NextDouble(); }
            for (int y = 0; y < H; y++)
                for (int x = 0; x < W; x++)
                {
                    float u = x / (float)W, v = y / (float)H, n = 0;
                    for (int o = 0; o < 4; o++)
                    {
                        float fx = u * gw[o], fy = v * gh[o];
                        int x0 = (int)fx, y0 = (int)fy; float tx = fx - x0, ty = fy - y0;
                        tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty);
                        int x1 = (x0 + 1) % gw[o], y1 = (y0 + 1) % gh[o]; x0 %= gw[o]; y0 %= gh[o];
                        float a = Mathf.Lerp(lat[o][x0, y0], lat[o][x1, y0], tx), b = Mathf.Lerp(lat[o][x0, y1], lat[o][x1, y1], tx);
                        n += Mathf.Lerp(a, b, ty) * amp[o];
                    }
                    float d = Mathf.Abs(u - 0.5f) * 2f;                                   // 0 centre .. 1 edge
                    float edge = 0.55f + 0.45f * n;                                        // ragged edge
                    float prof = Mathf.Clamp01(1f - Mathf.SmoothStep(edge * 0.35f, edge, d));
                    float dens = Mathf.Clamp01((n - 0.28f) * 1.9f);
                    float a2 = prof * (0.3f + 0.7f * dens);
                    float shade = 0.75f + 0.25f * n;                                       // lighter billow tops
                    t.SetPixel(x, y, new Color(shade, shade, shade, a2));
                }
            t.wrapMode = TextureWrapMode.Repeat; t.Apply(true);
            texs[seed] = t;
            return t;
        }

        void LateUpdate()
        {
            bool show;
            if (owner != null) show = owner.Lod < 3 && owner.isActiveAndEnabled;
            else if (Visible != null) show = Visible();
            else return;
            if (show != shown) { shown = show; foreach (var r in rends) if (r != null) r.enabled = show; }
            if (!show) return;
            Camera cam = FlightCamera.fetch != null ? FlightCamera.fetch.mainCamera : Camera.main;
            if (cam == null) return;
            Vector3 up = transform.up;
            Vector3 toCam = cam.transform.position - transform.position;
            Vector3 flat = toCam - up * Vector3.Dot(toCam, up);
            if (flat.sqrMagnitude < 1e-4f) flat = transform.forward;
            float t = Time.time;
            for (int i = 0; i < sheets.Count; i++)
            {
                // all sheets face the camera, each turned a little so the layers never line up exactly
                Quaternion face = Quaternion.LookRotation(flat.normalized, up);
                sheets[i].rotation = face * Quaternion.Euler(0, (i - (sheets.Count - 1) * 0.5f) * 14f, 0);
                mats[i].mainTextureOffset = new Vector2(phases[i] + Mathf.Sin(t * 0.07f + i) * 0.03f, -(t * speeds[i] + phases[i]));
            }
        }
    }
}
