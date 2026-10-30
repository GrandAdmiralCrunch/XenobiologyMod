using System;
using System.Collections.Generic;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Particle effects declared with EMITTER {} blocks (bubbles, spores, glowing motes, steam), plus one-shot
    /// splashes for leaping swimmers. Particles simulate in the creature's local space, so KSP's floating-origin
    /// shifts never strand them.
    /// </summary>
    public class CreatureEffects : MonoBehaviour
    {
        class Em
        {
            public EmitterInfo info;
            public ParticleSystem ps;
            public bool on;
        }

        readonly List<Em> list = new List<Em>();

        public void Init(CreatureController c)
        {
            foreach (var info in c.def.emitters)
            {
                Transform parent = string.IsNullOrEmpty(info.transform) ? null : c.FindChildRecursive(info.transform);
                var go = new GameObject("xeno_fx_" + info.kind);
                go.transform.SetParent(parent ?? transform, false);
                go.transform.localPosition = info.offset;
                list.Add(new Em { info = info, ps = Build(go, info) });
            }
        }

        static readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();

        static Material Mat(string kind)
        {
            string k = (kind ?? "Motes").ToLowerInvariant();
            Material m;
            if (mats.TryGetValue(k, out m) && m != null) return m;
            Shader sh = Shader.Find("KSP/Particles/Alpha Blended") ?? Shader.Find("Legacy Shaders/Particles/Alpha Blended") ?? Shader.Find("Particles/Alpha Blended") ?? Shader.Find("Sprites/Default");
            if (k == "motes" || k == "glow")
                sh = Shader.Find("KSP/Particles/Additive") ?? Shader.Find("Legacy Shaders/Particles/Additive") ?? sh;
            m = new Material(sh);
            m.mainTexture = Tex(k == "bubbles" ? 1 : k == "spores" ? 2 : k == "smoke" ? 3 : 0);
            mats[k] = m;
            return m;
        }

        static readonly Texture2D[] texs = new Texture2D[4];

        /// <summary>0 soft disc, 1 bubble ring, 2 grainy puff, 3 billowing smoke (cauliflower lobes, soft ragged edge)</summary>
        static Texture2D Tex(int kind)
        {
            if (texs[kind] != null) return texs[kind];
            if (kind == 3) return texs[3] = SmokeTex();
            const int N = 64;
            var t = new Texture2D(N, N, TextureFormat.RGBA32, false);
            var rnd = new System.Random(17 + kind);
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float dx = (x + 0.5f) / N * 2f - 1f, dy = (y + 0.5f) / N * 2f - 1f;
                    float r = Mathf.Sqrt(dx * dx + dy * dy);
                    float a;
                    if (kind == 1) a = Mathf.Clamp01(1f - Mathf.Abs(r - 0.8f) / 0.14f) * 0.9f + Mathf.Clamp01(1f - r / 0.8f) * 0.12f
                                   + (Mathf.Clamp01(1f - new Vector2(dx + 0.35f, dy - 0.35f).magnitude / 0.18f) * 0.8f);   // rim + highlight
                    else if (kind == 2) a = Mathf.Clamp01(1f - r) * Mathf.Clamp01(1f - r) * (0.6f + 0.4f * (float)rnd.NextDouble());
                    else a = Mathf.Pow(Mathf.Clamp01(1f - r), 2.2f);
                    t.SetPixel(x, y, new Color(1, 1, 1, Mathf.Clamp01(a)));
                }
            t.wrapMode = TextureWrapMode.Clamp;
            t.Apply();
            texs[kind] = t;
            return t;
        }

        static Texture2D SmokeTex()
        {
            const int N = 128;
            var t = new Texture2D(N, N, TextureFormat.RGBA32, true);
            var rnd = new System.Random(4711);
            // a few overlapping lobes + fractal value noise, so each puff is a lumpy billow rather than a dot
            var lobes = new List<Vector3>();
            for (int i = 0; i < 7; i++) { float a = (float)(rnd.NextDouble() * Math.PI * 2), r = (float)rnd.NextDouble() * 0.35f; lobes.Add(new Vector3(Mathf.Cos(a) * r, Mathf.Sin(a) * r, 0.3f + (float)rnd.NextDouble() * 0.25f)); }
            int[] g = { 4, 8, 16, 32 }; float[] amp = { 0.45f, 0.28f, 0.17f, 0.1f };
            var lat = new float[4][,];
            for (int o = 0; o < 4; o++) { lat[o] = new float[g[o] + 1, g[o] + 1]; for (int x = 0; x <= g[o]; x++) for (int y = 0; y <= g[o]; y++) lat[o][x, y] = (float)rnd.NextDouble(); }
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float u = (x + 0.5f) / N, v = (y + 0.5f) / N, dx = u * 2 - 1, dy = v * 2 - 1, n = 0;
                    for (int o = 0; o < 4; o++)
                    {
                        float fx = u * g[o], fy = v * g[o]; int x0 = Mathf.Min((int)fx, g[o] - 1), y0 = Mathf.Min((int)fy, g[o] - 1);
                        float tx = fx - x0, ty = fy - y0; tx = tx * tx * (3 - 2 * tx); ty = ty * ty * (3 - 2 * ty);
                        n += Mathf.Lerp(Mathf.Lerp(lat[o][x0, y0], lat[o][x0 + 1, y0], tx), Mathf.Lerp(lat[o][x0, y0 + 1], lat[o][x0 + 1, y0 + 1], tx), ty) * amp[o];
                    }
                    float body = 0;
                    foreach (var l in lobes) body = Mathf.Max(body, 1f - new Vector2(dx - l.x, dy - l.y).magnitude / l.z);
                    float a = Mathf.Clamp01(body * 1.6f - (1f - n) * 0.9f) * Mathf.Clamp01(1f - Mathf.Sqrt(dx * dx + dy * dy));
                    float shade = 0.7f + 0.3f * Mathf.Clamp01(n + (dy * 0.25f));                       // lit tops, darker undersides
                    t.SetPixel(x, y, new Color(shade, shade, shade, a));
                }
            t.wrapMode = TextureWrapMode.Clamp; t.Apply(true);
            return t;
        }

        public static ParticleSystem Build(GameObject go, EmitterInfo info)
        {
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.playOnAwake = false;
            main.loop = true;
            main.duration = 5f;
            main.startLifetime = new ParticleSystem.MinMaxCurve(info.lifetime * 0.7f, info.lifetime * 1.3f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(info.speed * 0.5f, info.speed * 1.5f);
            main.startSize = new ParticleSystem.MinMaxCurve(info.size * 0.6f, info.size * 1.4f);
            main.startColor = info.color;
            main.gravityModifier = info.gravity;
            main.simulationSpace = ParticleSystemSimulationSpace.Local;
            main.maxParticles = 600;
            main.scalingMode = ParticleSystemScalingMode.Hierarchy;
            var em = ps.emission;
            em.rateOverTime = 0f;
            var sh = ps.shape;
            sh.enabled = true;
            sh.shapeType = ParticleSystemShapeType.Sphere;
            sh.radius = Mathf.Max(0.01f, info.radius);
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(info.color, 0f), new GradientColorKey(info.colorEnd, 1f) },
                      new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(info.color.a, 0.12f), new GradientAlphaKey(info.color.a * 0.8f, 0.6f), new GradientAlphaKey(info.colorEnd.a, 1f) });
            col.color = new ParticleSystem.MinMaxGradient(g);
            var sz = ps.sizeOverLifetime;
            sz.enabled = true;
            sz.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0f, 1f, 1f, Mathf.Max(0.05f, info.sizeGrow)));
            if (string.Equals(info.kind, "Bubbles", StringComparison.OrdinalIgnoreCase) || string.Equals(info.kind, "Spores", StringComparison.OrdinalIgnoreCase))
            {
                var noise = ps.noise;
                noise.enabled = true;
                noise.strength = info.speed * 0.6f + 0.1f;
                noise.frequency = 0.6f;
            }
            if (string.Equals(info.kind, "Smoke", StringComparison.OrdinalIgnoreCase))
            {   // a buoyant column: a narrow upward cone, turbulence, slow tumbling billows that swell and thin out
                go.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);                     // cone emits along local +Z -> up
                sh.shapeType = ParticleSystemShapeType.Cone; sh.angle = 9f;
                main.startRotation = new ParticleSystem.MinMaxCurve(0f, Mathf.PI * 2f);
                var rot = ps.rotationOverLifetime; rot.enabled = true; rot.z = new ParticleSystem.MinMaxCurve(-0.35f, 0.35f);
                var noise = ps.noise; noise.enabled = true; noise.strength = 0.35f; noise.frequency = 0.25f; noise.scrollSpeed = 0.15f; noise.damping = true;
                var lim = ps.limitVelocityOverLifetime; lim.enabled = true; lim.limit = info.speed * 1.4f; lim.dampen = 0.08f;
                sz.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.6f), new Keyframe(0.25f, Mathf.Max(1f, info.sizeGrow * 0.45f)), new Keyframe(1f, Mathf.Max(1f, info.sizeGrow))));
                main.maxParticles = 300;
            }
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = Mat(info.kind);
            r.renderMode = ParticleSystemRenderMode.Billboard;
            r.sortMode = ParticleSystemSortMode.Distance;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            ps.Play();
            return ps;
        }

        bool Wanted(Em e, CreatureController c)
        {
            var i = e.info;
            if (i.underwaterOnly && c.alt > -0.5) return false;
            if (i.surfaceOnly && c.alt < -2.0) return false;
            switch (i.when)
            {
                case EmitWhen.Always: return c.state != CreatureState.Spent;
                case EmitWhen.Idle: return Mathf.Abs(c.speed) < 0.3f && c.state != CreatureState.Spent;
                case EmitWhen.Moving: return Mathf.Abs(c.speed) >= 0.3f;
                case EmitWhen.Fleeing: return c.state == CreatureState.Flee;
                case EmitWhen.Night: return !Geo.IsDaylight(c.body, c.lat, c.lon);
                case EmitWhen.Provoked: return c.Provoked;
                case EmitWhen.Leap: return c.state == CreatureState.Leap;
                default: return false;   // Burst: one-shot only
            }
        }

        public void Tick(CreatureController c)
        {
            foreach (var e in list)
            {
                if (e.ps == null) continue;
                bool want = Wanted(e, c);
                if (want != e.on)
                {
                    var em = e.ps.emission;
                    em.rateOverTime = want ? e.info.rate : 0f;
                    e.on = want;
                }
            }
        }

        /// <summary>One-shot bursts for the given trigger (Burst, Leap).</summary>
        public void Fire(EmitWhen when)
        {
            foreach (var e in list)
                if (e.ps != null && e.info.when == when && e.info.burst > 0) e.ps.Emit(e.info.burst);
        }

        /// <summary>A short-lived splash ring + spray at the water surface above (lat, lon).</summary>
        public static void Splash(CelestialBody body, double lat, double lon, float size)
        {
            try
            {
                var go = new GameObject("xeno_splash");
                go.transform.position = body.GetWorldSurfacePosition(lat, lon, 0.0);
                go.transform.rotation = Quaternion.FromToRotation(Vector3.forward, Geo.Up(body, go.transform.position));   // hemisphere emits along +Z
                var info = new EmitterInfo
                {
                    kind = "Splash", lifetime = 1.4f, speed = 3f + size * 0.4f, size = 0.35f + size * 0.08f, sizeGrow = 2.2f,
                    radius = Mathf.Max(0.2f, size * 0.25f), gravity = 0.6f, color = new Color(0.92f, 0.96f, 1f, 0.8f), colorEnd = new Color(1, 1, 1, 0)
                };
                var ps = Build(go, info);
                var sh = ps.shape;
                sh.shapeType = ParticleSystemShapeType.Hemisphere;
                ps.Emit(Mathf.Clamp((int)(20 + size * 6), 20, 160));
                Destroy(go, 4f);
            }
            catch (Exception ex) { XenoLog.Dbg("splash failed: " + ex.Message); }
        }
    }
}
