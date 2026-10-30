using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Life in the water around an underwater lair, while the camera is under the surface nearby:
    ///  - marine snow: slow, pale specks drifting around the camera (depth and parallax, the reef stops feeling like a set);
    ///  - at night, plankton that flash blue-green when disturbed: the active vessel (a swimming kerbal, a sub) leaves a
    ///    trail of sparks, densest when it moves fast.
    /// Both systems simulate in world space (so the specks stay put as the camera moves) and are re-centred cheaply;
    /// they stop entirely when the camera is above water or far away.
    /// </summary>
    public class ReefAmbience : MonoBehaviour
    {
        LairInstance lair;
        ParticleSystem snow, sparks;
        Transform snowT, sparkT;
        float timer;
        bool snowOn, sparksOn;
        const float Range = 450f;

        public void Init(LairInstance l)
        {
            lair = l;
            snow = Make("xeno_marinesnow", false, out snowT);
            var m = snow.main; m.startLifetime = new ParticleSystem.MinMaxCurve(10f, 18f); m.startSpeed = new ParticleSystem.MinMaxCurve(0.02f, 0.1f);
            m.startSize = new ParticleSystem.MinMaxCurve(0.015f, 0.05f); m.startColor = new Color(0.85f, 0.9f, 0.85f, 0.55f); m.maxParticles = 900;
            m.gravityModifier = 0.002f;
            var sh = snow.shape; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(36f, 22f, 36f);
            var nz = snow.noise; nz.enabled = true; nz.strength = 0.08f; nz.frequency = 0.15f; nz.scrollSpeed = 0.05f;
            var col = snow.colorOverLifetime; col.enabled = true;
            var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(0.55f, 0.15f), new GradientAlphaKey(0.55f, 0.85f), new GradientAlphaKey(0, 1) });
            col.color = g;

            sparks = Make("xeno_plankton", true, out sparkT);
            m = sparks.main; m.startLifetime = new ParticleSystem.MinMaxCurve(1.2f, 2.6f); m.startSpeed = new ParticleSystem.MinMaxCurve(0f, 0.15f);
            m.startSize = new ParticleSystem.MinMaxCurve(0.03f, 0.08f); m.startColor = new Color(0.35f, 1f, 0.85f, 1f); m.maxParticles = 600;
            sh = sparks.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 0.9f;
            nz = sparks.noise; nz.enabled = true; nz.strength = 0.15f; nz.frequency = 0.8f;
            col = sparks.colorOverLifetime; col.enabled = true;
            g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(new Color(0.6f, 1f, 0.95f), 0), new GradientColorKey(new Color(0.1f, 0.6f, 1f), 1) },
                new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0.7f, 0.3f), new GradientAlphaKey(0, 1) });
            col.color = g;
        }

        static Material snowMat, sparkMat;
        ParticleSystem Make(string name, bool additive, out Transform t)
        {
            var go = new GameObject(name);
            t = go.transform;
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.playOnAwake = false; main.loop = true; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var em = ps.emission; em.rateOverTime = 0f;
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            if (additive)
            {
                if (sparkMat == null)
                {
                    sparkMat = new Material(Shader.Find("KSP/Particles/Additive") ?? Shader.Find("Legacy Shaders/Particles/Additive"));
                    sparkMat.mainTexture = Dot();
                }
                r.sharedMaterial = sparkMat;
            }
            else
            {
                if (snowMat == null)
                {
                    snowMat = new Material(Shader.Find("KSP/Particles/Alpha Blended") ?? Shader.Find("Legacy Shaders/Particles/Alpha Blended"));
                    snowMat.mainTexture = Dot();
                }
                r.sharedMaterial = snowMat;
            }
            ps.Play();
            return ps;
        }

        static Texture2D dot;
        internal static Texture2D Dot()
        {
            if (dot != null) return dot;
            const int N = 32;
            dot = new Texture2D(N, N, TextureFormat.RGBA32, true);
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float dx = (x + 0.5f) / N * 2 - 1, dy = (y + 0.5f) / N * 2 - 1;
                    float a = Mathf.Pow(Mathf.Clamp01(1f - Mathf.Sqrt(dx * dx + dy * dy)), 2f);
                    dot.SetPixel(x, y, new Color(1, 1, 1, a));
                }
            dot.wrapMode = TextureWrapMode.Clamp; dot.Apply(true);
            return dot;
        }

        void LateUpdate()
        {
            Camera cam = FlightCamera.fetch != null ? FlightCamera.fetch.mainCamera : null;
            Vessel v = FlightGlobals.ActiveVessel;
            if (cam == null || lair == null || lair.body == null) return;
            timer -= Time.deltaTime;
            Vector3 cp = cam.transform.position;
            if (timer <= 0f)
            {
                timer = 0.5f;
                double camAlt = FlightGlobals.getAltitudeAtPos(cp, lair.body);
                bool near = (transform.position - cp).magnitude < Range;
                bool under = camAlt < -0.5;
                SetRate(snow, ref snowOn, near && under, 70f);
                bool night = !Geo.IsDaylight(lair.body, lair.lat, lair.lon);
                sparksOn = near && night && v != null && v.altitude < -0.5;
                if (!sparksOn) { var e = sparks.emission; e.rateOverTime = 0f; }
            }
            if (snowOn) snowT.position = cp;
            if (sparksOn && v != null)
            {
                sparkT.position = v.CoM;
                float spd = (float)v.srf_velocity.magnitude;
                var e = sparks.emission; e.rateOverTime = Mathf.Clamp(spd * 60f, 0f, 220f);
            }
        }

        static void SetRate(ParticleSystem ps, ref bool on, bool want, float rate)
        {
            if (on == want) return;
            on = want;
            var e = ps.emission; e.rateOverTime = want ? rate : 0f;
        }

        void OnDestroy()
        {
            if (snow != null) Destroy(snow.gameObject);
            if (sparks != null) Destroy(sparks.gameObject);
        }
    }
}
