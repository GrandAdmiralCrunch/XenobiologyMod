using UnityEngine;

namespace Xenobiology
{
    /// <summary>3D positional calls for a creature (idle calls, alarm, attack, flyby screech...).</summary>
    public class CreatureAudio : MonoBehaviour
    {
        SoundInfo info;
        AudioSource src;
        System.Random rng;
        float idleTimer, stepTimer;
        CreatureController cc;

        public void Init(SoundInfo s, int seed)
        {
            info = s;
            rng = new System.Random(seed ^ 0x5eed);
            src = gameObject.AddComponent<AudioSource>();
            src.playOnAwake = false;
            src.spatialBlend = 1f;
            src.rolloffMode = AudioRolloffMode.Linear;
            src.minDistance = 4f;
            src.maxDistance = Mathf.Max(10f, s.range);
            src.dopplerLevel = 1f;
            idleTimer = (float)(rng.NextDouble() * s.idleInterval);
        }

        AudioClip Clip(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            AudioClip c = GameDatabase.Instance.GetAudioClip(path);
            if (c == null) XenoLog.Warn("Sound not found: " + path);
            return c;
        }

        public void Play(string path, float pitchJitter = 0.08f)
        {
            AudioClip c = Clip(path);
            if (c == null || src == null) return;
            src.pitch = info.pitch * (1f + (float)(rng.NextDouble() * 2 - 1) * pitchJitter);
            src.volume = Mathf.Clamp01(info.volume * GameSettings.SHIP_VOLUME);
            src.PlayOneShot(c);
        }

        public void OnState(CreatureState s)
        {
            switch (s)
            {
                case CreatureState.Alert: Play(info.alert); break;
                case CreatureState.Attack: Play(info.attack); break;
                case CreatureState.Flee: Play(info.flee); break;
                case CreatureState.Screech: Play(info.flyby, 0.12f); break;
                case CreatureState.Burrow: Play(info.dig); break;
                case CreatureState.Roar: Play(info.roar, 0.05f); break;
            }
        }

        void Update()
        {
            if (info == null) return;
            if (cc == null) cc = GetComponent<CreatureController>();
            Footsteps();
            if (string.IsNullOrEmpty(info.idle) || info.idleInterval <= 0f) return;
            idleTimer -= Time.deltaTime;
            if (idleTimer > 0f) return;
            idleTimer = info.idleInterval * (0.5f + (float)rng.NextDouble());
            if (cc != null && (cc.state == CreatureState.Sleep || cc.state == CreatureState.Underground)) return;
            Play(info.idle);
        }

        void Footsteps()
        {
            if (string.IsNullOrEmpty(info.footstep) || info.stepInterval <= 0f || cc == null || cc.def == null) return;
            float spd = Mathf.Abs(cc.speed);
            if (cc.airborne || spd < 0.3f || cc.state == CreatureState.Underground) { stepTimer = Mathf.Min(stepTimer, info.stepInterval * 0.3f); return; }
            float native = cc.def.model != null && cc.def.model.moveAnimSpeed > 0f ? cc.def.model.moveAnimSpeed : Mathf.Max(0.5f, cc.def.speed);
            stepTimer -= Time.deltaTime * Mathf.Clamp(spd / native, 0.3f, 2.5f);
            if (stepTimer > 0f) return;
            stepTimer = info.stepInterval;
            Play(info.footstep, 0.1f);
        }
    }

    /// <summary>A short-lived prop glued to the surface (e.g. the spoil heap left by a burrower).</summary>
    public class SurfaceProp : MonoBehaviour
    {
        CelestialBody body; double lat, lon, alt; float life, age;
        Vector3 baseScale;

        public static void SpawnMound(CelestialBody b, double lat, double lon, double ground, float radius, Color col, float life)
        {
            GameObject g = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Object.Destroy(g.GetComponent<Collider>());
            g.name = "XenoMound";
            g.GetComponent<Renderer>().sharedMaterial = XenoMaterials.Get(col, Color.black);
            var p = g.AddComponent<SurfaceProp>();
            p.body = b; p.lat = lat; p.lon = lon; p.alt = ground; p.life = life;
            p.baseScale = new Vector3(radius * 2.2f, radius * 0.7f, radius * 2.2f);
            g.transform.localScale = p.baseScale;
            p.LateUpdate();
        }

        void LateUpdate()
        {
            if (body == null) { Destroy(gameObject); return; }
            age += Time.deltaTime;
            if (age > life) { Destroy(gameObject); return; }
            float sink = Mathf.Clamp01((age - life * 0.7f) / (life * 0.3f));
            transform.position = body.GetWorldSurfacePosition(lat, lon, alt - baseScale.y * 0.25f - baseScale.y * 0.5f * sink);
            transform.rotation = Quaternion.FromToRotation(Vector3.up, body.GetSurfaceNVector(lat, lon));
        }
    }
}
