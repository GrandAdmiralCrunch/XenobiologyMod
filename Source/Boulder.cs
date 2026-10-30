using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// A thrown rock. A real rigidbody (so it can knock over and break parts) with gravity applied
    /// by hand, kept glued to the planet across floating-origin shifts. With projectileDamage off
    /// it is a trigger that only shoves what it hits.
    /// </summary>
    public class Boulder : MonoBehaviour
    {
        CelestialBody body;
        Rigidbody rb;
        ThrowInfo info;
        SoundInfo sounds;
        AudioSource src;
        Vector3d lastRel;
        float life;
        bool impacted, damage, stopped;
        string thrower;

        public static GameObject MakeRock(string name, float radius, Color col, int seed)
        {
            GameObject g = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            g.name = name;
            UnityEngine.Object.Destroy(g.GetComponent<Collider>());
            var rnd = new System.Random(seed);
            // lumpy: squash the sphere a little on random axes
            g.transform.localScale = new Vector3(1f + (float)rnd.NextDouble() * 0.25f, 0.8f + (float)rnd.NextDouble() * 0.2f, 1f + (float)rnd.NextDouble() * 0.15f) * radius * 2f;
            g.transform.localRotation = Quaternion.Euler((float)rnd.NextDouble() * 360f, (float)rnd.NextDouble() * 360f, 0f);
            g.GetComponent<Renderer>().sharedMaterial = XenoMaterials.Get(col, Color.black);
            return g;
        }

        /// <summary>Launch velocity that lands on target (+ its velocity * time of flight). Flat arc preferred.</summary>
        public static bool Solve(CelestialBody body, Vector3d from, Vector3d target, Vector3d targetVel, float speed, out Vector3 vel)
        {
            vel = Vector3.zero;
            Vector3 up = Geo.Up(body, from);
            float g = (float)FlightGlobals.getGeeForceAtPosition(from).magnitude;
            if (g < 0.01f) g = 9.81f;
            Vector3d aim = target;
            for (int iter = 0; iter < 3; iter++)
            {
                Vector3 d = (Vector3)(aim - from);
                float h = Vector3.Dot(d, up);
                Vector3 flat = d - up * h;
                float x = flat.magnitude;
                if (x < 1f) { vel = up * speed * 0.3f; return true; }
                float v2 = speed * speed;
                float disc = v2 * v2 - g * (g * x * x + 2f * h * v2);
                float ang = disc < 0f ? Mathf.PI / 4f : Mathf.Atan((v2 - Mathf.Sqrt(disc)) / (g * x));
                Vector3 dir = flat / x;
                vel = (dir * Mathf.Cos(ang) + up * Mathf.Sin(ang)) * speed;
                float t = x / Mathf.Max(1f, speed * Mathf.Cos(ang));
                aim = target + targetVel * t;
            }
            return true;
        }

        public static Boulder Launch(CelestialBody body, Vector3d from, Vector3 vel, ThrowInfo t, SoundInfo s, CreatureController owner)
        {
            GameObject g = MakeRock("XenoBoulder", t.radius, t.color, UnityEngine.Random.Range(0, 99999));
            g.transform.position = from;
            var col = g.AddComponent<SphereCollider>();
            col.radius = 0.5f;
            var b = g.AddComponent<Boulder>();
            b.body = body; b.info = t; b.sounds = s;
            b.thrower = owner != null ? owner.def.displayName : "something";
            b.damage = XenoSettings.ProjectileDamage;
            col.isTrigger = !b.damage;
            b.rb = g.AddComponent<Rigidbody>();
            b.rb.mass = Mathf.Max(0.1f, t.mass);
            b.rb.useGravity = false;
            b.rb.drag = 0f; b.rb.angularDrag = 0.3f;
            b.rb.interpolation = RigidbodyInterpolation.Interpolate;
            b.rb.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            b.rb.velocity = vel;
            b.rb.angularVelocity = UnityEngine.Random.insideUnitSphere * 3f;
            b.lastRel = from - body.position;
            if (s != null && !string.IsNullOrEmpty(s.impact))
            {
                b.src = g.AddComponent<AudioSource>();
                b.src.spatialBlend = 1f; b.src.rolloffMode = AudioRolloffMode.Linear; b.src.minDistance = 8f; b.src.maxDistance = Mathf.Max(100f, s.range);
                b.src.playOnAwake = false;
            }
            return b;
        }

        void FixedUpdate()
        {
            if (body == null || rb == null) { Destroy(gameObject); return; }
            float dt = Time.fixedDeltaTime;
            // floating origin moved the world but not us: snap back to where we belong relative to the planet
            Vector3d rel = (Vector3d)rb.position - body.position;
            if ((rel - lastRel).magnitude > rb.velocity.magnitude * dt * 3f + 20f)
            {
                rb.position = body.position + lastRel + (Vector3d)(rb.velocity * dt);
                transform.position = rb.position;
                rel = (Vector3d)rb.position - body.position;
            }
            lastRel = rel;
            if (!stopped) rb.AddForce(FlightGlobals.getGeeForceAtPosition(rb.position), ForceMode.Acceleration);
            life += dt;

            if (!damage && !stopped)
            {
                // trigger mode: no physical contact with the ground, so stop it ourselves
                double alt = body.GetAltitude(rb.position);
                double lat = body.GetLatitude(rb.position), lon = body.GetLongitude(rb.position);
                double ground = Math.Max(Geo.Terrain(body, lat, lon), body.ocean ? 0 : double.MinValue);
                if (alt < ground + info.radius * 0.6) { Impact(); stopped = true; rb.isKinematic = true; }
            }
            if (life > 30f || (stopped && life > 12f) || body.GetAltitude(rb.position) < -50) Destroy(gameObject);
        }

        void Impact()
        {
            if (impacted) return;
            impacted = true;
            if (src != null) { AudioClip c = GameDatabase.Instance.GetAudioClip(sounds.impact); if (c != null) { src.volume = Mathf.Clamp01(sounds.volume * GameSettings.SHIP_VOLUME); src.PlayOneShot(c); } }
            // everything nearby scatters
            var sp = XenoSpawner.Instance;
            if (sp != null)
                foreach (var c in sp.Creatures)
                    if (c != null && c.lair == null && !c.Ridden && (c.WorldPos - (Vector3d)rb.position).magnitude < 60)
                        c.Startle(Geo.Bearing(body, body.GetLatitude(rb.position), body.GetLongitude(rb.position), c.lat, c.lon));
        }

        void OnCollisionEnter(Collision c)
        {
            if (c.relativeVelocity.magnitude < 3f) return;
            Impact();
            Part p = c.collider != null ? c.collider.GetComponentInParent<Part>() : null;
            if (p != null && p.vessel != null && p.vessel.isEVA && c.relativeVelocity.magnitude > 8f)
                ScreenMessages.PostScreenMessage(string.Format("<color=#FFB060>{0} was flattened by a boulder hurled by the {1}!</color>", p.vessel.vesselName, thrower), 5f, ScreenMessageStyle.UPPER_CENTER);
        }

        void OnTriggerEnter(Collider other)
        {
            if (damage || stopped) return;
            Part p = other.GetComponentInParent<Part>();
            if (p == null || p.vessel == null) return;
            Impact();
            Vector3 push = rb.velocity.normalized * Mathf.Min(12f, rb.velocity.magnitude * 0.35f);
            foreach (Part q in p.vessel.parts) if (q.Rigidbody != null) q.Rigidbody.AddForce(push, ForceMode.VelocityChange);
            rb.velocity *= 0.3f;
            if (p.vessel.isEVA) ScreenMessages.PostScreenMessage(string.Format("<color=#FFB060>{0} was bowled over by a boulder!</color>", p.vessel.vesselName), 4f, ScreenMessageStyle.UPPER_CENTER);
        }
    }
}
